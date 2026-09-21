import os
import sys
from unittest.mock import MagicMock
import pytest

# Asegurar que el directorio raíz del proyecto esté en sys.path
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

# ---------------------------------------------------------------------------
# Aislamiento de módulos pesados (ML/Torch/Whisper/FAISS/Audio/UI)
# Permite ejecutar estos tests de lógica pura en milisegundos y en CI ligero.
# ---------------------------------------------------------------------------
MODULOS_PESADOS = [
    "torch",
    "whisper",
    "faiss",
    "sentence_transformers",
    "speech_recognition",
    "pyaudio",
    "pygame",
    "webview",
    "ollama",
    "edge_tts",
    "thefuzz",
    "psutil",
    "requests",
    "memoria_rag",
    "voz",
    "percepcion",
    "cerebro",
    "herramientas",
    "interfaz",
]

for mod in MODULOS_PESADOS:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Importación segura de módulos bajo prueba
import config
from main import normalizar, _extraer_llamada
from memoria import _normalizar_nombre_archivo


# ===========================================================================
# Tests de Normalización de Texto (main.py)
# ===========================================================================

def test_comandos_salida_coincidencia_exacta():
    """Verifica que '¡Salir!' se normalice a 'salir' y coincida con COMANDOS_SALIDA."""
    resultado = normalizar("¡Salir!")
    assert resultado == "salir"
    assert resultado in config.COMANDOS_SALIDA


def test_frase_con_palabra_salida_no_coincide():
    """Verifica que una frase que contiene 'salir' dentro no sea interpretada como comando de salida."""
    frase = "recuérdame salir a las cinco"
    resultado = normalizar(frase)
    assert resultado == "recuerdame salir a las cinco"
    assert resultado not in config.COMANDOS_SALIDA


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("¡CANCELAR!", "cancelar"),
        ("¿Detener?", "detener"),
        ("Ápagar", "apagar"),
        ("HASTA LUEGO...", "hasta luego"),
    ],
)
def test_variaciones_comandos_salida(entrada, esperado):
    """Prueba mayúsculas, tildes y signos de puntuación en comandos de salida."""
    resultado = normalizar(entrada)
    assert resultado == esperado
    assert resultado in config.COMANDOS_SALIDA


def test_frases_reinicio():
    """Verifica que frases de reinicio se normalicen adecuadamente."""
    resultado = normalizar("¡Olvida todo!")
    assert resultado == "olvida todo"
    assert resultado in config.FRASES_REINICIO


def test_texto_vacio_y_espacios():
    """Manejo de strings vacíos, None o únicamente espacios."""
    assert normalizar("") == ""
    assert normalizar(None) == ""
    assert normalizar("     ") == ""


def test_colapso_espacios_multiples():
    """Múltiples espacios continuos y tabulaciones deben reducirse a un solo espacio."""
    assert normalizar("   hola    mundo   jinx   ") == "hola mundo jinx"


# ===========================================================================
# Tests de Normalización de Nombres de Archivo (memoria.py)
# ===========================================================================

@pytest.mark.parametrize(
    "nombre_reservado",
    ["CON", "con", "PRN", "prn", "AUX", "NUL", "COM1", "com1", "LPT1", "lpt9"],
)
def test_nombres_reservados_windows(nombre_reservado):
    """Los nombres reservados en Windows deben ser sufijados para evitar errores de sistema operativo."""
    archivo = _normalizar_nombre_archivo(nombre_reservado)
    assert archivo.lower() != f"{nombre_reservado.lower()}.md"
    assert archivo.endswith("_.md")


def test_caracteres_prohibidos_windows():
    """Caracteres como \\ / : * ? \" < > | deben ser eliminados."""
    titulo = 'Nota con : * ? " < > | y \\ / barras'
    resultado = _normalizar_nombre_archivo(titulo)
    caracteres_invalidos = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}
    assert not any(c in resultado for c in caracteres_invalidos)
    assert resultado.endswith(".md")


def test_extension_md_existente():
    """Si el título ya termina en .md, no debe duplicarse la extensión a .md.md."""
    resultado = _normalizar_nombre_archivo("apuntes_python.md")
    assert resultado == "apuntes_python.md"


def test_titulo_solo_caracteres_invalidos():
    """Si el título queda vacío tras limpiar caracteres inválidos, debe usar 'Sin titulo'."""
    resultado = _normalizar_nombre_archivo("***???///")
    assert resultado == "Sin titulo.md"


def test_longitud_maxima_titulo():
    """Verifica que el nombre base del archivo respete TITULO_NOTA_MAX."""
    titulo_largo = "A" * 150
    resultado = _normalizar_nombre_archivo(titulo_largo)
    base = resultado[:-3]
    assert len(base) <= config.TITULO_NOTA_MAX


# ===========================================================================
# Tests de Extracción de Llamadas a Herramientas (main.py)
# ===========================================================================

def test_extraer_llamada_desde_dict():
    """Parsea correctamente un diccionario con argumentos como string JSON."""
    tool_call = {
        "function": {
            "name": "abrir_aplicacion",
            "arguments": '{"nombre_app": "calc"}',
        }
    }
    nombre, args = _extraer_llamada(tool_call)
    assert nombre == "abrir_aplicacion"
    assert args == {"nombre_app": "calc"}


def test_extraer_llamada_desde_dict_argumentos_objeto():
    """Parsea un diccionario donde arguments ya es un dict de Python."""
    tool_call = {
        "function": {
            "name": "obtener_clima",
            "arguments": {},
        }
    }
    nombre, args = _extraer_llamada(tool_call)
    assert nombre == "obtener_clima"
    assert args == {}


# ===========================================================================
# Tests de Configuración General (config.py)
# ===========================================================================

def test_configurar_consola_no_lanza_excepcion():
    """La función configurar_consola debe ejecutarse sin fallar."""
    config.configurar_consola()


def test_ciudad_por_defecto_configurada():
    """La ciudad por defecto debe estar definida y no vacía."""
    assert isinstance(config.CIUDAD_POR_DEFECTO, str)
    assert len(config.CIUDAD_POR_DEFECTO.strip()) > 0
