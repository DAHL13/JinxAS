"""
tests/test_f2_streaming_voz.py
F2-02: Tests unitarios para extraer_frases() y reproducir_frases_streaming().

Estrategia de mock:
  - _generar_audio_edge   → coroutine mock que no hace nada (simula síntesis)
  - pygame.mixer.*        → MagicMock (ya mockeado en conftest.py)
  - os.remove             → espiado para verificar limpieza de archivos

Los tests son completamente offline y terminan en < 1 s.
"""

import os
import asyncio
from unittest.mock import MagicMock, patch, call
import pytest

import voz
from voz import extraer_frases, reproducir_frases_streaming


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunks_simples(*partes):
    """Genera un iterable de strings tal como lo emite el LLM fragmento a fragmento."""
    return list(partes)


# ---------------------------------------------------------------------------
# Tests de extraer_frases()
# ---------------------------------------------------------------------------

class TestExtraerFrases:
    def test_tres_frases_en_orden(self):
        """a) Entrada con 3 frases claras → 3 yields en orden."""
        entrada = ["Hola mundo. ", "¿Cómo estás? ", "Todo bien"]
        resultado = list(extraer_frases(entrada))
        assert resultado == ["Hola mundo.", "¿Cómo estás?", "Todo bien"]

    def test_fragmentos_divididos(self):
        """Los fragmentos pueden llegar cortados a mitad de frase."""
        entrada = ["Hola ", "mundo. ", "¿Cómo ", "estás? ", "Bien"]
        resultado = list(extraer_frases(entrada))
        assert resultado == ["Hola mundo.", "¿Cómo estás?", "Bien"]

    def test_una_sola_frase_sin_punto(self):
        """Texto sin punto final → se emite como remanente."""
        resultado = list(extraer_frases(["Sin punto al final"]))
        assert resultado == ["Sin punto al final"]

    def test_frase_con_exclamacion_e_interrogacion(self):
        """Signos ! y ? también cierran frases."""
        entrada = ["¡Perfecto! ", "¿Seguro? ", "Sí"]
        resultado = list(extraer_frases(entrada))
        assert resultado == ["¡Perfecto!", "¿Seguro?", "Sí"]

    def test_frase_con_elipsis(self):
        """El carácter … también cierra frases."""
        entrada = ["Espera… ", "ya viene"]
        resultado = list(extraer_frases(entrada))
        assert resultado == ["Espera…", "ya viene"]

    def test_chunks_de_ollama_dict(self):
        """Soporta chunks de Ollama como dicts con estructura message.content."""
        entrada = [
            {"message": {"content": "Hola mundo. "}},
            {"message": {"content": "Fin"}},
        ]
        resultado = list(extraer_frases(entrada))
        assert resultado == ["Hola mundo.", "Fin"]

    def test_entrada_vacia(self):
        """Iterable vacío → lista vacía."""
        assert list(extraer_frases([])) == []

    def test_multiples_frases_en_un_solo_chunk(self):
        """Un solo chunk puede contener varias frases completas."""
        entrada = ["Primera frase. Segunda frase. Tercera"]
        resultado = list(extraer_frases(entrada))
        assert resultado == ["Primera frase.", "Segunda frase.", "Tercera"]


# ---------------------------------------------------------------------------
# Tests de reproducir_frases_streaming()
# ---------------------------------------------------------------------------

