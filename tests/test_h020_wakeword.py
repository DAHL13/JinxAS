"""
tests/test_h020_wakeword.py
============================
Pruebas para H-020: Reducción de falsos positivos en palabra de activación.
Usa thefuzz real para evaluar fuzzy matching contra variantes de wake word con umbral 90.
"""
import pytest
from jinxas import config
from jinxas.percepcion import coincide_wakeword


@pytest.mark.parametrize(
    "palabra_falso_positivo",
    [
        "inks",
        "links",
        "sinks",
        "winks",
        "pinks",
        "minks",
        "kinks",
        "finks",
        "hinks",
        "jenks",
        "think",
        "thanks",
    ],
)
def test_falsos_positivos_retornan_false(palabra_falso_positivo):
    """Palabras fonéticamente parecidas que antes activaban al 80% deben dar False al umbral 90."""
    assert coincide_wakeword(palabra_falso_positivo, config.VARIANTES_WAKEWORD) is False
    # En frase completa tampoco deben activar
    assert coincide_wakeword(f"check the {palabra_falso_positivo} now", config.VARIANTES_WAKEWORD) is False


@pytest.mark.parametrize(
    "variante_valida",
    [
        "jinx",
        "jinks",
        "jinxs",
        "sphinx",
    ],
)
def test_variantes_validas_retornan_true(variante_valida):
    """Las variantes aceptadas de Jinx deben dar True."""
    assert coincide_wakeword(variante_valida, config.VARIANTES_WAKEWORD) is True
    # En frase hablada
    assert coincide_wakeword(f"oye {variante_valida} cómo estás", config.VARIANTES_WAKEWORD) is True


@pytest.mark.parametrize("palabra_corta", ["a", "in", "yo", "si", "ok", "no"])
def test_palabras_menos_de_tres_letras_ignoradas(palabra_corta):
    """Palabras de menos de 3 letras se ignoran para evitar falsas coincidencias."""
    assert coincide_wakeword(palabra_corta, config.VARIANTES_WAKEWORD) is False
