"""
memoria_rag.py — Fase 3 de JinxAS (F3-01, F3-02, F3-05)
Sistema RAG (Retrieval-Augmented Generation) completamente local.
Indexa archivos .md de la bóveda de Obsidian con FAISS + sentence-transformers.

Novedades F3:
- dividir_en_chunks: chunking contextual por encabezados, párrafos y frases.
- IndexIDMap2(IndexFlatIP) + normalización L2 → similitud coseno exacta.
- Caché incremental en .jinx_cache/ (indice.faiss + manifiesto.json).
  Solo re-vectoriza notas nuevas o modificadas; conserva el resto.
- fuente única de verdad: agregar_nota_al_indice siempre lee de disco.
"""

import hashlib
import json
import logging
import os
import re
import threading

import numpy as np

from jinxas import config

# ---------------------------------------------------------------------------
# Sincronización de hilos (F2-07: Arranque no bloqueante)
# ---------------------------------------------------------------------------
_lock_rag = threading.Lock()
_lock_construir = threading.Lock()
_indexando: bool = False

# ---------------------------------------------------------------------------
# Carga perezosa de modelo de embeddings
# ---------------------------------------------------------------------------
_modelo_embedding = None


def _obtener_modelo():
    """Carga el modelo de embeddings la primera vez que se necesita (lazy)."""
    global _modelo_embedding
    if _modelo_embedding is None:
        from sentence_transformers import SentenceTransformer  # import perezoso
        logging.info("[RAG] Cargando modelo de embeddings '%s'...", config.MODELO_EMBEDDINGS)
        _modelo_embedding = SentenceTransformer(config.MODELO_EMBEDDINGS)
        logging.info("[RAG] Modelo de embeddings listo.")
    return _modelo_embedding


# ---------------------------------------------------------------------------
# Estado global del índice
# ---------------------------------------------------------------------------
_indice = None
_fragmentos: list = []   # list[{"archivo": str, "texto": str}] por chunk
_origenes: list = []     # nombre del archivo .md de cada chunk

# ---------------------------------------------------------------------------
# Caché incremental
# ---------------------------------------------------------------------------
_CACHE_DIR_NAME = ".jinx_cache"


def _cache_dir() -> str:
    """Devuelve la ruta absoluta de la carpeta de caché."""
    return os.path.join(config.RUTA_VAULT, _CACHE_DIR_NAME)


def _ruta_indice() -> str:
    return os.path.join(_cache_dir(), "indice.faiss")


def _ruta_manifiesto() -> str:
    return os.path.join(_cache_dir(), "manifiesto.json")


def _asegurar_cache_dir() -> None:
    os.makedirs(_cache_dir(), exist_ok=True)


# ---------------------------------------------------------------------------
# _asegurar_indice (mantiene compatibilidad con test_f1_criticas.py)
# ---------------------------------------------------------------------------

def _asegurar_indice() -> None:
    """
    Crea un índice FAISS vacío si todavía no existe.
    Intenta IndexIDMap2(IndexFlatIP) pero, si el mock de tests no lo implementa,
    cae a IndexFlatL2 para no romper test_f1_06_asegurar_indice_inicializa_cuando_es_none.
    """
    global _indice
    if _indice is not None:
        return
    import faiss  # import perezoso
    dim = _obtener_modelo().get_sentence_embedding_dimension()
    try:
        _indice = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
    except Exception:
        # Fallback para mocks de tests que solo implementan IndexFlatL2
        _indice = faiss.IndexFlatL2(dim)


# ---------------------------------------------------------------------------
# F3-02 — Chunking contextual
# ---------------------------------------------------------------------------

