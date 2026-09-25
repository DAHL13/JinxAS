"""
memoria_rag.py — Fase 4 de JinxAS
Sistema RAG (Retrieval-Augmented Generation) completamente local.
Indexa archivos .md de la bóveda de Obsidian con FAISS + sentence-transformers.
Optimizado para CPU sin agotar memoria: chunks pequeños, modelo multilingüe
(paraphrase-multilingual-MiniLM-L12-v2).
"""

import os
import logging
import threading
import numpy as np
from tqdm import tqdm
import config

# ---------------------------------------------------------------------------
# Sincronización de hilos (F2-07: Arranque no bloqueante)
# ---------------------------------------------------------------------------
_lock_rag = threading.Lock()
_indexando: bool = False

# ---------------------------------------------------------------------------
# Carga perezosa (lazy loading) del modelo de embeddings.
# faiss y SentenceTransformer se importan dentro de las funciones para:
#   a) No bloquear el arranque del proceso principal.
#   b) Permitir que los mocks de sys.modules en conftest.py sigan funcionando:
#      Python resuelve imports desde sys.modules (ya mockeado) en tiempo de
#      llamada, por lo que patch("faiss.IndexFlatL2") funciona correctamente.
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
# Estado global del índice (se construye una sola vez al inicio de Jinx)
# ---------------------------------------------------------------------------
_indice = None
_fragmentos: list = []    # Lista de {"archivo": str, "texto": str} por chunk
_origenes: list = []      # Nombre del archivo .md de cada chunk


def _asegurar_indice() -> None:
    global _indice
    if _indice is None:
        import faiss  # import perezoso
        dim = _obtener_modelo().get_sentence_embedding_dimension()
        _indice = faiss.IndexFlatL2(dim)

# ---------------------------------------------------------------------------
# Parámetros de chunking
# ---------------------------------------------------------------------------
CHUNK_TAMANO = 700        # Tamaño objetivo en caracteres por fragmento
CHUNK_SOLAPAMIENTO = 100  # Solapamiento entre chunks consecutivos


def _dividir_en_chunks(texto: str, nombre_archivo: str) -> list:
    """
    Divide un texto en fragmentos de aprox. CHUNK_TAMANO caracteres,
    con solapamiento para no perder contexto en los bordes.
    Devuelve lista de (chunk_texto, nombre_archivo).
    """
    chunks = []
    inicio = 0
    longitud = len(texto)
    titulo = os.path.splitext(nombre_archivo)[0]
    while inicio < longitud:
        fin = min(inicio + CHUNK_TAMANO, longitud)
        fragmento = texto[inicio:fin].strip()
        if fragmento:
            chunks.append((f"{titulo}\n{fragmento}", nombre_archivo))
        inicio += CHUNK_TAMANO - CHUNK_SOLAPAMIENTO
    return chunks


def agregar_nota_al_indice(ruta_archivo: str = None, contenido: str = None) -> None:
    """
    Sincroniza en tiempo real el índice vectorial en memoria cuando se crea
    o actualiza una nota en la bóveda durante la sesión.
    Garantiza que el índice exista antes de reindexar.
    Protegido con _lock_rag para acceso concurrente seguro.
    """
    _asegurar_indice()
    logging.info("[RAG] Reindexando bóveda tras actualización de nota...")
    construir_indice()


