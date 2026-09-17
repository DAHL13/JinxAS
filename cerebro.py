import logging
import sys
import ollama
from config import MODELO_LLM, SYSTEM_PROMPT

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

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
            "description": "Lee estrictamente la temperatura del hardware del PC (CPU/GPU). NO usar para el clima exterior.",
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
            "description": "Abre una aplicación permitida en Windows (por ejemplo calculadora, notepad, vscode, chrome).",
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
            "description": "Busca una coincidencia exacta de una palabra clave en los títulos de las notas. NO usar para preguntas semánticas o conceptuales.",
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
            "description": "Consulta estrictamente el clima exterior y la temperatura ambiente en Tehuacán.",
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

def procesar_pensamiento(mensajes: list, modelo: str = MODELO_LLM) -> dict:
    """
    Envía una lista de mensajes a Ollama con tool calling nativo
    y retorna el objeto completo del mensaje de respuesta.
    """
    try:
        response = ollama.chat(
            model=modelo,
            messages=mensajes,
            tools=ESQUEMAS_HERRAMIENTAS,
        )
        return _mensaje_a_dict(response["message"])
    except Exception as e:
        error_msg = f"[X] Error al comunicarse con Ollama: {e}"
        logging.error(error_msg)
        return {"role": "assistant", "content": error_msg}

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
