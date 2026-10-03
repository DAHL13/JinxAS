"""
tests/test_rag_faiss_real.py
=============================
Pruebas con FAISS real (sin mocks) para H-026.
Valida la escritura atómica en disco, recarga de caché, remove_ids y ntotal.
"""
import importlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from jinxas import config, memoria_rag


class ModeloDeterminista:
    """Generador determinista de embeddings normalizados para pruebas con FAISS real."""

    def __init__(self, dim: int = 16):
        self.dim = dim
        self.encode_calls = 0

    def get_sentence_embedding_dimension(self) -> int:
        return self.dim

    def get_embedding_dimension(self) -> int:
        return self.dim

    def encode(self, textos, batch_size=32, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True):
        self.encode_calls += 1
        np.random.seed(len(textos) + 123)
        vecs = np.random.randn(len(textos), self.dim).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return (vecs / norms).astype(np.float32)


@pytest.fixture
def env_faiss_real(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    monkeypatch.setattr(config, "RUTA_VAULT", str(vault))
    monkeypatch.setattr(config, "RUTA_CACHE", str(cache_dir))
    monkeypatch.setattr(config, "MAX_CHARS_CHUNK", 900)
    monkeypatch.setattr(config, "UMBRAL_SIMILITUD_RAG", 0.1)

    importlib.reload(memoria_rag)
    monkeypatch.setattr(memoria_rag, "RUTA_VAULT", str(vault), raising=False)
    monkeypatch.setattr(memoria_rag, "config", config)

    modelo = ModeloDeterminista(dim=16)
    monkeypatch.setattr(memoria_rag, "_obtener_modelo", lambda: modelo)

    # Limpiar estado
    memoria_rag._indice = None
    memoria_rag._fragmentos = []
    memoria_rag._origenes = []
    memoria_rag._indexando = False
    memoria_rag._reindex_pendiente = False

    return {
        "vault": vault,
        "cache": cache_dir,
        "modelo": modelo,
    }


def test_faiss_real_construccion_y_escritura_atomica(env_faiss_real):
    """Construye índice con FAISS real, escribe caché y valida ntotal."""
    vault = env_faiss_real["vault"]
    cache = env_faiss_real["cache"]

    (vault / "nota1.md").write_text("# Nota 1\nContenido de la primera nota.", encoding="utf-8")
    (vault / "nota2.md").write_text("# Nota 2\nContenido de la segunda nota.", encoding="utf-8")

    total = memoria_rag.construir_indice()
    assert total == 2

    # Verificar archivos de caché creados
    idx_path = cache / "indice.faiss"
    man_path = cache / "manifiesto.json"
    assert idx_path.exists()
    assert man_path.exists()
    assert not Path(str(idx_path) + ".tmp").exists()
    assert not Path(str(man_path) + ".tmp").exists()

    # Cargar directamente con FAISS y comprobar ntotal
    idx_real = faiss.read_index(str(idx_path))
    assert idx_real.ntotal == 2

    with open(man_path, "r", encoding="utf-8") as f:
        man = json.load(f)
    assert man["nota1.md"]["size"] > 0
    assert "sha1" in man["nota1.md"]


def test_faiss_real_recarga_cache_sin_revectorizar(env_faiss_real):
    """Verifica que en una segunda llamada sin cambios se recarga FAISS de disco sin llamadas a encode."""
    vault = env_faiss_real["vault"]
    modelo = env_faiss_real["modelo"]

    (vault / "nota_a.md").write_text("# Nota A\nTexto A estable.", encoding="utf-8")
    memoria_rag.construir_indice()
    llamadas_iniciales = modelo.encode_calls
    assert llamadas_iniciales >= 1

    # Resetear memoria RAM para forzar lectura de disco
    memoria_rag._indice = None
    memoria_rag._fragmentos = []
    memoria_rag._origenes = []

    total = memoria_rag.construir_indice()
    assert total == 1
    # No debe re-vectorizar la nota estable
    assert modelo.encode_calls == llamadas_iniciales


def test_faiss_real_remove_ids_al_eliminar_nota(env_faiss_real):
    """Verifica que al eliminar una nota de la bóveda, remove_ids decrementa ntotal en FAISS."""
    vault = env_faiss_real["vault"]
    cache = env_faiss_real["cache"]

    nota_quedara = vault / "firme.md"
    nota_borrar = vault / "borrable.md"
    nota_quedara.write_text("# Firme\nPermanece.", encoding="utf-8")
    nota_borrar.write_text("# Borrable\nSera eliminada.", encoding="utf-8")

    memoria_rag.construir_indice()
    assert memoria_rag._indice.ntotal == 2

    # Eliminar nota del disco
    os.remove(str(nota_borrar))

    memoria_rag.construir_indice()
    assert memoria_rag._indice.ntotal == 1

    # El índice persistido en disco también debe tener ntotal == 1
    idx_disco = faiss.read_index(str(cache / "indice.faiss"))
    assert idx_disco.ntotal == 1
    assert "borrable.md" not in [f["archivo"] for f in memoria_rag._fragmentos]
