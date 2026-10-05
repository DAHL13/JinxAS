"""
tests/test_h029_rag_robustez.py
================================
Pruebas para H-029: Robustez del RAG:
1. Fallo al guardar manifiesto no interrumpe disponibilidad de buscar_semantica.
2. _escritura_atomica lanza OSError si escribir() no genera el archivo temporal.
3. Sincronización concurrente de construcción sin pérdida (vía threading.Event).
4. Vaciado de notas limpia IDs y entradas sin provocar reconstrucción total en reinicio.
"""
import threading
from unittest.mock import patch
import pytest

from tests.test_f3_rag import _crear_nota

pytest_plugins = ("tests.test_f3_rag",)


def test_guardar_manifiesto_falla_mantiene_busqueda_semantica(env_rag):
    """Si _guardar_manifiesto lanza excepción, se publica el índice y buscar_semantica sigue operativa."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]

    _crear_nota(vault, "nota_valiosa.md", "# Conocimiento Clave\nEste es un dato fundamental para el asistente.")

    with patch.object(rag, "_guardar_manifiesto", side_effect=IOError("Permiso denegado al escribir manifiesto")):
        chunks = rag.construir_indice()
        assert chunks >= 1
        assert rag._indice is not None
        assert len(rag._fragmentos) >= 1

        # En esa misma sesión buscar_semantica debe responder con éxito usando el índice en memoria
        resultado = rag.buscar_semantica("dato fundamental", top_k=1)
        assert "nota_valiosa.md" in resultado
        assert "dato fundamental" in resultado


def test_escritura_atomica_lanza_oserror_si_no_crea_temporal(tmp_path, env_rag):
    """_escritura_atomica lanza OSError si la función de escritura no crea el archivo temporal."""
    rag = env_rag["rag"]
    destino = tmp_path / "salida.dat"

    def escritor_defectuoso(tmp):
        pass  # No crea el archivo tmp

    with pytest.raises(OSError, match="La escritura atómica no generó el archivo temporal"):
        rag._escritura_atomica(str(destino), escritor_defectuoso)

    assert not destino.exists()


def test_concurrencia_construir_indice_sin_perdida(env_rag):
    """Una llamada concurrente durante la construcción activa _reindex_pendiente y no pierde notas."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]
    modelo = env_rag["modelo"]

    _crear_nota(vault, "nota_hilo1.md", "# Hilo 1\nContenido del primer hilo.")

    evento_en_pasada = threading.Event()
    evento_continuar = threading.Event()
    orig_encode = modelo.encode

    def encode_con_pausa(textos, **kwargs):
        res = orig_encode(textos, **kwargs)
        if not evento_en_pasada.is_set():
            evento_en_pasada.set()
            evento_continuar.wait(timeout=5.0)
        return res

    with patch.object(modelo, "encode", side_effect=encode_con_pausa):
        hilo_constructor = threading.Thread(target=rag.construir_indice)
        hilo_constructor.start()

        # Esperar a que el constructor esté dentro de su primera pasada
        assert evento_en_pasada.wait(timeout=5.0) is True

        # Mientras el constructor está trabajando, agregamos una segunda nota y disparamos llamada concurrente
        _crear_nota(vault, "nota_hilo2.md", "# Hilo 2\nContenido del segundo hilo agregado concurrentemente.")
        rag.construir_indice()
        # La llamada concurrente detecta ejecución en progreso y marca reindexación pendiente
        assert rag._reindex_pendiente is True

        # Permitir que el primer hilo continúe: al terminar su pasada debe procesar la reindexación pendiente
        evento_continuar.set()
        hilo_constructor.join(timeout=5.0)

    assert not hilo_constructor.is_alive()
    assert rag._reindex_pendiente is False

    # Ambas notas deben estar indexadas en los fragmentos en memoria
    archivos_indexados = {f["archivo"] for f in rag._fragmentos}
    assert "nota_hilo1.md" in archivos_indexados
    assert "nota_hilo2.md" in archivos_indexados


def test_vaciar_nota_no_provoca_reconstruccion_completa(env_rag):
    """Vaciar una nota existente actualiza el manifiesto eliminando la entrada y no reindexa todo en el reinicio."""
    vault = env_rag["vault"]
    rag = env_rag["rag"]
    modelo = env_rag["modelo"]

    _crear_nota(vault, "nota_vaciable.md", "# A Borrar\nTexto que luego será vaciado.")
    _crear_nota(vault, "nota_persistente.md", "# Persistente\nEste contenido se mantiene intacto.")

    # 1. Primera construcción: ambas notas se vectorizan
    rag.construir_indice()
    calls_iniciales = modelo.encode_calls
    assert calls_iniciales >= 1

    manifiesto = rag._cargar_manifiesto()
    assert "nota_vaciable.md" in manifiesto
    assert "nota_persistente.md" in manifiesto

    # 2. Vaciamos nota_vaciable.md
    ruta_vaciable = vault / "nota_vaciable.md"
    ruta_vaciable.write_text("", encoding="utf-8")

    # Segunda construcción: detecta nota vacía, remueve sus IDs y hace entradas.pop("nota_vaciable.md")
    rag.construir_indice()

    manifiesto_actualizado = rag._cargar_manifiesto()
    assert "nota_vaciable.md" not in manifiesto_actualizado
    assert "nota_persistente.md" in manifiesto_actualizado

    calls_tras_vaciado = modelo.encode_calls
    # No debería haber necesitado re-vectorizar nota_persistente
    assert calls_tras_vaciado == calls_iniciales

    # 3. Simular reinicio (construir_indice de nuevo sobre la misma caché)
    rag.construir_indice()

    # Si hubiera habido desfase de ntotal, se habría descartado la caché y encode_calls habría aumentado
    calls_tras_reinicio = modelo.encode_calls
    assert calls_tras_reinicio == calls_tras_vaciado
