import logging
import re
import sys
import numpy as np
# pyrefly: ignore [missing-import]
import speech_recognition as sr
import whisper
import config
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

_MODELO_CENTINELA = None

def esperar_palabra_activacion(palabra_clave: str = PALABRA_ACTIVACION, variaciones: list = None) -> bool:
    """
    Modo Centinela: Escucha pasivamente en segundo plano con Whisper (modelo tiny.en)
    hasta detectar la palabra clave de activación 'Jinx' o sus variantes fonéticas.
    """
    global _MODELO_CENTINELA
    if _MODELO_CENTINELA is None:
        logging.info("Cargando modelo centinela de Whisper (%s)...", config.MODELO_WAKEWORD)
        _MODELO_CENTINELA = whisper.load_model(config.MODELO_WAKEWORD)
    modelo_centinela = _MODELO_CENTINELA

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    variantes = list(config.VARIANTES_WAKEWORD)
    if variaciones:
        variantes.extend(variaciones)
    if palabra_clave and palabra_clave.lower() not in variantes:
        variantes.append(palabra_clave.lower())

    try:
        with sr.Microphone() as source:
            logging.info("Calibrando ruido ambiental para modo centinela...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            logging.info("Centinela activo. Esperando palabra de activación...")

            while True:
                try:
                    # Captura ráfagas cortas con VAD nativo para esperar en silencio sin saturar CPU
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue

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

                    # Verificar si ALGUNA de las palabras en config.VARIANTES_WAKEWORD está en el texto
                    palabras_texto = texto_limpio.split()
                    coincidencia = any(var in palabras_texto for var in variantes)

                    if coincidencia:
                        logging.info("¡Palabra de activación detectada con éxito! ('%s')", texto_detectado)
                        return True

                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    logging.debug("Ráfaga de audio no procesada o descartada: %s", e)
                    continue

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
