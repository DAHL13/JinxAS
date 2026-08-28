import logging
import re
import sys
import numpy as np
import openwakeword.model
import pyaudio
# pyrefly: ignore [missing-import]
import speech_recognition as sr
from config import (
    IDIOMA_WHISPER,
    MODELO_WHISPER,
    PALABRA_ACTIVACION,
    PHRASE_TIME_LIMIT,
    PROMPT_INICIAL_WHISPER,
    TIEMPO_MAXIMO_ESCUCHA,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_MODELO_OPENWAKEWORD = None

def _obtener_modelo_openwakeword():
    """
    Obtiene o inicializa el modelo openWakeWord para detección ultraligera de wake word.
    Se mantiene en memoria para evitar recargas constantes.
    """
    global _MODELO_OPENWAKEWORD
    if _MODELO_OPENWAKEWORD is None:
        try:
            _MODELO_OPENWAKEWORD = openwakeword.model.Model(wakeword_models=["hey_jarvis"])
        except Exception as e:
            logging.error("Error al cargar el modelo openWakeWord: %s", e)
            raise e
    return _MODELO_OPENWAKEWORD

def esperar_palabra_activacion(palabra_clave: str = PALABRA_ACTIVACION, variaciones: list = None) -> bool:
    """
    Escucha pasivamente en segundo plano con openWakeWord (offline)
    hasta detectar la palabra clave de activación ('hey_jarvis').
    
    CRÍTICO: Libera y cierra por completo el stream y la instancia de PyAudio
    en el bloque finally antes de retornar True, garantizando que el micrófono
    quede completamente libre para Whisper.
    """
    try:
        modelo = _obtener_modelo_openwakeword()
    except Exception as e:
        logging.error("No se pudo iniciar el reconocedor openWakeWord: %s", e)
        return False

    audio_p = None
    stream = None
    chunk = 1280

    try:
        audio_p = pyaudio.PyAudio()
        stream = audio_p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=chunk
        )
        stream.start_stream()

        contador_chunks = 0
        while True:
            data = stream.read(chunk, exception_on_overflow=False)
            if not data:
                continue

            audio_chunk = np.frombuffer(data, dtype=np.int16)
            prediccion = modelo.predict(audio_chunk)
            score = prediccion.get("hey_jarvis", 0.0)
            contador_chunks += 1

            if score > 0.01 or contador_chunks % 25 == 0:
                logging.info(f"[DEBUG WakeWord] Score Jarvis: {score}")

            if score > 0.2:
                return True

    except KeyboardInterrupt:
        return False
    except OSError as e:
        logging.error("Error de hardware/micrófono/PyAudio en detección de palabra clave: %s", e)
        return False
    except Exception as e:
        logging.error("Error inesperado en espera de palabra clave: %s", e)
        return False
    finally:
        # Liberación estricta de recursos del micrófono antes de salir
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                logging.error("Error al cerrar stream de PyAudio: %s", e)
        if audio_p is not None:
            try:
                audio_p.terminate()
            except Exception as e:
                logging.error("Error al finalizar PyAudio: %s", e)

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
