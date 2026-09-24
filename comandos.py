import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes (NFD/Mn), sin puntuación, espacios colapsados."""
    if not texto:
        return ""
    texto = texto.lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


# Comandos que provocan el apagado del asistente.
COMANDOS_SALIDA = {"salir", "apagar", "cancelar", "detener", "hasta luego"}

# Frases que reinician la memoria de conversación.
COMANDOS_REINICIO = {"olvida todo", "borra la memoria", "nueva conversacion"}

# Prefijos opcionales que el usuario puede anteponer al comando.
_PREFIJOS = ("jinx ", "por favor ")


def es_comando(texto: str, comandos: set[str]) -> bool:
    """
    Devuelve True si *texto* (normalizado y sin prefijos opcionales) coincide
    exactamente con algún elemento del set *comandos*.

    La comparación es por igualdad exacta para evitar falsos positivos por
    subcadena (p. ej. "recuérdame cancelar la cita" no dispara COMANDOS_SALIDA).
    """
    normalizado = normalizar(texto)
    for prefijo in _PREFIJOS:
        if normalizado.startswith(prefijo):
            normalizado = normalizado[len(prefijo):]
            break
    return normalizado in comandos