def construir_indice(panel=None) -> int:
    """
    Recorre recursivamente config.RUTA_VAULT buscando archivos .md,
    genera embeddings y construye un índice FAISS IndexFlatIP con IndexIDMap2.
    Los resultados se almacenan en variables globales para consultas rápidas.
    Devuelve la cantidad total de fragmentos indexados.

    Thread-safe (F2-07): usa _lock_rag para proteger la escritura en _indice
    y _fragmentos. La bandera _indexando se activa al inicio y se restaura con
    try/finally para garantizar que siempre quede en False al terminar.
    """
    global _indice, _fragmentos, _origenes, _indexando

    import faiss  # import perezoso

    _indexando = True
    try:
        modelo = _obtener_modelo()
        dim = (
            modelo.get_embedding_dimension()
            if hasattr(modelo, "get_embedding_dimension")
            else modelo.get_sentence_embedding_dimension()
        )
        nuevo_indice = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        nuevos_fragmentos = []
        nuevos_origenes = []

        ruta_vault = config.RUTA_VAULT
        logging.info("[RAG] Iniciando construcción del índice sobre: %s", ruta_vault)

        if not os.path.isdir(ruta_vault):
            logging.warning(
                "[RAG] La bóveda no existe en '%s'. El índice quedará vacío.", ruta_vault
            )
            if panel:
                panel.actualizar_satelite(3, 3, "Memoria RAG", "Bóveda no encontrada")
            return 0

        logging.info("Iniciando escaneo de la bóveda Obsidian...")

        archivos_md = []
        # Recorrido recursivo de la bóveda ignorando carpetas que empiezan con '.' (.obsidian, .git, .trash, etc.)
        for raiz, dirs, archivos in os.walk(ruta_vault):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for nombre in archivos:
                if nombre.lower().endswith(".md") and not nombre.startswith('.'):
                    archivos_md.append((raiz, nombre))

        if not archivos_md:
            logging.warning("[RAG] No se encontraron archivos .md en la bóveda.")
            if panel:
                panel.actualizar_satelite(3, 3, "Memoria RAG", "0 Chunks")
            return 0

        todos_los_chunks: list = []
        for raiz, nombre in tqdm(archivos_md, desc="Vectorizando notas"):
            ruta_completa = os.path.join(raiz, nombre)
            try:
                with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
                    contenido = f.read()
                if not contenido.strip():
                    continue
                chunks = _dividir_en_chunks(contenido, nombre)
                todos_los_chunks.extend(chunks)
            except Exception as e:
                logging.warning("[RAG] No se pudo leer '%s': %s", ruta_completa, e)

        if not todos_los_chunks:
            logging.warning("[RAG] No se encontraron fragmentos. El índice quedará vacío.")
            if panel:
                panel.actualizar_satelite(3, 3, "Memoria RAG", "0 Chunks")
            return 0

        textos = [c[0] for c in todos_los_chunks]
        origenes = [c[1] for c in todos_los_chunks]

        logging.info("[RAG] Generando embeddings para %d fragmentos...", len(textos))
        vectores = modelo.encode(
            textos,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)

        ids = np.arange(len(vectores), dtype=np.int64)
        nuevo_indice.add_with_ids(vectores, ids)

        nuevos_fragmentos = [{"archivo": orig, "texto": txt} for txt, orig in zip(textos, origenes)]
        nuevos_origenes = origenes

        logging.info(
            "[RAG] Índice construido: %d fragmentos de %d archivos .md indexados.",
            len(nuevos_fragmentos),
            len(set(nuevos_origenes)),
        )
        total_chunks = len(nuevos_fragmentos)
        logging.info("Índice FAISS construido con éxito: %d fragmentos vectorizados.", total_chunks)

        # Proteger la escritura atómica en las variables globales compartidas
        with _lock_rag:
            _indice = nuevo_indice
            _fragmentos = nuevos_fragmentos
            _origenes = nuevos_origenes

        if panel:
            panel.actualizar_satelite(3, 3, "Memoria RAG", f"{total_chunks} Chunks Listos")
        return total_chunks

    finally:
        # Garantizar que _indexando siempre vuelva a False, incluso si hay excepción
        _indexando = False


def obtener_cantidad_fragmentos() -> int:
    """Devuelve la cantidad total de fragmentos indexados en memoria."""
    return len(_fragmentos)


def buscar_semantica(consulta: str, top_k: int = 3) -> str:
    """
    Busca semánticamente en el índice FAISS de forma thread-safe (F2-07).
    Si el índice se está construyendo (_indexando=True) y aún no hay datos,
    devuelve inmediatamente un mensaje amigable sin bloquear.
    Protege la lectura de _indice y _fragmentos con _lock_rag.

    Parámetros
    ----------
    consulta : str
        Pregunta o tema a buscar en la bóveda.
    top_k : int
        Número de fragmentos más relevantes a devolver (por defecto 3).

    Retorna
    -------
    str
        Texto formateado con los fragmentos más relevantes y su origen,
        o un mensaje explicativo si el índice está vacío o en construcción.
    """
    # Respuesta rápida no bloqueante si el índice aún se está construyendo
    if _indexando and _indice is None:
        return "Sigo preparando mis notas, dame un momento."

    with _lock_rag:
        indice_local = _indice
        fragmentos_local = list(_fragmentos)

    if indice_local is None or len(fragmentos_local) == 0:
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
        distancias, indices = indice_local.search(vector_consulta, k)

        resultados = []
        for dist, idx in zip(distancias[0], indices[0]):
            if idx < 0 or idx >= len(fragmentos_local):
                continue
            if dist < config.UMBRAL_SIMILITUD_RAG:
                continue
            frag = fragmentos_local[idx]
            texto_chunk = frag["texto"]
            nombre_archivo = frag["archivo"]
            rango = len(resultados) + 1
            resultados.append(
                f"[Resultado {rango} — {nombre_archivo}]\n"
                f"{texto_chunk}"
            )

        if not resultados:
            return "No se encontró información relevante en las notas."

        return "\n\n---\n\n".join(resultados)

    except Exception as e:
        logging.error("[RAG] Error durante la búsqueda: %s", e)
        return f"Error durante la búsqueda en la bóveda: {e}"


def buscar_en_notas(consulta: str, top_k: int = 3) -> str:
    """
    Vectoriza `consulta`, busca los `top_k` fragmentos más cercanos en el índice FAISS
    (IndexFlatIP con similitud coseno) y devuelve un string formateado con el texto y su archivo de origen.
    Filtra resultados donde score >= config.UMBRAL_SIMILITUD_RAG.

    Parámetros
    ----------
    consulta : str
        Pregunta o tema a buscar en la bóveda.
    top_k : int
        Número de fragmentos más relevantes a devolver (por defecto 3).

    Retorna
    -------
    str
        Texto formateado con los fragmentos más relevantes y su origen,
        o un mensaje explicativo si el índice está vacío.
    """
    return buscar_semantica(consulta, top_k)


# Alias para compatibilidad directa
consultar_boveda = buscar_en_notas
