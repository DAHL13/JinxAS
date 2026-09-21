import logging
import re
import sys
import numpy as np
import speech_recognition as sr
import whisper
from thefuzz import fuzz
import config
from config import (
    IDIOMA_WHISPER,
    MODELO_WHISPER,
    PALABRA_ACTIVACION,
    PHRASE_TIME_LIMIT,
    PROMPT_INICIAL_WHISPER,
    TIEMPO_MAXIMO_ESCUCHA,
    configurar_consola,
)

configurar_consola()

_MODELO_CENTINELA = None
_MODELO_COMANDO = None

_RECOGNIZER = sr.Recognizer()
_RECOGNIZER.energy_threshold = 300
_RECOGNIZER.dynamic_energy_threshold = True
_RECOGNIZER.dynamic_energy_adjustment_damping = 0.15
_RECOGNIZER.pause_threshold = 0.8

def coincide_wakeword(texto: str, variantes: list, umbral: int = 80) -> bool:
    # Compara cada palabra del texto transcrito contra las variantes aceptadas
    return any(fuzz.ratio(p.lower(), v.lower()) >= umbral for p in texto.split() for v in variantes)

def _obtener_modelo_comando(nombre_modelo: str = "small"):
    """
    Obtiene el modelo Whisper principal para comandos de voz desde la caché en memoria.
    Se inicializa de forma perezosa una sola vez si aún no ha sido cargado.
    """
    global _MODELO_COMANDO
    if _MODELO_COMANDO is None:
        logging.info("Cargando modelo principal de Whisper (%s)...", nombre_modelo)
        _MODELO_COMANDO = whisper.load_model(nombre_modelo)
    return _MODELO_COMANDO

