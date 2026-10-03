"""
tests/test_h024_nombres_reservados.py
======================================
Pruebas para H-024: Manejo seguro de nombres reservados de Windows en títulos de notas.
Verifica que dispositivos DOS/Windows queden prefijados con 'nota ', incluso cuando
incluyen extensiones o múltiples puntos (p. ej. CON.md, nul.txt, aux.notas).
"""
import pytest
from jinxas.memoria import _normalizar_nombre_archivo


@pytest.mark.parametrize(
    "entrada,prefijo_esperado",
    [
        ("con", "nota con"),
        ("CON.md", "nota CON.md"),
        ("nul.txt", "nota nul.txt"),
        ("aux.notas", "nota aux.notas"),
        ("COM1.md", "nota COM1.md"),
        ("lpt9.x.y", "nota lpt9.x.y"),
    ],
)
def test_nombres_reservados_con_extension_quedan_prefijados(entrada, prefijo_esperado):
    """Nombres reservados con o sin extensiones deben quedar prefijados con 'nota '."""
    resultado = _normalizar_nombre_archivo(entrada)
    assert resultado.startswith("nota ")
    assert prefijo_esperado.lower() in resultado.lower()
    assert resultado.endswith(".md")


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("Reunión: lunes", "Reunión lunes.md"),
        ("Apuntes de Python", "Apuntes de Python.md"),
        ("Lista de compras 2026", "Lista de compras 2026.md"),
    ],
)
def test_titulos_normales_no_modifican_prefijo(entrada, esperado):
    """Títulos normales no deben ser prefijados con 'nota ' innecesariamente."""
    resultado = _normalizar_nombre_archivo(entrada)
    assert resultado == esperado
