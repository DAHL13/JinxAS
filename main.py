import json
import logging
import sys
import threading
import time
import webview
from percepcion import escuchar_y_transcribir, esperar_palabra_activacion
from cerebro import procesar_pensamiento
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
from interfaz import ControladorPanel
from config import (
    MODELO_WHISPER,
    PALABRA_ACTIVACION,
    PHRASE_TIME_LIMIT,
    SYSTEM_PROMPT,
    TIEMPO_MAXIMO_ESCUCHA,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

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

def bucle_voz_secundario(evento_apagar: threading.Event = None, panel=None):
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
                texto_limpio = texto_reconocido.lower()
                palabras_salida = ["salir", "cancelar", "apagar", "detener"]

                if any(palabra in texto_limpio for palabra in palabras_salida):
                    logging.info("Cerrando asistente Jinx...")
                    reproducir_voz("Hasta luego, apagando sistema.")
                    evento_apagar.set()
                    try:
                        if panel.ventana:
                            panel.ventana.destroy()
                    except Exception:
                        pass
                    break

                frases_reinicio = ["olvida todo", "borra la memoria", "nueva conversación"]
                if any(frase in texto_limpio for frase in frases_reinicio):
                    logging.info("Reiniciando memoria de conversación...")
                    contexto = [{"role": "system", "content": SYSTEM_PROMPT}]
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

                respuesta = procesar_pensamiento(contexto)
                contexto.append(respuesta)

                if respuesta.get("tool_calls"):
                    for tool_call in respuesta["tool_calls"]:
                        nombre_fn, argumentos = _extraer_llamada(tool_call)
                        logging.info("Herramienta solicitada: %s %s", nombre_fn, argumentos)
                        panel.actualizar_satelite(3, 2, "Ejecutando Tool", nombre_fn)
                        funcion = FUNCIONES_DISPONIBLES.get(nombre_fn)
                        try:
                            if funcion is None:
                                resultado = f"Herramienta no permitida: {nombre_fn}"
                            else:
                                resultado = funcion(**argumentos)
                        except Exception as e:
                            logging.error("Error al ejecutar %s: %s", nombre_fn, e)
                            resultado = f"Error al ejecutar {nombre_fn}: {e}"
                        logging.info("Resultado: %s", resultado)
                        contexto.append({"role": "tool", "content": str(resultado)})

                    logging.info("Jinx generando frase final hablada...")
                    panel.actualizar_satelite(3, 1, "Inferencia", "Sintetizando razonamiento...")
                    panel.actualizar_satelite(3, 2, "qwen2.5:3b", "Tool completada")
                    respuesta = procesar_pensamiento(contexto, permitir_herramientas=False)
                    texto_final = (respuesta.get("content") or "").strip() if isinstance(respuesta, dict) else str(respuesta).strip()
                    if not texto_final or texto_final.strip() == "":
                        texto_final = "Comando ejecutado."
                    if isinstance(respuesta, dict):
                        respuesta["content"] = texto_final
                else:
                    texto_final = (respuesta.get("content") or "").strip()

                # Agregar la respuesta final al contexto solo si no está ya registrada
                if contexto[-1] != respuesta:
                    contexto.append(respuesta)

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
                if panel.ventana:
                    panel.ventana.destroy()
            except Exception:
                pass
            break
        except Exception as e:
            logging.error("Ocurrió un error en el ciclo principal: %s", e)
            time.sleep(2)

if __name__ == "__main__":
    hilo_voz = threading.Thread(target=bucle_voz_secundario, args=(evento_apagar, panel), daemon=True)
    hilo_voz.start()

    ventana = webview.create_window(
        'SENTINEL // PIPELINE GRAPH',
        'panel_sentinel.html',
        width=1760,
        height=900,
    )
    ventana.events.closed += lambda: evento_apagar.set()
    # Conecta el controlador de UI con la ventana nativa
    panel.ventana = ventana
    webview.start()
