import json
import logging
import os
import re
import sys
import threading
import time
import unicodedata
from logging.handlers import RotatingFileHandler
import webview
import ollama
import config
from percepcion import escuchar_y_transcribir, esperar_palabra_activacion, MicrofonoNoDisponible
from cerebro import procesar_pensamiento, procesar_pensamiento_stream
from voz import reproducir_voz, extraer_frases, reproducir_frases_streaming
from herramientas import (
    obtener_estado_sistema,
    obtener_temperatura,
    abrir_aplicacion,
    obtener_clima,
    consultar_boveda,
)
from memoria import guardar_nota, buscar_nota
from memoria_rag import construir_indice, obtener_cantidad_fragmentos
from interfaz import ControladorPanel, InterfazAPI, WebViewLogHandler
from metricas import medir, CronometroTurno
from comandos import es_comando, COMANDOS_SALIDA, COMANDOS_REINICIO
from atajos import resolver_atajo
from config import (
    MODELO_WHISPER,
    PALABRA_ACTIVACION,
    PHRASE_TIME_LIMIT,
    SYSTEM_PROMPT,
    TIEMPO_MAXIMO_ESCUCHA,
    MAX_RONDAS_TOOLS,
    configurar_utf8,
)

configurar_utf8()

os.makedirs("logs", exist_ok=True)
_fmt = logging.Formatter("%(asctime)s %(levelname)s - %(message)s")
_handler_consola = logging.StreamHandler()
_handler_consola.setFormatter(_fmt)
_handler_archivo = RotatingFileHandler(
    "logs/jinx.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
)
_handler_archivo.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_handler_consola, _handler_archivo])

# Instancia global del controlador de UI.
# panel.ventana se asigna desde __main__ después de create_window().
panel = ControladorPanel()
detener = threading.Event()

FUNCIONES_DISPONIBLES = {
    "obtener_estado_sistema": obtener_estado_sistema,
    "obtener_temperatura": obtener_temperatura,
    "abrir_aplicacion": abrir_aplicacion,
    "guardar_nota": guardar_nota,
    "buscar_nota": buscar_nota,
    "obtener_clima": obtener_clima,
    "consultar_boveda": consultar_boveda,
}

def normalizar(texto: str) -> str:
    """
    Pasa el texto a minúsculas, quita tildes (NFD sin categoría 'Mn'),
    elimina signos de puntuación y colapsa espacios múltiples.
    """
    if not texto:
        return ""
    texto = texto.lower()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def _extraer_llamada(tool_call) -> tuple:
    if isinstance(tool_call, dict):
        funcion = tool_call.get("function", {})
        nombre = funcion.get("name", "")
        argumentos = funcion.get("arguments", {}) or {}
    else:
        funcion = getattr(tool_call, "function", None)
        nombre = getattr(funcion, "name", "") if funcion else ""
        argumentos = getattr(funcion, "arguments", {}) if funcion else {}

    if isinstance(argumentos, str):
        try:
            argumentos = json.loads(argumentos) if argumentos else {}
        except json.JSONDecodeError:
            argumentos = {}
    if not isinstance(argumentos, dict):
        argumentos = {}
    return nombre, argumentos

def ejecutar_herramienta(nombre: str, argumentos: dict) -> str:
    funcion = FUNCIONES_DISPONIBLES.get(nombre)
    if funcion is None:
        return f"Herramienta no permitida: {nombre}"
    try:
        return str(funcion(**argumentos))
    except TypeError as e:
        return f"Argumentos inválidos para {nombre}: {e}"
    except Exception:
        import logging
        logging.exception("Fallo en %s", nombre)
        return f"Error al ejecutar {nombre}."


_ejecutar_herramienta = ejecutar_herramienta


