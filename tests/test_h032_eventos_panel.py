"""
tests/test_h032_eventos_panel.py
================================
Pruebas para H-032: Manejo de eventos del panel (Emergency Flush y Regenerar).
Verifica:
1. evento_reinicio activo purga el contexto a solo system, limpia el flag y actualiza api_js.contexto.
2. evento_regenerar activo invoca reproducir_voz exactamente una vez con el último mensaje del asistente.
3. Ambos eventos inactivos devuelven manejado=False y mantienen el contexto intacto.
"""
import threading
from unittest.mock import MagicMock, patch

from jinxas import __main__ as main_module


def test_evento_reinicio_activo_purga_contexto_y_actualiza_api():
    """evento_reinicio activo purga el contexto a solo el mensaje de sistema y limpia el evento."""
    evento_reinicio = threading.Event()
    evento_reinicio.set()
    evento_regenerar = threading.Event()

    contexto_inicial = [
        {"role": "system", "content": main_module.SYSTEM_PROMPT},
        {"role": "user", "content": "hola jinx"},
        {"role": "assistant", "content": "hola usuario"},
    ]

    api_js = MagicMock()
    panel = MagicMock()

    with patch.object(main_module, "reproducir_voz") as mock_voz:
        contexto_nuevo, manejado = main_module.procesar_eventos_panel(
            contexto_inicial,
            evento_reinicio,
            evento_regenerar,
            api_js,
            panel,
        )

        assert manejado is True
        assert not evento_reinicio.is_set()
        assert len(contexto_nuevo) == 1
        assert contexto_nuevo[0]["role"] == "system"
        assert contexto_nuevo[0]["content"] == main_module.SYSTEM_PROMPT
        assert api_js.contexto == contexto_nuevo
        mock_voz.assert_called_once_with("Memoria reiniciada.")
        panel.actualizar_respuesta.assert_called_once_with("Memoria reiniciada.", 0)


def test_evento_regenerar_activo_reproduce_ultimo_mensaje_asistente():
    """evento_regenerar activo invoca reproducir_voz con la última respuesta del asistente y limpia el evento."""
    evento_reinicio = threading.Event()
    evento_regenerar = threading.Event()
    evento_regenerar.set()

    contexto = [
        {"role": "system", "content": main_module.SYSTEM_PROMPT},
        {"role": "user", "content": "¿cuál es tu nombre?"},
        {"role": "assistant", "content": "Mi nombre es Jinx."},
    ]

    api_js = MagicMock()
    panel = MagicMock()

    with patch.object(main_module, "reproducir_voz") as mock_voz:
        contexto_nuevo, manejado = main_module.procesar_eventos_panel(
            contexto,
            evento_reinicio,
            evento_regenerar,
            api_js,
            panel,
        )

        assert manejado is True
        assert not evento_regenerar.is_set()
        assert contexto_nuevo == contexto
        mock_voz.assert_called_once_with("Mi nombre es Jinx.")


def test_eventos_inactivos_no_modifican_contexto_y_retornan_false():
    """Si ambos eventos están inactivos, manejado es False y el contexto no cambia."""
    evento_reinicio = threading.Event()
    evento_regenerar = threading.Event()

    contexto = [
        {"role": "system", "content": main_module.SYSTEM_PROMPT},
        {"role": "user", "content": "pregunta"},
    ]

    api_js = MagicMock()
    panel = MagicMock()

    with patch.object(main_module, "reproducir_voz") as mock_voz:
        contexto_nuevo, manejado = main_module.procesar_eventos_panel(
            contexto,
            evento_reinicio,
            evento_regenerar,
            api_js,
            panel,
        )

        assert manejado is False
        assert contexto_nuevo == contexto
        mock_voz.assert_not_called()
