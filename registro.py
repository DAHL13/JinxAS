"""
registro.py – F4-06: Registro único de herramientas (single source of truth).

Sin dependencias pesadas. Define REGISTRO y el decorador @herramienta que
cada módulo usa para registrar sus funciones públicas.

Formato de cada entrada en REGISTRO:
    REGISTRO[nombre_función] = {
        "fn":     <callable>,
        "schema": {schema OpenAI/Ollama listo para usar},
    }
"""

from __future__ import annotations

from typing import Callable

REGISTRO: dict[str, dict] = {}


def herramienta(descripcion: str, parametros: dict | None = None) -> Callable:
    """
    Decorador que registra una función en REGISTRO.

    Args:
        descripcion: Texto que el LLM verá como descripción de la herramienta.
        parametros:  Dict en formato JSON-Schema "properties" con los parámetros
                     aceptados. Si es None, la función no acepta parámetros.

    La clave "required" se genera automáticamente listando todas las propiedades
    definidas en `parametros`.
    """
    def deco(fn: Callable) -> Callable:
        props = parametros or {}
        REGISTRO[fn.__name__] = {
            "fn": fn,
            "schema": {
                "type": "function",
                "function": {
                    "name": fn.__name__,
                    "description": descripcion,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": list(props),
                    },
                },
            },
        }
        return fn
    return deco
