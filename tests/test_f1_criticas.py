import json
from unittest.mock import MagicMock, patch
import pytest
import config
from config import configurar_utf8
import memoria_rag
from interfaz import ControladorPanel
import cerebro
from main import ejecutar_turno
from percepcion import filtrar_transcripcion


def test_f1_06_asegurar_indice_inicializa_cuando_es_none():
    """F1-06: _asegurar_indice crea un IndexFlatL2 si _indice es None."""
    memoria_rag._indice = None
    with patch("memoria_rag._obtener_modelo") as mock_modelo, \
         patch("faiss.IndexFlatL2") as mock_faiss_l2:
        mock_modelo.return_value.get_sentence_embedding_dimension.return_value = 384
        memoria_rag._asegurar_indice()
        mock_faiss_l2.assert_called_once_with(384)
        assert memoria_rag._indice is not None


def test_f1_06_agregar_nota_llama_asegurar_indice():
    """F1-06: agregar_nota_al_indice invoca _asegurar_indice antes de reindexar."""
    with patch("memoria_rag._asegurar_indice") as mock_asegurar, \
         patch("memoria_rag.construir_indice") as mock_construir:
        memoria_rag.agregar_nota_al_indice("nota.md", "contenido")
        mock_asegurar.assert_called_once()
        mock_construir.assert_called_once()


def test_f1_07_actualizar_respuesta_escapa_json():
    """F1-07: actualizar_respuesta usa json.dumps e int(latencia)."""
    panel = ControladorPanel()
    mock_ventana = MagicMock()
    panel.ventana = mock_ventana

    texto_complejo = 'Respuesta con "comillas", saltos\nde línea y comillas simples \'test\''
    latencia = 345.89

    panel.actualizar_respuesta(texto_complejo, latencia)

    mock_ventana.evaluate_js.assert_called_once()
    llamada_js = mock_ventana.evaluate_js.call_args[0][0]
    # Comprobar que contiene json.dumps y el entero de latencia
    assert json.dumps(texto_complejo) in llamada_js
    assert "345" in llamada_js
    assert "window.jinxUI.setRespuesta" in llamada_js


def test_actualizar_tiempos_escapa_json_y_llama_js():
    """Verifica que actualizar_tiempos formatea el dict a JSON y llama a window.jinxUI.setTiempos."""
    panel = ControladorPanel()
    mock_ventana = MagicMock()
    panel.ventana = mock_ventana

    tiempos = {"stt": 1250.4, "llm": 2340.1, "tts": 780.0}
    panel.actualizar_tiempos(tiempos)

    mock_ventana.evaluate_js.assert_called_once()
    llamada_js = mock_ventana.evaluate_js.call_args[0][0]
    assert "window.jinxUI.setTiempos" in llamada_js
    assert json.dumps(tiempos) in llamada_js


def test_actualizar_tiempos_sin_ventana_no_falla():
    """Verifica que actualizar_tiempos retorna sin error si no hay ventana activa."""
    panel = ControladorPanel()
    panel.ventana = None
    # No debe levantar ninguna excepción
    panel.actualizar_tiempos({"stt": 100, "llm": 200, "tts": 300})


def test_f1_09_cerebro_error_ollama_retorna_dict_error():
    """F1-09: procesar_pensamiento maneja silenciosamente fallos de Ollama retornando dict con _error."""
    with patch("cerebro.ollama.chat", side_effect=RuntimeError("Ollama daemon down")):
        res = cerebro.procesar_pensamiento([{"role": "user", "content": "hola"}])
        assert res.get("_error") is True
        assert res.get("role") == "assistant"
        assert "Ollama" in res.get("content", "")


def test_f1_09_ejecutar_turno_no_guarda_error_en_contexto():
    """F1-09: ejecutar_turno no contamina el historial cuando procesar_pensamiento retorna _error."""
    dict_error = {
        "role": "assistant",
        "_error": True,
        "content": "No pude pensar eso ahora. Revisa que Ollama esté corriendo.",
    }
    contexto_original = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "hola"},
    ]
    contexto = list(contexto_original)

    with patch("main.procesar_pensamiento", return_value=dict_error):
        texto_final = ejecutar_turno(contexto)
        assert texto_final == dict_error["content"]
        assert len(contexto) == 2
        assert contexto == contexto_original


def test_f1_14_configurar_utf8_ejecuta_sin_error():
    """F1-14: configurar_utf8 ejecuta sin lanzar excepciones."""
    configurar_utf8()
    assert hasattr(config, "configurar_utf8")
    assert hasattr(config, "configurar_consola")


