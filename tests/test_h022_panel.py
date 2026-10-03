"""
tests/test_h022_panel.py
=========================
Pruebas para H-022: Seguridad en el panel UI.
Verifica que addLog en panel.html utilice textContent y el DOM para renderizar
mensajes de log, previniendo inyección HTML (XSS).
"""
from pathlib import Path


def test_addlog_no_usa_innerhtml_con_content():
    """Verifica que addLog en panel.html no use innerHTML con interpolación de content."""
    ruta_panel = Path(__file__).parent.parent / "jinxas" / "ui" / "panel.html"
    assert ruta_panel.exists(), f"No se encontró el archivo {ruta_panel}"

    contenido = ruta_panel.read_text(encoding="utf-8")

    # Extraer la función addLog
    assert "addLog:" in contenido
    inicio_addlog = contenido.find("addLog:")
    fin_addlog = contenido.find("};", inicio_addlog)
    codigo_addlog = contenido[inicio_addlog:fin_addlog]

    # No debe usar innerHTML con interpolación de contenido
    assert "linea.innerHTML" not in codigo_addlog
    assert "${content}" not in codigo_addlog

    # Debe usar textContent y nodos DOM
    assert "spanTexto.textContent = content" in codigo_addlog
    assert "linea.append" in codigo_addlog
