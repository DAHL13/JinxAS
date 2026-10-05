"""
tests/test_h033_rag_boveda_ausente.py
=====================================
Pruebas para H-033: construir_indice no descarta _reindex_pendiente cuando la bóveda no existe.
"""
import os
from unittest.mock import patch

from tests.test_f3_rag import _crear_nota

pytest_plugins = ("tests.test_f3_rag",)


def test_boveda_ausente_con_reindex_pendiente_reintenta_e_indexa(env_rag):
    """Si la bóveda no existe en la primera pasada pero se marca _reindex_pendiente y se crea, se indexa en la segunda."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]

    # Eliminar la bóveda creada por el fixture para que inicialmente no exista
    vault.rmdir()

    orig_isdir = os.path.isdir
    llamadas = 0

    def isdir_side_effect(ruta):
        nonlocal llamadas
        llamadas += 1
        if llamadas == 1:
            with rag._lock_flag:
                rag._reindex_pendiente = True
            vault.mkdir(parents=True, exist_ok=True)
            _crear_nota(vault, "nota_tardia.md", "# Nota Tardía\nContenido creado durante la primera pasada.")
            return False
        return orig_isdir(ruta)

    with patch.object(rag.os.path, "isdir", side_effect=isdir_side_effect):
        chunks = rag.construir_indice()

    assert chunks >= 1
    archivos_indexados = {f["archivo"] for f in rag._fragmentos}
    assert "nota_tardia.md" in archivos_indexados
    assert rag._reindex_pendiente is False

    adquirido = rag._lock_construir.acquire(blocking=False)
    assert adquirido is True
    rag._lock_construir.release()


def test_boveda_ausente_sin_reindex_pendiente_retorna_cero_y_libera_cerrojo(env_rag):
    """Si la bóveda no existe y no hay petición pendiente, retorna 0 y libera _lock_construir."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]

    vault.rmdir()

    chunks = rag.construir_indice()
    assert chunks == 0
    assert rag._indice is None
    assert rag._fragmentos == []
    assert rag._origenes == []

    adquirido = rag._lock_construir.acquire(blocking=False)
    assert adquirido is True
    rag._lock_construir.release()
