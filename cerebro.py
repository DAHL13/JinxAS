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
            "description": "Intenta leer la temperatura de los sensores del sistema o informa el uso de CPU.",
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
            "description": "Busca coincidencias de una palabra clave en las notas de la bóveda.",
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
]

historial_mensajes = []

def limpiar_historial() -> str:
    historial_mensajes.clear()
    return "Memoria de conversación borrada."

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

def procesar_estado_sistema(datos_sistema: str, pregunta_usuario: str = "", modelo: str = MODELO_LLM) -> str:
    """
    Envía los datos de telemetría del sistema a Qwen para que redacte una respuesta corta,
    hablada (1 o 2 oraciones) y con el estilo característico de Jinx.
    """
    prompt = (
        f"El usuario preguntó: '{pregunta_usuario}'. "
        f"Los datos reales del sistema son:\n{datos_sistema}\n"
        "Redacta una respuesta muy breve (máximo 2 oraciones), conversacional, hablada y con tu estilo ingenioso y fresco (ej. 'Tienes la RAM al 45% y el procesador fresco al 12%')."
    )
    try:
        response = ollama.chat(
            model=modelo,
            messages=[
                {"role": "system", "content": "Eres Jinx, un asistente de voz genial, directo, brillante y astuto. Responde en español de forma hablada y concisa."},
                {"role": "user", "content": prompt}
            ]
        )
        return response["message"]["content"]
    except Exception as e:
        error_msg = f"[X] Error al comunicarse con Ollama: {e}"
        logging.error(error_msg)
        return error_msg

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
