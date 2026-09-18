"""
interfaz.py — Puente Python → Frontend (pywebview)
Fase 5 · JinxAS

Expone ControladorPanel, que traduce llamadas Python a JavaScript
usando ventana.evaluate_js(). Los métodos son seguros para ser llamados
desde el hilo de voz secundario sin bloquear ni lanzar excepciones.
"""
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
        self._eval(f"window.jinxUI.setEstado({paso})")

    def actualizar_respuesta(self, texto: str, latencia: int) -> None:
        """Actualiza el texto de la última respuesta y la latencia en ms."""
        # Escapar comillas simples para no romper el JS inline
        texto_escapado = texto.replace("\\", "\\\\").replace("'", "\\'")
        self._eval(f"window.jinxUI.setRespuesta('{texto_escapado}', {latencia})")

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
