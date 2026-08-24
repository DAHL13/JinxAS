import os
import re
import sys
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ruta de la bóveda de Obsidian (relativa a la raíz del proyecto)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_VAULT = os.path.join(_BASE_DIR, "Boveda_Obsidian")

def _normalizar_nombre_archivo(titulo: str) -> str:
    """
    Convierte un título a un nombre de archivo válido en formato .md.
    Elimina caracteres no permitidos en nombres de archivo de Windows.
    """
    nombre = titulo.strip()
    # Reemplazar caracteres no permitidos en Windows: \ / : * ? " < > |
    nombre = re.sub(r'[\\/:*?"<>|]', '', nombre)
    # Reemplazar espacios múltiples con uno solo
    nombre = re.sub(r'\s+', ' ', nombre)
    nombre = nombre[:80]
    # Asegurarse de que termine en .md
    if not nombre.lower().endswith('.md'):
        nombre = nombre + '.md'
    return nombre

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
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        if os.path.exists(ruta_archivo):
            # Añadir al final del archivo existente
            with open(ruta_archivo, "a", encoding="utf-8") as f:
                f.write(f"\n\n---\n**Actualización {ahora}:**\n\n{contenido}\n")
            return f"Nota '{titulo}' actualizada correctamente en la bóveda ({ahora})."
        else:
            # Crear nota nueva con encabezado Markdown
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(f"# {titulo}\n\n")
                f.write(f"*Creada el {ahora}*\n\n")
                f.write(f"---\n\n")
                f.write(f"{contenido}\n")
            return f"Nota '{titulo}' creada correctamente en la bóveda ({ahora})."

    except Exception as e:
        return f"Error al guardar la nota '{titulo}': {e}"

def buscar_nota(palabra_clave: str) -> str:
    """
    Busca coincidencias de una palabra clave en los títulos y contenidos
    de todos los archivos .md dentro de RUTA_VAULT.
    Retorna un resumen del contenido encontrado o un aviso si no hay registros.
    """
    if not palabra_clave or not palabra_clave.strip():
        return "No se proporcionó una palabra clave para buscar."

    clave = palabra_clave.strip().lower()
    resultados = []

    try:
        archivos_md = [f for f in os.listdir(RUTA_VAULT) if f.lower().endswith('.md')]
    except Exception as e:
        return f"Error al acceder a la bóveda: {e}"

    if not archivos_md:
        return f"La bóveda está vacía. No hay notas guardadas aún."

    for archivo in archivos_md:
        titulo_archivo = archivo.replace('.md', '')
        ruta_archivo = os.path.join(RUTA_VAULT, archivo)

        try:
            with open(ruta_archivo, "r", encoding="utf-8") as f:
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

        except Exception:
            continue

    if resultados:
        encabezado = f"Se encontraron {len(resultados)} nota(s) con '{palabra_clave}':\n\n"
        return encabezado + "\n\n".join(resultados)
    else:
        return f"No se encontraron notas sobre '{palabra_clave}' en la bóveda."

if __name__ == "__main__":
    print("==================================================")
    print("    MÓDULO DE MEMORIA - BÓVEDA OBSIDIAN           ")
    print("==================================================")

    # Prueba: guardar una nota nueva
    print("\n--- PRUEBA: GUARDAR NOTA ---")
    resultado_guardar = guardar_nota(
        "Jinx Primera Prueba",
        "Esta es la primera nota de prueba guardada por Jinx. Todo funciona correctamente."
    )
    print(resultado_guardar)

    # Prueba: buscar la nota recién creada
    print("\n--- PRUEBA: BUSCAR NOTA ---")
    resultado_buscar = buscar_nota("Jinx")
    print(resultado_buscar)

    print("==================================================")
