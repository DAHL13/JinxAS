"""
tests/test_h021_logs_privacidad.py
===================================
Pruebas para H-021: Privacidad en logs.
Verifica que el texto del usuario no se registre en nivel INFO (solo metadatos)
y que solo aparezca si el nivel de logging se eleva a DEBUG.
"""
import logging
from unittest.mock import MagicMock, patch

from jinxas import percepcion


def test_escuchar_y_transcribir_no_expone_texto_en_info(caplog, monkeypatch):
    """En nivel INFO, la transcripción no debe registrar el texto dictado por el usuario."""
    texto_privado = "mi secreto confidencial 987654"

    fake_model = MagicMock()
    fake_model.transcribe.return_value = {
        "text": texto_privado,
        "segments": [{"no_speech_prob": 0.0, "avg_logprob": -0.1}],
    }
    monkeypatch.setattr(percepcion, "_MODELO_WHISPER_COMANDOS", fake_model)

    fake_audio = MagicMock()
    fake_audio.get_raw_data.return_value = b"\x00" * 3200

    with caplog.at_level(logging.INFO), \
         patch.object(percepcion._RECOGNIZER, "listen", return_value=fake_audio), \
         patch("speech_recognition.Microphone"):

        resultado = percepcion.escuchar_y_transcribir(modelo=fake_model)
        assert resultado == texto_privado

        # Validar logs INFO: contiene metadatos de longitud pero no el texto privado
        assert texto_privado not in caplog.text
        assert "Texto reconocido (" in caplog.text


def test_escuchar_y_transcribir_registra_texto_en_debug(caplog, monkeypatch):
    """En nivel DEBUG, la transcripción sí incluye el texto para diagnóstico."""
    texto_privado = "mi secreto confidencial 987654"

    fake_model = MagicMock()
    fake_model.transcribe.return_value = {
        "text": texto_privado,
        "segments": [{"no_speech_prob": 0.0, "avg_logprob": -0.1}],
    }
    monkeypatch.setattr(percepcion, "_MODELO_WHISPER_COMANDOS", fake_model)

    fake_audio = MagicMock()
    fake_audio.get_raw_data.return_value = b"\x00" * 3200

    with caplog.at_level(logging.DEBUG), \
         patch.object(percepcion._RECOGNIZER, "listen", return_value=fake_audio), \
         patch("speech_recognition.Microphone"):

        resultado = percepcion.escuchar_y_transcribir(modelo=fake_model)
        assert resultado == texto_privado

        # Validar logs DEBUG: sí contiene el texto
        assert texto_privado in caplog.text


def test_wakeword_log_no_expone_texto_en_info(caplog):
    """La detección de wakeword no expone el texto detectado en nivel INFO."""
    with caplog.at_level(logging.INFO):
        logging.info("¡Palabra de activación detectada con éxito!")
        logging.debug("Palabra de activación detectada: '%s'", "jinx activar secreto")

        assert "jinx activar secreto" not in caplog.text
        assert "¡Palabra de activación detectada con éxito!" in caplog.text
