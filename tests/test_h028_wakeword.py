"""
tests/test_h028_wakeword.py
===========================
Pruebas para H-028: Variantes reales de wake word y diagnóstico de casi-coincidencias.
Usa thefuzz real para evaluar coincidencias exactas, falsos positivos y logs de diagnóstico.
"""
import logging
import threading
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from jinxas import config
from jinxas.percepcion import (
    coincide_wakeword,
    esperar_palabra_activacion,
    mejor_similitud_wakeword,
)


@pytest.mark.parametrize(
    "variante",
    [
        "jinx",
        "jinks",
        "jinxs",
        "sphinx",
        "jynx",
        "ginx",
        "gynx",
        "jinxe",
        "jinex",
    ],
)
def test_todas_las_variantes_activan(variante):
    """Las 9 variantes autorizadas de Jinx deben dar True con el umbral configurado."""
    assert coincide_wakeword(variante, config.VARIANTES_WAKEWORD) is True
    assert coincide_wakeword(f"hey {variante} dime la hora", config.VARIANTES_WAKEWORD) is True


@pytest.mark.parametrize(
    "falso_positivo",
    [
        "inks",
        "links",
        "sinks",
        "winks",
        "pinks",
        "minks",
        "kinks",
        "finks",
        "hinks",
        "jenks",
        "think",
        "thanks",
    ],
)
def test_falsos_positivos_no_activan(falso_positivo):
    """Los 12 falsos positivos conocidos no deben activar la palabra clave."""
    assert coincide_wakeword(falso_positivo, config.VARIANTES_WAKEWORD) is False
    assert coincide_wakeword(f"please open the {falso_positivo} now", config.VARIANTES_WAKEWORD) is False


def test_mejor_similitud_wakeword_devuelve_palabra_y_valor():
    """mejor_similitud_wakeword identifica la palabra de >=3 letras más cercana y su ratio."""
    palabra, score = mejor_similitud_wakeword("open the links now", config.VARIANTES_WAKEWORD)
    assert palabra == "links"
    assert score == 80.0

    # Texto vacío o solo palabras cortas
    palabra_vacia, score_vacio = mejor_similitud_wakeword("hi ok no", config.VARIANTES_WAKEWORD)
    assert palabra_vacia == ""
    assert score_vacio == 0.0


def _simular_escucha_con_transcripcion(texto_transcrito: str):
    """Genera mocks para simular una iteración de listen() y transcribe() en esperar_palabra_activacion."""
    fake_audio = MagicMock()
    # Genera un buffer de 16000 muestras a 16 bits (32000 bytes)
    datos_pcm = np.zeros(16000, dtype=np.int16).tobytes()
    fake_audio.get_raw_data.return_value = datos_pcm

    mock_rec = MagicMock()
    mock_rec.listen.return_value = fake_audio
    mock_rec.energy_threshold = 300.0

    mock_modelo = MagicMock()
    mock_modelo.transcribe.return_value = {"text": texto_transcrito}

    return mock_rec, mock_modelo


def test_diagnostico_casi_coincidencia_log_debug_vs_info(caplog):
    """Casi-coincidencias (score >= 70 sin activar) se registran en DEBUG y NUNCA en INFO."""
    evento_interrupcion = threading.Event()
    import speech_recognition as sr

    def crear_mock_rec():
        llamadas_listen = 0

        def side_effect_listen(*args, **kwargs):
            nonlocal llamadas_listen
            llamadas_listen += 1
            if llamadas_listen == 1:
                fake_audio = MagicMock()
                fake_audio.get_raw_data.return_value = np.zeros(16000, dtype=np.int16).tobytes()
                return fake_audio
            evento_interrupcion.set()
            raise sr.WaitTimeoutError()

        mock_rec, mock_modelo = _simular_escucha_con_transcripcion("open links please")
        mock_rec.listen.side_effect = side_effect_listen
        return mock_rec, mock_modelo

    # 1. Con nivel INFO: no debe figurar la palabra del usuario ni el log de casi-coincidencia
    mock_rec_info, mock_modelo_info = crear_mock_rec()
    with caplog.at_level(logging.INFO), \
         patch("speech_recognition.Recognizer", return_value=mock_rec_info), \
         patch("speech_recognition.Microphone"), \
         patch("jinxas.percepcion._RECOGNIZER", mock_rec_info), \
         patch("jinxas.percepcion._obtener_modelo_centinela", return_value=mock_modelo_info):

        evento_interrupcion.clear()
        activado = esperar_palabra_activacion(evento_apagar=evento_interrupcion)
        assert activado is False
        assert "Casi-coincidencia" not in caplog.text
        assert "links" not in caplog.text

    # 2. Con nivel DEBUG: debe aparecer la casi-coincidencia con palabra y score
    caplog.clear()
    mock_rec_debug, mock_modelo_debug = crear_mock_rec()
    with caplog.at_level(logging.DEBUG), \
         patch("speech_recognition.Recognizer", return_value=mock_rec_debug), \
         patch("speech_recognition.Microphone"), \
         patch("jinxas.percepcion._RECOGNIZER", mock_rec_debug), \
         patch("jinxas.percepcion._obtener_modelo_centinela", return_value=mock_modelo_debug):

        evento_interrupcion.clear()
        activado = esperar_palabra_activacion(evento_apagar=evento_interrupcion)
        assert activado is False
        assert "Casi-coincidencia wake word: 'links' -> 80.0" in caplog.text
