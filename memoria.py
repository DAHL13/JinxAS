import logging
import os
import re
import sys
from datetime import datetime
from config import RUTA_VAULT, TITULO_NOTA_MAX
from memoria_rag import agregar_nota_al_indice

def _normalizar_nombre_archivo(titulo: str) -> str:
    """
    Convierte un título a un nombre de archivo válido en formato .md.
    Elimina caracteres no permitidos en nombres de archivo de Windows y nombres reservados.
    """
    RESERVADOS = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
    }
    nombre = titulo.strip()
    if nombre.lower().endswith(".md"):
        nombre = nombre[:-3]
    # Reemplazar caracteres no permitidos en Windows: \ / : * ? " < > |
    nombre = re.sub(r'[\\/:*?"<>|]', '', nombre)
    # Reemplazar espacios múltiples con uno solo
    nombre = re.sub(r'\s+', ' ', nombre)
    nombre = nombre[:TITULO_NOTA_MAX]
    base = nombre.rstrip(" .") or "Sin titulo"
    if base.lower() in RESERVADOS:
        base = f"{base}_"
    return f"{base}.md"

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
    ruta_archivo = os.path.join(RUTA_VAULT, nombre_archivo)

    # Confinamiento de ruta dentro de la bóveda
    ruta_vault_abs = os.path.abspath(RUTA_VAULT)
    ruta_archivo_abs = os.path.abspath(ruta_archivo)
    if os.path.commonpath([ruta_vault_abs, ruta_archivo_abs]) != ruta_vault_abs:
        return "Error: Título no válido."

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        if os.path.exists(ruta_archivo):
            # Añadir al final del archivo existente
            with open(ruta_archivo, "a", encoding="utf-8") as f:
                f.write(f"\n\n---\n**Actualización {ahora}:**\n\n{contenido}\n")
            try:
                agregar_nota_al_indice(ruta_archivo, contenido)
            except Exception as e:
                logging.error("Error al sincronizar nota en RAG: %s", e)
            return f"Nota '{titulo}' actualizada correctamente en la bóveda ({ahora})."
        else:
            # Crear nota nueva con encabezado Markdown
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(f"# {titulo}\n\n")
                f.write(f"*Creada el {ahora}*\n\n")
                f.write(f"---\n\n")
                f.write(f"{contenido}\n")
            try:
                agregar_nota_al_indice(ruta_archivo, contenido)
            except Exception as e:
                logging.error("Error al sincronizar nota en RAG: %s", e)
            return f"Nota '{titulo}' creada correctamente en la bóveda ({ahora})."

    except Exception as e:
        logging.error("Error al guardar la nota '%s': %s", titulo, e)
        return f"Error al guardar la nota '{titulo}': {e}"

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
    resultados = []

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

    for raiz, archivo in archivos_md:
        titulo_archivo = os.path.splitext(archivo)[0]
        ruta_archivo = os.path.join(raiz, archivo)

        try:
            with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()

            coincidencia_titulo = clave in titulo_archivo.lower()
            coincidencia_contenido = clave in contenido.lower()

            if coincidencia_titulo or coincidencia_contenido:
                # Extraer un fragmento relevante del contenido
                lineas = contenido.splitlines()
                extracto = []
                for linea in lineas:
                    if clave in linea.lower() and linea.strip():
                        extracto.append(f"  → {linea.strip()}")
                    if len(extracto) >= 3:
                        break

                resumen = f"📄 **{titulo_archivo}**"
                if extracto:
                    resumen += "\n" + "\n".join(extracto)
                resultados.append(resumen)

        except Exception as e:
            logging.error("Error al leer la nota '%s': %s", archivo, e)
            continue

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