def ejecutar_turno_streaming(
    texto_usuario: str,
    contexto: list,
    tiempos: dict,
    cronometro,
    panel=None,
) -> str:
    """
    Turno completo con streaming en tiempo real (F2-02, optimizado).

    Flujo de rondas
    ───────────────
    1. Solicita un stream a procesar_pensamiento_stream(contexto).
    2. Lee el primer chunk para decidir el modo de la ronda:
       a) tool_calls  → acumula todo el stream sin hablar, ejecuta herramientas
                        y repite la ronda (hasta MAX_RONDAS_TOOLS).
       b) texto       → crea un generador en vivo que emite el primer fragmento
                        ya recibido y sigue consumiendo el stream en tiempo real,
                        acumulando partes simultáneamente para reconstruir
                        texto_final. El generador alimenta directamente a
                        extraer_frases() → reproducir_frases_streaming() sin
                        esperar al final del stream de Ollama.
       c) _error      → devuelve mensaje de error sin hablar.

    Garantiza que config.STREAMING=False nunca llega aquí.
    """
    # ── Atajo rápido (misma lógica que el modo normal) ────────────────────────
    if config.ATAJOS:
        atajo = resolver_atajo(texto_usuario)
        if atajo:
            nombre_tool, args = atajo
            logging.info("[STR] Atajo detectado: %s", nombre_tool)
            if panel:
                panel.actualizar_satelite(3, 2, "Ejecutando Tool", nombre_tool)
            resultado = ejecutar_herramienta(nombre_tool, args)
            contexto.append({"role": "assistant", "content": f"Ejecutando orden directa: {nombre_tool}"})
            tiempos["llm"] = 0
            return resultado

    texto_final = ""
    rondas = 0

    while rondas <= config.MAX_RONDAS_TOOLS:

        stream = procesar_pensamiento_stream(contexto)

        # ── Leer el primer chunk para decidir el modo de la ronda ─────────────
        try:
            primer_chunk = next(iter(stream))
        except StopIteration:
            # Stream vacío inesperado
            break

        # Caso error
        if primer_chunk.get("_error"):
            msg = primer_chunk.get("message") or {}
            texto_final = msg.get("content") or "No pude pensar eso ahora. Revisa que Ollama esté corriendo."
            break

        primer_msg = primer_chunk.get("message") or {}
        primer_content = primer_msg.get("content") or ""
        primer_tc = primer_msg.get("tool_calls")

        # ── Caso tool_calls: acumular sin hablar ──────────────────────────────
        if primer_tc:
            tool_calls_acum = list(primer_tc)
            content_acum = [primer_content]
            for chunk in stream:
                if chunk.get("_error"):
                    break
                msg = chunk.get("message") or {}
                content_acum.append(msg.get("content") or "")
                tc = msg.get("tool_calls")
                if tc:
                    tool_calls_acum.extend(tc)

            contenido_texto = "".join(content_acum).strip()
            msg_asistente = {"role": "assistant", "content": contenido_texto, "tool_calls": tool_calls_acum}
            contexto.append(msg_asistente)
            for tc in tool_calls_acum:
                nombre, args = _extraer_llamada(tc)
                if panel:
                    panel.actualizar_satelite(3, 2, "Ejecutando Tool", nombre)
                resultado_tool = ejecutar_herramienta(nombre, args)
                contexto.append({"role": "tool", "tool_name": nombre, "content": resultado_tool})
            rondas += 1
            continue

        # ── Caso texto: generador en vivo → TTS en tiempo real ───────────────
        # partes_texto acumula los fragmentos para reconstruir texto_final
        # sin bloquear el flujo al TTS.
        partes_texto = []
        tool_calls_tardios = []  # Por si tool_calls llega en medio del texto

        def _generador_texto():
            """
            Generador en vivo que emite el primer chunk ya leído y luego
            sigue consumiendo el stream de Ollama chunk a chunk, acumulando
            en partes_texto. Si aparece un tool_call tardío, lo guarda en
            tool_calls_tardios y corta la emisión de texto.
            """
            # Emitir el primer fragmento de texto ya leído
            if primer_content:
                partes_texto.append(primer_content)
                yield primer_content

            for chunk in stream:
                if chunk.get("_error"):
                    break
                msg = chunk.get("message") or {}
                content = msg.get("content") or ""
                tc = msg.get("tool_calls")
                if tc:
                    # Tool call tardío: cortar emisión de texto y guardarlo
                    tool_calls_tardios.extend(tc)
                    break
                if content:
                    partes_texto.append(content)
                    yield content

        frases_iter = extraer_frases(_generador_texto())
        with medir("tts", tiempos):
            reproducir_frases_streaming(
                frases_iter,
                on_start=cronometro.marcar_primer_audio,
            )

        texto_final = "".join(partes_texto).strip() or "Listo."

        if tool_calls_tardios:
            # Hubo tool_calls en medio del stream: guardar y procesar otra ronda
            contexto.append({"role": "assistant", "content": texto_final, "tool_calls": tool_calls_tardios})
            for tc in tool_calls_tardios:
                nombre, args = _extraer_llamada(tc)
                if panel:
                    panel.actualizar_satelite(3, 2, "Ejecutando Tool", nombre)
                resultado_tool = ejecutar_herramienta(nombre, args)
                contexto.append({"role": "tool", "tool_name": nombre, "content": resultado_tool})
            rondas += 1
            continue

        # Ronda de texto limpia: guardar en contexto y terminar
        contexto.append({"role": "assistant", "content": texto_final})
        break

    return texto_final or "Listo."


