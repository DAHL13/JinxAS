"""
tests/test_h031_limite_rondas.py
================================
Pruebas para H-031: Mensaje coherente al agotar rondas de herramientas.
Verifica que cuando un modelo agota MAX_RONDAS_TOOLS devolviendo tool_calls continuamente,
tanto en streaming como en no-streaming:
1. El texto final retornado sea config.MSG_LIMITE_RONDAS ("No pude completar la acción: se alcanzó el límite de pasos.").
2. El historial de contexto no deje tool_calls sin su correspondiente mensaje de tipo tool.
"""
from jinxas import __main__ as main_module
from jinxas import config


def test_no_streaming_agota_rondas_retorna_msg_limite_y_cierra_tools(monkeypatch):
    """En ruta no-streaming (ejecutar_turno), agotar rondas devuelve MSG_LIMITE_RONDAS y cierra tool_calls."""
    def fake_procesar_pensamiento(ctx):
        # Siempre devuelve un tool_call sin contenido final
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "obtener_hora", "arguments": {}}}],
        }

    monkeypatch.setattr(main_module, "procesar_pensamiento", fake_procesar_pensamiento)
    monkeypatch.setattr(main_module, "ejecutar_herramienta", lambda name, args: "12:00")

    contexto = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "ejecuta la hora"},
    ]

    texto_final = main_module.ejecutar_turno(contexto)

    # 1. El texto final no debe ser "Listo." sino el mensaje honesto de límite
    assert texto_final == config.MSG_LIMITE_RONDAS

    # 2. Verificar coherencia del historial: todo tool_call tiene mensaje tool
    mensajes_asistente_con_tools = [
        msg for msg in contexto if msg.get("role") == "assistant" and msg.get("tool_calls")
    ]
    mensajes_tool = [msg for msg in contexto if msg.get("role") == "tool"]

    total_tool_calls = sum(len(m.get("tool_calls", [])) for m in mensajes_asistente_con_tools)
    assert total_tool_calls == len(mensajes_tool)

    # El último mensaje de tool debe ser el de corte por límite
    ultimo_tool = mensajes_tool[-1]
    assert "[Límite de rondas de herramientas alcanzado; acción no ejecutada]" in ultimo_tool.get("content", "")


def test_streaming_agota_rondas_retorna_msg_limite_y_cierra_tools(monkeypatch):
    """En ruta streaming (ejecutar_turno_streaming), agotar rondas devuelve MSG_LIMITE_RONDAS y cierra tool_calls."""
    def fake_procesar_pensamiento_stream(ctx):
        # Generador de chunks simulando stream que siempre emite tool_calls
        yield {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "obtener_hora", "arguments": {}}}],
            }
        }

    monkeypatch.setattr(main_module, "procesar_pensamiento_stream", fake_procesar_pensamiento_stream)
    monkeypatch.setattr(main_module, "ejecutar_herramienta", lambda name, args: "12:00")

    contexto = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "ejecuta la hora en streaming"},
    ]

    tiempos = {}
    crono = main_module.CronometroTurno()
    texto_final = main_module.ejecutar_turno_streaming(
        "ejecuta la hora en streaming",
        contexto,
        tiempos,
        crono,
    )

    # 1. El texto final debe ser config.MSG_LIMITE_RONDAS
    assert texto_final == config.MSG_LIMITE_RONDAS

    # 2. Verificar coherencia del historial: ningún tool_call sin respuesta tool
    mensajes_asistente_con_tools = [
        msg for msg in contexto if msg.get("role") == "assistant" and msg.get("tool_calls")
    ]
    mensajes_tool = [msg for msg in contexto if msg.get("role") == "tool"]

    total_tool_calls = sum(len(m.get("tool_calls", [])) for m in mensajes_asistente_con_tools)
    assert total_tool_calls == len(mensajes_tool)

    # El último mensaje de tool debe ser el de límite alcanzado
    ultimo_tool = mensajes_tool[-1]
    assert "[Límite de rondas de herramientas alcanzado; acción no ejecutada]" in ultimo_tool.get("content", "")
