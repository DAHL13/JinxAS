import logging
import time
from contextlib import contextmanager


@contextmanager
def medir(etapa: str, acumulador: dict | None = None):
    """Context manager que mide el tiempo de una etapa del pipeline y lo registra en el log."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - t0) * 1000
        if acumulador is not None:
            acumulador[etapa] = ms
        logging.info("[METRICA] %s: %.0f ms", etapa, ms)
