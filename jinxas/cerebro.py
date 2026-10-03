import logging
import ollama
from jinxas import config
from jinxas.config import MODELO_LLM, SYSTEM_PROMPT
from jinxas import herramientas  # noqa: F401 – registra herramientas en REGISTRO al importar
from jinxas import memoria       # noqa: F401 – registra guardar_nota y buscar_nota en REGISTRO al importar
from jinxas.registro import REGISTRO

# ESQUEMAS_HERRAMIENTAS se construye desde REGISTRO para mantener
# herramientas.py y memoria.py como única fuente de verdad (F4-06).
ESQUEMAS_HERRAMIENTAS = [entrada["schema"] for entrada in REGISTRO.values()]

# Alias para que cerebro.py pueda seguir importando MAPA_APLICACIONES
MAPA_APLICACIONES = herramientas.MAPA_APLICACIONES

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
        if isinstance(response, dict):
            eval_count = response.get("eval_count", 0)
            eval_duration = response.get("eval_duration", 0)
            prompt_eval = response.get("prompt_eval_count", 0)
            msg = response.get("message", {})
        else:
            eval_count = getattr(response, "eval_count", 0) or 0
            eval_duration = getattr(response, "eval_duration", 0) or 0
            prompt_eval = getattr(response, "prompt_eval_count", 0) or 0
            msg = getattr(response, "message", {})

        tok_sec = round(eval_count / (eval_duration / 1e9), 1) if eval_duration > 0 else 0.0
        logging.info("Ollama TPS: %.2f | Contexto usado: %s tokens", tok_sec, prompt_eval)
        num_ctx = config.LLM_OPCIONES.get("num_ctx", 4096)
        if prompt_eval >= 0.9 * num_ctx:
            logging.warning(
                "Contexto de LLM al límite: prompt_eval_count=%s tokens (>= 90%% de num_ctx=%s)",
                prompt_eval,
                num_ctx,
            )
        resultado = _mensaje_a_dict(msg)
        resultado["tok_sec"] = tok_sec
        return resultado
    except Exception as e:
        logging.error("Ollama fall\u00f3: %s", e)
        return {
            "role": "assistant",
            "_error": True,
            "content": "No pude pensar eso ahora. Revisa que Ollama est\u00e9 corriendo.",
        }


def procesar_pensamiento_stream(mensajes: list, modelo: str = MODELO_LLM, usar_tools: bool = True, **kwargs):
    """
    Versión streaming de procesar_pensamiento (F2-02).
    Llama a ollama.chat con stream=True y emite los chunks del generador
    tal como los devuelve la API, permitiendo TTS por frases en paralelo.
    Si usar_tools es False, no se envían herramientas para forzar respuesta de texto.

    Cada chunk tiene la estructura:
        {"message": {"role": "assistant", "content": "...", "tool_calls": [...]}}

    En caso de error, emite un único chunk con _error=True para que el
    consumidor pueda detectarlo sin colapsar el hilo de voz.

    Yields
    ------
    dict
        Chunk de Ollama o dict de error con clave "_error".
    """
    if "permitir_herramientas" in kwargs:
        usar_tools = kwargs["permitir_herramientas"]
    try:
        for chunk in ollama.chat(
            model=modelo,
            messages=mensajes,
            tools=ESQUEMAS_HERRAMIENTAS if usar_tools else None,
            options=config.LLM_OPCIONES,
            keep_alive=config.LLM_KEEP_ALIVE,
            stream=True,
        ):
            if isinstance(chunk, dict):
                ec = chunk.get("eval_count", 0)
                ed = chunk.get("eval_duration", 0)
                pec = chunk.get("prompt_eval_count", 0)
            else:
                ec = getattr(chunk, "eval_count", 0) or 0
                ed = getattr(chunk, "eval_duration", 0) or 0
                pec = getattr(chunk, "prompt_eval_count", 0) or 0
            if pec:
                num_ctx = config.LLM_OPCIONES.get("num_ctx", 4096)
                if pec >= 0.9 * num_ctx:
                    logging.warning(
                        "Contexto de LLM al límite: prompt_eval_count=%s tokens (>= 90%% de num_ctx=%s)",
                        pec,
                        num_ctx,
                    )
            if ed and ed > 0:
                tps = round(ec / (ed / 1e9), 1)
                if isinstance(chunk, dict):
                    chunk["tok_sec"] = tps
                else:
                    try:
                        setattr(chunk, "tok_sec", tps)
                    except Exception:
                        pass
            yield chunk
    except Exception as e:
        logging.error("Ollama falló en stream: %s", e)
        yield {
            "message": {
                "role": "assistant",
                "content": "No pude pensar eso ahora. Revisa que Ollama esté corriendo.",
            },
            "_error": True,
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
