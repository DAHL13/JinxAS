import logging
import os
import shutil
import subprocess
import sys
from urllib.parse import quote
import psutil
import requests
import config
from config import MAPA_APLICACIONES, configurar_consola
from memoria_rag import buscar_en_notas

configurar_consola()

def obtener_estado_sistema() -> str:
    """
    Obtiene y formatea un resumen del estado actual del sistema:
    - Porcentaje de uso de CPU.
    - Porcentaje y cantidad en GB de memoria RAM (usada/total).
    - Porcentaje y espacio en el disco principal C: (GB usados/totales).
    """
    try:
        # Uso de CPU (intervalo breve para medición representativa)
        cpu_uso = psutil.cpu_percent(interval=0.5)

        # Uso de memoria RAM
        memoria = psutil.virtual_memory()
        ram_uso_pct = memoria.percent
        ram_usada_gb = memoria.used / (1024 ** 3)
        ram_total_gb = memoria.total / (1024 ** 3)

        # Uso del disco principal C:
        ruta_disco = "C:\\" if sys.platform == "win32" else "/"
        disco = psutil.disk_usage(ruta_disco)
        disco_uso_pct = disco.percent
        disco_usado_gb = disco.used / (1024 ** 3)
        disco_total_gb = disco.total / (1024 ** 3)

        resumen = (
            f"Estado del sistema:\n"
            f"- CPU: {cpu_uso:.1f}% de uso.\n"
            f"- Memoria RAM: {ram_uso_pct:.1f}% en uso ({ram_usada_gb:.2f} GB de {ram_total_gb:.2f} GB).\n"
            f"- Disco principal (C:): {disco_uso_pct:.1f}% en uso ({disco_usado_gb:.2f} GB de {disco_total_gb:.2f} GB usados/totales)."
        )
        return resumen

    except Exception as e:
        logging.error("Error al obtener el estado del sistema: %s", e)
        return f"Error al obtener el estado del sistema: {e}"

def obtener_temperatura() -> str:
    """
    Obtiene la temperatura de los sensores de la CPU y zona térmica del sistema.
    Intenta leer usando psutil o comandos WMI/PowerShell en Windows.
    Si no hay sensores accesibles, retorna un mensaje amable indicando el uso de CPU y que
    la lectura directa de temperatura requiere permisos elevados.
    """
    # 1. Intentar con psutil (si la plataforma o drivers lo soportan)
    if hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                lineas = []
                for nombre, entradas in temps.items():
                    for entrada in entradas:
                        lineas.append(f"{nombre} ({entrada.label or 'sensor'}): {entrada.current:.1f}°C")
                if lineas:
                    return "Lectura de temperatura de sensores:\n" + "\n".join(lineas)
        except Exception as e:
            logging.error("No se pudieron leer sensores de temperatura con psutil: %s", e)

    # 2. Intentar con WMI / PowerShell en Windows
    if sys.platform == "win32":
        try:
            ps_cmd = (
                "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
                "| ForEach-Object { [math]::Round(($_.CurrentTemperature - 2732) / 10, 1) }"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                temp_c = result.stdout.strip().splitlines()[0]
                if temp_c:
                    return f"La temperatura actual de la CPU / sistema es de {temp_c}°C."
        except Exception as e:
            logging.error("No se pudo leer temperatura por WMI/PowerShell: %s", e)

    # 3. Fallback informativo y amable.
    # Se usa interval=0.2 para obtener una medición real e independiente sin importar el orden de llamada.
    try:
        cpu_uso = psutil.cpu_percent(interval=0.2)
    except Exception as e:
        logging.error("Error al medir uso de CPU: %s", e)
        cpu_uso = 0.0

    return (
        f"No se pudo acceder a los sensores de temperatura directos porque Windows requiere permisos de administrador o soporte específico de hardware. "
        f"Sin embargo, el procesador está al {cpu_uso:.1f}% de uso, operando con normalidad."
    )

def abrir_aplicacion(app_name: str = "", nombre_app: str = "") -> str:
    """
    Abre una aplicación en Windows solo si está en la lista permitida (allowlist).
    Verifica si el ejecutable está en el PATH con shutil.which. Si existe,
    lo abre con subprocess.Popen([ruta]). Si no (es una app registrada de Windows como 'calc' o 'spotify'),
    usa os.startfile(ejecutable).
    """
    nombre = (app_name or nombre_app or "").strip()
    if not nombre:
        return "No se especificó ninguna aplicación para abrir."

    app_limpia = nombre.lower()

    if app_limpia not in MAPA_APLICACIONES:
        return f"La aplicación '{nombre}' no está permitida."

    ejecutable = MAPA_APLICACIONES[app_limpia]

    try:
        ruta = shutil.which(ejecutable)
        if ruta:
            subprocess.Popen([ruta])
        else:
            os.startfile(ejecutable)

        logging.info(f"App lanzada de forma segura: {nombre}")
        return f"Abriendo {nombre} correctamente."
    except Exception as e:
        logging.error("Error al intentar ejecutar '%s': %s", nombre, e)
        return f"Error al intentar ejecutar '{nombre}': {e}"

def obtener_clima() -> str:
    """
    Obtiene el clima actual y la temperatura consultando la API de wttr.in
    utilizando la ciudad por defecto configurada en config.py.
    """
    try:
        url = f"https://wttr.in/{quote(config.CIUDAD_POR_DEFECTO)}?format=%C+%t"
        respuesta = requests.get(url, timeout=5)
        if respuesta.status_code == 200:
            texto = respuesta.text.strip()
            texto_lower = texto.lower()
            if not texto or "unknown location" in texto_lower or "404" in texto:
                return "Error: No se pudo obtener el clima en este momento."
            return texto
        return "Error: No se pudo obtener el clima en este momento."
    except requests.RequestException as e:
        logging.error("Error de red al consultar el clima: %s", e)
        return "Error: No se pudo obtener el clima en este momento."


def consultar_boveda(consulta: str) -> str:
    """
    Busca información, conceptos o código en los apuntes personales del usuario
    almacenados en la bóveda de Obsidian, usando el índice RAG local (FAISS).
    """
    try:
        return buscar_en_notas(consulta)
    except Exception as e:
        logging.error("[RAG] Error al consultar la bóveda: %s", e)
        return f"Error al consultar la bóveda de Obsidian: {e}"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    logging.info("Módulo de herramientas - pruebas")
    logging.info("Estado del sistema:\n%s", obtener_estado_sistema())
    logging.info("Temperatura del sistema:\n%s", obtener_temperatura())
    logging.info("Clima actual:\n%s", obtener_clima())
    logging.info("Prueba: abrir bloc de notas")
    resultado_app = abrir_aplicacion("bloc de notas")
    logging.info(resultado_app)
