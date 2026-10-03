"""
tests/test_h017_panel_audio.py
==============================
Pruebas de aceptación para H-017:
- Interrupción inmediata de esperar_palabra_activacion mediante eventos_interrupcion.
- repetir_audio_ui no crea hilos y activa evento_regenerar.
- Concurrencia segura: dos reproducciones simultáneas no se solapan gracias a _LOCK_AUDIO.
"""
import threading
import time
from unittest.mock import MagicMock, patch
import speech_recognition as sr

from jinxas.percepcion import esperar_palabra_activacion
from jinxas.interfaz import ApiPanel
from jinxas.voz import reproducir_voz


def test_centinela_retorna_false_al_activar_evento_interrupcion():
    """El centinela retorna False al activarse un evento de interrupción antes o durante la escucha."""
    evento_reinicio = threading.Event()
    rec_mock = MagicMock()
    # Primera vuelta: timeout, luego se activa el evento y debe retornar False de inmediato
    def _listen_side_effect(*args, **kwargs):
        evento_reinicio.set()
        raise sr.WaitTimeoutError("timeout")

    rec_mock.listen.side_effect = _listen_side_effect

    with patch("jinxas.percepcion.sr.Microphone"), \
         patch("jinxas.percepcion._RECOGNIZER", rec_mock), \
         patch("jinxas.percepcion.whisper.load_model"):
        resultado = esperar_palabra_activacion(
            eventos_interrupcion=(evento_reinicio,),
        )
    assert resultado is False


def test_repetir_audio_ui_no_crea_hilos_y_marca_regenerar():
    """repetir_audio_ui solo delega en self.regenerar() sin crear nuevos hilos."""
    ev_regenerar = threading.Event()
    api = ApiPanel(evento_regenerar=ev_regenerar)

    with patch("threading.Thread") as mock_thread:
        api.repetir_audio_ui()
        mock_thread.assert_not_called()

    assert ev_regenerar.is_set() is True


def test_reproducir_voz_bloqueo_concurrente_sin_solape():
    """Dos llamadas concurrentes a reproducir_voz se sincronizan con _LOCK_AUDIO sin solape en pygame."""
    solapes = []
    en_seccion = []
    lock_test = threading.Lock()

    def _play_mock():
        with lock_test:
            en_seccion.append(1)
            if len(en_seccion) > 1:
                solapes.append(True)
        time.sleep(0.05)
        with lock_test:
            en_seccion.pop()

    with patch("jinxas.voz.asyncio.run"), \
         patch("jinxas.voz.asyncio.wait_for"), \
         patch("jinxas.voz.pygame.mixer.get_init", return_value=True), \
         patch("jinxas.voz.pygame.mixer.music") as mock_music, \
         patch("jinxas.voz.os.remove"):

        mock_music.get_busy.side_effect = [True, False, True, False]
        mock_music.play.side_effect = _play_mock

        t1 = threading.Thread(target=reproducir_voz, args=("Frase uno",))
        t2 = threading.Thread(target=reproducir_voz, args=("Frase dos",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

    assert len(solapes) == 0, "Se detectó solapamiento en la sección crítica de reproducción"
