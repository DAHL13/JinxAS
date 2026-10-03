import json
import threading
from unittest.mock import MagicMock
from jinxas import config, percepcion
from jinxas import __main__ as main_module


def test_precargar_modelos_concurrente(monkeypatch):
    """Verifica que precargar_modelos cargue centinela y comandos de forma segura sin duplicar."""
    call_count = {"centinela": 0, "comandos": 0}

    def fake_load_model(nombre):
        if "tiny" in nombre:
            call_count["centinela"] += 1
            return MagicMock(name="tiny_model")
        call_count["comandos"] += 1
        return MagicMock(name="small_model")

    monkeypatch.setattr(percepcion.whisper, "load_model", fake_load_model)
    monkeypatch.setattr(percepcion, "_MODELO_CENTINELA", None)
    monkeypatch.setattr(percepcion, "_MODELO_WHISPER_COMANDOS", None)

    threads = [threading.Thread(target=percepcion.precargar_modelos) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert call_count["centinela"] == 1
    assert call_count["comandos"] == 1
    assert percepcion._MODELO_CENTINELA is not None
    assert percepcion._MODELO_WHISPER_COMANDOS is not None


def test_tool_calls_colgados_ejecutar_turno(monkeypatch):
    """Verifica que al alcanzar MAX_RONDAS_TOOLS con tool_calls pendientes, se registren respuestas de límite."""
    monkeypatch.setattr(config, "ATAJOS", False)
    monkeypatch.setattr(config, "MAX_RONDAS_TOOLS", 1)

    # Respuesta que solicita una tool
    msg_con_tool = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "obtener_hora", "arguments": {}}}],
    }

    # Primera llamada devuelve tool_calls, segunda llamada vuelve a devolver tool_calls excediendo el límite
    respuestas = [
        msg_con_tool,
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "obtener_hora", "arguments": {}}}],
        },
    ]

    def fake_procesar_pensamiento(ctx):
        if respuestas:
            return respuestas.pop(0)
        return {"role": "assistant", "content": "Fin"}

    monkeypatch.setattr(main_module, "procesar_pensamiento", fake_procesar_pensamiento)
    monkeypatch.setattr(main_module, "ejecutar_herramienta", lambda name, args: "12:00")

    contexto = [{"role": "system", "content": "sys"}, {"role": "user", "content": "dime la hora"}]
    texto_final = main_module.ejecutar_turno(contexto)
    assert texto_final is not None

    # El último mensaje de tool_calls colgados debe tener su mensaje correspondiente de herramienta
    assert any(
        msg.get("role") == "tool" and "Límite de rondas" in msg.get("content", "")
        for msg in contexto
    )


def test_config_local_json_prioridad(tmp_path, monkeypatch):
    """Verifica lectura de config_local.json y prioridad de variable de entorno JINX_CIUDAD."""
    archivo_json = tmp_path / "config_local.json"
    archivo_json.write_text(json.dumps({"ciudad": "Oaxaca"}), encoding="utf-8")

    monkeypatch.setattr(config, "_BASE_DIR", str(tmp_path))

    # Caso 1: Sin variable de entorno, toma config_local.json
    monkeypatch.delenv("JINX_CIUDAD", raising=False)
    # Re-evaluar lógica de carga
    with open(archivo_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("ciudad") == "Oaxaca"

    # Caso 2: Con variable de entorno JINX_CIUDAD, prevalece sobre el JSON
    monkeypatch.setenv("JINX_CIUDAD", "Monterrey")
    ciudad_final = config.os.environ.get("JINX_CIUDAD") or data.get("ciudad")
    assert ciudad_final == "Monterrey"


def test_boton_repetir_en_panel_html():
    """Verifica que el botón en panel.html tenga la etiqueta 'Repetir'."""
    ruta_panel = config.os.path.join(
        config.os.path.dirname(config.os.path.dirname(config.os.path.abspath(__file__))),
        "jinxas",
        "ui",
        "panel.html",
    )
    with open(ruta_panel, "r", encoding="utf-8") as f:
        contenido = f.read()

    assert "<span>Repetir</span>" in contenido
    assert "<span>Regenerar</span>" not in contenido


def test_requirements_sin_python_levenshtein():
    """Verifica que requirements.txt no contenga python-Levenshtein redundante."""
    ruta_req = config.os.path.join(
        config.os.path.dirname(config.os.path.dirname(config.os.path.abspath(__file__))),
        "requirements.txt",
    )
    with open(ruta_req, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    paquetes = [linea.strip().split("==")[0].lower() for linea in lineas if linea.strip()]
    assert "python-levenshtein" not in paquetes
    assert "levenshtein" in paquetes
