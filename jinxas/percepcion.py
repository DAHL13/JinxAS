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
)


class MicrofonoNoDisponible(RuntimeError):
    """Se lanza cuando el hardware de micrófono no es accesible (OSError de PyAudio)."""

_MODELO_CENTINELA = None

# ── Caché perezosa para STT de comandos (independiente del centinela) ──────────
_RECONOCEDOR_COMANDOS = None
_MODELO_WHISPER_COMANDOS = None

# Reconocedor compartido del centinela (se mantiene para no romper la lógica interna)
_RECOGNIZER = sr.Recognizer()
_RECOGNIZER.energy_threshold = 300
_RECOGNIZER.dynamic_energy_threshold = True
_RECOGNIZER.dynamic_energy_adjustment_damping = 0.15
_RECOGNIZER.pause_threshold = 0.8


def _obtener_reconocedor_comandos() -> sr.Recognizer:
    """Devuelve el reconocedor dedicado a comandos, creándolo la primera vez."""
    global _RECONOCEDOR_COMANDOS
    if _RECONOCEDOR_COMANDOS is None:
        _RECONOCEDOR_COMANDOS = sr.Recognizer()
        _RECONOCEDOR_COMANDOS.energy_threshold = 300
        _RECONOCEDOR_COMANDOS.dynamic_energy_threshold = True
        _RECONOCEDOR_COMANDOS.pause_threshold = 0.8
    return _RECONOCEDOR_COMANDOS


def _obtener_modelo_comandos():
    """Carga el modelo Whisper principal para comandos, una sola vez."""
    global _MODELO_WHISPER_COMANDOS
    if _MODELO_WHISPER_COMANDOS is None:
        logging.info("Cargando modelo Whisper principal (comandos)...")
        _MODELO_WHISPER_COMANDOS = whisper.load_model(config.MODELO_WHISPER)
    return _MODELO_WHISPER_COMANDOS


# ── Filtro de alucinaciones ────────────────────────────────────────────────────
ALUCINACIONES = ("amara.org", "subtitulos", "gracias por ver", "suscribete")


def _normalizar_simple(texto: str) -> str:
    """Versión mínima de normalizar() para evitar importación circular con comandos."""
    import unicodedata
    if not texto:
        return ""
    texto = texto.lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^\w\s]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def filtrar_transcripcion(res: dict) -> str | None:
    """
    Descarta transcripciones vacías, alucinadas o con baja probabilidad de habla real.
    Retorna el texto limpio o None si debe ignorarse.
    """
    texto = (res.get("text") or "").strip()
    if len(texto) < 2:
        return None

    segs = res.get("segments") or []
    if not segs:
        return None

    # Todos los segmentos sin habla detectada → descartar
    if all(s.get("no_speech_prob", 0.0) > 0.6 for s in segs):
        return None

    # Logprob promedio muy bajo → transcripción de ruido
    avg_logprob = sum(s.get("avg_logprob", 0.0) for s in segs) / len(segs)
    if avg_logprob < -1.0:
        return None

    # Cadenas propias de subtítulos de YouTube u otros artefactos
    texto_norm = _normalizar_simple(texto)
    if any(a in texto_norm for a in ALUCINACIONES):
        return None

    return texto

def coincide_wakeword(texto: str, variantes: list, umbral: int = 80) -> bool:
    # Compara cada palabra del texto transcrito contra las variantes aceptadas
    return any(fuzz.ratio(p.lower(), v.lower()) >= umbral for p in texto.split() for v in variantes)

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
        # Propagamos el error de hardware para que main.py aplique el backoff
        raise MicrofonoNoDisponible(str(e)) from e
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
    modelo: str = MODELO_WHISPER,
    tiempo_maximo: int = TIEMPO_MAXIMO_ESCUCHA,
    phrase_time_limit: int = PHRASE_TIME_LIMIT,
    initial_prompt: str = "",
    evento_apagar=None,
    panel=None,
) -> str | None:
    """
    Captura un comando de voz y lo transcribe con Whisper.

    - Usa el reconocedor y el modelo cacheados para comandos (independiente del centinela).
    - NO llama a adjust_for_ambient_noise para no perder el primer segundo de audio.
    - Propaga MicrofonoNoDisponible si el hardware falla.
    - Aplica filtrar_transcripcion() para descartar alucinaciones.
    """
    if evento_apagar and evento_apagar.is_set():
        return None

    r = _obtener_reconocedor_comandos()
    modelo_whisper = _obtener_modelo_comandos()

    # ── Captura de audio ──────────────────────────────────────────────────────
    try:
        with sr.Microphone() as fuente:
            logging.info("Escuchando comando... (máximo %s s)", phrase_time_limit)
            if panel:
                panel.actualizar_satelite(2, 1, "Micrófono", f"Escuchando ({phrase_time_limit}s)...")
                panel.actualizar_satelite(2, 2, "Modelo Whisper", f"{config.MODELO_WHISPER} (en caché)")
            try:
                audio = r.listen(
                    fuente,
                    timeout=config.TIEMPO_MAXIMO_ESCUCHA,
                    phrase_time_limit=config.PHRASE_TIME_LIMIT,
                )
                logging.info("Audio capturado. Transcribiendo...")
            except sr.WaitTimeoutError:
                logging.info("Tiempo de espera agotado: no se detectó voz.")
                return None
    except OSError as e:
        raise MicrofonoNoDisponible(str(e)) from e

    if evento_apagar and evento_apagar.is_set():
        return None

    # ── Transcripción numpy directa ───────────────────────────────────────────
    try:
        crudo = audio.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768.0

        if panel:
            panel.actualizar_satelite(2, 1, "Whisper", "Transcribiendo...")

        res = modelo_whisper.transcribe(
            audio_np,
            language=config.IDIOMA_WHISPER,
            fp16=False,
            initial_prompt=initial_prompt,
            condition_on_previous_text=False,
        )

        texto = filtrar_transcripcion(res)
        if texto:
            texto = limpiar_texto_transcrito(texto)
            logging.info('Texto reconocido: "%s"', texto)
        else:
            logging.info("Transcripción descartada por filtro de alucinaciones.")
        return texto or None

    except Exception as e:
        logging.error("Error durante la transcripción: %s", e)
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    escuchar_y_transcribir()
