import os
import subprocess
import sys
import psutil

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Diccionario de comandos y ejecutables comunes en Windows
MAPA_APLICACIONES = {
    # Navegadores
    'navegador': 'msedge',
    'edge': 'msedge',
    'microsoft edge': 'msedge',
    'chrome': 'chrome',
    'google chrome': 'chrome',

    # Código y desarrollo
    'codigo': 'code',
    'código': 'code',
    'vscode': 'code',
    'visual studio': 'code',
    'visual studio code': 'code',
    'code': 'code',

    # Bloc de notas
    'bloc de notas': 'notepad',
    'notas': 'notepad',
    'notepad': 'notepad',

    # Calculadora
    'calculadora': 'calc',
    'calc': 'calc',

    # Terminal / Consola
    'terminal': 'cmd',
    'cmd': 'cmd',
    'consola': 'cmd',
    'simbolo del sistema': 'cmd',

    # Extras comunes
    'spotify': 'spotify',
    'discord': 'discord',
}

def obtener_estado_sistema() -> str:
    """
    Obtiene y formatea un resumen del estado actual del sistema:
    - Porcentaje de uso de CPU.
    - Porcentaje y cantidad en GB de memoria RAM (usada/total).
    - Porcentaje y espacio en el disco principal C:.
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
            f"- Disco principal (C:): {disco_uso_pct:.1f}% en uso ({disco_usado_gb:.2f} GB de {disco_total_gb:.2f} GB libres/totales)."
        )
        return resumen

    except Exception as e:
        return f"Error al obtener el estado del sistema: {e}"

def obtener_temperatura() -> str:
    """
    Intenta leer la temperatura de los sensores del sistema usando psutil o comandos WMI/PowerShell en Windows.
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
        except Exception:
            pass

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
        except Exception:
            pass

    # 3. Fallback informativo y amable
    try:
        cpu_uso = psutil.cpu_percent(interval=0.5)
    except Exception:
        cpu_uso = 0.0

    return (
        f"No se pudo acceder a los sensores de temperatura directos porque Windows requiere permisos de administrador o soporte específico de hardware. "
        f"Sin embargo, el procesador está al {cpu_uso:.1f}% de uso, operando con normalidad."
    )

def abrir_aplicacion(nombre_app: str) -> str:
    """
    Abre una aplicación en Windows mediante un mapeo estricto y directo de nombres.
    Si el nombre no coincide con una clave del mapeo, intenta lanzarlo directamente con os.system(start ...).
    Si no se encuentra, retorna un aviso indicando que no se encontró el ejecutable.
    """
    if not nombre_app:
        return "No se especificó ninguna aplicación para abrir."

    app_limpia = nombre_app.strip().lower()

    # 1. Comprobación estricta en el diccionario de mapeo
    if app_limpia in MAPA_APLICACIONES:
        ejecutable = MAPA_APLICACIONES[app_limpia]
        try:
            if sys.platform == "win32":
                os.system(f"start {ejecutable}")
            else:
                subprocess.Popen([ejecutable], shell=True)
            return f"Abriendo {nombre_app} correctamente."
        except Exception as e:
            return f"Error al intentar ejecutar '{nombre_app}': {e}"

    # 2. Intento de lanzamiento directo del comando / aplicación
    try:
        if sys.platform == "win32":
            retorno = os.system(f'start "" "{app_limpia}"')
        else:
            retorno = os.system(f"{app_limpia} &")

        if retorno == 0:
            return f"Abriendo {nombre_app} correctamente."
        else:
            return f"No se encontró el ejecutable para la aplicación '{nombre_app}'."
    except Exception as e:
        return f"Error al intentar abrir '{nombre_app}': {e}"

if __name__ == "__main__":
    print("==================================================")
    print("       MÓDULO DE HERRAMIENTAS - PRUEBAS           ")
    print("==================================================")
    print("\n--- ESTADO DEL SISTEMA ---")
    print(obtener_estado_sistema())
    print("\n--- TEMPERATURA DEL SISTEMA ---")
    print(obtener_temperatura())
    print("\n--- PRUEBA: ABRIR BLOC DE NOTAS ---")
    resultado_app = abrir_aplicacion("bloc de notas")
    print(resultado_app)
    print("==================================================")