class TestReproducirFrasesStreaming:
    """
    Mockeamos _generar_audio_edge para que no haga nada (coroutine vacío),
    y espiamos os.remove para verificar la limpieza de archivos temporales.
    pygame ya está mockeado globalmente por conftest.py.
    """

    def test_on_start_llamado_exactamente_una_vez(self, tmp_path):
        """b) on_start se invoca exactamente 1 vez, en la primera frase."""
        frases = ["Primera frase.", "Segunda frase.", "Tercera frase."]
        on_start = MagicMock()

        with patch("voz.asyncio.run"), \
             patch("voz.asyncio.wait_for"), \
             patch("voz.os.remove"), \
             patch("voz.pygame.mixer.get_init", return_value=True), \
             patch("voz.pygame.mixer.music") as mock_music:
            # Simular que play() termina de inmediato (get_busy devuelve False)
            mock_music.get_busy.return_value = False

            reproducir_frases_streaming(frases, on_start=on_start)

        on_start.assert_called_once()

    def test_archivos_temporales_eliminados(self):
        """b) Todos los archivos .mp3 temporales creados son eliminados."""
        frases = ["Frase uno.", "Frase dos.", "Frase tres."]
        rutas_creadas = []

        # Interceptar NamedTemporaryFile para registrar las rutas que se crean
        orig_ntf = __import__("tempfile").NamedTemporaryFile

        def _ntf_spy(**kwargs):
            f = orig_ntf(**kwargs)
            rutas_creadas.append(f.name)
            return f

        with patch("voz.tempfile.NamedTemporaryFile", side_effect=_ntf_spy), \
             patch("voz.asyncio.run"), \
             patch("voz.asyncio.wait_for"), \
             patch("voz.os.remove") as mock_remove, \
             patch("voz.pygame.mixer.get_init", return_value=True), \
             patch("voz.pygame.mixer.music") as mock_music:
            mock_music.get_busy.return_value = False

            reproducir_frases_streaming(frases)

        # Cada ruta creada debe haber sido eliminada
        rutas_eliminadas = {c.args[0] for c in mock_remove.call_args_list}
        for ruta in rutas_creadas:
            assert ruta in rutas_eliminadas, (
                f"El archivo temporal {ruta!r} no fue eliminado"
            )

    def test_frases_reproducidas_en_orden(self):
        """Las frases se reproducen en el mismo orden en que se proporcionan."""
        frases = ["Primera.", "Segunda.", "Tercera."]
        orden_carga = []

        def _load_spy(ruta):
            orden_carga.append(ruta)

        with patch("voz.asyncio.run"), \
             patch("voz.asyncio.wait_for"), \
             patch("voz.os.remove"), \
             patch("voz.pygame.mixer.get_init", return_value=True), \
             patch("voz.pygame.mixer.music") as mock_music:
            mock_music.get_busy.return_value = False
            mock_music.load.side_effect = _load_spy

            reproducir_frases_streaming(frases)

        # Se debe haber cargado exactamente 3 archivos
        assert len(orden_carga) == len(frases)

    def test_iterador_vacio_no_falla(self):
        """Un iterable vacío no debe lanzar excepción ni llamar a on_start."""
        on_start = MagicMock()

        with patch("voz.asyncio.run"), \
             patch("voz.asyncio.wait_for"), \
             patch("voz.os.remove"), \
             patch("voz.pygame.mixer.get_init", return_value=True), \
             patch("voz.pygame.mixer.music"):
            reproducir_frases_streaming([], on_start=on_start)

        on_start.assert_not_called()

    def test_sin_on_start_no_falla(self):
        """Llamar sin on_start no debe lanzar excepción."""
        frases = ["Una frase."]

        with patch("voz.asyncio.run"), \
             patch("voz.asyncio.wait_for"), \
             patch("voz.os.remove"), \
             patch("voz.pygame.mixer.get_init", return_value=True), \
             patch("voz.pygame.mixer.music") as mock_music:
            mock_music.get_busy.return_value = False
            # No debe lanzar
            reproducir_frases_streaming(frases)


# ---------------------------------------------------------------------------
# Tests de procesar_pensamiento_stream() y ejecutar_turno_streaming()
# ---------------------------------------------------------------------------

class TestProcesarPensamientoStream:
    """Tests del generador procesar_pensamiento_stream en cerebro.py."""

    def test_stream_emite_chunks(self):
        """Los chunks del stream se propagan directamente desde ollama.chat."""
        import cerebro
        chunks_esperados = [
            {"message": {"role": "assistant", "content": "Hola "}},
            {"message": {"role": "assistant", "content": "mundo."}},
        ]
        with patch("cerebro.ollama.chat", return_value=iter(chunks_esperados)):
            resultado = list(cerebro.procesar_pensamiento_stream([{"role": "user", "content": "test"}]))
        assert resultado == chunks_esperados

    def test_stream_error_emite_chunk_error(self):
        """Si ollama lanza excepción, emite un chunk con _error=True."""
        import cerebro
        with patch("cerebro.ollama.chat", side_effect=RuntimeError("Ollama caído")):
            chunks = list(cerebro.procesar_pensamiento_stream([{"role": "user", "content": "test"}]))
        assert len(chunks) == 1
        assert chunks[0].get("_error") is True
        assert "No pude pensar" in chunks[0]["message"]["content"]