def esperar_palabra_activacion(
    palabra_clave: str = PALABRA_ACTIVACION,
    variaciones: list = None,
    evento_apagar=None,
    panel=None,
) -> bool:
    """
    Modo Centinela: Escucha pasivamente en segundo plano con Whisper (modelo tiny.en)
    hasta detectar la palabra clave de activación 'Jinx' o sus variantes fonéticas.
    """
    global _MODELO_CENTINELA
    if _MODELO_CENTINELA is None:
        logging.info("Cargando modelo centinela de Whisper (%s)...", config.MODELO_WAKEWORD)
        _MODELO_CENTINELA = whisper.load_model(config.MODELO_WAKEWORD)
    modelo_centinela = _MODELO_CENTINELA

    recognizer = _RECOGNIZER

    variantes = list(config.VARIANTES_WAKEWORD)
    if variaciones:
        variantes.extend(variaciones)
    if palabra_clave and palabra_clave.lower() not in variantes:
        variantes.append(palabra_clave.lower())

    try:
        with sr.Microphone() as source:
            logging.info("Calibrando ruido ambiental para modo centinela...")
            if panel: panel.actualizar_satelite(1, 1, "Centinela", "Calibrando ruido...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            logging.info("Centinela activo. Esperando palabra de activación...")
            if panel:
                panel.actualizar_satelite(1, 1, "Centinela Activo", "Esperando 'Jinx'...")
                panel.actualizar_satelite(1, 2, "Umbral Energía", f"{recognizer.energy_threshold:.2f} SNR")

            while not (evento_apagar and evento_apagar.is_set()):
                try:
                    # Captura ráfagas cortas con VAD nativo para esperar en silencio sin saturar CPU
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                except sr.WaitTimeoutError:
                    continue

                if evento_apagar and evento_apagar.is_set():
                    return False

                try:
                    # Convertir el audio capturado a numpy float32 a 16kHz en memoria
                    raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                    if not raw_data:
                        continue

                    audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                    if audio_np.size == 0:
                        continue

                    # Transcribir ráfaga con el modelo centinela
                    resultado = modelo_centinela.transcribe(
                        audio_np,
                        language="en",
                        fp16=False,
                    )
                    texto_detectado = resultado.get("text", "").strip()
                    if not texto_detectado:
                        continue

                    # Convertir a minúsculas y eliminar signos de puntuación
                    texto_limpio = texto_detectado.lower()
                    texto_limpio = re.sub(r"[^\w\s]", "", texto_limpio)
                    texto_limpio = re.sub(r"\s+", " ", texto_limpio).strip()

                    # Verificar si coincide con el wake word usando fuzzy matching
                    coincidencia = coincide_wakeword(texto_limpio, variantes)

                    if coincidencia:
                        logging.info("¡Palabra de activación detectada con éxito! ('%s')", texto_detectado)
                        if panel: panel.actualizar_satelite(1, 1, "Micrófono", "Detectado: ¡Jinx!")
                        return True

                except Exception as e:
                    logging.debug("Ráfaga de audio no procesada o descartada: %s", e)
                    continue

            return False

    except KeyboardInterrupt:
        logging.info("Espera de palabra de activación interrumpida.")
        return False
    except OSError as e:
        logging.error("Error de hardware o micrófono: %s", e)
        return False
    except Exception as e:
        logging.error("Error inesperado en centinela de activación: %s", e)
        return False

def limpiar_texto_transcrito(texto: str) -> str:
    """
    Limpia el texto transcrito eliminando espacios duplicados,
    caracteres no imprimibles y signos extraños al inicio/final.
    """
    if not texto:
        return ""

    # Eliminar caracteres de control no imprimibles
    texto = "".join(ch for ch in texto if ch.isprintable())

    # Normalizar espacios en blanco múltiples a uno solo
    texto = re.sub(r"\s+", " ", texto).strip()

    # Eliminar signos de puntuación o caracteres extraños al inicio o final
    texto = re.sub(r"^[\s\-_~`\"'«»“”„*#]+|[\s\-_~`\"'«»“”„*#]+$", "", texto)

    return texto.strip()

def escuchar_y_transcribir(
    modelo=MODELO_WHISPER,
    tiempo_maximo=TIEMPO_MAXIMO_ESCUCHA,
    phrase_time_limit=15,
    initial_prompt=PROMPT_INICIAL_WHISPER,
    evento_apagar=None,
    panel=None,
):
    """
    Inicializa el micrófono y escucha por un máximo de tiempo_maximo segundos.
    Transcribe el audio usando el modelo Whisper en caché (fp16=False) sin recalibrar
    el ruido ambiental (ya calibrado previamente por el centinela).
    """
    if evento_apagar and evento_apagar.is_set():
        return None

    recognizer = _RECOGNIZER

    logging.info("Módulo de percepción - asistente de voz local")

    try:
        with sr.Microphone() as source:
            logging.info("Escuchando... (habla ahora, máximo %s segundos)", phrase_time_limit)
            if panel:
                panel.actualizar_satelite(2, 1, "Micrófono", f"Escuchando ({phrase_time_limit}s)...")
                panel.actualizar_satelite(2, 2, "Modelo Whisper", "small (en caché)")
            try:
                # Escuchar con límite de tiempo y tiempo máximo de frase
                audio = recognizer.listen(
                    source,
                    timeout=tiempo_maximo,
                    phrase_time_limit=15,
                )
                logging.info("Audio capturado exitosamente. Procesando con Whisper...")

            except sr.WaitTimeoutError:
                logging.info("Tiempo de espera agotado: no se detectó voz dentro del tiempo límite.")
                return None

    except OSError as e:
        logging.error("Error de PyAudio / Micrófono: %s", e)
        logging.error("Verifica que tu micrófono esté conectado y que Windows tenga activados los permisos de micrófono.")
        return None
    except Exception as e:
        logging.error("Error al inicializar el micrófono: %s", e)
        return None

    if evento_apagar and evento_apagar.is_set():
        return None

    # Transcripción directa con el modelo Whisper en caché (ultra-rápida, fp16=False)
    try:
        nombre_modelo = modelo if isinstance(modelo, str) else "small"
        modelo_whisper = _obtener_modelo_comando(nombre_modelo)

        raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw_data, dtype=np.int16).flatten().astype(np.float32) / 32768.0

        logging.info("Transcribiendo audio directamente con Whisper (fp16=False)...")
        if panel:
            panel.actualizar_satelite(2, 1, "Whisper Small", "Transcribiendo...")
            panel.actualizar_satelite(2, 2, "Modelo Whisper", "small (en caché)")
        resultado = modelo_whisper.transcribe(
            audio_np,
            language="es",
            fp16=False,
            initial_prompt=initial_prompt,
        )

        texto_transcrito = resultado.get("text", "")
        texto_limpio = limpiar_texto_transcrito(texto_transcrito)
        logging.info('Texto reconocido: "%s"', texto_limpio)
        return texto_limpio if texto_limpio else None

    except Exception as e:
        logging.error("Error inesperado durante la transcripción: %s", e)
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    escuchar_y_transcribir()
