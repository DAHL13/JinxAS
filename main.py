import json
import logging
import sys
import time
from percepcion import escuchar_y_transcribir, esperar_palabra_activacion
from cerebro import procesar_pensamiento
from voz import reproducir_voz
from herramientas import (
    obtener_estado_sistema,
    obtener_temperatura,
    abrir_aplicacion,
    obtener_clima,
)
from memoria import guardar_nota, buscar_nota
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

FUNCIONES_DISPONIBLES = {
    "obtener_estado_sistema": obtener_estado_sistema,
    "obtener_temperatura": obtener_temperatura,
    "abrir_aplicacion": abrir_aplicacion,
    "guardar_nota": guardar_nota,
    "buscar_nota": buscar_nota,
    "obtener_clima": obtener_clima,
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

def iniciar_asistente():
    logging.info("Jinx Asistente - asistente de voz local")
    logging.info("Di 'salir', 'cancelar', 'apagar', 'detener' o presiona Ctrl+C para salir.")

    contexto = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            logging.info("Esperando palabra de activación 'Jinx'...")
            activado = esperar_palabra_activacion(PALABRA_ACTIVACION)
            if not activado:
                continue

            logging.info("¡Despierta!")
            reproducir_voz("Dime")
            time.sleep(0.3)

            logging.info("Escuchando tu comando...")
            texto_usuario = escuchar_y_transcribir(
                modelo=MODELO_WHISPER,
                tiempo_maximo=TIEMPO_MAXIMO_ESCUCHA,
                phrase_time_limit=PHRASE_TIME_LIMIT,
            )

            if texto_usuario and texto_usuario.strip():
                texto_reconocido = texto_usuario.strip()
                texto_limpio = texto_reconocido.lower()
                palabras_salida = ["salir", "cancelar", "apagar", "detener"]

                if any(palabra in texto_limpio for palabra in palabras_salida):
                    logging.info("Cerrando asistente Jinx...")
                    reproducir_voz("Hasta luego, apagando sistema.")
                    break

                frases_reinicio = ["olvida todo", "borra la memoria", "nueva conversación"]
                if any(frase in texto_limpio for frase in frases_reinicio):
                    logging.info("Reiniciando memoria de conversación...")
                    contexto = [{"role": "system", "content": SYSTEM_PROMPT}]
                    reproducir_voz("Memoria borrada. ¿De qué hablamos ahora?")
                    time.sleep(0.8)
                    continue

                logging.info('Procesando respuesta para: "%s"...', texto_reconocido)
                contexto.append({"role": "user", "content": texto_reconocido})

                # Recortar el historial manteniendo siempre el mensaje de sistema (índice 0)
                # y las últimas 8 entradas del historial de conversación.
                # Si el punto de corte cae sobre un mensaje 'tool', se retrocede hasta incluir
                # el 'assistant' con tool_calls que lo originó, para no romper el par.
                cola = contexto[1:][-8:]
                while cola and cola[0].get("role") == "tool":
                    cola = cola[1:]
                contexto = [contexto[0]] + cola

                respuesta = procesar_pensamiento(contexto)
                contexto.append(respuesta)

                if respuesta.get("tool_calls"):
                    for tool_call in respuesta["tool_calls"]:
                        nombre_fn, argumentos = _extraer_llamada(tool_call)
                        logging.info("Herramienta solicitada: %s %s", nombre_fn, argumentos)
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
                    respuesta = procesar_pensamiento(contexto)
                    texto_final = (respuesta.get("content") or "").strip()
                else:
                    texto_final = (respuesta.get("content") or "").strip()

                # Agregar la respuesta final al contexto solo si no está ya registrada
                if contexto[-1] != respuesta:
                    contexto.append(respuesta)

                logging.info("Respuesta Jinx: %s", texto_final)

                logging.info("Jinx respondiendo con voz...")
                reproducir_voz(texto_final)
                time.sleep(0.8)  # Purga el buffer del micrófono y evita captura de eco
            else:
                logging.info("No se detectó ninguna instrucción clara. Reintentando...")
                continue

        except KeyboardInterrupt:
            logging.info("Cerrando asistente Jinx...")
            break
        except Exception as e:
            logging.error("Ocurrió un error en el ciclo principal: %s", e)
            time.sleep(2)

if __name__ == "__main__":
    try:
        iniciar_asistente()
    except KeyboardInterrupt:
        logging.info("Cerrando asistente Jinx...")
