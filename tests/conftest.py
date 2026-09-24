import sys
from unittest.mock import MagicMock

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
):
    sys.modules.setdefault(nombre, MagicMock())
