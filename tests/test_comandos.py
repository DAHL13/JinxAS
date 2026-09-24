import pytest
from comandos import es_comando, COMANDOS_SALIDA, COMANDOS_REINICIO


# ── Casos que SÍ deben disparar el apagado ───────────────────────────────────
@pytest.mark.parametrize("texto", [
    "Salir.",
    "APAGAR",
    "detener",
    "Cancelar",
    "Jinx, detener",
    "por favor salir",
    "hasta luego",
])
def test_comando_salida_verdadero(texto):
    assert es_comando(texto, COMANDOS_SALIDA), f"Se esperaba True para: {texto!r}"


# ── Frases normales que contienen la palabra pero NO son comandos exactos ─────
@pytest.mark.parametrize("texto", [
    "Recuérdame cancelar la cita del jueves",
    "¿Puedes apagar la luz de la sala?",
    "No quiero salir todavía",
    "Tengo que detener el script de Python",
])
def test_comando_salida_falso(texto):
    assert not es_comando(texto, COMANDOS_SALIDA), f"Se esperaba False para: {texto!r}"


# ── Casos que SÍ deben disparar el reinicio de memoria ───────────────────────
@pytest.mark.parametrize("texto", [
    "olvida todo",
    "Borra la memoria",
    "nueva conversacion",
    "Jinx olvida todo",
])
def test_comando_reinicio_verdadero(texto):
    assert es_comando(texto, COMANDOS_REINICIO), f"Se esperaba True para: {texto!r}"


# ── Frases con "olvida" que NO son comandos de reinicio ──────────────────────
@pytest.mark.parametrize("texto", [
    "no olvida todo lo que te dije",
    "olvida todo el mundo lo que pasó",
])
def test_comando_reinicio_falso(texto):
    assert not es_comando(texto, COMANDOS_REINICIO), f"Se esperaba False para: {texto!r}"
