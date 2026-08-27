import logging
import re
import sys
# pyrefly: ignore [missing-import]
import speech_recognition as sr
from config import (
    IDIOMA_WHISPER,
    MODELO_WHISPER,
    PHRASE_TIME_LIMIT,
    PROMPT_INICIAL_WHISPER,
    TIEMPO_MAXIMO_ESCUCHA,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

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
    phrase_time_limit=PHRASE_TIME_LIMIT,
    initial_prompt=PROMPT_INICIAL_WHISPER
):
    """
    Inicializa el micrófono, calibra el ruido ambiental y escucha por un máximo de tiempo_maximo segundos.
    Transcribe el audio usando el modelo Whisper local optimizado en español ('es')
    con un prompt inicial de contexto técnico.
    """
    recognizer = sr.Recognizer()

    # Ajustes finos de reconocimiento
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    recognizer.pause_threshold = 0.8  # Pausa tras la cual se considera finalizada la frase

    logging.info("Módulo de percepción - asistente de voz local")

    try:
        with sr.Microphone() as source:
            logging.info("Calibrando ruido ambiental... Por favor guarda silencio un momento.")
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            logging.info("Umbral de energía establecido en: %.2f", recognizer.energy_threshold)

            logging.info("Escuchando... (habla ahora, máximo %s segundos)", phrase_time_limit)
            try:
                # Escuchar con límite de tiempo y tiempo máximo de frase
                audio = recognizer.listen(
                    source,
                    timeout=tiempo_maximo,
                    phrase_time_limit=phrase_time_limit
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

    # Transcripción con Whisper local a través de SpeechRecognition
    try:
        logging.info("Transcribiendo audio con Whisper (modelo '%s', idioma '%s')...", modelo, IDIOMA_WHISPER)
        texto_transcrito = recognizer.recognize_whisper(
            audio,
            model=modelo,
            language=IDIOMA_WHISPER,
            initial_prompt=initial_prompt
        )

        texto_limpio = limpiar_texto_transcrito(texto_transcrito)
        logging.info('Texto reconocido: "%s"', texto_limpio)
        return texto_limpio if texto_limpio else None

    except sr.UnknownValueError:
        logging.info("Whisper no pudo entender el audio.")
        return None
    except sr.RequestError as e:
        logging.error("Error en el motor de Whisper: %s", e)
        return None
    except Exception as e:
        logging.error("Error inesperado durante la transcripción: %s", e)
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    escuchar_y_transcribir()
