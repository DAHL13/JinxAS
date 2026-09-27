"""
conversacion.py — F7-01: Lógica pura de gestión de contexto y memoria conversacional.

Funciones aisladas sin dependencias de I/O ni modelos de ML, permitiendo
pruebas unitarias deterministas y de alta velocidad.
"""
from __future__ import annotations


def recortar(contexto: list[dict], max_msgs: int = 16) -> list[dict]:
    """
    Recorta el historial conversacional manteniendo siempre el mensaje del sistema
    (índice 0) y los últimos `max_msgs` mensajes.
    Garantiza que el primer mensaje tras el system prompt NO sea de rol 'tool'
    para evitar errores de validación en Ollama.
    """
    if not contexto:
        return []
    if len(contexto) <= 1:
        return list(contexto)

    sistema = contexto[0]
    cola = contexto[1:][-max_msgs:]
    while cola and cola[0].get("role") == "tool":
        cola = cola[1:]

    return [sistema] + cola