def ejecutar_turno(contexto: list) -> str:
    texto_reconocido = ""
    for msg in reversed(contexto):
        if msg.get("role") == "user":
            texto_reconocido = msg.get("content") or ""
            break
    if config.ATAJOS:
        atajo = resolver_atajo(texto_reconocido)
        if atajo:
            nombre_tool, args = atajo
            logging.info("Atajo detectado: %s", nombre_tool)
            resultado = ejecutar_herramienta(nombre_tool, args)
            contexto.append({"role": "assistant", "content": f"Ejecutando orden directa: {nombre_tool}"})
            return resultado

    respuesta = procesar_pensamiento(contexto)
    if not respuesta.get("_error"):
        contexto.append(respuesta)

    rondas = 0
    while respuesta.get("tool_calls") and rondas < config.MAX_RONDAS_TOOLS:
        for tc in respuesta["tool_calls"]:
            nombre, args = _extraer_llamada(tc)
            resultado = ejecutar_herramienta(nombre, args)
            # F1-11: Asegurar que se envía tool_name
            contexto.append({"role": "tool", "tool_name": nombre, "content": resultado})

        respuesta = procesar_pensamiento(contexto)
        if not respuesta.get("_error"):
            contexto.append(respuesta)
        rondas += 1

    texto_final = (respuesta.get("content") or "").strip() or "Listo."
    return texto_final

