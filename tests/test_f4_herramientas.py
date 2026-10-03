from datetime import datetime
from unittest.mock import MagicMock, patch

import config
import herramientas


# ============================================================================
# F4-01: Pruebas de abrir_aplicacion
# ============================================================================

def test_abrir_aplicacion_no_permitida():
    """Aplicaciones no permitidas (incluyendo cmd) deben ser rechazadas."""
    for app in ["cmd", "terminal", "consola", "simbolo del sistema", "malware", "powershell"]:
        res = herramientas.abrir_aplicacion(app)
        assert res == f"La aplicación '{app}' no está permitida."


def test_abrir_aplicacion_exe_encontrada():
    """Aplicación tipo 'exe:' encontrada debe ejecutarse con shell=False y creationflags."""
    with patch("herramientas.shutil.which", return_value=r"C:\Windows\System32\notepad.exe"), \
         patch("herramientas.subprocess.Popen") as mock_popen:
        res = herramientas.abrir_aplicacion("bloc de notas")
        assert res == "Abriendo bloc de notas."
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0] == [r"C:\Windows\System32\notepad.exe"]
        assert kwargs.get("shell") is False
        assert "creationflags" in kwargs


def test_abrir_aplicacion_exe_no_instalada():
    """Aplicación permitida pero no encontrada en PATH (shutil.which -> None)."""
    with patch("herramientas.shutil.which", return_value=None):
        res = herramientas.abrir_aplicacion("calculadora")
        assert res == "No encontré calculadora instalada."


def test_abrir_aplicacion_uri_exitosa():
    """Aplicación tipo 'uri:' debe invocarse con os.startfile."""
    with patch("herramientas.os.startfile") as mock_startfile:
        res = herramientas.abrir_aplicacion("spotify")
        assert res == "Abriendo spotify."
        mock_startfile.assert_called_once_with("spotify:")

    with patch("herramientas.os.startfile") as mock_startfile:
        res = herramientas.abrir_aplicacion("notas")
        assert res == "Abriendo notas."
        mock_startfile.assert_called_once_with("obsidian://")


def test_abrir_aplicacion_manejo_oserror():
    """Manejo seguro de OSError al intentar abrir una aplicación."""
    with patch("herramientas.shutil.which", return_value=r"C:\fake\code.exe"), \
         patch("herramientas.subprocess.Popen", side_effect=OSError("Permiso denegado")):
        res = herramientas.abrir_aplicacion("vscode")
        assert res == "No pude abrir vscode."

    with patch("herramientas.os.startfile", side_effect=OSError("Protocolo no registrado")):
        res = herramientas.abrir_aplicacion("discord")
        assert res == "No pude abrir discord."


# ============================================================================
# F4-02: Pruebas de obtener_temperatura
# ============================================================================

def test_obtener_temperatura_sin_sensor():
    """Si no hay sensor, debe devolver mensaje honesto sin afirmar que opera con normalidad."""
    with patch("herramientas.psutil.sensors_temperatures", return_value={}), \
         patch("herramientas.subprocess.run", side_effect=Exception("WMI no disponible")), \
         patch("herramientas.psutil.cpu_percent", return_value=18.5):
        res = herramientas.obtener_temperatura()
        assert res == "No tengo acceso a un sensor de temperatura en este equipo. La CPU está al 18.5% de uso."
        assert "operando con normalidad" not in res


def test_obtener_temperatura_con_sensor_psutil():
    """Si hay sensor en psutil, devuelve lectura en °C."""
    mock_sensor = MagicMock()
    mock_sensor.label = "CPU Core"
    mock_sensor.current = 52.3
    with patch("herramientas.psutil.sensors_temperatures", return_value={"coretemp": [mock_sensor]}):
        res = herramientas.obtener_temperatura()
        assert "52.3°C" in res
        assert "coretemp" in res


# ============================================================================
# F4-03: Pruebas de obtener_estado_sistema
# ============================================================================

def test_obtener_estado_sistema_linea_unica():
    """Debe devolver una sola línea corta con CPU, RAM (usada de total) y disco con SystemDrive."""
    mock_ram = MagicMock()
    mock_ram.percent = 50.0
    mock_ram.used = 8 * (1024 ** 3)
    mock_ram.total = 16 * (1024 ** 3)

    mock_disco = MagicMock()
    mock_disco.percent = 40.0

    with patch("herramientas.psutil.cpu_percent", return_value=12.0), \
         patch("herramientas.psutil.virtual_memory", return_value=mock_ram), \
         patch("herramientas.psutil.disk_usage", return_value=mock_disco) as mock_disk_usage, \
         patch.dict("os.environ", {"SystemDrive": "D:"}):
        res = herramientas.obtener_estado_sistema()
        assert "\n" not in res
        assert res == "CPU 12.0%, RAM 50.0% (8.0 de 16.0 GB usados), disco 40.0%."
        mock_disk_usage.assert_called_once_with("D:\\")


# ============================================================================
# F4-04: Pruebas de obtener_clima (User-Agent y caché)
# ============================================================================

def test_obtener_clima_user_agent_y_cache():
    """Debe consultar config.URL_CLIMA con User-Agent y usar caché de 10 minutos."""
    herramientas._cache_clima = (0.0, "")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "Soleado +24°C"

    with patch("herramientas.requests.get", return_value=mock_resp) as mock_get:
        res1 = herramientas.obtener_clima()
        assert res1 == "Soleado +24°C"
        mock_get.assert_called_once_with(
            config.URL_CLIMA,
            headers={"User-Agent": "JinxAS/1.0"},
            timeout=5,
        )

        # Segunda llamada inmediata: debe responder desde caché
        res2 = herramientas.obtener_clima()
        assert res2 == "Soleado +24°C"
        assert mock_get.call_count == 1


# ============================================================================
# F4-05: Pruebas de obtener_fecha_hora
# ============================================================================

def test_obtener_fecha_hora():
    """Debe formatear la fecha y hora en español."""
    # 2026-09-26 es sábado
    fecha_fija = datetime(2026, 9, 26, 14, 45)
    with patch("herramientas.datetime") as mock_datetime:
        mock_datetime.now.return_value = fecha_fija
        res = herramientas.obtener_fecha_hora()
        assert res == "Es sábado 26 de septiembre de 2026, 14:45."