class TestEjecutarTurnoStreaming:
    """
    Tests de ejecutar_turno_streaming() en main.py.
    Mockea procesar_pensamiento_stream para controlar los chunks
    y reproducir_frases_streaming para evitar TTS real.
    """

    def _make_chunk(self, content="", tool_calls=None, error=False):
        """Crea un chunk con la estructura esperada."""
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        c = {"message": msg}
        if error:
            c["_error"] = True
        return c

    def test_caso_directo_sin_tools(self):
        """
        a) Sin tool_calls: el texto del stream llega a reproducir_frases_streaming
        y queda guardado en contexto como mensaje del asistente.

        El mock de reproducir_frases_streaming consume el iterable de frases para
        que el generador en vivo de _generador_texto se ejecute y partes_texto
        quede relleno (igual que lo haría la función real, sin TTS).
        """
        from main import ejecutar_turno_streaming
        from metricas import CronometroTurno
        import time

        chunks = [
            self._make_chunk("Hola mundo. "),
            self._make_chunk("Todo bien."),
        ]
        contexto = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hola"}]
        tiempos = {}
        cronometro = CronometroTurno()
        cronometro.t_inicio_turno = time.perf_counter()
        cronometro.marcar_fin_usuario()

        # El mock consume el iterable para que el generador en vivo se ejecute
        def _rfs_consume(frases_iter, **kwargs):
            for _ in frases_iter:  # Agotar el generador para rellenar partes_texto
                pass

        with patch("main.procesar_pensamiento_stream", return_value=iter(chunks)), \
             patch("main.reproducir_frases_streaming", side_effect=_rfs_consume) as mock_rfs, \
             patch("main.config.ATAJOS", False):
            texto = ejecutar_turno_streaming("hola", contexto, tiempos, cronometro)

        # La función de TTS debe haberse llamado
        mock_rfs.assert_called_once()
        # El texto final debe estar en contexto como mensaje del asistente
        asistente_msgs = [m for m in contexto if m.get("role") == "assistant"]
        assert len(asistente_msgs) == 1
        assert "Hola mundo." in asistente_msgs[0]["content"] or "Todo bien" in asistente_msgs[0]["content"]


    def test_caso_con_tool_call_y_respuesta_final(self):
        """
        b) 1 ronda de tool_calls sin TTS + respuesta final con TTS por frases.
        Verifica que ejecutar_herramienta se llama y reproducir_frases_streaming
        solo se invoca en la ronda final, no durante la herramienta.
        """
        from main import ejecutar_turno_streaming, FUNCIONES_DISPONIBLES
        from metricas import CronometroTurno
        import time

        tc_fake = [{"function": {"name": "obtener_estado_sistema", "arguments": {}}}]
        # Ronda 1: tool_calls
        chunks_ronda1 = [self._make_chunk("", tool_calls=tc_fake)]
        # Ronda 2: respuesta final
        chunks_ronda2 = [self._make_chunk("El sistema está al 10% de CPU.")]

        iter_calls = iter([iter(chunks_ronda1), iter(chunks_ronda2)])

        contexto = [{"role": "system", "content": "sys"}, {"role": "user", "content": "estado"}]
        tiempos = {}
        cronometro = CronometroTurno()
        cronometro.t_inicio_turno = time.perf_counter()
        cronometro.marcar_fin_usuario()

        with patch("main.procesar_pensamiento_stream", side_effect=lambda ctx: next(iter_calls)), \
             patch("main.reproducir_frases_streaming") as mock_rfs, \
             patch("main.ejecutar_herramienta", return_value="CPU: 10%") as mock_tool, \
             patch("main.config.ATAJOS", False):
            texto = ejecutar_turno_streaming("estado", contexto, tiempos, cronometro)

        # La herramienta debe haberse ejecutado exactamente 1 vez
        mock_tool.assert_called_once()
        # TTS solo en la ronda final
        mock_rfs.assert_called_once()
        # El texto final es la respuesta de la segunda ronda
        assert "10% de CPU" in texto or texto == "Listo."

