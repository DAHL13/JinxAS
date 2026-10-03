"""
tests/test_h019_truncados.py
============================
Pruebas para H-019: Truncados silenciosos.
- envolver_resultado_tool usa MAX_CHARS_RESULTADO_TOOL (3200) y marca recorte.
- buscar_semantica acumula resultados completos bajo presupuesto (3000 chars) y nunca corta a la mitad.
- cerebro emite logging.warning si prompt_eval_count >= 90% de num_ctx.
"""
import logging
from unittest.mock import MagicMock, patch

import numpy as np

from jinxas import config
from jinxas.__main__ import envolver_resultado_tool
from jinxas.cerebro import procesar_pensamiento, procesar_pensamiento_stream
from jinxas import memoria_rag


def test_envolver_resultado_tool_conserva_tres_resultados_rag():
    """Conserva 3 resultados RAG de ~860 caracteres (total ~2580 < 3200) sin recortar."""
    r1 = "A" * 860
    r2 = "B" * 860
    r3 = "C" * 860
    texto_rag = f"[Resultado 1]\n{r1}\n\n---\n\n[Resultado 2]\n{r2}\n\n---\n\n[Resultado 3]\n{r3}"
    assert len(texto_rag) < config.MAX_CHARS_RESULTADO_TOOL

    env = envolver_resultado_tool("buscar_en_notas", texto_rag)
    assert "[…resultado recortado]" not in env
    assert r1 in env
    assert r2 in env
    assert r3 in env


def test_envolver_resultado_tool_marca_recorte_si_excede():
    """Añade sufijo […resultado recortado] cuando el contenido excede MAX_CHARS_RESULTADO_TOOL."""
    texto_largo = "X" * (config.MAX_CHARS_RESULTADO_TOOL + 100)
    env = envolver_resultado_tool("herramienta", texto_largo)
    assert env.endswith("[…resultado recortado]")
    assert len(env) < len(texto_largo) + 100


def test_buscar_semantica_no_parte_resultados_y_respeta_presupuesto(monkeypatch):
    """buscar_semantica descarta fragmentos que no caben completos en vez de partirlos a la mitad."""
    presupuesto = config.MAX_CHARS_RESULTADO_TOOL - 200

    # Simular fragmentos: frag1 (2000 chars), frag2 (1500 chars).
    # Juntos con separador superarían el presupuesto (3500 > 3000).
    # Por tanto, frag2 debe descartarse completo, no cortarse a la mitad.
    f1 = {"_id": 0, "archivo": "nota1.md", "texto": "A" * 1900}
    f2 = {"_id": 1, "archivo": "nota2.md", "texto": "B" * 1500}

    mock_indice = MagicMock()
    mock_indice.search.return_value = (np.array([[0.9, 0.85]], dtype=np.float32), np.array([[0, 1]], dtype=np.int64))

    mock_modelo = MagicMock()
    mock_modelo.encode.return_value = np.ones((1, 8), dtype=np.float32)

    monkeypatch.setattr(memoria_rag, "_indice", mock_indice)
    monkeypatch.setattr(memoria_rag, "_fragmentos", [f1, f2])
    monkeypatch.setattr(memoria_rag, "_obtener_modelo", lambda: mock_modelo)

    resultado = memoria_rag.buscar_semantica("consulta de prueba", top_k=2)

    assert "nota1.md" in resultado
    # frag2 no cupo completo en el presupuesto restante, debe descartarse
    assert "nota2.md" not in resultado
    assert "B" * 1500 not in resultado
    assert len(resultado) <= presupuesto


def test_cerebro_warning_contexto_al_limite(caplog):
    """Emite logging.warning cuando prompt_eval_count >= 0.9 * num_ctx."""
    num_ctx = config.LLM_OPCIONES["num_ctx"]
    tokens_al_limite = int(num_ctx * 0.92)

    fake_response = {
        "message": {"role": "assistant", "content": "Respuesta"},
        "eval_count": 20,
        "eval_duration": 1000000000,
        "prompt_eval_count": tokens_al_limite,
    }

    with caplog.at_level(logging.WARNING), patch("ollama.chat", return_value=fake_response):
        res = procesar_pensamiento([{"role": "user", "content": "hola"}])
        assert res["content"] == "Respuesta"
        assert any("Contexto de LLM al límite" in r.message for r in caplog.records)


def test_cerebro_warning_contexto_stream(caplog):
    """Emite logging.warning en procesar_pensamiento_stream cuando prompt_eval_count >= 0.9 * num_ctx."""
    num_ctx = config.LLM_OPCIONES["num_ctx"]
    tokens_al_limite = int(num_ctx * 0.95)

    chunks = [
        {"message": {"role": "assistant", "content": "Hola "}},
        {
            "message": {"role": "assistant", "content": "mundo"},
            "eval_count": 10,
            "eval_duration": 500000000,
            "prompt_eval_count": tokens_al_limite,
        },
    ]

    with caplog.at_level(logging.WARNING), patch("ollama.chat", return_value=iter(chunks)):
        list(procesar_pensamiento_stream([{"role": "user", "content": "hola"}]))
        assert any("Contexto de LLM al límite" in r.message for r in caplog.records)
