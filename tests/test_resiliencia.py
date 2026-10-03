"""
tests/test_resiliencia.py
=========================
Pruebas de inyección de fallos y resiliencia para JinxAS:
- Ollama no disponible / error de inferencia
- Micrófono desconectado / PyAudio inaccesible
- Conexión a internet no disponible para clima y TTS
- Caché FAISS / manifiesto corrupto
- Bóveda de Obsidian vacía o inexistente
- Hardware térmico sin sensores (fallback CPU)
- Argumentos malformados en llamadas a herramientas
"""

from unittest.mock import MagicMock, patch
import pytest

from jinxas import config
from jinxas.cerebro import procesar_pensamiento, procesar_pensamiento_stream
from jinxas.herramientas import obtener_clima, obtener_temperatura
from jinxas.memoria import guardar_nota
from jinxas.memoria_rag import buscar_en_notas, construir_indice, _cargar_manifiesto
from jinxas.percepcion import MicrofonoNoDisponible, escuchar_y_transcribir
from jinxas.voz import reproducir_voz
from jinxas.__main__ import _extraer_llamada


def test_resiliencia_ollama_caido_pensamiento_sincrono():
    """Si Ollama no responde, procesar_pensamiento devuelve respuesta de contingencia sin crashear."""
    with patch("jinxas.cerebro.ollama.chat", side_effect=ConnectionError("Ollama daemon caido")):
        resp = procesar_pensamiento([{"role": "user", "content": "hola"}])
        assert isinstance(resp, dict)
        contenido = resp.get("content", "") or resp.get("message", {}).get("content", "")
        assert "no pude pensar" in contenido.lower() or "problema" in contenido.lower()


def test_resiliencia_ollama_caido_pensamiento_stream():
    """Si Ollama falla en streaming, emite chunk de error con _error=True."""
    with patch("jinxas.cerebro.ollama.chat", side_effect=RuntimeError("Servicio inaccesible")):
        chunks = list(procesar_pensamiento_stream([{"role": "user", "content": "hola"}]))
        assert len(chunks) == 1
        assert chunks[0].get("_error") is True
        assert "No pude pensar" in chunks[0]["message"]["content"]


def test_resiliencia_microfono_no_disponible():
    """Si PyAudio no encuentra dispositivos de entrada, se propaga MicrofonoNoDisponible."""
    rec = MagicMock()
    # Simular que rec.listen lanza OSError (hardware ausente)
    rec.listen.side_effect = OSError("No default input device available")

    with patch("jinxas.percepcion.sr.Recognizer", return_value=rec), \
         patch("jinxas.percepcion.sr.Microphone", side_effect=OSError("Dispositivo no encontrado")):
        with pytest.raises(MicrofonoNoDisponible):
            escuchar_y_transcribir()


def test_resiliencia_clima_sin_internet():
    """Si wttr.in no responde por falta de conexion o timeout, devuelve mensaje informativo."""
    with patch("jinxas.herramientas.requests.get", side_effect=Exception("Fallo DNS o timeout")):
        resultado = obtener_clima()
        assert "no se pudo obtener el clima" in resultado.lower() or "error" in resultado.lower()


def test_resiliencia_temperatura_fallback():
    """Si PowerShell/WMI no expone sensores termicos, usa el porcentaje de CPU como fallback honesto."""
    with patch("jinxas.herramientas.subprocess.run", side_effect=OSError("No PowerShell")):
        with patch("jinxas.herramientas.psutil.cpu_percent", return_value=15.5):
            res = obtener_temperatura()
            assert "15.5%" in res or "sensores" in res.lower()


def test_resiliencia_tts_error_audio():
    """Si edge-tts falla, reproducir_voz no colapsa el hilo y finaliza limpiamente."""
    with patch("jinxas.voz.asyncio.run", side_effect=RuntimeError("Fallo edge-tts")):
        # No debe propagar excepcion hacia arriba
        reproducir_voz("Texto de prueba")


def test_resiliencia_boveda_inexistente(tmp_path, monkeypatch):
    """Si la bóveda no existe, buscar_en_notas no falla y avisa honestamente."""
    ruta_falsa = tmp_path / "boveda_inexistente_12345"
    monkeypatch.setattr(config, "RUTA_VAULT", str(ruta_falsa))

    construir_indice()
    res = buscar_en_notas("inteligencia artificial")
    assert (
        "vacío" in res.lower()
        or "no existe" in res.lower()
        or "sin notas" in res.lower()
        or "no encontré" in res.lower()
        or "no se encontró" in res.lower()
    )


def test_resiliencia_boveda_vacia(tmp_path, monkeypatch):
    """Si la bóveda está vacía, construir_indice y buscar_en_notas no lanzan excepciones."""
    boveda_vacia = tmp_path / "boveda_vacia"
    boveda_vacia.mkdir()
    monkeypatch.setattr(config, "RUTA_VAULT", str(boveda_vacia))

    construir_indice()
    res = buscar_en_notas("cualquier cosa")
    assert isinstance(res, str)


def test_resiliencia_cache_rag_corrupta(tmp_path, monkeypatch):
    """Si el archivo de manifiesto en .jinx_cache contiene JSON corrupto, se descarta limpiamente."""
    cache_dir = tmp_path / ".jinx_cache"
    cache_dir.mkdir()
    manifiesto_corrupto = cache_dir / "manifiesto.json"
    manifiesto_corrupto.write_text("ESTO NO ES UN JSON VALIDO {[[[", encoding="utf-8")

    monkeypatch.setattr(config, "RUTA_VAULT", str(tmp_path))

    resultado = _cargar_manifiesto()
    assert resultado == {}


def test_resiliencia_tool_call_json_invalido():
    """Si el modelo emite un tool_call con JSON malformado, _extraer_llamada lo neutraliza."""
    tool_call_corrupto = {
        "function": {
            "name": "abrir_aplicacion",
            "arguments": "ESTE STRING NO ES JSON {abc:",
        }
    }
    nombre, args = _extraer_llamada(tool_call_corrupto)
    assert nombre == "abrir_aplicacion"
    assert args == {}


def test_resiliencia_guardar_nota_permisos_error(tmp_path, monkeypatch):
    """Si open() lanza OSError al guardar nota, devuelve mensaje de error sin crashear."""
    monkeypatch.setattr(config, "RUTA_VAULT", str(tmp_path))
    from jinxas import memoria
    monkeypatch.setattr(memoria, "RUTA_VAULT", str(tmp_path))

    with patch("builtins.open", side_effect=PermissionError("Acceso denegado")):
        res = guardar_nota("Nota Imposible", "Contenido")
        assert "error" in res.lower() or "acceso" in res.lower() or "no pude" in res.lower()
