"""
interfaz.py — Puente Python → Frontend (pywebview)
Fase 6 · JinxAS

Expone ControladorPanel, que traduce llamadas Python a JavaScript
usando ventana.evaluate_js(), y ApiPanel (JS → Python) para control
desde el frontend (Emergency Flush, Regenerar, etc.).
"""
from __future__ import annotations

import json
import logging
import os

from jinxas import config


class ApiPanel:
    """Clase puente para pywebview (JS → Python) (F6-02, F6-04)."""

    def __init__(self, evento_reinicio=None, evento_regenerar=None):
        self.evento_reinicio = evento_reinicio
        self.evento_regenerar = evento_regenerar
        self.contexto: list | None = None

    def reiniciar_memoria(self) -> bool:
        if self.evento_reinicio:
            self.evento_reinicio.set()
        return True

    def regenerar(self) -> bool:
        if self.evento_regenerar:
            self.evento_regenerar.set()
        return True

    # Métodos para retrocompatibilidad
    def limpiar_memoria_ui(self) -> None:
        try:
            self.reiniciar_memoria()
            if self.contexto is not None and len(self.contexto) > 1:
                del self.contexto[1:]
                logging.info("[ApiPanel] Historial borrado desde el panel UI (Emergency Flush).")
            else:
                logging.info("[ApiPanel] Flush solicitado: historial ya estaba vacío.")
        except Exception as exc:
            logging.error("[ApiPanel] Error al limpiar historial: %s", exc)

    def repetir_audio_ui(self) -> None:
        import threading
        try:
            self.regenerar()
            ultimo_texto = ""
            if self.contexto:
                for msg in reversed(self.contexto):
                    if msg.get("role") == "assistant":
                        ultimo_texto = (msg.get("content") or "").strip()
                        break
            if ultimo_texto:
                from jinxas.voz import reproducir_voz
                logging.info("[ApiPanel] Repitiendo último audio desde el panel UI.")
                threading.Thread(target=reproducir_voz, args=(ultimo_texto,), daemon=True).start()
            else:
                logging.info("[ApiPanel] Repetir audio: no hay respuesta previa en el contexto.")
        except Exception as exc:
            logging.error("[ApiPanel] Error al repetir audio: %s", exc)


# Alias para retrocompatibilidad
InterfazAPI = ApiPanel


class ControladorPanel:
    """Controlador del panel SENTINEL.

    Uso:
        panel = ControladorPanel(evento_reinicio, evento_regenerar)
        panel.crear_ventana()
        panel.actualizar_estado(1)
        panel.actualizar_respuesta("Hola mundo", 843)
    """

    def __init__(self, evento_reinicio=None, evento_regenerar=None) -> None:
        self.evento_reinicio = evento_reinicio
        self.evento_regenerar = evento_regenerar
        self._ventana = None
        self._ultimo_paso = 1
        self._ultima_respuesta = ""
        self._ultima_latencia = 0
        self._ultimos_tiempos: dict = {}

    @property
    def ventana(self):
        return self._ventana

    @ventana.setter
    def ventana(self, val):
        self._ventana = val
        if val is not None and hasattr(val, "events") and hasattr(val.events, "loaded"):
            try:
                val.events.loaded += self.sincronizar
            except Exception:
                pass

    def sincronizar(self) -> None:
        """Sincroniza el estado del backend con el frontend al cargar la ventana (F6-06)."""
        if not self.ventana:
            return
        try:
            self.enviar_configuracion()
            self.actualizar_estado(self._ultimo_paso)
            if self._ultima_respuesta:
                self.actualizar_respuesta(self._ultima_respuesta, self._ultima_latencia)
            if self._ultimos_tiempos:
                self.actualizar_tiempos(self._ultimos_tiempos)
            self._eval("if (typeof ajustarLienzo === 'function') { ajustarLienzo(); }")
        except Exception as exc:
            logging.warning("[ControladorPanel] Error en sincronizar arranque: %s", exc)

    def enviar_configuracion(self) -> None:
        """Envía los parámetros reales de configuración al panel UI (F6-01)."""
        if not self.ventana:
            return
        datos = {
            "modelo_llm": config.MODELO_LLM,
            "modelo_whisper": config.MODELO_WHISPER,
            "idioma_whisper": config.IDIOMA_WHISPER,
            "voz_tts": config.VOZ_TTS,
            "temperatura": config.LLM_OPCIONES.get("temperature", 0.3),
            "ciudad": config.CIUDAD,
        }
        self._eval(f"if(window.jinxUI && window.jinxUI.setConfig) {{ window.jinxUI.setConfig({json.dumps(datos)}); }}")

    def crear_ventana(self, ruta_html: str | None = None) -> object:
        import webview
        if ruta_html is None:
            ruta_html = os.path.join(config._BASE_DIR, "ui", "panel.html")
        api = ApiPanel(self.evento_reinicio, self.evento_regenerar)
        self.ventana = webview.create_window(
            "JinxAS",
            ruta_html,
            width=1200,
            height=800,
            min_size=(1000, 640),
            js_api=api,
        )
        return self.ventana

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
        self._ultimo_paso = paso
        self._eval(f"if (window.jinxUI) {{ window.jinxUI.setEstado({paso}); }}")

    def actualizar_respuesta(self, texto: str, latencia: int) -> None:
        """Actualiza el texto de la última respuesta y la latencia en ms."""
        self._ultima_respuesta = texto
        self._ultima_latencia = int(latencia)
        self._eval(f"if (window.jinxUI && window.jinxUI.setRespuesta) {{ window.jinxUI.setRespuesta({json.dumps(texto)}, {int(latencia)}); }}")

    def actualizar_tiempos(self, tiempos: dict) -> None:
        """Actualiza las métricas de telemetría de tiempos en el panel UI."""
        self._ultimos_tiempos = tiempos
        if not self.ventana:
            return
        tiempos_seguros = json.dumps(tiempos)
        try:
            self._eval(f"if(window.jinxUI && window.jinxUI.setTiempos) {{ window.jinxUI.setTiempos({tiempos_seguros}); }}")
        except Exception as e:
            logging.warning("Error al actualizar tiempos en UI: %s", e)

    def actualizar_satelite(self, hub: int, sat: int, titulo: str = None, desc: str = None) -> None:
        """Actualiza dinámicamente el título y descripción de cualquier satélite en el panel."""
        if not self.ventana:
            return
        t_seguro = json.dumps(titulo) if titulo else "null"
        d_seguro = json.dumps(desc) if desc else "null"
        self._eval(
            f"if(window.jinxUI && window.jinxUI.actualizarSatelite) {{ window.jinxUI.actualizarSatelite({hub}, {sat}, {t_seguro}, {d_seguro}); }}"
        )

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


# Instancia o referencia por defecto para resolución de panel
panel: ControladorPanel | None = None


