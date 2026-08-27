import logging
import os
import sys
import tempfile
import time
import asyncio
import edge_tts
from config import VOZ_TTS

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

async def _generar_audio_edge(texto: str, voz: str, archivo: str):
    comunicador = edge_tts.Communicate(texto, voz)
    await comunicador.save(archivo)

def reproducir_voz(texto: str, voz: str = VOZ_TTS):
    """
    Genera audio a partir de texto usando edge-tts y lo reproduce con pygame.mixer de forma bloqueante.
    Usa un archivo temporal dinámico por invocación para evitar colisiones y limpiar el sistema correctamente.
    """
    if not texto or not texto.strip():
        return

    # Crear un archivo temporal único para esta reproducción
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    archivo_temporal = tmp.name
    tmp.close()  # Cerrar antes de que edge-tts escriba en él

    try:
        # Generar archivo de audio con edge-tts
        asyncio.run(_generar_audio_edge(texto, voz, archivo_temporal))

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
