"""
test_f7_conversacion.py — Pruebas unitarias para conversacion.py (F7-01).

Valida el recorte determinista de contexto conversacional y la purga
de llamadas a herramientas huérfanas tras el system prompt.
"""
from conversacion import recortar


def test_recortar_contexto_vacio():
    """Contexto vacío debe retornar lista vacía."""
    assert recortar([]) == []


def test_recortar_solo_system_prompt():
    """Contexto con un único mensaje (system prompt) se retorna sin alteración."""
    ctx = [{"role": "system", "content": "Eres Jinx"}]
    resultado = recortar(ctx, max_msgs=16)
    assert resultado == ctx
    # Verifica que no muta ni devuelve la misma referencia si se modifica
    assert resultado is not ctx or len(resultado) == 1


def test_recortar_contexto_menor_a_max_msgs():
    """Si el contexto tiene menos mensajes que max_msgs, se conserva íntegro."""
    ctx = [
        {"role": "system", "content": "Eres Jinx"},
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¡Qué onda!"},
        {"role": "user", "content": "Cómo estás"},
    ]
    resultado = recortar(ctx, max_msgs=16)
    assert resultado == ctx
    assert len(resultado) == 4


def test_recortar_contexto_igual_a_max_msgs():
    """Si la cola tiene exactamente max_msgs, se conserva completa junto al system prompt."""
    sistema = {"role": "system", "content": "Eres Jinx"}
    cola = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(16)]
    ctx = [sistema] + cola

    resultado = recortar(ctx, max_msgs=16)
    assert len(resultado) == 17
    assert resultado[0] == sistema
    assert resultado[1:] == cola


def test_recortar_supera_max_msgs_conserva_system_y_ultimos_n():
    """Cuando supera max_msgs, conserva el system prompt y los últimos max_msgs mensajes."""
    sistema = {"role": "system", "content": "Eres Jinx"}
    cola = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(30)]
    ctx = [sistema] + cola

    resultado = recortar(ctx, max_msgs=16)
    assert len(resultado) == 17
    assert resultado[0] == sistema
    # Los últimos 16 elementos de la cola original
    assert resultado[1:] == cola[-16:]


def test_recortar_purga_mensajes_tool_huerfanos_al_inicio_de_cola():
    """
    Si tras recortar el primer mensaje resultante de la cola es de rol 'tool',
    debe descartarlo en bucle hasta encontrar 'user' o 'assistant'.
    """
    sistema = {"role": "system", "content": "Eres Jinx"}
    ctx = [
        sistema,
        {"role": "user", "content": "qué hora es"},
        {"role": "assistant", "content": None, "tool_calls": [{"function": {"name": "obtener_fecha_hora"}}]},
        {"role": "tool", "content": "10:00"},
        {"role": "tool", "content": "datos extras"},
        {"role": "assistant", "content": "Son las 10:00."},
        {"role": "user", "content": "¿y el clima?"},
        {"role": "assistant", "content": "Soleado."},
    ]

    # Si recortamos con max_msgs=5:
    # cola[-5:] sería: [tool ("10:00"), tool ("datos extras"), assistant ("Son las 10:00"), user, assistant]
    # Al iniciar con 2 'tool', deben purgarse, quedando solo 3 mensajes en cola.
    resultado = recortar(ctx, max_msgs=5)
    assert resultado[0] == sistema
    assert resultado[1]["role"] == "assistant"
    assert resultado[1]["content"] == "Son las 10:00."
    assert len(resultado) == 4
    # Ningún mensaje inmediatamente posterior al system prompt es 'tool'
    assert resultado[1]["role"] != "tool"


def test_recortar_purga_todos_si_cola_solo_tiene_tools():
    """Si toda la cola recortada está compuesta por mensajes de rol 'tool', queda solo el sistema."""
    sistema = {"role": "system", "content": "Eres Jinx"}
    ctx = [
        sistema,
        {"role": "tool", "content": "dato 1"},
        {"role": "tool", "content": "dato 2"},
    ]
    resultado = recortar(ctx, max_msgs=2)
    assert resultado == [sistema]


def test_recortar_no_muta_contexto_original():
    """Garantiza que la lista original no es modificada por efectos secundarios."""
    ctx_original = [
        {"role": "system", "content": "Eres Jinx"},
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "tool", "content": "3"},
        {"role": "assistant", "content": "4"},
    ]
    copia = list(ctx_original)
    _ = recortar(ctx_original, max_msgs=2)
    assert ctx_original == copia