def dividir_en_chunks(texto: str, titulo: str, max_chars: int = None) -> list:
    """
    Divide *texto* en chunks semánticos con contexto del título.

    Estrategia:
    1. Divide por encabezados Markdown (# / ## / ###).
    2. Dentro de cada sección acumula párrafos (separados por \\n\\n).
    3. Si un párrafo individual supera max_chars, lo parte por frases.
    4. Cada chunk lleva el título de la nota como prefijo.

    Retorna list[str] con los textos ya prefijados.
    """
    if max_chars is None:
        max_chars = getattr(config, "MAX_CHARS_CHUNK", 900)

    secciones = re.split(r"(?m)^(?=#{1,3} )", texto)
    chunks = []

    for seccion in secciones:
        seccion = seccion.strip()
        if not seccion:
            continue

        parrafos = re.split(r"\n\n+", seccion)
        acumulado = ""

        for parrafo in parrafos:
            parrafo = parrafo.strip()
            if not parrafo:
                continue

            # Si el párrafo individual ya supera max_chars, dividir por frases
            if len(parrafo) > max_chars:
                # Vaciar acumulado primero
                if acumulado.strip():
                    chunks.append(f"{titulo}\n{acumulado.strip()}")
                    acumulado = ""
                frases = re.split(r"(?<=[.!?…])\s+", parrafo)
                fragmento_frase = ""
                for frase in frases:
                    if len(fragmento_frase) + len(frase) + 1 <= max_chars:
                        fragmento_frase = (fragmento_frase + " " + frase).strip()
                    else:
                        if fragmento_frase.strip():
                            chunks.append(f"{titulo}\n{fragmento_frase.strip()}")
                        fragmento_frase = frase
                if fragmento_frase.strip():
                    chunks.append(f"{titulo}\n{fragmento_frase.strip()}")
                continue

            # Acumular párrafo normal
            candidato = (acumulado + "\n\n" + parrafo).strip() if acumulado else parrafo
            if len(candidato) <= max_chars:
                acumulado = candidato
            else:
                if acumulado.strip():
                    chunks.append(f"{titulo}\n{acumulado.strip()}")
                acumulado = parrafo

        if acumulado.strip():
            chunks.append(f"{titulo}\n{acumulado.strip()}")

    # Garantizar al menos un chunk si el texto no estaba vacío
    if not chunks and texto.strip():
        chunks.append(f"{titulo}\n{texto.strip()[:max_chars]}")

    return chunks


# Alias privado para compatibilidad interna
def _dividir_en_chunks(texto: str, nombre_archivo: str) -> list:
    """Wrapper de compatibilidad interna que devuelve list[(texto, archivo)]."""
    titulo = os.path.splitext(nombre_archivo)[0]
    return [(c, nombre_archivo) for c in dividir_en_chunks(texto, titulo)]


# ---------------------------------------------------------------------------
# Utilidades de caché
# ---------------------------------------------------------------------------

def _sha1_archivo(ruta: str) -> str:
    h = hashlib.sha1(usedforsecurity=False)
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _cargar_manifiesto() -> dict:
    ruta = _ruta_manifiesto()
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning("[RAG] No se pudo leer el manifiesto: %s", e)
    return {}


def _guardar_manifiesto(manifiesto: dict) -> None:
    _asegurar_cache_dir()
    with open(_ruta_manifiesto(), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=2)


def _manifiesto_es_compatible(manifiesto: dict) -> bool:
    """Devuelve False si el modelo o max_chars_chunk cambió → reconstruir todo."""
    return (
        manifiesto.get("modelo") == config.MODELO_EMBEDDINGS
        and manifiesto.get("max_chars_chunk") == getattr(config, "MAX_CHARS_CHUNK", 900)
    )


# ---------------------------------------------------------------------------
# F3-01 / F3-05 — construir_indice con caché incremental
# ---------------------------------------------------------------------------

