import logging
import sys
import ollama
import config
from config import MODELO_LLM, SYSTEM_PROMPT
from herramientas import MAPA_APLICACIONES

ESQUEMAS_HERRAMIENTAS = [
    {
        "type": "function",
        "function": {
            "name": "obtener_estado_sistema",
            "description": "Obtiene un resumen del estado actual del sistema: CPU, RAM y disco.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_temperatura",
            "description": "Obtiene la temperatura de los sensores de la CPU y sistema.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_aplicacion",
            "description": f"Abre una aplicación. Aplicaciones permitidas: {', '.join(MAPA_APLICACIONES.keys())}",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_app": {
                        "type": "string",
                        "description": "Nombre de la aplicación a abrir, en minúsculas si es posible.",
                    }
                },
                "required": ["nombre_app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_nota",
            "description": "Guarda o actualiza una nota Markdown en la bóveda de Obsidian.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {
                        "type": "string",
                        "description": "Título de la nota.",
                    },
                    "contenido": {
                        "type": "string",
                        "description": "Texto a guardar en la nota.",
                    },
                },
                "required": ["titulo", "contenido"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_nota",
            "description": "Búsqueda literal por palabra clave en títulos y contenido de las notas. Para preguntas conceptuales usa consultar_boveda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "palabra_clave": {
                        "type": "string",
                        "description": "Palabra o tema a buscar en títulos y contenidos.",
                    }
                },
                "required": ["palabra_clave"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_clima",
            "description": f"Consulta estrictamente el clima exterior y la temperatura ambiente en {config.CIUDAD_POR_DEFECTO}.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_boveda",
            "description": "Búsqueda semántica (RAG) en los apuntes del usuario en Obsidian. Úsala SIEMPRE que el usuario haga preguntas abiertas sobre sus conocimientos, proyectos, clases o conceptos documentados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Término, pregunta o concepto a buscar en la bóveda.",
                    }
                },
                "required": ["consulta"],
            },
        },
    },
]

def _mensaje_a_dict(mensaje) -> dict:
    if isinstance(mensaje, dict):
        return mensaje
    if hasattr(mensaje, "model_dump"):
        return mensaje.model_dump()
    resultado = {
        "role": getattr(mensaje, "role", "assistant"),
        "content": getattr(mensaje, "content", "") or "",
    }
    tool_calls = getattr(mensaje, "tool_calls", None)
    if tool_calls:
        resultado["tool_calls"] = tool_calls
    return resultado

class ErrorLLM(Exception):
    pass


def procesar_pensamiento(mensajes: list, modelo: str = MODELO_LLM, usar_tools: bool = True, **kwargs) -> dict:
    """
    Envía una lista de mensajes a Ollama con tool calling nativo
    y retorna el objeto completo del mensaje de respuesta.
    Si usar_tools es False, no se envían herramientas para forzar respuesta de texto.
    """
    if "permitir_herramientas" in kwargs:
        usar_tools = kwargs["permitir_herramientas"]
    try:
        response = ollama.chat(
            model=modelo,
            messages=mensajes,
            tools=ESQUEMAS_HERRAMIENTAS if usar_tools else None,
            options=config.LLM_OPCIONES,
            keep_alive=config.LLM_KEEP_ALIVE,
        )
        eval_count = response.get("eval_count", 0)
        eval_duration = response.get("eval_duration", 1) or 1
        tps = eval_count / (eval_duration / 1e9)
        logging.info(f"Ollama TPS: {tps:.2f} | Contexto usado: {response.get('prompt_eval_count', 0)} tokens")
        return _mensaje_a_dict(response["message"])
    except Exception as e:
        logging.error("Ollama fall\u00f3: %s", e)
        return {
            "role": "assistant",
            "_error": True,
            "content": "No pude pensar eso ahora. Revisa que Ollama est\u00e9 corriendo.",
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    mensaje_prueba = "¿Cómo está el estado de la computadora?"
    logging.info("Módulo de razonamiento - cerebro con Ollama")
    logging.info("Enviando consulta a Ollama (modelo: '%s'): \"%s\"", MODELO_LLM, mensaje_prueba)

    resultado = procesar_pensamiento([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": mensaje_prueba},
    ])

    logging.info("Respuesta de Ollama: %s", resultado)
