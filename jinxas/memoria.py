import logging
import os
import re
from datetime import datetime
from jinxas.config import RUTA_VAULT, TITULO_NOTA_MAX
from jinxas.memoria_rag import agregar_nota_al_indice
from jinxas.registro import herramienta

# Nombres reservados de Windows (case-insensitive)
_RESERVADOS = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def _normalizar_nombre_archivo(titulo: str) -> str:
    """
    Convierte un título a un nombre de archivo .md válido y seguro en Windows.
    Elimina caracteres prohibidos (incluidos los de control), colapsa espacios,
    trunca al máximo configurado y evita nombres reservados del sistema.
    """
    base = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", titulo).strip().rstrip(". ")
    base = re.sub(r"\s+", " ", base)[:TITULO_NOTA_MAX].rstrip(". ")
    if not base or base.lower() in _RESERVADOS:
        base = f"nota {base or 'sin titulo'}"
    return base if base.lower().endswith(".md") else base + ".md"


def _ruta_segura(nombre: str) -> str:
    """
    Resuelve la ruta completa de *nombre* dentro de RUTA_VAULT y verifica
    que no escape de la bóveda (protección contra path traversal).
    Lanza ValueError si la ruta resuelta queda fuera de la bóveda.
    """
    raiz = os.path.realpath(RUTA_VAULT)
    ruta = os.path.realpath(os.path.join(raiz, nombre))
    if os.path.commonpath([raiz, ruta]) != raiz:
        raise ValueError("Ruta fuera de la bóveda")
    return ruta

@herramienta(
    "Guarda o actualiza una nota Markdown en la bóveda de Obsidian.",
    parametros={
        "titulo": {"type": "string", "description": "Título de la nota."},
        "contenido": {"type": "string", "description": "Texto a guardar en la nota."},
    },
)
def guardar_nota(titulo: str, contenido: str) -> str:
    """
    Guarda o actualiza una nota Markdown en la bóveda de Obsidian.
    - Si el archivo ya existe, añade el contenido al final con fecha y hora.
    - Si no existe, crea la nota con encabezado Markdown.
    Retorna una confirmación en texto.
    """
    if not titulo or not titulo.strip():
        return "No se proporcionó un título para la nota."

    os.makedirs(RUTA_VAULT, exist_ok=True)
    nombre_archivo = _normalizar_nombre_archivo(titulo)
    try:
        ruta_archivo = _ruta_segura(nombre_archivo)
    except ValueError:
        return "Error: Título no válido."

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        if os.path.exists(ruta_archivo):
            # Añadir al final del archivo existente
            with open(ruta_archivo, "a", encoding="utf-8") as f:
                f.write(f"\n\n---\n**Actualización {ahora}:**\n\n{contenido}\n")
            try:
                agregar_nota_al_indice(ruta_archivo)
            except Exception as e:
                logging.error("Error al sincronizar nota en RAG: %s", e)
            return f"Nota '{titulo}' actualizada correctamente en la bóveda ({ahora})."
        else:
            # Crear nota nueva con encabezado Markdown
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(f"# {titulo}\n\n")
                f.write(f"*Creada el {ahora}*\n\n")
                f.write("---\n\n")
                f.write(f"{contenido}\n")
            try:
                agregar_nota_al_indice(ruta_archivo)
            except Exception as e:
                logging.error("Error al sincronizar nota en RAG: %s", e)
            return f"Nota '{titulo}' creada correctamente en la bóveda ({ahora})."

    except Exception as e:
        logging.error("Error al guardar la nota '%s': %s", titulo, e)
        return f"Error al guardar la nota '{titulo}': {e}"

@herramienta(
    "Busca una palabra literal en títulos y contenido de las notas. Para preguntas conceptuales usa consultar_boveda.",
    parametros={
        "palabra_clave": {
            "type": "string",
            "description": "Palabra o tema a buscar en títulos y contenidos.",
        }
    },
)
def buscar_nota(palabra_clave: str) -> str:
    """
    Busca coincidencias de una palabra clave en los títulos y contenidos
    de todos los archivos .md dentro de RUTA_VAULT (recorrido recursivo).
    Retorna un resumen del contenido encontrado o un aviso si no hay registros.
    """
    if not palabra_clave or not palabra_clave.strip():
        return "No se proporcionó una palabra clave para buscar."

    if not os.path.isdir(RUTA_VAULT):
        return "La bóveda está vacía. No hay notas guardadas aún."

    clave = palabra_clave.strip().lower()

    archivos_md = []
    try:
        for raiz, dirs, archivos in os.walk(RUTA_VAULT):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for archivo in archivos:
                if archivo.lower().endswith('.md') and not archivo.startswith('.'):
                    archivos_md.append((raiz, archivo))
    except Exception as e:
        logging.error("Error al acceder a la bóveda: %s", e)
        return f"Error al acceder a la bóveda: {e}"

    if not archivos_md:
        return "La bóveda está vacía. No hay notas guardadas aún."

    # Prioridad: coincidencias en el título primero, luego solo en contenido
    hits_titulo = []     # (titulo, extracto)
    hits_contenido = []  # (titulo, extracto)

    for raiz, archivo in archivos_md:
        titulo_archivo = os.path.splitext(archivo)[0]
        ruta_archivo = os.path.join(raiz, archivo)

        try:
            with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()

            coincidencia_titulo = clave in titulo_archivo.lower()
            coincidencia_contenido = clave in contenido.lower()

            if not (coincidencia_titulo or coincidencia_contenido):
                continue

            # Extraer fragmento relevante (máx. ~200 caracteres)
            extracto_partes = []
            for linea in contenido.splitlines():
                if clave in linea.lower() and linea.strip():
                    parte = linea.strip()
                    if len(parte) > 200:
                        parte = parte[:197] + "..."
                    extracto_partes.append(f"  → {parte}")
                if len(extracto_partes) >= 3:
                    break

            resumen = f"📄 **{titulo_archivo}**"
            if extracto_partes:
                resumen += "\n" + "\n".join(extracto_partes)

            if coincidencia_titulo:
                hits_titulo.append(resumen)
            else:
                hits_contenido.append(resumen)

        except Exception as e:
            logging.error("Error al leer la nota '%s': %s", archivo, e)
            continue

    # Combinar priorizando título, limitar a 5
    resultados = (hits_titulo + hits_contenido)[:5]

    if resultados:
        encabezado = f"Se encontraron {len(resultados)} nota(s) con '{palabra_clave}':\n\n"
        return encabezado + "\n\n".join(resultados)
    else:
        return f"No se encontraron notas sobre '{palabra_clave}' en la bóveda."

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    logging.info("Módulo de memoria - bóveda Obsidian")

    logging.info("Prueba: guardar nota")
    resultado_guardar = guardar_nota(
        "Jinx Primera Prueba",
        "Esta es la primera nota de prueba guardada por Jinx. Todo funciona correctamente."
    )
    logging.info(resultado_guardar)

    logging.info("Prueba: buscar nota")
    resultado_buscar = buscar_nota("Jinx")
    logging.info(resultado_buscar)
