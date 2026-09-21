import json
import logging
import re
import sys
import threading
import time
import unicodedata
import webview
import config
from percepcion import escuchar_y_transcribir, esperar_palabra_activacion
from cerebro import procesar_pensamiento, ErrorLLM
from voz import reproducir_voz
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
from config import (
    MODELO_WHISPER,
    PALABRA_ACTIVACION,
    PHRASE_TIME_LIMIT,
    SYSTEM_PROMPT,
    TIEMPO_MAXIMO_ESCUCHA,
    COMANDOS_SALIDA,
    FRASES_REINICIO,
    MAX_RONDAS_TOOLS,
    configurar_consola,
)

configurar_consola()

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# Instancia global del controlador de UI.
# panel.ventana se asigna desde __main__ después de create_window().
panel = ControladorPanel()
evento_apagar = threading.Event()

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

def _ejecutar_herramienta(nombre_fn: str, argumentos: dict) -> str:
    logging.info("Herramienta solicitada: %s %s", nombre_fn, argumentos)
    if panel:
        panel.actualizar_satelite(3, 2, "Ejecutando Tool", nombre_fn)
    funcion = FUNCIONES_DISPONIBLES.get(nombre_fn)
    try:
        if funcion is None:
            resultado = f"Herramienta no permitida: {nombre_fn}"
        else:
            resultado = str(funcion(**argumentos))
    except Exception as e:
        logging.error("Error al ejecutar %s: %s", nombre_fn, e)
        resultado = f"Error al ejecutar {nombre_fn}: {e}"
    logging.info("Resultado: %s", resultado)
    return resultado

def ejecutar_turno(contexto: list) -> str:
    respuesta = {}
    for ronda in range(config.MAX_RONDAS_TOOLS):
        ultima = (ronda == config.MAX_RONDAS_TOOLS - 1)
        respuesta = procesar_pensamiento(contexto, usar_tools=not ultima)
        contexto.append(respuesta)
        tool_calls = respuesta.get("tool_calls")
        if tool_calls:
            for tool_call in tool_calls:
                nombre_fn, argumentos = _extraer_llamada(tool_call)
                resultado = _ejecutar_herramienta(nombre_fn, argumentos)
                resultado_seguro = f"<datos_herramienta nombre='{nombre_fn}'>\n{str(resultado)[:1500]}\n</datos_herramienta>"
                contexto.append({"role": "tool", "content": resultado_seguro})
            if panel:
                panel.actualizar_satelite(3, 1, "Inferencia", "Sintetizando razonamiento...")
                panel.actualizar_satelite(3, 2, "qwen2.5:3b", "Tool completada")
        else:
            break

    texto_final = (respuesta.get("content") or "").strip()
    if not texto_final:
        texto_final = "No pude completar eso."
        if respuesta.get("role") == "assistant" and not respuesta.get("content"):
            respuesta["content"] = texto_final
    return texto_final

