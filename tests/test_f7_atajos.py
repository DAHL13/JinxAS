"""
test_f7_atajos.py — Pruebas unitarias para atajos.py (F7-01).

Valida el enrutamiento determinista de comandos rápidos y atajos sin invocar al LLM,
así como la resiliencia a mayúsculas, acentos, signos de puntuación y espacios extras.
"""
import pytest
from atajos import resolver_atajo


# ── a) Coincidencias de aplicaciones ──────────────────────────────────────────
@pytest.mark.parametrize(
    ("texto", "app_esperada"),
    [
        ("abre la calculadora", "calculadora"),
        ("abre bloc de notas", "bloc de notas"),
        ("abre chrome", "chrome"),
        ("abre obsidian", "obsidian"),
        ("abre el bloc de notas", "bloc de notas"),
        ("abre notas", "notas"),
        ("abre vscode", "vscode"),
    ],
)
def test_resolver_atajo_aplicaciones(texto, app_esperada):
    resultado = resolver_atajo(texto)
    assert resultado is not None, f"Se esperaba atajo para: {texto!r}"
    tool, args = resultado
    assert tool == "abrir_aplicacion"
    assert args == {"nombre_app": app_esperada}


# ── b) Coincidencias de sistema y temperatura ────────────────────────────────
@pytest.mark.parametrize(
    "texto",
    [
        "cómo está la ram",
        "como esta la ram",
        "estado del sistema",
    ],
)
def test_resolver_atajo_estado_sistema(texto):
    resultado = resolver_atajo(texto)
    assert resultado is not None, f"Se esperaba atajo para: {texto!r}"
    tool, args = resultado
    assert tool == "obtener_estado_sistema"
    assert args == {}


@pytest.mark.parametrize(
    "texto",
    [
        "qué temperatura tiene",
        "que temperatura tiene",
        "cómo está la temperatura",
        "como esta la temperatura",
    ],
)
def test_resolver_atajo_temperatura(texto):
    resultado = resolver_atajo(texto)
    assert resultado is not None, f"Se esperaba atajo para: {texto!r}"
    tool, args = resultado
    assert tool == "obtener_temperatura"
    assert args == {}


# ── c) Coincidencias de fecha y hora ──────────────────────────────────────────
@pytest.mark.parametrize(
    "texto",
    [
        "qué hora es",
        "que hora es",
        "dime la hora",
        "qué día es hoy",
        "que dia es hoy",
        "fecha y hora",
    ],
)
def test_resolver_atajo_fecha_hora(texto):
    resultado = resolver_atajo(texto)
    assert resultado is not None, f"Se esperaba atajo para: {texto!r}"
    tool, args = resultado
    assert tool == "obtener_fecha_hora"
    assert args == {}


# ── d) Comandos no coincidentes que deben devolver None ───────────────────────
@pytest.mark.parametrize(
    "texto",
    [
        "cuéntame un chiste",
        "busca mis notas de python",
        "abre una ventana al azar",
        "cuál es la capital de Francia",
        "hola jinx",
        "reproduce algo de música",
    ],
)
def test_resolver_atajo_no_coincidente_retorna_none(texto):
    resultado = resolver_atajo(texto)
    assert resultado is None, f"Se esperaba None para: {texto!r}, pero devolvió {resultado!r}"


# ── e) Resiliencia a mayúsculas, acentos y espacios adicionales ───────────────
@pytest.mark.parametrize(
    ("texto", "tool_esperada", "args_esperados"),
    [
        ("  ABRE   LA   CALCULADORA  ", "abrir_aplicacion", {"nombre_app": "calculadora"}),
        ("CÓMO ESTÁ LA RAM", "obtener_estado_sistema", {}),
        ("¿QUÉ DÍA ES HOY?", "obtener_fecha_hora", {}),
        ("¡¡DIME LA HORA!!", "obtener_fecha_hora", {}),
        ("  Estado   Del   Sistema  ", "obtener_estado_sistema", {}),
        ("¿Qué temperatura tiene?", "obtener_temperatura", {}),
        ("ABRE  CHROME", "abrir_aplicacion", {"nombre_app": "chrome"}),
    ],
)
def test_resolver_atajo_resiliencia_normalizacion(texto, tool_esperada, args_esperados):
    resultado = resolver_atajo(texto)
    assert resultado is not None, f"Se esperaba atajo para texto normalizado: {texto!r}"
    tool, args = resultado
    assert tool == tool_esperada
    assert args == args_esperados
