import os
import sys
from unittest.mock import MagicMock

# Permitir importaciones directas de módulos migrados a jinxas/ para retrocompatibilidad
_jinxas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jinxas")
if _jinxas_dir not in sys.path:
    sys.path.insert(0, _jinxas_dir)

# Mockear librerías pesadas para que pytest no las cargue ni consuma RAM
for nombre in (
    "whisper",
    "speech_recognition",
    "pygame",
    "edge_tts",
    "ollama",
    "faiss",
    "sentence_transformers",
    "webview",
    "psutil",
    "thefuzz",
    "thefuzz.fuzz",
):
    sys.modules.setdefault(nombre, MagicMock())

import jinxas.__main__ as _jm
sys.modules["main"] = _jm

