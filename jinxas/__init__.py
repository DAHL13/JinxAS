"""
jinxas — Asistente de voz local para PC con STT, LLM y RAG autónomos.
"""
from __future__ import annotations

import os
import sys

# Asegurar que el directorio del paquete esté en sys.path para resolución de módulos internos
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

__version__ = "0.5.0"