def bucle_voz_secundario(detener: threading.Event = None, panel=None, api_js=None):
    if detener is None:
        detener = threading.Event()
    if panel is None:
        from interfaz import panel as panel_instancia
        panel = panel_instancia

    logging.info("Jinx Asistente arrancado. Di 'salir', 'apagar' o 'detener' para cerrar.")

    # ── Fase 4 / F2-07: construir el índice RAG en segundo plano (hilo daemon) ──
    # Se lanza antes del bucle de voz para que el micrófono arranque de inmediato.
    # Si el usuario habla mientras el índice aún se construye, buscar_semantica()
    # devuelve "Sigo preparando mis notas, dame un momento." sin bloquear.
    def _construir_indice_bg():
        logging.info("[RAG] Cargando bóveda de Obsidian en segundo plano...")
        construir_indice(panel=panel)
        logging.info("[RAG] Índice listo en segundo plano.")
        cantidad = obtener_cantidad_fragmentos()
        if panel:
            panel.actualizar_satelite(3, 3, "Memoria RAG", f"{cantidad} fragmentos listos")

    threading.Thread(target=_construir_indice_bg, daemon=True, name="rag-indexer").start()

    contexto = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Conectar el contexto mutable a la API inversa para Emergency Flush
    if api_js is not None:
        api_js.contexto = contexto

    fallos_micro = 0
    while not detener.is_set():
        try:
            # ── Estado 1: Centinela — esperando wake word ──
            panel.actualizar_estado(1)
            if panel:
                panel.actualizar_satelite(2, 1, "Transcriptor", "En reposo")
                panel.actualizar_satelite(2, 2, "Buffer Audio", "Vacío")
                panel.actualizar_satelite(3, 2, "Herramientas", "Ninguna activa")
            logging.info("Esperando palabra de activación 'Jinx'...")
            try:
                activado = esperar_palabra_activacion(PALABRA_ACTIVACION, evento_apagar=detener, panel=panel)
            except MicrofonoNoDisponible as e:
                fallos_micro += 1
                logging.error("[MICRO] Fallo de micrófono (#%d): %s", fallos_micro, e)
                if fallos_micro >= 5:
                    reproducir_voz("Fallo de micrófono. Me apago.")
                    detener.set()
                    break
                time.sleep(min(2 ** fallos_micro, 30))
                continue
            fallos_micro = 0  # éxito → reiniciar contador
            if not activado:
                if detener.is_set():
                    break
                continue

            # Capturamos el tiempo de inicio del turno completo
            inicio_turno = time.time()
            tiempos: dict = {}

            # F2-06: Cronómetro de alta precisión para TTFA y duración total
            cronometro = CronometroTurno()
            cronometro.t_inicio_turno = time.perf_counter()

            logging.info("¡Despierta!")
            reproducir_voz("Dime")
            time.sleep(0.3)

            # ── Estado 2: Transcripción — Whisper procesando audio ──
            panel.actualizar_estado(2)
            logging.info("Escuchando tu comando...")
            with medir("stt", tiempos):
                texto_usuario = escuchar_y_transcribir(
                    modelo=MODELO_WHISPER,
                    tiempo_maximo=TIEMPO_MAXIMO_ESCUCHA,
                    phrase_time_limit=PHRASE_TIME_LIMIT,
                    panel=panel,
                )
            # F2-06: El usuario terminó de hablar → referencia para calcular TTFA
            cronometro.marcar_fin_usuario()

            if texto_usuario and texto_usuario.strip():
                texto_reconocido = texto_usuario.strip()

                if es_comando(texto_reconocido, COMANDOS_SALIDA):
                    logging.info("Cerrando asistente Jinx...")
                    reproducir_voz("Hasta luego.")
                    detener.set()
                    break

                if es_comando(texto_reconocido, COMANDOS_REINICIO):
                    logging.info("Reiniciando memoria de conversación...")
                    contexto = [{"role": "system", "content": SYSTEM_PROMPT}]
                    # Reasignar la nueva lista al api_js para que Emergency Flush siga operativo
                    if api_js is not None:
                        api_js.contexto = contexto
                    reproducir_voz("Memoria borrada. ¿De qué hablamos ahora?")
                    time.sleep(0.8)
                    continue

                # ── Estado 3: El Núcleo — llamada a Ollama/herramientas ──
                panel.actualizar_estado(3)
                panel.actualizar_satelite(3, 1, "Inferencia", "Generando respuesta...")
                logging.info('Procesando respuesta para: "%s"...', texto_reconocido)
                contexto.append({"role": "user", "content": texto_reconocido})

                # Recortar el historial manteniendo siempre el mensaje de sistema (índice 0)
                # y las últimas 16 entradas del historial de conversación.
                # Si el punto de corte cae sobre un mensaje 'tool', se retrocede hasta incluir
                # el 'assistant' con tool_calls que lo originó, para no romper el par.
                cola = contexto[1:][-16:]
                while cola and cola[0].get("role") == "tool":
                    cola = cola[1:]
                contexto = [contexto[0]] + cola
                if panel:
                    panel.actualizar_satelite(3, 1, "Contexto RAM", f"{len(contexto)} mensajes")
                if api_js is not None:
                    api_js.contexto = contexto

                # ── Bifurcación streaming / clásico (F2-02) ──────────────────
                if config.STREAMING:
                    # Modo streaming: LLM + TTS por frases en paralelo
                    panel.actualizar_estado(3)
                    panel.actualizar_satelite(3, 1, "Inferencia", "Streaming...")
                    with medir("llm", tiempos):
                        texto_final = ejecutar_turno_streaming(
                            texto_reconocido, contexto, tiempos, cronometro, panel
                        )
                    cronometro.finalizar_turno()
                    logging.info("Respuesta Jinx [STR]: %s", texto_final)
                    # El panel se actualiza con TTFA ya calculado por marcar_primer_audio
                    ttfa_display = int(cronometro.ttfa_ms) if cronometro.ttfa_ms > 0 else int((time.time() - inicio_turno) * 1000)
                    panel.actualizar_respuesta(texto_final, ttfa_display)

                else:
                    # Modo clásico: LLM completo → TTS completo (comportamiento original intacto)
                    atajo = resolver_atajo(texto_reconocido) if config.ATAJOS else None
                    if atajo:
                        nombre_tool, args = atajo
                        logging.info("Atajo detectado: %s", nombre_tool)
                        if panel:
                            panel.actualizar_satelite(3, 2, "Ejecutando Tool", nombre_tool)
                        resultado = ejecutar_herramienta(nombre_tool, args)
                        contexto.append({"role": "assistant", "content": f"Ejecutando orden directa: {nombre_tool}"})
                        texto_final = resultado
                        tiempos["llm"] = 0
                    else:
                        with medir("llm", tiempos):
                            respuesta = procesar_pensamiento(contexto)
                            if not respuesta.get("_error"):
                                contexto.append(respuesta)

                            rondas = 0
                            while respuesta.get("tool_calls") and rondas < config.MAX_RONDAS_TOOLS:
                                for tc in respuesta["tool_calls"]:
                                    nombre, args = _extraer_llamada(tc)
                                    if panel:
                                        panel.actualizar_satelite(3, 2, "Ejecutando Tool", nombre)
                                    resultado = ejecutar_herramienta(nombre, args)
                                    # F1-11: Asegurar que se envía tool_name
                                    contexto.append({"role": "tool", "tool_name": nombre, "content": resultado})

                                respuesta = procesar_pensamiento(contexto)
                                if not respuesta.get("_error"):
                                    contexto.append(respuesta)
                                rondas += 1

                            texto_final = (respuesta.get("content") or "").strip() or "Listo."

                    # F1-13: Mostrar texto en el panel UI antes de reproducir TTS
                    latencia_ms = int((time.time() - inicio_turno) * 1000)
                    panel.actualizar_respuesta(texto_final, latencia_ms)

                    logging.info("Respuesta Jinx: %s", texto_final)

                    # ── Estado 4: Síntesis — TTS generando y reproduciendo audio ──
                    panel.actualizar_estado(4)
                    panel.actualizar_satelite(4, 1, "Síntesis TTS", "Procesando audio")
                    if panel:
                        panel.actualizar_satelite(4, 2, "Pygame Mixer", "Reproduciendo audio...")
                    logging.info("Jinx respondiendo con voz...")
                    with medir("tts", tiempos):
                        # F2-06: on_start dispara marcar_primer_audio() justo antes del primer sample
                        reproducir_voz(texto_final, on_start=cronometro.marcar_primer_audio)
                    if panel:
                        panel.actualizar_satelite(4, 2, "Pygame Mixer", "En espera")
                    # F2-06: Turno terminado (incluye TTS completo)
                    cronometro.finalizar_turno()
                time.sleep(0.8)  # Purga el buffer del micrófono y evita captura de eco


                # ── Estado 5: Completado — turno finalizado ──
                latencia_ms = int((time.time() - inicio_turno) * 1000)
                panel.actualizar_estado(5)
                # F2-06: Mostrar TTFA como latencia principal en el panel
                ttfa_display = int(cronometro.ttfa_ms) if cronometro.ttfa_ms > 0 else latencia_ms
                panel.actualizar_respuesta(texto_final, ttfa_display)
                # F2-06: Añadir métricas honestas al diccionario de telemetría
                tiempos["ttfa"] = cronometro.ttfa_ms
                tiempos["total"] = cronometro.turno_ms
                logging.info(
                    "[METRICA_HONESTA] TTFA: %.0f ms | Turno total: %.0f ms",
                    cronometro.ttfa_ms,
                    cronometro.turno_ms,
                )
                logging.info("[TURNO] %s", {k: round(v) for k, v in tiempos.items()})
                if panel:
                    panel.actualizar_tiempos(tiempos)

                # Latido del pipeline - Reset visual
                if panel:
                    panel.actualizar_satelite(2, 1, "Transcriptor", "En reposo")
                    panel.actualizar_satelite(2, 2, "Buffer Audio", "Vacío")
                    panel.actualizar_satelite(3, 2, "Herramientas", "Ninguna activa")
            else:
                logging.info("No se detectó ninguna instrucción clara. Reintentando...")
                if panel:
                    panel.actualizar_satelite(2, 1, "Transcriptor", "En reposo")
                    panel.actualizar_satelite(2, 2, "Buffer Audio", "Vacío")
                    panel.actualizar_satelite(3, 2, "Herramientas", "Ninguna activa")
                continue

        except KeyboardInterrupt:
            logging.info("Cerrando asistente Jinx...")
            detener.set()
            break
        except Exception as e:
            logging.error("Ocurrió un error en el ciclo principal: %s", e)
            time.sleep(2)

    # Apagado limpio: destruir la ventana si todavía existe
    try:
        if panel and getattr(panel, "ventana", None):
            panel.ventana.destroy()
    except Exception:
        pass


