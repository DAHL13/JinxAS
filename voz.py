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

def reproducir_voz(texto: str, voz: str = VOZ_TTS, on_start: callable = None):
    """
    Genera audio a partir de texto usando edge-tts y lo reproduce con pygame.mixer de forma bloqueante.
    Usa un archivo temporal dinámico por invocación para evitar colisiones y limpiar el sistema correctamente.

    Parámetros
    ----------
    texto : str
        Texto a sintetizar y reproducir.
    voz : str
        Voz de edge-tts a usar (por defecto la de config.VOZ_TTS).
    on_start : callable, opcional
        Callback invocado justo antes de que pygame inicie la reproducción.
        Úsalo para registrar el timestamp de primer audio (TTFA).
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
        # Invocar el callback de inicio justo antes del primer sample de audio
        if callable(on_start):
            on_start()
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


# ---------------------------------------------------------------------------
# F2-02: Streaming TTS por frases
# ---------------------------------------------------------------------------
import queue
import threading

# Detecta el final de una frase: cualquier contenido terminado en . ! ? … seguido de espacio
FIN_DE_FRASE = re.compile(r"(.+?[.!?…])\s")


def extraer_frases(flujo_texto):
    """
    Generador que consume un iterable de fragmentos de texto (strings o chunks
    de Ollama) y emite frases completas una a una.

    Algoritmo:
      - Acumula fragmentos en un buffer.
      - Emite (yield) cada frase completa que detecte FIN_DE_FRASE.match() al
        principio del buffer, consumiendo exactamente ese prefijo del buffer.
      - Al agotar el iterable, emite el remanente si no está vacío.

    Parámetros
    ----------
    flujo_texto : iterable de str
        Puede ser una lista, generador o respuesta chunk-by-chunk de Ollama.

    Yields
    ------
    str
        Una frase completa por cada yield.
    """
    buf = ""
    for fragmento in flujo_texto:
        # Soporta chunks de Ollama (dict con 'message'.content) y strings puros
        if isinstance(fragmento, dict):
            fragmento = (fragmento.get("message") or {}).get("content", "")
        buf += fragmento
        # Emitir todas las frases completas que haya en el buffer
        while True:
            m = FIN_DE_FRASE.match(buf)
            if not m:
                break
            yield m.group(1)
            buf = buf[m.end():]
    # Emitir el remanente final (frase sin punto al final)
    resto = buf.strip()
    if resto:
        yield resto


def reproducir_frases_streaming(
    frases_iter,
    voz: str = VOZ_TTS,
    on_start: callable = None,
) -> None:
    """
    Reproduce un iterable de frases de texto con TTS pipeline streaming:
    un hilo productor sintetiza cada frase a .mp3 en paralelo mientras
    el hilo actual (consumidor) reproduce los archivos en orden.

    Arquitectura:
      - Cola bounded  : queue.Queue(maxsize=4) — back-pressure natural.
      - Productor     : hilo daemon que sintetiza y encola rutas de .mp3.
      - Consumidor    : hilo actual que desencola y reproduce con pygame.
      - Centinela     : None al final de la cola indica fin de producción.
      - on_start      : callback disparado justo antes del PRIMER play().
      - Limpieza      : cada .mp3 se elimina inmediatamente tras reproducirlo.

    Parámetros
    ----------
    frases_iter : iterable de str
        Frases ya segmentadas (salida de extraer_frases() o lista manual).
    voz : str
        Voz de edge-tts.
    on_start : callable, opcional
        Se invoca exactamente una vez, antes del primer pygame.play().
    """
    cola: queue.Queue = queue.Queue(maxsize=4)

    # ── Hilo productor: síntesis TTS → archivos temporales ──────────────────
    def _productor():
        for frase in frases_iter:
            frase_limpia = limpiar_para_tts(frase)
            if not frase_limpia:
                continue
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            ruta = tmp.name
            tmp.close()
            sintetizado = False
            for intento in range(2):
                try:
                    asyncio.run(
                        asyncio.wait_for(
                            _generar_audio_edge(frase_limpia, voz, ruta),
                            timeout=8,
                        )
                    )
                    sintetizado = True
                    break
                except Exception as e:
                    logging.warning("[STR] TTS intento %d falló: %s", intento + 1, e)
            if sintetizado:
                cola.put(ruta)
            else:
                # Fallback sonoro solo en la primera frase fallida
                if sys.platform == "win32":
                    try:
                        import winsound
                        winsound.MessageBeep()
                    except Exception:
                        pass
                # Limpiar el .mp3 vacío y no encolar
                try:
                    os.remove(ruta)
                except Exception:
                    pass
        # Centinela: indica al consumidor que no hay más frases
        cola.put(None)

    hilo = threading.Thread(target=_productor, daemon=True, name="tts-streaming-producer")
    hilo.start()

    # ── Consumidor: reproduce en orden en el hilo actual ────────────────────
    primer_audio = True
    while True:
        ruta = cola.get()
        if ruta is None:
            break
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(ruta)
            # Disparar on_start solo antes del PRIMER sample de audio
            if primer_audio:
                if callable(on_start):
                    on_start()
                primer_audio = False
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
        except Exception as e:
            logging.error("[STR] Error reproduciendo frase: %s", e)
        finally:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            try:
                os.remove(ruta)
            except Exception:
                pass

    hilo.join(timeout=2)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    mensaje_prueba = "¡Hola! Soy Jinx, tu asistente de voz local. El módulo de voz está listo."
    logging.info("Módulo de síntesis de voz (TTS) - Jinx")
    logging.info('Generando y reproduciendo: "%s"', mensaje_prueba)
    reproducir_voz(mensaje_prueba)
    logging.info("Reproducción finalizada.")
