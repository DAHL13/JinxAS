"""
tests/test_f3_rag.py
====================
Pruebas unitarias para F3-01, F3-02 y F3-05 del roadmap de consolidacion.

- Test a: dividir_en_chunks (chunking contextual)
- Test b: indexacion incremental (cache .jinx_cache)
- Test c: consistencia guardar_nota <-> construir_indice

Modelo de embeddings mockeado con contador de llamadas a encode.
Bóveda temporal con tmp_path + monkeypatch sobre RUTA_VAULT y config.
"""
import importlib
import json
import os
import time
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers para el mock del modelo de embeddings
# ---------------------------------------------------------------------------

class ModeloMock:
    """
    Simula SentenceTransformer devolviendo vectores unitarios deterministas.
    Cuenta cuantas veces se llamo a encode para verificar indexacion incremental.
    """

    def __init__(self, dim: int = 8):
        self.dim = dim
        self.encode_calls = 0
        self.encode_texts = []

    def get_sentence_embedding_dimension(self) -> int:
        return self.dim

    def get_embedding_dimension(self) -> int:
        return self.dim

    def encode(self, textos, batch_size=32, show_progress_bar=False,
               convert_to_numpy=True, normalize_embeddings=False):
        self.encode_calls += 1
        self.encode_texts.extend(textos)
        n = len(textos)
        # Vectores unitarios (similitud coseno = 1 consigo mismo)
        vecs = np.ones((n, self.dim), dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return (vecs / norms).astype(np.float32)


# ---------------------------------------------------------------------------
# Fixture principal: vault temporal + mocks de faiss y modelo
# ---------------------------------------------------------------------------

@pytest.fixture()
def env_rag(tmp_path, monkeypatch):
    """
    Configura un entorno RAG aislado:
    - RUTA_VAULT apunta a tmp_path/vault
    - faiss mockeado con implementacion minima funcional
    - modelo de embeddings reemplazado por ModeloMock
    - modulos config y memoria_rag recargados
    """
    vault = tmp_path / "vault"
    vault.mkdir()

    monkeypatch.setenv("JINX_VAULT", str(vault))

    # ---- Mock de faiss minimal pero funcional ----------------------------
    import faiss as faiss_mod  # ya mockeado por conftest.py

    dim = 8

    class FaissIndexMock:
        def __init__(self):
            self._vectors = {}   # id (int) -> ndarray(dim,)
            self.ntotal = 0

        def add_with_ids(self, vecs, ids):
            for vec, id_ in zip(vecs, ids):
                self._vectors[int(id_)] = vec.copy()
            self.ntotal = len(self._vectors)

        def remove_ids(self, ids_arr):
            for id_ in ids_arr:
                self._vectors.pop(int(id_), None)
            self.ntotal = len(self._vectors)

        def search(self, query_vec, k):
            if not self._vectors:
                return np.array([[-1.0] * k]), np.array([[-1] * k])
            q = query_vec[0]
            scored = []
            for id_, vec in self._vectors.items():
                score = float(np.dot(q, vec))
                scored.append((score, id_))
            scored.sort(key=lambda x: -x[0])
            top = scored[:k]
            while len(top) < k:
                top.append((-1.0, -1))
            scores = np.array([[s for s, _ in top]], dtype=np.float32)
            idxs = np.array([[i for _, i in top]], dtype=np.int64)
            return scores, idxs

    def make_index(*args, **kwargs):
        return FaissIndexMock()

    faiss_mod.IndexFlatIP = MagicMock(side_effect=make_index)
    faiss_mod.IndexFlatL2 = MagicMock(side_effect=make_index)
    faiss_mod.IndexIDMap2 = MagicMock(side_effect=lambda inner: inner)
    faiss_mod.write_index = MagicMock()  # no escribe en disco (aislado)
    faiss_mod.read_index = MagicMock(side_effect=Exception("no cache"))  # fuerza reconstruccion

    # ---- Recargar config con el vault temporal ---------------------------
    import config
    importlib.reload(config)
    monkeypatch.setattr(config, "RUTA_VAULT", str(vault))
    monkeypatch.setattr(config, "MAX_CHARS_CHUNK", 900)
    monkeypatch.setattr(config, "UMBRAL_SIMILITUD_RAG", 0.35)

    # ---- Recargar memoria_rag y resetear estado global ------------------
    import memoria_rag
    importlib.reload(memoria_rag)
    monkeypatch.setattr(memoria_rag, "RUTA_VAULT", str(vault), raising=False)

    # Inyectar config en memoria_rag
    monkeypatch.setattr(memoria_rag, "config", config)

    # Resetear estado global del modulo
    memoria_rag._indice = None
    memoria_rag._fragmentos = []
    memoria_rag._origenes = []
    memoria_rag._indexando = False
    memoria_rag._modelo_embedding = None

    # ---- Instalar el modelo mock ----------------------------------------
    modelo_mock = ModeloMock(dim=dim)
    monkeypatch.setattr(memoria_rag, "_obtener_modelo", lambda: modelo_mock)

    yield {
        "vault": vault,
        "config": config,
        "rag": memoria_rag,
        "modelo": modelo_mock,
        "faiss": faiss_mod,
    }

    # Restaurar
    memoria_rag._indice = None
    memoria_rag._fragmentos = []
    memoria_rag._origenes = []
    memoria_rag._modelo_embedding = None
    importlib.reload(config)
    importlib.reload(memoria_rag)


def _crear_nota(vault, relpath: str, contenido: str):
    ruta = vault / relpath
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


# ===========================================================================
# Test a: dividir_en_chunks
# ===========================================================================

class TestDividirEnChunks:

    def test_prefija_titulo_en_cada_chunk(self, env_rag):
        rag = env_rag["rag"]
        titulo = "Mi Nota"
        texto = "Parrafo uno.\n\nParrafo dos."
        chunks = rag.dividir_en_chunks(texto, titulo, max_chars=900)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.startswith(titulo + "\n"), f"Chunk sin prefijo: {chunk[:40]!r}"

    def test_corte_por_encabezado_markdown(self, env_rag):
        rag = env_rag["rag"]
        titulo = "Nota"
        texto = "# Seccion Uno\n\nContenido de la seccion uno.\n\n## Seccion Dos\n\nContenido de la seccion dos."
        chunks = rag.dividir_en_chunks(texto, titulo, max_chars=900)
        # Cada seccion debe generar al menos un chunk
        assert len(chunks) >= 2
        textos_concatenados = " ".join(chunks)
        assert "Seccion Uno" in textos_concatenados
        assert "Seccion Dos" in textos_concatenados

    def test_parrafos_acumulados_hasta_max_chars(self, env_rag):
        rag = env_rag["rag"]
        titulo = "Nota"
        # Dos parrafos cortos que caben juntos en 900 chars
        texto = "Parrafo A.\n\nParrafo B."
        chunks = rag.dividir_en_chunks(texto, titulo, max_chars=900)
        # Deben acabar en un solo chunk
        assert len(chunks) == 1
        assert "Parrafo A" in chunks[0]
        assert "Parrafo B" in chunks[0]

    def test_parrafo_gigante_partido_por_frases(self, env_rag):
        rag = env_rag["rag"]
        titulo = "Nota"
        # Un parrafo que supera max_chars=50
        parrafo = "Primera frase larga aqui. Segunda frase larga aqui tambien. Tercera frase mas."
        chunks = rag.dividir_en_chunks(parrafo, titulo, max_chars=50)
        # Debe haber mas de un chunk
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.startswith(titulo + "\n")

    def test_texto_vacio_genera_lista_vacia(self, env_rag):
        rag = env_rag["rag"]
        chunks = rag.dividir_en_chunks("", "Nota", max_chars=900)
        assert chunks == []

    def test_texto_solo_espacios_genera_lista_vacia(self, env_rag):
        rag = env_rag["rag"]
        chunks = rag.dividir_en_chunks("   \n\n   ", "Nota", max_chars=900)
        assert chunks == []

    def test_chunk_no_supera_max_chars_mas_titulo(self, env_rag):
        rag = env_rag["rag"]
        titulo = "T"
        # Texto con parrafos largos
        texto = ("Frase corta. " * 20).strip()
        chunks = rag.dividir_en_chunks(texto, titulo, max_chars=100)
        for chunk in chunks:
            contenido_chunk = chunk[len(titulo)+1:]  # quitar "T\n"
            assert len(contenido_chunk) <= 120, f"Chunk demasiado largo: {len(contenido_chunk)}"


# ===========================================================================
# Test b: indexacion incremental
# ===========================================================================

class TestIndexacionIncremental:

    def _resetear_estado(self, env_rag):
        """Limpia el estado global del modulo RAG entre llamadas."""
        rag = env_rag["rag"]
        rag._indice = None
        rag._fragmentos = []
        rag._origenes = []
        rag._indexando = False
        env_rag["modelo"].encode_calls = 0
        env_rag["modelo"].encode_texts = []

    def test_primera_indexacion_vectoriza_todas_las_notas(self, env_rag):
        vault = env_rag["vault"]
        rag = env_rag["rag"]

        _crear_nota(vault, "nota1.md", "# Nota 1\n\nContenido de la primera nota.")
        _crear_nota(vault, "nota2.md", "# Nota 2\n\nContenido de la segunda nota.")
        _crear_nota(vault, "nota3.md", "# Nota 3\n\nContenido de la tercera nota.")

        total = rag.construir_indice()
        assert total > 0
        assert env_rag["modelo"].encode_calls >= 1
        assert len(rag._fragmentos) == total

    def test_segunda_ejecucion_sin_cambios_no_re_vectoriza(self, env_rag):
        vault = env_rag["vault"]
        rag = env_rag["rag"]

        _crear_nota(vault, "nota1.md", "# Nota 1\n\nContenido estable.")
        _crear_nota(vault, "nota2.md", "# Nota 2\n\nOtro contenido estable.")
        _crear_nota(vault, "nota3.md", "# Nota 3\n\nMas contenido estable.")

        # Primera indexacion
        rag.construir_indice()
        calls_primera = env_rag["modelo"].encode_calls

        # Guardar manifiesto manualmente (porque write_index esta mockeado)
        # Simulamos que el manifiesto quedo escrito con los datos correctos
        cache_dir = vault / ".jinx_cache"
        cache_dir.mkdir(exist_ok=True)
        manifiesto = {
            "modelo": env_rag["config"].MODELO_EMBEDDINGS,
            "max_chars_chunk": 900,
            "next_id": len(rag._fragmentos),
        }
        # Agregar entradas de cada nota con mtime y sha1 actuales
        import hashlib
        for ruta_rel in ["nota1.md", "nota2.md", "nota3.md"]:
            ruta_completa = vault / ruta_rel
            h = hashlib.sha1()
            with open(ruta_completa, "rb") as f:
                h.update(f.read())
            sha1 = h.hexdigest()
            mtime = os.path.getmtime(str(ruta_completa))
            # Reconstruir chunks del manifiesto
            titulo = ruta_rel.replace(".md", "")
            with open(str(ruta_completa), "r", encoding="utf-8") as f:
                contenido = f.read()
            chunks = rag.dividir_en_chunks(contenido, titulo, max_chars=900)
            start_id = len(manifiesto) - 3  # aproximado
            manifiesto[ruta_rel] = {
                "mtime": mtime,
                "sha1": sha1,
                "ids": list(range(start_id, start_id + len(chunks))),
                "chunks": chunks,
            }
        with open(str(cache_dir / "manifiesto.json"), "w", encoding="utf-8") as f:
            json.dump(manifiesto, f)

        # Resetear contadores
        self._resetear_estado(env_rag)

        # Segunda indexacion (con manifiesto en disco)
        rag.construir_indice()
        calls_segunda = env_rag["modelo"].encode_calls

        assert calls_segunda == 0, (
            f"Segunda indexacion sin cambios llamo a encode {calls_segunda} veces "
            f"(se esperaba 0)"
        )

    def test_nota_modificada_se_re_vectoriza(self, env_rag):
        vault = env_rag["vault"]
        rag = env_rag["rag"]

        nota1 = _crear_nota(vault, "nota_a.md", "# Nota A\n\nContenido original.")
        _crear_nota(vault, "nota_b.md", "# Nota B\n\nContenido que no cambia.")

        # Primera indexacion
        rag.construir_indice()
        calls_primera = env_rag["modelo"].encode_calls

        # Guardar manifiesto con nota_a con hash FALSO para simular cambio detectado
        cache_dir = vault / ".jinx_cache"
        cache_dir.mkdir(exist_ok=True)

        import hashlib
        manifiesto = {
            "modelo": env_rag["config"].MODELO_EMBEDDINGS,
            "max_chars_chunk": 900,
            "next_id": 100,
        }
        # nota_b sin cambios (hash real)
        ruta_b = vault / "nota_b.md"
        h = hashlib.sha1()
        with open(str(ruta_b), "rb") as f:
            h.update(f.read())
        with open(str(ruta_b), "r", encoding="utf-8") as f:
            cont_b = f.read()
        chunks_b = rag.dividir_en_chunks(cont_b, "nota_b", max_chars=900)
        manifiesto["nota_b.md"] = {
            "mtime": os.path.getmtime(str(ruta_b)),
            "sha1": h.hexdigest(),
            "ids": [0],
            "chunks": chunks_b,
        }
        # nota_a con sha1 INVALIDO para forzar re-vectorizacion
        manifiesto["nota_a.md"] = {
            "mtime": os.path.getmtime(str(nota1)),
            "sha1": "sha1_invalido_forzar_cambio",
            "ids": [1],
            "chunks": ["Nota A\nContenido original."],
        }
        with open(str(cache_dir / "manifiesto.json"), "w", encoding="utf-8") as f:
            json.dump(manifiesto, f)

        # Resetear estado
        self._resetear_estado(env_rag)

        # Segunda indexacion: solo nota_a debe re-vectorizarse
        rag.construir_indice()
        calls_segunda = env_rag["modelo"].encode_calls

        assert calls_segunda >= 1, "Se esperaba al menos una llamada a encode para la nota modificada"
        # Los textos codificados deben ser de nota_a, no de nota_b
        textos_codificados = " ".join(env_rag["modelo"].encode_texts)
        assert "Nota A" in textos_codificados, "Se esperaba re-vectorizar chunks de nota_a"

    def test_nota_eliminada_desaparece_de_busquedas(self, env_rag):
        vault = env_rag["vault"]
        rag = env_rag["rag"]

        _crear_nota(vault, "nota_viva.md", "# Nota Viva\n\nContenido que permanece.")
        nota_borrar = _crear_nota(vault, "nota_borrar.md", "# Borrar\n\nEsta nota sera eliminada.")

        # Primera indexacion
        rag.construir_indice()
        fragmentos_primera = len(rag._fragmentos)
        assert fragmentos_primera > 0

        # Simular manifiesto con ambas notas
        cache_dir = vault / ".jinx_cache"
        cache_dir.mkdir(exist_ok=True)

        import hashlib
        manifiesto = {
            "modelo": env_rag["config"].MODELO_EMBEDDINGS,
            "max_chars_chunk": 900,
            "next_id": 50,
        }
        for nombre, ruta in [("nota_viva.md", vault / "nota_viva.md"),
                              ("nota_borrar.md", vault / "nota_borrar.md")]:
            h = hashlib.sha1()
            with open(str(ruta), "rb") as f:
                h.update(f.read())
            with open(str(ruta), "r", encoding="utf-8") as f:
                cont = f.read()
            titulo = nombre.replace(".md", "")
            chunks = rag.dividir_en_chunks(cont, titulo, max_chars=900)
            manifiesto[nombre] = {
                "mtime": os.path.getmtime(str(ruta)),
                "sha1": h.hexdigest(),
                "ids": list(range(manifiesto["next_id"], manifiesto["next_id"] + len(chunks))),
                "chunks": chunks,
            }
            manifiesto["next_id"] += len(chunks)

        with open(str(cache_dir / "manifiesto.json"), "w", encoding="utf-8") as f:
            json.dump(manifiesto, f)

        # Borrar nota_borrar.md del disco
        os.remove(str(nota_borrar))

        # Resetear estado y re-indexar
        self._resetear_estado(env_rag)
        rag.construir_indice()

        # La nota eliminada no debe aparecer en _fragmentos
        archivos_indexados = {f["archivo"] for f in rag._fragmentos}
        assert "nota_borrar.md" not in archivos_indexados, (
            "La nota eliminada no deberia estar en el indice"
        )
        assert "nota_viva.md" in archivos_indexados or any(
            "nota_viva" in f["texto"].lower() for f in rag._fragmentos
        ), "La nota viva debe seguir en el indice"


# ===========================================================================
# Test c: consistencia guardar_nota <-> construir_indice
# ===========================================================================

class TestConsistenciaGuardarNota:

    def test_chunks_guardar_nota_identicos_a_construir_indice(self, env_rag, tmp_path, monkeypatch):
        """
        Guarda una nota con guardar_nota, captura los chunks indexados al vuelo,
        luego reinicia el estado, ejecuta construir_indice y verifica que
        los chunks resultantes son identicos.
        """
        vault = env_rag["vault"]
        rag = env_rag["rag"]
        cfg = env_rag["config"]

        # Recargar memoria con el vault temporal
        import memoria
        importlib.reload(memoria)
        monkeypatch.setattr(memoria, "RUTA_VAULT", str(vault))
        monkeypatch.setattr(memoria, "agregar_nota_al_indice", rag.agregar_nota_al_indice)

        titulo = "Nota Consistencia"
        contenido = "Primer parrafo de la nota.\n\nSegundo parrafo de la nota."

        # Capturar chunks generados por agregar_nota_al_indice
        chunks_indexados_al_vuelo = []
        original_construir = rag.construir_indice

        def construir_captura(panel=None):
            resultado = original_construir(panel)
            chunks_indexados_al_vuelo.extend([f["texto"] for f in rag._fragmentos])
            return resultado

        monkeypatch.setattr(rag, "construir_indice", construir_captura)

        # Guardar nota
        resultado = memoria.guardar_nota(titulo, contenido)
        assert "creada" in resultado.lower() or "actualizada" in resultado.lower()

        # Los chunks deben haber sido capturados
        assert len(chunks_indexados_al_vuelo) > 0

        # Resetear y reconstruir desde cero
        rag._indice = None
        rag._fragmentos = []
        rag._origenes = []
        rag._indexando = False
        monkeypatch.setattr(rag, "construir_indice", original_construir)

        rag.construir_indice()
        chunks_reconstruidos = [f["texto"] for f in rag._fragmentos]

        # Verificar que los textos son equivalentes (mismo conjunto)
        assert set(chunks_indexados_al_vuelo) == set(chunks_reconstruidos), (
            f"Chunks al vuelo: {chunks_indexados_al_vuelo}\n"
            f"Chunks reconstruidos: {chunks_reconstruidos}"
        )

    def test_guardar_nota_llama_agregar_nota_al_indice_con_ruta(self, env_rag, monkeypatch):
        """Verifica que guardar_nota pasa la ruta completa a agregar_nota_al_indice."""
        vault = env_rag["vault"]

        import memoria
        importlib.reload(memoria)
        monkeypatch.setattr(memoria, "RUTA_VAULT", str(vault))

        rutas_capturadas = []

        def capturar(ruta_archivo=None, contenido=None):
            rutas_capturadas.append(ruta_archivo)

        monkeypatch.setattr(memoria, "agregar_nota_al_indice", capturar)

        memoria.guardar_nota("Test Ruta", "Contenido de prueba para verificar la ruta.")

        assert len(rutas_capturadas) == 1
        ruta = rutas_capturadas[0]
        assert ruta is not None
        assert ruta.endswith(".md"), f"Se esperaba ruta .md, se obtuvo: {ruta}"
        assert str(vault) in ruta, f"La ruta no esta dentro del vault: {ruta}"