def verificar_ollama(modelo: str = config.MODELO_LLM) -> None:
    try:
        instalados = {m.model for m in ollama.list().models}
    except Exception as e:
        raise RuntimeError("Ollama no responde. Ábrelo y reintenta.") from e
    if not any(n.startswith(modelo) for n in instalados):
        raise RuntimeError(f"Falta el modelo. Ejecuta: ollama pull {modelo}")


if __name__ == "__main__":
    verificar_ollama()
    # Holder mutable compartido entre el hilo de voz y la API inversa.
    # El hilo asigna holder[0] cuando inicializa el contexto;
    # InterfazAPI.limpiar_memoria_ui() lo limpia vía api_js.contexto.
    api_js = InterfazAPI()

    hilo_voz = threading.Thread(target=bucle_voz_secundario, args=(detener, panel, api_js), daemon=True)
    hilo_voz.start()

    ventana = webview.create_window(
        'SENTINEL // PIPELINE GRAPH',
        'panel_sentinel.html',
        width=1760,
        height=900,
        js_api=api_js,
    )
    # Asegurarnos de que el logger raíz envíe datos a la UI
    handler_ui = WebViewLogHandler(ventana)
    handler_ui.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler_ui)

    # Al cerrar la ventana con la 'X', el hilo de voz también para
    ventana.events.closed += detener.set
    # Conecta el controlador de UI con la ventana nativa
    panel.ventana = ventana
    webview.start()
