"""
memoria_rag.py — Fase 4 de JinxAS
Sistema RAG (Retrieval-Augmented Generation) completamente local.
Indexa archivos .md de la bóveda de Obsidian con FAISS + sentence-transformers.
Optimizado para CPU sin agotar memoria: chunks pequeños, modelo ligero (MiniLM-L6-v2).
"""

import os
import logging
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import config

# ---------------------------------------------------------------------------
# Carga global del modelo de embeddings (se hace UNA sola vez al importar)
# all-MiniLM-L6-v2: ~80 MB en disco, ~22 M parámetros, muy rápido en CPU.
# ---------------------------------------------------------------------------
logging.info("[RAG] Cargando modelo de embeddings 'all-MiniLM-L6-v2'...")
modelo_embedding = SentenceTransformer("all-MiniLM-L6-v2")
logging.info("[RAG] Modelo de embeddings listo.")

# ---------------------------------------------------------------------------
# Estado global del índice (se construye una sola vez al inicio de Jinx)
# ---------------------------------------------------------------------------
_indice_faiss = None
_fragmentos: list = []    # Texto de cada chunk
_origenes: list = []      # Nombre del archivo .md de cada chunk

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
    while inicio < longitud:
        fin = min(inicio + CHUNK_TAMANO, longitud)
        fragmento = texto[inicio:fin].strip()
        if fragmento:
            chunks.append((fragmento, nombre_archivo))
        inicio += CHUNK_TAMANO - CHUNK_SOLAPAMIENTO
    return chunks


def construir_indice() -> None:
    """
    Recorre recursivamente config.RUTA_VAULT buscando archivos .md,
    genera embeddings y construye un índice FAISS IndexFlatL2.
    Los resultados se almacenan en variables globales para consultas rápidas.
    Se ignoran silenciosamente archivos que no se puedan leer.
    """
    global _indice_faiss, _fragmentos, _origenes

    ruta_vault = config.RUTA_VAULT
    logging.info("[RAG] Iniciando construcción del índice sobre: %s", ruta_vault)

    if not os.path.isdir(ruta_vault):
        logging.warning(
            "[RAG] La bóveda no existe en '%s'. El índice quedará vacío.", ruta_vault
        )
        _indice_faiss = None
        _fragmentos = []
        _origenes = []
        return

    print("Iniciando escaneo de la bóveda Obsidian...")

    archivos_md = []
    # Recorrido recursivo de la bóveda ignorando carpetas que empiezan con '.' (.obsidian, .git, .trash, etc.)
    for raiz, dirs, archivos in os.walk(ruta_vault):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for nombre in archivos:
            if nombre.lower().endswith(".md") and not nombre.startswith('.'):
                archivos_md.append((raiz, nombre))

    if not archivos_md:
        logging.warning("[RAG] No se encontraron archivos .md en la bóveda.")
        _indice_faiss = None
        _fragmentos = []
        _origenes = []
        return

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
        _indice_faiss = None
        _fragmentos = []
        _origenes = []
        return

    textos = [c[0] for c in todos_los_chunks]
    origenes = [c[1] for c in todos_los_chunks]

    logging.info("[RAG] Generando embeddings para %d fragmentos...", len(textos))
    # batch_size=32 y show_progress_bar=False para mantener salida limpia en producción
    vectores = modelo_embedding.encode(
        textos,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype(np.float32)

    dimension = vectores.shape[1]
    indice = faiss.IndexFlatL2(dimension)
    indice.add(vectores)

    _indice_faiss = indice
    _fragmentos = textos
    _origenes = origenes

    logging.info(
        "[RAG] Índice construido: %d fragmentos de %d archivos .md indexados.",
        len(_fragmentos),
        len(set(_origenes)),
    )
    print(f"Índice FAISS construido con éxito: {len(_fragmentos)} fragmentos vectorizados.")


def buscar_en_notas(consulta: str, top_k: int = 3) -> str:
    """
    Vectoriza `consulta`, busca los `top_k` fragmentos más cercanos en el índice FAISS
    y devuelve un string formateado con el texto y su archivo de origen.

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
    if _indice_faiss is None or len(_fragmentos) == 0:
        return (
            "El índice RAG está vacío. Puede que la bóveda no exista, "
            "no contenga archivos .md, o que construir_indice() no se haya ejecutado."
        )

    if not consulta or not consulta.strip():
        return "No se proporcionó una consulta válida para buscar en la bóveda."

    try:
        vector_consulta = modelo_embedding.encode(
            [consulta.strip()],
            convert_to_numpy=True,
        ).astype(np.float32)

        k = min(top_k, len(_fragmentos))
        distancias, indices = _indice_faiss.search(vector_consulta, k)

        resultados = []
        for rango, (dist, idx) in enumerate(zip(distancias[0], indices[0]), start=1):
            if idx < 0 or idx >= len(_fragmentos):
                continue
            texto_chunk = _fragmentos[idx]
            nombre_archivo = _origenes[idx]
            resultados.append(
                f"[Resultado {rango} — {nombre_archivo} | distancia L2: {dist:.4f}]\n"
                f"{texto_chunk}"
            )

        if not resultados:
            return "No se encontraron fragmentos relevantes para la consulta."

        return "\n\n---\n\n".join(resultados)

    except Exception as e:
        logging.error("[RAG] Error durante la búsqueda: %s", e)
        return f"Error durante la búsqueda en la bóveda: {e}"