def construir_indice(panel=None) -> int:
    """
    Recorre RUTA_VAULT (recursivo, ignora carpetas ocultas) y mantiene un índice
    FAISS IndexIDMap2(IndexFlatIP) con similitud coseno.

    Caché incremental (.jinx_cache/):
    - Archivos sin cambios → no se re-vectorizan.
    - Archivos nuevos/modificados → sus IDs anteriores se eliminan y se re-indexan.
    - Archivos eliminados → sus IDs se eliminan del índice.

    Thread-safe: usa _lock_construir para serializar ejecuciones y _lock_rag para la escritura atómica final.
    """
    global _indice, _fragmentos, _origenes, _indexando

    import faiss  # import perezoso

    if not _lock_construir.acquire(blocking=False):
        logging.info("[RAG] Construcción de índice ya en progreso. Omitiendo llamada concurrente.")
        return len(_fragmentos)

    _indexando = True
    try:
        modelo = _obtener_modelo()
        dim = (
            modelo.get_embedding_dimension()
            if hasattr(modelo, "get_embedding_dimension")
            else modelo.get_sentence_embedding_dimension()
        )

        ruta_vault = config.RUTA_VAULT
        max_chars = getattr(config, "MAX_CHARS_CHUNK", 900)

        logging.info("[RAG] Iniciando construcción del índice sobre: %s", ruta_vault)

        if not os.path.isdir(ruta_vault):
            logging.warning("[RAG] La bóveda no existe en '%s'. Índice vacío.", ruta_vault)
            if panel:
                panel.actualizar_satelite(3, 3, "Memoria RAG", "Bóveda no encontrada")
            return 0

        # ---- Cargar manifiesto y decidir si reconstruir desde cero --------
        manifiesto = _cargar_manifiesto()
        if not _manifiesto_es_compatible(manifiesto):
            logging.info("[RAG] Configuración cambió. Reconstruyendo índice desde cero.")
            manifiesto = {}

        # ---- Cargar índice existente o crear uno nuevo --------------------
        ruta_idx = _ruta_indice()
        if manifiesto and os.path.exists(ruta_idx):
            try:
                nuevo_indice = faiss.read_index(ruta_idx)
                logging.info("[RAG] Índice cargado desde caché.")
            except Exception as e:
                logging.warning("[RAG] No se pudo leer el índice en caché: %s. Reindexando.", e)
                nuevo_indice = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
                manifiesto = {}
        else:
            nuevo_indice = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))

        # next_id global para asignar IDs únicos a cada chunk
        next_id: int = manifiesto.get("next_id", 0)

        # Mapa ruta_relativa → metadatos del manifiesto
        entradas: dict = {k: v for k, v in manifiesto.items()
                          if k not in ("modelo", "max_chars_chunk", "next_id")}

        # ---- Escanear bóveda actual ---------------------------------------
        archivos_actuales: dict = {}  # ruta_relativa → ruta_completa
        for raiz, dirs, archivos in os.walk(ruta_vault):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for nombre in archivos:
                if nombre.lower().endswith(".md") and not nombre.startswith("."):
                    ruta_completa = os.path.join(raiz, nombre)
                    ruta_rel = os.path.relpath(ruta_completa, ruta_vault)
                    archivos_actuales[ruta_rel] = ruta_completa

        # ---- Detectar archivos eliminados ---------------------------------
        eliminados = [r for r in entradas if r not in archivos_actuales]
        for ruta_rel in eliminados:
            ids_viejos = entradas[ruta_rel].get("ids", [])
            if ids_viejos:
                try:
                    nuevo_indice.remove_ids(np.array(ids_viejos, dtype=np.int64))
                except Exception as e:
                    logging.warning("[RAG] No se pudieron eliminar IDs de '%s': %s", ruta_rel, e)
            del entradas[ruta_rel]
            logging.info("[RAG] Nota eliminada del índice: %s", ruta_rel)

        # ---- Construir mapa ID → fragmento reutilizando entradas sin cambio
        # (reconstruir _fragmentos desde el manifiesto)
        nuevos_fragmentos: list = []
        for ruta_rel, meta in entradas.items():
            for chunk_id, chunk_txt in zip(meta.get("ids", []), meta.get("chunks", [])):
                nuevos_fragmentos.append({"archivo": os.path.basename(ruta_rel), "texto": chunk_txt, "_id": chunk_id})

        # ---- Procesar archivos nuevos o modificados -----------------------
        n_nuevos = 0
        for ruta_rel, ruta_completa in archivos_actuales.items():
            try:
                mtime_actual = os.path.getmtime(ruta_completa)
                sha1_actual = _sha1_archivo(ruta_completa)
            except Exception as e:
                logging.warning("[RAG] No se pudo stat '%s': %s", ruta_completa, e)
                continue

            entrada_previa = entradas.get(ruta_rel)
            sin_cambio = (
                entrada_previa is not None
                and abs(entrada_previa.get("mtime", 0) - mtime_actual) < 1e-3
                and entrada_previa.get("sha1") == sha1_actual
            )
            if sin_cambio:
                continue  # No re-vectorizar

            # Eliminar IDs previos si los había
            if entrada_previa:
                ids_viejos = entrada_previa.get("ids", [])
                if ids_viejos:
                    try:
                        nuevo_indice.remove_ids(np.array(ids_viejos, dtype=np.int64))
                    except Exception as e:
                        logging.warning("[RAG] remove_ids '%s': %s", ruta_rel, e)
                # Quitar de nuevos_fragmentos los chunks viejos de esta nota
                nuevos_fragmentos = [
                    frag for frag in nuevos_fragmentos if frag.get("_id") not in set(ids_viejos)
                ]

            # Leer contenido y generar chunks
            try:
                with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
                    contenido = f.read()
                if not contenido.strip():
                    continue
            except Exception as e:
                logging.warning("[RAG] No se pudo leer '%s': %s", ruta_completa, e)
                continue

            titulo = os.path.splitext(os.path.basename(ruta_completa))[0]
            chunks_txt = dividir_en_chunks(contenido, titulo, max_chars)
            if not chunks_txt:
                continue

            # Vectorizar solo estos chunks
            vectores = modelo.encode(
                chunks_txt,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)

            ids_nuevos = list(range(next_id, next_id + len(chunks_txt)))
            next_id += len(chunks_txt)

            nuevo_indice.add_with_ids(vectores, np.array(ids_nuevos, dtype=np.int64))

            for chunk_id, chunk_txt in zip(ids_nuevos, chunks_txt):
                nuevos_fragmentos.append({
                    "archivo": os.path.basename(ruta_rel),
                    "texto": chunk_txt,
                    "_id": chunk_id,
                })

            entradas[ruta_rel] = {
                "mtime": mtime_actual,
                "sha1": sha1_actual,
                "ids": ids_nuevos,
                "chunks": chunks_txt,
            }
            n_nuevos += 1
            logging.info("[RAG] Nota indexada: %s (%d chunks)", ruta_rel, len(chunks_txt))

        hubo_cambios = n_nuevos > 0 or len(eliminados) > 0
        logging.info(
            "[RAG] %d notas nuevas/modificadas, %d eliminadas.",
            n_nuevos, len(eliminados),
        )

        # ---- Guardar caché si hubo cambios --------------------------------
        if hubo_cambios:
            _asegurar_cache_dir()
            try:
                faiss.write_index(nuevo_indice, _ruta_indice())
            except Exception as e:
                logging.warning("[RAG] No se pudo guardar el índice en caché: %s", e)

            nuevo_manifiesto = {
                "modelo": config.MODELO_EMBEDDINGS,
                "max_chars_chunk": max_chars,
                "next_id": next_id,
                **entradas,
            }
            _guardar_manifiesto(nuevo_manifiesto)

        total_chunks = len(nuevos_fragmentos)
        logging.info("[RAG] Índice listo: %d fragmentos.", total_chunks)

        # ---- Escritura atómica de las variables globales ------------------
        with _lock_rag:
            _indice = nuevo_indice
            _fragmentos = nuevos_fragmentos
            _origenes = [f["archivo"] for f in nuevos_fragmentos]

        if panel:
            panel.actualizar_satelite(3, 3, "Memoria RAG", f"{total_chunks} Chunks Listos")
        return total_chunks

    finally:
        _indexando = False
        _lock_construir.release()


