"""
tests/test_h030_modelos.py
===========================
Pruebas para H-030: Carga única y segura de modelos Whisper.
Verifica que llamadas concurrentes entre precargar_modelos y esperar_palabra_activacion
no produzcan cargas duplicadas de los modelos en memoria.
"""
import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from jinxas import config, percepcion


@pytest.fixture(autouse=True)
def reset_modelos_whisper():
    """Resetea las referencias globales de modelos antes y después de cada test."""
    orig_centinela = percepcion._MODELO_CENTINELA
    orig_comandos = percepcion._MODELO_WHISPER_COMANDOS
    percepcion._MODELO_CENTINELA = None
    percepcion._MODELO_WHISPER_COMANDOS = None
    try:
        yield
    finally:
        percepcion._MODELO_CENTINELA = orig_centinela
        percepcion._MODELO_WHISPER_COMANDOS = orig_comandos


def test_carga_concurrente_invoca_load_model_una_vez_por_modelo():
    """Con 4 hilos llamando simultáneamente a precargar_modelos y esperar_palabra_activacion,

    load_model se invoca exactamente una sola vez por cada modelo.
    """
    llamadas = []
    lock_contador = threading.Lock()

    def fake_load_model(nombre_modelo, **kwargs):
        with lock_contador:
            llamadas.append(nombre_modelo)
        time.sleep(0.02)  # Simula latencia para forzar carreras si faltase sincronización
        mock_m = MagicMock()
        mock_m.transcribe.return_value = {"text": "hello"}
        return mock_m

    barrera = threading.Barrier(4)
    evento_apagar = threading.Event()
    evento_apagar.set()  # Permite que esperar_palabra_activacion salga de inmediato tras cargar el modelo

    def tarea_precarga():
        barrera.wait()
        percepcion.precargar_modelos()

    def tarea_centinela():
        barrera.wait()
        with patch("speech_recognition.Microphone"):
            percepcion.esperar_palabra_activacion(evento_apagar=evento_apagar)

    with patch("whisper.load_model", side_effect=fake_load_model):
        hilos = [
            threading.Thread(target=tarea_precarga),
            threading.Thread(target=tarea_precarga),
            threading.Thread(target=tarea_centinela),
            threading.Thread(target=tarea_centinela),
        ]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=5.0)
            assert not h.is_alive()

    # Debe haber exactamente 1 carga para MODELO_WAKEWORD y 1 carga para MODELO_WHISPER
    assert llamadas.count(config.MODELO_WAKEWORD) == 1
    assert llamadas.count(config.MODELO_WHISPER) == 1
    assert len(llamadas) == 2
