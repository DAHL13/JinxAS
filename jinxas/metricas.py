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


class CronometroTurno:
    """
    Registra timestamps de alta precisión de los hitos clave de un turno de voz.

    Hitos:
      - t_inicio_turno   : inicio del turno (asignar manualmente con perf_counter)
      - t_fin_usuario    : fin de la frase del usuario (fin de STT)
      - t_primer_audio   : instante en que pygame inicia la reproducción (TTFA)

    Métricas calculadas:
      - ttfa_ms   : Time To First Audio = t_primer_audio - t_fin_usuario (ms)
      - turno_ms  : Duración total del turno desde t_inicio_turno (ms)
    """

    def __init__(self):
        self.t_inicio_turno: float = 0.0
        self.t_fin_usuario: float = 0.0
        self.t_primer_audio: float = 0.0
        self.ttfa_ms: float = 0.0
        self.turno_ms: float = 0.0

    def marcar_fin_usuario(self) -> None:
        """Registra el instante en que el usuario terminó de hablar (fin de STT)."""
        self.t_fin_usuario = time.perf_counter()

    def marcar_primer_audio(self) -> None:
        """
        Registra el instante en que comienza la reproducción del audio (primer sample).
        Solo actúa la primera vez: ignora llamadas duplicadas dentro del mismo turno.
        """
        if self.t_fin_usuario > 0 and self.t_primer_audio == 0.0:
            self.t_primer_audio = time.perf_counter()
            self.ttfa_ms = (self.t_primer_audio - self.t_fin_usuario) * 1000.0

    def finalizar_turno(self) -> None:
        """Calcula la duración total del turno desde t_inicio_turno."""
        if self.t_inicio_turno > 0:
            self.turno_ms = (time.perf_counter() - self.t_inicio_turno) * 1000.0