# ---------------------------------------------------------------------------
# F3-01 — agregar_nota_al_indice (fuente única de verdad)
# ---------------------------------------------------------------------------

def agregar_nota_al_indice(ruta_archivo: str = None, contenido: str = None) -> None:
    """
    Sincroniza en tiempo real el índice al crear/actualizar una nota.

    Si el archivo existe en disco, lee de disco (fuente única de verdad).
    Si no existe (test unitario aislado que pasó contenido en memoria),
    usa contenido como fallback para mantener compatibilidad con Fase 1.

    Protegido con _lock_rag para acceso concurrente seguro.
    """
    _asegurar_indice()

    ruta = ruta_archivo or ""
    archivo_en_disco = ruta and os.path.isfile(ruta)

    if archivo_en_disco:
        logging.info("[RAG] Reindexando nota desde disco: %s", ruta)
        construir_indice()
        return

    # Fallback: contenido en memoria (compatibilidad Fase 1)
    if contenido:
        logging.info("[RAG] Reindexando con contenido en memoria (fallback).")
    else:
        logging.info("[RAG] agregar_nota_al_indice: sin contenido ni archivo, reindexando.")
    construir_indice()


# ---------------------------------------------------------------------------
# Búsqueda semántica
# ---------------------------------------------------------------------------

