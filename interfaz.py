"""
interfaz.py — Puente Python → Frontend (pywebview)
Fase 5 · JinxAS

Expone ControladorPanel, que traduce llamadas Python a JavaScript
usando ventana.evaluate_js(). Los métodos son seguros para ser llamados
desde el hilo de voz secundario sin bloquear ni lanzar excepciones.
"""
import json
import logging


class ControladorPanel:
    """Controlador del panel SENTINEL.

    Uso:
        panel = ControladorPanel()
        panel.ventana = webview.create_window(...)
        panel.actualizar_estado(1)
        panel.actualizar_respuesta("Hola mundo", 843)
    """

    def __init__(self) -> None:
        # Se asigna desde main.py después de create_window()
        self.ventana = None

    # ──────────────────────────────────────────
    # Métodos públicos (seguros para hilos)
    # ──────────────────────────────────────────

    def actualizar_estado(self, paso: int) -> None:
        """Resalta el hub activo en el pipeline (pasos 1-5).

        Paso 1 → Centinela  (hub-1)
        Paso 2 → Transcripción (hub-2)
        Paso 3 → El Núcleo  (hub-3)
        Paso 4 → Síntesis   (hub-4)
        Paso 5 → Completado (terminalNode)
        """
        self._eval(f"if (window.jinxUI) {{ window.jinxUI.setEstado({paso}); }}")

    def actualizar_respuesta(self, texto: str, latencia: int) -> None:
        """Actualiza el texto de la última respuesta y la latencia en ms."""
        texto_seguro = json.dumps(texto)
        self._eval(f"if (window.jinxUI) {{ window.jinxUI.setRespuesta({texto_seguro}, {latencia}); }}")

    def actualizar_satelite(self, hub: int, sat: int, titulo: str = None, desc: str = None) -> None:
        """Actualiza dinámicamente el título y descripción de cualquier satélite en el panel."""
        if not self.ventana:
            return
        t_seguro = json.dumps(titulo) if titulo else "null"
        d_seguro = json.dumps(desc) if desc else "null"
        try:
            self.ventana.evaluate_js(
                f"if(window.jinxUI) {{ window.jinxUI.actualizarSatelite({hub}, {sat}, {t_seguro}, {d_seguro}); }}"
            )
        except Exception as e:
            logging.error(f"Error UI: {e}")

    def actualizar_detalle(self, paso: int, titulo: str, desc: str) -> None:
        """Compatibilidad con satélite principal de cada etapa (satélite 1)."""
        self.actualizar_satelite(paso, 1, titulo, desc)

    # ──────────────────────────────────────────
    # Método interno
    # ──────────────────────────────────────────

    def _eval(self, js: str) -> None:
        """Ejecuta JS en la ventana pywebview de forma segura.

        Si la ventana no está lista o ya fue cerrada, captura la
        excepción y registra un warning en lugar de propagar el error.
        """
        if not self.ventana:
            return
        try:
            self.ventana.evaluate_js(js)
        except Exception as exc:
            logging.warning("[ControladorPanel] evaluate_js falló: %s", exc)
