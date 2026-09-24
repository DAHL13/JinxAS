import logging
import os
import re
import sys
import tempfile
import time
import asyncio
import edge_tts
from config import VOZ_TTS

_URL = re.compile(r"https?://\S+")
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
_MD = re.compile(r"[*_`#>]+")


def limpiar_para_tts(texto: str) -> str:
    """Elimina URLs, emojis y markdown para asegurar una pronunciación limpia en TTS."""
    if not texto:
        return ""
    texto = _URL.sub("", texto)
    texto = _EMOJI.sub("", texto)
    texto = _MD.sub("", texto)
    return re.sub(r"\s+", " ", texto).strip()


os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

async def _generar_audio_edge(texto: str, voz: str, archivo: str):
    comunicador = edge_tts.Communicate(texto, voz)
    await comunicador.save(archivo)

def reproducir_voz(texto: str, voz: str = VOZ_TTS):
    """
    Genera audio a partir de texto usando edge-tts y lo reproduce con pygame.mixer de forma bloqueante.
    Usa un archivo temporal dinámico por invocación para evitar colisiones y limpiar el sistema correctamente.
    """
    texto = limpiar_para_tts(texto)
    if not texto:
        return

    # Crear un archivo temporal único para esta reproducción
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    archivo_temporal = tmp.name
    tmp.close()  # Cerrar antes de que edge-tts escriba en él

    try:
        # Generar archivo de audio con edge-tts con reintentos y timeout de red
        for intento in range(2):
            try:
                asyncio.run(asyncio.wait_for(_generar_audio_edge(texto, voz, archivo_temporal), timeout=8))
                break
            except Exception as e:
                logging.warning("TTS intento %d falló: %s", intento + 1, e)
        else:
            if sys.platform == "win32":
                import winsound
                winsound.MessageBeep()
            return

        # Inicializar mixer si no está activo
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # Cargar y reproducir el archivo de audio
        pygame.mixer.music.load(archivo_temporal)
        pygame.mixer.music.play()

        # Bucle de espera activo que bloquea el hilo hasta terminar la reproducción
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        # Descargar y liberar el archivo de audio
        pygame.mixer.music.unload()

    except Exception as e:
        logging.error("Error en módulo de voz TTS: %s", e)
    finally:
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        # Eliminar archivo temporal dinámico del sistema
        if os.path.exists(archivo_temporal):
            try:
                os.remove(archivo_temporal)
            except Exception as e:
                logging.error("No se pudo eliminar el archivo TTS temporal: %s", e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    mensaje_prueba = "¡Hola! Soy Jinx, tu asistente de voz local. El módulo de voz está listo."
    logging.info("Módulo de síntesis de voz (TTS) - Jinx")
    logging.info('Generando y reproduciendo: "%s"', mensaje_prueba)
    reproducir_voz(mensaje_prueba)
    logging.info("Reproducción finalizada.")