def test_f1_08_f1_11_multiples_rondas_y_tool_name():
    """F1-08 y F1-11: Soporte de rondas múltiples de herramientas y clave tool_name."""
    from main import ejecutar_turno, ejecutar_herramienta

    # Simulamos 2 rondas de tool calls seguidas de respuesta final
    resp_ronda_1 = {
        "role": "assistant",
        "tool_calls": [
            {"function": {"name": "obtener_clima", "arguments": {}}}
        ],
    }
    resp_ronda_2 = {
        "role": "assistant",
        "tool_calls": [
            {"function": {"name": "obtener_estado_sistema", "arguments": {}}}
        ],
    }
    resp_final = {
        "role": "assistant",
        "content": "El clima está despejado y el sistema al 15% de CPU.",
    }

    contexto = [{"role": "user", "content": "¿Cómo está el clima y el sistema?"}]

    with patch("main.procesar_pensamiento", side_effect=[resp_ronda_1, resp_ronda_2, resp_final]), \
         patch("main.ejecutar_herramienta", side_effect=["Clima: 22C", "CPU: 15%"]):
        texto = ejecutar_turno(contexto)
        assert texto == resp_final["content"]

        # Verificar que se enviaron los mensajes de tool con tool_name
        tool_msgs = [m for m in contexto if m.get("role") == "tool"]
        assert len(tool_msgs) == 2
        assert tool_msgs[0]["tool_name"] == "obtener_clima"
        assert tool_msgs[0]["content"] == "Clima: 22C"
        assert tool_msgs[1]["tool_name"] == "obtener_estado_sistema"
        assert tool_msgs[1]["content"] == "CPU: 15%"


def test_ejecutar_herramienta_manejo_errores():
    """Verifica respuestas de error seguras en ejecutar_herramienta."""
    from main import ejecutar_herramienta, FUNCIONES_DISPONIBLES

    # Herramienta no permitida
    res = ejecutar_herramienta("herramienta_inexistente", {})
    assert "Herramienta no permitida" in res

    # TypeError por argumentos inválidos
    mock_fn_type_error = MagicMock(side_effect=TypeError("missing required argument 'x'"))
    with patch.dict(FUNCIONES_DISPONIBLES, {"tool_error_tipo": mock_fn_type_error}):
        res = ejecutar_herramienta("tool_error_tipo", {})
        assert "Argumentos inválidos para tool_error_tipo" in res

    # Excepción general
    mock_fn_error = MagicMock(side_effect=RuntimeError("hardware failure"))
    with patch.dict(FUNCIONES_DISPONIBLES, {"tool_error_gen": mock_fn_error}):
        res = ejecutar_herramienta("tool_error_gen", {})
        assert "Error al ejecutar tool_error_gen." in res


def test_f1_12_limpiar_para_tts():
    """F1-12: limpiar_para_tts elimina URLs, emojis y markdown."""
    from voz import limpiar_para_tts

    # Entrada con URLs, emojis y markdown variado
    entrada = (
        "Revisa https://github.com/proyecto/repo y https://jinx.ai 😊🚀! "
        "# Título Principal\n"
        "Este es un texto con **negrita**, *cursiva*, `código` y > cita."
    )
    salida = limpiar_para_tts(entrada)

    assert "https://" not in salida
    assert "😊" not in salida
    assert "🚀" not in salida
    assert "*" not in salida
    assert "#" not in salida
    assert "`" not in salida
    assert ">" not in salida
    assert "Título Principal" in salida
    assert "Este es un texto con negrita, cursiva, código y cita." in salida

    # Caso borde: texto vacío o solo espacios
    assert limpiar_para_tts("") == ""
    assert limpiar_para_tts("    ") == ""


def test_f1_13_reproducir_voz_resiliencia_sin_red():
    """F1-13: reproducir_voz no colapsa si edge_tts falla por desconexión."""
    from voz import reproducir_voz
    import voz

    with patch.object(voz, "_generar_audio_edge", side_effect=TimeoutError("No internet")), \
         patch("voz.pygame.mixer.music.unload") as mock_unload:
        # No debe lanzar excepción
        reproducir_voz("Prueba de audio sin red")
        # El bloque finally debe descargar mixer para liberar archivos
        mock_unload.assert_called()


def _resultado_whisper(texto: str) -> dict:
    return {
        "text": texto,
        "segments": [{"no_speech_prob": 0.1, "avg_logprob": -0.5}],
    }


def test_filtrar_transcripcion():
    """F1-10: descarta transcripciones cortas o alucinadas y deja pasar texto válido."""
    assert filtrar_transcripcion(_resultado_whisper("enciende la luz")) == "enciende la luz"
    assert filtrar_transcripcion(_resultado_whisper("a")) is None
    assert filtrar_transcripcion(_resultado_whisper("gracias por ver el video")) is None

