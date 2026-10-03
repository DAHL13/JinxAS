"""
tests/test_h023_abrir_navegadores.py
====================================
Pruebas para H-023: Apertura de navegadores (Edge, Chrome) mediante ShellExecute (app:).
Valida que se use os.startfile para tipo 'app:' y 'uri:', subprocess para 'exe:',
y que el allowlist rechace aplicaciones no autorizadas.
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from jinxas import herramientas


@pytest.fixture
def mock_startfile(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(os, "startfile", mock, raising=False)
    return mock


@pytest.mark.parametrize("app,objetivo_esperado", [
    ("navegador", "msedge"),
    ("edge", "msedge"),
    ("chrome", "chrome"),
])
def test_abrir_navegadores_tipo_app(mock_startfile, app, objetivo_esperado):
    """Las entradas de navegador tipo app: deben invocar os.startfile con el binario correspondiente."""
    res = herramientas.abrir_aplicacion(app)
    assert f"Abriendo {app}" in res
    mock_startfile.assert_called_with(objetivo_esperado)


def test_abrir_app_tipo_uri(mock_startfile):
    """Aplicaciones con prefijo uri: deben invocar os.startfile con la URI."""
    res = herramientas.abrir_aplicacion("spotify")
    assert "Abriendo spotify" in res
    mock_startfile.assert_called_with("spotify:")


def test_abrir_app_tipo_exe():
    """Aplicaciones con prefijo exe: deben validar con shutil.which y ejecutar con Popen."""
    with patch("shutil.which", return_value="C:\\Windows\\System32\\calc.exe"), \
         patch("subprocess.Popen") as mock_popen:
        res = herramientas.abrir_aplicacion("calculadora")
        assert "Abriendo calculadora" in res
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0] == ["C:\\Windows\\System32\\calc.exe"]
        assert kwargs["shell"] is False


def test_abrir_app_no_permitida():
    """Nombres fuera de MAPA_APLICACIONES deben ser rechazados."""
    res = herramientas.abrir_aplicacion("malware.exe")
    assert "no está permitida" in res


def test_abrir_app_error_os(mock_startfile):
    """Si os.startfile lanza OSError, la función debe capturarlo y avisar amablemente."""
    mock_startfile.side_effect = OSError("Acceso denegado")
    res = herramientas.abrir_aplicacion("chrome")
    assert res == "No pude abrir chrome."
