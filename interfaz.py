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


class InterfazAPI:
    """API inversa expuesta a JavaScript a través de pywebview (JS → Python).

    pywebview inyecta esta clase en el contexto del navegador como
    ``window.pywebview.api``, permitiendo que el frontend llame métodos
    Python directamente desde el <script> del panel.

    Para conectar el historial de conversación, asigna la referencia
    antes de crear la ventana:
        api_js = InterfazAPI()
        api_js.contexto = contexto  # la lista mutable del bucle de voz
    """

    def __init__(self) -> None:
        # Se asigna desde main.py para apuntar al contexto activo del bucle
        self.contexto: list | None = None

    def limpiar_memoria_ui(self) -> None:
        """Borra el historial de conversación desde el botón 'Emergency Flush' del panel."""
        try:
            if self.contexto is not None and len(self.contexto) > 1:
                # Conserva sólo el mensaje de sistema (index 0)
                del self.contexto[1:]
                logging.info("[InterfazAPI] Historial borrado desde el panel UI (Emergency Flush).")
            else:
                logging.info("[InterfazAPI] Flush solicitado: historial ya estaba vacío.")
        except Exception as exc:
            logging.error("[InterfazAPI] Error al limpiar historial: %s", exc)

    def repetir_audio_ui(self) -> None:
        """Repite en voz alta el último mensaje del asistente desde el botón Play del panel."""
        import threading
        try:
            ultimo_texto = ""
            if self.contexto:
                # Buscar el último mensaje del asistente en el contexto
                for msg in reversed(self.contexto):
                    if msg.get("role") == "assistant":
                        ultimo_texto = (msg.get("content") or "").strip()
                        break
            if ultimo_texto:
                from voz import reproducir_voz
                logging.info("[InterfazAPI] Repitiendo último audio desde el panel UI.")
                threading.Thread(target=reproducir_voz, args=(ultimo_texto,), daemon=True).start()
            else:
                logging.info("[InterfazAPI] Repetir audio: no hay respuesta previa en el contexto.")
        except Exception as exc:
            logging.error("[InterfazAPI] Error al repetir audio: %s", exc)


class WebViewLogHandler(logging.Handler):
    def __init__(self, ventana):
        super().__init__()
        self.ventana = ventana
        self.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

    def emit(self, record):
        if not self.ventana:
            return
        msg = self.format(record)
        msg_seguro = json.dumps(msg)
        try:
            self.ventana.evaluate_js(f"if(window.jinxUI && window.jinxUI.addLog) {{ window.jinxUI.addLog({msg_seguro}); }}")
        except Exception:
            pass

