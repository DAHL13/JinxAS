import os

def test_panel_html_in_package():
    """H-001: Verificar que panel.html existe relativo al paquete jinxas."""
    import jinxas
    base_dir = os.path.dirname(jinxas.__file__)
    panel_path = os.path.join(base_dir, "ui", "panel.html")
    assert os.path.isfile(panel_path), "panel.html no se encuentra en jinxas/ui/"
