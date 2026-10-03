import os
import sys
from unittest.mock import MagicMock

# Permitir importaciones directas de módulos migrados a jinxas/ para retrocompatibilidad
_jinxas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jinxas")
if _jinxas_dir not in sys.path:
    sys.path.insert(0, _jinxas_dir)

import importlib

# Mockear librerías pesadas para que pytest no las cargue ni consuma RAM
for nombre in (
    "whisper",
    "speech_recognition",
    "pygame",
    "edge_tts",
    "ollama",
    "sentence_transformers",
    "webview",
):
    sys.modules.setdefault(nombre, MagicMock())


def _mock_si_falta(nombre: str) -> None:
    try:
        mod = importlib.import_module(nombre)
        if nombre == "psutil" and not hasattr(mod, "sensors_temperatures"):
            mod.sensors_temperatures = MagicMock()
    except ImportError:
        sys.modules.setdefault(nombre, MagicMock())


for nombre in ("faiss", "thefuzz", "psutil"):
    _mock_si_falta(nombre)

import jinxas.__main__ as _jm
sys.modules["main"] = _jm

