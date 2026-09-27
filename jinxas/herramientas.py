import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
import psutil
import requests
import config
from config import MAPA_APLICACIONES
from comandos import normalizar
from memoria_rag import buscar_en_notas
from registro import herramienta

_cache_clima: tuple[float, str] = (0.0, "")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


@herramienta("Obtiene un resumen del estado actual del sistema: CPU, RAM y disco.")
def obtener_estado_sistema() -> str:
    """
    Obtiene y formatea un resumen del estado actual del sistema en una sola línea corta:
    CPU, RAM (usada de total en GB) y disco principal.
    """
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        usada_gb = ram.used / (1024 ** 3)
        total_gb = ram.total / (1024 ** 3)

        unidad = os.environ.get("SystemDrive", "C:") + "\\"
        disco = psutil.disk_usage(unidad)

        return f"CPU {cpu}%, RAM {ram.percent}% ({usada_gb:.1f} de {total_gb:.1f} GB usados), disco {disco.percent}%."
    except Exception as e:
        logging.error("Error al obtener el estado del sistema: %s", e)
        return f"Error al obtener el estado del sistema: {e}"


@herramienta("Obtiene la temperatura de los sensores de la CPU y sistema.")
def obtener_temperatura() -> str:
    """
    Obtiene la temperatura de los sensores de la CPU y zona térmica del sistema.
    Intenta leer usando psutil o comandos WMI/PowerShell en Windows.
    Si no hay sensores accesibles, retorna un mensaje honesto indicando el uso de CPU.
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
                timeout=3,
            )
            if result.returncode == 0 and result.stdout.strip():
                temp_c = result.stdout.strip().splitlines()[0]
                if temp_c:
                    return f"La temperatura actual de la CPU / sistema es de {temp_c}°C."
        except Exception as e:
            logging.error("No se pudo leer temperatura por WMI/PowerShell: %s", e)

    # 3. Fallback honesto sin afirmaciones falsas
    try:
        uso_cpu = psutil.cpu_percent(interval=0.2)
    except Exception as e:
        logging.error("Error al medir uso de CPU: %s", e)
        uso_cpu = 0.0

    return f"No tengo acceso a un sensor de temperatura en este equipo. La CPU está al {uso_cpu}% de uso."


@herramienta(
    f"Abre una aplicación. Aplicaciones permitidas: {', '.join(MAPA_APLICACIONES.keys())}",
    parametros={
        "nombre_app": {
            "type": "string",
            "description": "Nombre de la aplicación a abrir, en minúsculas si es posible.",
        }
    },
)
def abrir_aplicacion(nombre_app: str = "", app_name: str = "") -> str:
    """
    Abre una aplicación en Windows solo si está en la lista permitida (allowlist).
    Valida contra config.MAPA_APLICACIONES. Si es URI, usa os.startfile.
    Si es ejecutable, verifica con shutil.which y ejecuta con subprocess.Popen sin shell.
    """
    app = nombre_app or app_name
    destino = config.MAPA_APLICACIONES.get(normalizar(app or ""))
    if not destino:
        return f"La aplicación '{app}' no está permitida."
    tipo, _, objetivo = destino.partition(":")
    try:
        if tipo == "uri":
            os.startfile(objetivo)
        else:
            ruta = shutil.which(objetivo)
            if not ruta:
                return f"No encontré {app} instalada."
            subprocess.Popen(
                [ruta],
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        return f"Abriendo {app}."
    except OSError as e:
        logging.error("No pude abrir %s: %s", app, e)
        return f"No pude abrir {app}."


@herramienta(f"Consulta estrictamente el clima exterior y la temperatura ambiente en {config.CIUDAD}.")
def obtener_clima() -> str:
    """
    Obtiene el clima actual y la temperatura consultando la API de wttr.in
    utilizando config.URL_CLIMA con caché en memoria de 10 minutos (600s).
    """
    global _cache_clima
    ts, texto = _cache_clima
    if texto and time.time() - ts < 600:
        return texto
    try:
        url = config.URL_CLIMA
        respuesta = requests.get(url, headers={"User-Agent": "JinxAS/1.0"}, timeout=5)
        if respuesta.status_code == 200:
            resultado = respuesta.text.strip()
            texto_lower = resultado.lower()
            if not resultado or "unknown location" in texto_lower or "404" in resultado:
                return "Error: No se pudo obtener el clima en este momento."
            _cache_clima = (time.time(), resultado)
            return resultado
        return "Error: No se pudo obtener el clima en este momento."
    except requests.RequestException as e:
        logging.error("Error de red al consultar el clima: %s", e)
        return "Error: No se pudo obtener el clima en este momento."


@herramienta("Obtiene la fecha y hora actuales en español.")
def obtener_fecha_hora() -> str:
    """
    Obtiene la fecha y hora actual formateada en español.
    """
    a = datetime.now()
    return f"Es {DIAS[a.weekday()]} {a.day} de {MESES[a.month - 1]} de {a.year}, {a:%H:%M}."


@herramienta(
    "Búsqueda semántica (RAG) en los apuntes del usuario en Obsidian. Úsala SIEMPRE que el usuario haga preguntas abiertas sobre sus conocimientos, proyectos, clases o conceptos documentados.",
    parametros={
        "consulta": {
            "type": "string",
            "description": "Término, pregunta o concepto a buscar en la bóveda.",
        }
    },
)
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
    logging.info("Estado del sistema: %s", obtener_estado_sistema())
    logging.info("Temperatura del sistema: %s", obtener_temperatura())
    logging.info("Fecha y hora: %s", obtener_fecha_hora())
    logging.info("Clima actual: %s", obtener_clima())
    logging.info("Prueba: abrir bloc de notas")
    resultado_app = abrir_aplicacion("bloc de notas")
    logging.info(resultado_app)