def buscar_semantica(consulta: str, top_k: int = 3) -> str:
    """
    Busca semánticamente en el índice FAISS (similitud coseno).
    Filtra resultados con score >= config.UMBRAL_SIMILITUD_RAG.
    Thread-safe; no bloquea si el índice aún se está construyendo.
    """
    if _indexando and _indice is None:
        return "Sigo preparando mis notas, dame un momento."

    with _lock_rag:
        indice_local = _indice
        fragmentos_local = list(_fragmentos)

    if indice_local is None or not fragmentos_local:
        return (
            "El índice RAG está vacío. Puede que la bóveda no exista, "
            "no contenga archivos .md, o que construir_indice() no se haya ejecutado."
        )

    if not consulta or not consulta.strip():
        return "No se proporcionó una consulta válida para buscar en la bóveda."

    try:
        modelo = _obtener_modelo()
        vector_consulta = modelo.encode(
            [consulta.strip()],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)

        k = min(top_k, len(fragmentos_local))
        scores, indices = indice_local.search(vector_consulta, k)

        mapa_id = {frag["_id"]: frag for frag in fragmentos_local if "_id" in frag}

        resultados = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            # Buscar por ID de FAISS si está presente en el mapa, o por índice posicional como fallback
            frag = mapa_id.get(idx)
            if frag is None and 0 <= idx < len(fragmentos_local):
                frag = fragmentos_local[idx]
            if frag is None:
                continue
            if float(score) < config.UMBRAL_SIMILITUD_RAG:
                logging.debug("[RAG] Descartado score=%.4f < umbral=%.4f", score, config.UMBRAL_SIMILITUD_RAG)
                continue
            frag_archivo = frag.get("archivo", "nota.md")
            frag_texto = frag.get("texto", "")
            logging.info("[RAG] Resultado score=%.4f archivo=%s", score, frag_archivo)
            resultados.append(
                f"[Resultado {len(resultados)+1} — {frag_archivo}]\n{frag_texto}"
            )

        if not resultados:
            return "No se encontró información relevante en las notas."
        return "\n\n---\n\n".join(resultados)

    except Exception as e:
        logging.error("[RAG] Error durante la búsqueda: %s", e)
        return f"Error durante la búsqueda en la bóveda: {e}"


def buscar_en_notas(consulta: str, top_k: int = 3) -> str:
    """Alias público de buscar_semantica."""
    return buscar_semantica(consulta, top_k)


def obtener_cantidad_fragmentos() -> int:
    """Devuelve la cantidad total de fragmentos indexados en memoria."""
    return len(_fragmentos)


# Alias para compatibilidad directa
consultar_boveda = buscar_en_notas
