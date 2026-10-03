"""
tests/test_h018_rag_integridad.py
=================================
Pruebas de integridad del caché RAG para H-018:
1. Manifiesto existente pero sin indice.faiss -> reindexa todo desde cero.
2. Fallo en faiss.write_index -> no se escribe el manifiesto (escritura atómica consistente).
3. ntotal del índice desfasado respecto a los IDs del manifiesto -> reconstrucción completa.
4. _sha1_archivo no se llama cuando mtime y size coinciden (SHA-1 perezoso).
5. Reindexación pendiente tras llamada concurrente.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

from tests.test_f3_rag import _crear_nota

pytest_plugins = ("tests.test_f3_rag",)


def test_manifiesto_sin_indice_reindexa_todo(env_rag):
    """Si existe un manifiesto con notas pero falta indice.faiss, descarta caché y reindexa todo."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]
    cfg = env_rag["config"]

    _crear_nota(vault, "nota1.md", "# Nota 1\nContenido de prueba.")
    cache_dir = Path(rag._cache_dir())
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Crear manifiesto huérfano (sin indice.faiss)
    manifiesto = {
        "modelo": cfg.MODELO_EMBEDDINGS,
        "max_chars_chunk": 900,
        "next_id": 1,
        "nota1.md": {"mtime": 1000.0, "size": 30, "sha1": "abc", "ids": [0], "chunks": ["# Nota 1\nContenido"]}
    }
    with open(rag._ruta_manifiesto(), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f)

    assert not Path(rag._ruta_indice()).exists()

    # Al construir índice, debe detectar la falta de indice.faiss, descartar y vectorizar
    chunks = rag.construir_indice()
    assert chunks >= 1
    assert env_rag["modelo"].encode_calls >= 1


def test_fallo_write_index_no_escribe_manifiesto(env_rag):
    """Si faiss.write_index falla, la escritura atómica aborta y NO se escribe el manifiesto."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]
    faiss_mod = env_rag["faiss"]

    _crear_nota(vault, "nota_fail.md", "# Falla\nTexto.")
    faiss_mod.write_index.side_effect = IOError("Disco lleno o permiso denegado")

    manifiesto_path = Path(rag._ruta_manifiesto())
    if manifiesto_path.exists():
        manifiesto_path.unlink()

    rag.construir_indice()

    # El manifiesto NO debe haberse escrito
    assert not manifiesto_path.exists()


def test_ntotal_desfasado_reconstruye_completo(env_rag):
    """Si ntotal en el índice cargado no coincide con la suma de IDs del manifiesto, se reconstruye todo."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]
    cfg = env_rag["config"]
    faiss_mod = env_rag["faiss"]

    _crear_nota(vault, "nota_desfasada.md", "# Nota\nContenido.")
    cache_dir = Path(rag._cache_dir())
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Crear archivo de índice simulado
    Path(rag._ruta_indice()).write_text("fake index", encoding="utf-8")

    # Manifiesto con 2 IDs esperados
    manifiesto = {
        "modelo": cfg.MODELO_EMBEDDINGS,
        "max_chars_chunk": 900,
        "next_id": 2,
        "nota_desfasada.md": {"mtime": 1000.0, "size": 30, "sha1": "abc", "ids": [0, 1], "chunks": ["c1", "c2"]}
    }
    with open(rag._ruta_manifiesto(), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f)

    # Mock de read_index que devuelve un índice con ntotal = 1 (desfasado de 2)
    fake_idx = MagicMock()
    fake_idx.ntotal = 1
    faiss_mod.read_index.side_effect = None
    faiss_mod.read_index.return_value = fake_idx

    chunks = rag.construir_indice()
    assert chunks >= 1
    # Debe haber re-vectorizado porque descartó el caché inconsistente
    assert env_rag["modelo"].encode_calls >= 1


def test_sha1_perezoso_no_calcula_hash_si_mtime_y_size_coinciden(env_rag):
    """No se calcula SHA-1 si mtime y size coinciden con la entrada previa en el manifiesto."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]

    _crear_nota(vault, "nota_estable.md", "# Estable\nContenido constante sin cambios.")

    # Primera indexación: genera manifiesto con mtime, size y sha1
    rag.construir_indice()

    # Segunda indexación: con mtime y size intactos, _sha1_archivo no debe llamarse para ese archivo
    with patch.object(rag, "_sha1_archivo", wraps=rag._sha1_archivo) as mock_sha1:
        rag.construir_indice()
        mock_sha1.assert_not_called()


def test_reindexacion_pendiente_tras_llamada_concurrente(env_rag):
    """Si una llamada ocurre mientras ya se está construyendo el índice, queda pendiente y se ejecuta al terminar."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]

    _crear_nota(vault, "nota_base.md", "# Base\nContenido base.")
    rag.construir_indice()

    # Simular bloqueo: adquirir cerrojo manualmente
    adquirido = rag._lock_construir.acquire(blocking=False)
    assert adquirido is True

    try:
        # Llamada mientras está bloqueado: marca reindexación pendiente
        rag.construir_indice()
        assert rag._reindex_pendiente is True
    finally:
        rag._lock_construir.release()

    # Al ejecutar nuevamente con el cerrojo libre, debe consumir el pendiente
    _crear_nota(vault, "nota_nueva.md", "# Nueva\nContenido adicional.")
    rag._reindex_pendiente = True
    rag.construir_indice()
    assert rag._reindex_pendiente is False
    assert any("nota_nueva.md" in f["archivo"] for f in rag._fragmentos)