def bucle_voz_secundario(evento_apagar: threading.Event = None, panel=None, api_js=None):
    if evento_apagar is None:
        evento_apagar = threading.Event()
    if panel is None:
        from interfaz import panel as panel_instancia
        panel = panel_instancia

    logging.info("Jinx Asistente - asistente de voz local")
    logging.info("Di 'salir', 'cancelar', 'apagar', 'detener' o presiona Ctrl+C para salir.")

    # ── Fase 4: construir el índice RAG una sola vez al arrancar ──
    logging.info("[RAG] Cargando bóveda de Obsidian en memoria...")
    construir_indice(panel=panel)
    cantidad = obtener_cantidad_fragmentos()
    if panel:
        panel.actualizar_satelite(3, 3, "Memoria RAG", f"{cantidad} fragmentos listos")
    logging.info("[RAG] Bóveda lista para consultas.")

    contexto = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Conectar el contexto mutable a la API inversa para Emergency Flush
    if api_js is not None:
        api_js.contexto = contexto

    while not evento_apagar.is_set():
        try:
            # ── Estado 1: Centinela — esperando wake word ──
            panel.actualizar_estado(1)
            if panel:
                panel.actualizar_satelite(2, 1, "Transcriptor", "En reposo")
                panel.actualizar_satelite(2, 2, "Buffer Audio", "Vacío")
                panel.actualizar_satelite(3, 2, "Herramientas", "Ninguna activa")
            logging.info("Esperando palabra de activación 'Jinx'...")
            activado = esperar_palabra_activacion(PALABRA_ACTIVACION, evento_apagar=evento_apagar, panel=panel)
            if not activado:
                if evento_apagar.is_set():
                    break
                continue

            # Capturamos el tiempo de inicio del turno completo
            inicio_turno = time.time()

            logging.info("¡Despierta!")
            reproducir_voz("Dime")
            time.sleep(0.3)

            # ── Estado 2: Transcripción — Whisper procesando audio ──
            panel.actualizar_estado(2)
            logging.info("Escuchando tu comando...")
            texto_usuario = escuchar_y_transcribir(
                modelo=MODELO_WHISPER,
                tiempo_maximo=TIEMPO_MAXIMO_ESCUCHA,
                phrase_time_limit=PHRASE_TIME_LIMIT,
                panel=panel,
            )

            if texto_usuario and texto_usuario.strip():
                texto_reconocido = texto_usuario.strip()

                if normalizar(texto_reconocido) in config.COMANDOS_SALIDA:
                    logging.info("Cerrando asistente Jinx...")
                    reproducir_voz("Hasta luego, apagando sistema.")
                    evento_apagar.set()
                    try:
                        if panel and getattr(panel, "ventana", None):
                            panel.ventana.destroy()
                    except Exception:
                        pass
                    break

                if normalizar(texto_reconocido) in config.FRASES_REINICIO:
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

                n_previo = len(contexto)
                try:
                    texto_final = ejecutar_turno(contexto)
                except ErrorLLM:
                    del contexto[n_previo:]
                    texto_final = "No puedo pensar ahora mismo, revisa que Ollama esté corriendo."

                logging.info("Respuesta Jinx: %s", texto_final)

                # ── Estado 4: Síntesis — TTS generando y reproduciendo audio ──
                panel.actualizar_estado(4)
                panel.actualizar_satelite(4, 1, "Síntesis TTS", "Procesando audio")
                if panel:
                    panel.actualizar_satelite(4, 2, "Pygame Mixer", "Reproduciendo audio...")
                logging.info("Jinx respondiendo con voz...")
                reproducir_voz(texto_final)
                if panel:
                    panel.actualizar_satelite(4, 2, "Pygame Mixer", "En espera")
                time.sleep(0.8)  # Purga el buffer del micrófono y evita captura de eco

                # ── Estado 5: Completado — turno finalizado ──
                latencia_ms = int((time.time() - inicio_turno) * 1000)
                panel.actualizar_estado(5)
                panel.actualizar_respuesta(texto_final, latencia_ms)

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
            evento_apagar.set()
            try:
                if panel and getattr(panel, "ventana", None):
                    panel.ventana.destroy()
            except Exception:
                pass
            break
        except Exception as e:
            logging.error("Ocurrió un error en el ciclo principal: %s", e)
            time.sleep(2)

if __name__ == "__main__":
    # Holder mutable compartido entre el hilo de voz y la API inversa.
    # El hilo asigna holder[0] cuando inicializa el contexto;
    # InterfazAPI.limpiar_memoria_ui() lo limpia vía api_js.contexto.
    api_js = InterfazAPI()

    hilo_voz = threading.Thread(target=bucle_voz_secundario, args=(evento_apagar, panel, api_js), daemon=True)
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

    ventana.events.closed += lambda: evento_apagar.set()
    # Conecta el controlador de UI con la ventana nativa
    panel.ventana = ventana
    webview.start()
