# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.
El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [0.5.1] - 2026-10-02
### Corregido
- **(H-001)** `ui/panel.html` no se incluía en el wheel; movido a `jinxas/ui/` con resolución de ruta por `__file__`.
- **(H-002)** `pywebview` sin versión fijada en `requirements.txt`; `thefuzz` faltante en `requirements.in`.
- **(H-003)** Eliminada manipulación de `sys.path` en `__init__.py` (antipatrón PEP 517).
- **(H-004)** Documentado falso positivo de Bandit B324 (`hashlib.sha1` con `usedforsecurity=False` en caché RAG).
- **(H-005)** Imports muertos en `__main__.py` y `percepcion.py`.
- **(H-006)** Parámetro `tiempo_maximo` ignorado en `escuchar_y_transcribir()`.
- **(H-007/H-008)** Discrepancias en `BASELINE.md`: versión de Python y `num_ctx`.
- **(H-010)** Reemplazo de importación dinámica de configuración por lectura segura de `config_local.json` sin `importlib`.
- **(H-011)** Limpieza de avisos en suite de pruebas y endurecimiento de Ruff retirando F401, F841, F541 y E741 de `ignore`.
- **(H-012)** Pin de `urllib3==2.8.0` en `requirements.txt` para mitigar vulnerabilidades reportadas por pip-audit.
- **(H-013)** Formato deprecated de licencia en `pyproject.toml` migrado a especificación PEP 639.
- **(H-015)** Sincronización de acceso a `contexto` en `ApiPanel` mediante `threading.Lock` eliminando condición de carrera (CWE-362).
- **(H-016)** Manejo robusto de excepciones de red en `obtener_clima`.
- **(H-017)** Desacople y concurrencia de audio/panel: Emergency Flush inmediato, interrupción reactiva del centinela con tupla de eventos y exclusión mutua (`_LOCK_AUDIO_PLAYBACK`) en reproducción de voz.
- **(H-018)** Integridad de caché RAG y FAISS: escritura atómica con archivo temporal (`_escritura_atomica`), hashing SHA-1 perezoso por mtime/size, validación de `ntotal` contra manifiesto y bucle de reindexación ante construcciones pendientes.
- **(H-019)** Presupuesto de contexto LLM y truncado defensivo: `MAX_CHARS_RESULTADO_TOOL = 3200`, `LLM_OPCIONES` con `num_ctx: 4096, num_predict: 256`, recorte no destructivo por fragmentos en `buscar_semantica` y advertencia al 90% de ocupación de contexto.
- **(H-020)** Eliminación de falsos positivos en centinela: umbral difuso elevado a 90, descarte de tokens de menos de 3 caracteres y soporte de la variante fonética `"jinxs"`.
- **(H-021)** Privacidad de datos del usuario en logs: transcripciones de usuario y palabras de activación movidas a nivel `DEBUG`, registrando únicamente metadatos y longitudes a nivel `INFO`.
- **(H-022)** Endurecimiento XSS en panel SENTINEL: sustitución de interpolación `innerHTML` con datos de logs por creación de nodos DOM y asignación de `textContent`.
- **(H-023)** Despacho de navegadores en Windows vía App Paths / ShellExecute: esquema `app:msedge` y `app:chrome` en `MAPA_APLICACIONES` mediante `os.startfile`.
- **(H-024)** Sanitización estricta de nombres de dispositivos reservados de Windows con extensiones (`CON.md`, `nul.txt`, `aux.notas`, `COM1.md`, etc.).
- **(H-025)** Mejoras menores: precarga en segundo plano de modelos Whisper (`tiny.en` y `small`) con cerrojo de sincronización, saneamiento de `tool_calls` colgados al agotar rondas, soporte de `config_local.json`, botón "Repetir" en panel y retiro de `python-Levenshtein` redundante.
- **(H-026)** Integración Continua y conftest realistas: carga condicional de dependencias reales (`faiss`, `thefuzz`, `psutil`) en tests, incorporación de `faiss-cpu` y `thefuzz` a `requirements-dev.txt`, prueba unitaria con FAISS real e incorporación de escáneres `pip-audit` y `bandit` en CI.

### Añadido
- 93 pruebas unitarias nuevas (281 en total) cubriendo lógica crítica, inyección de fallos, resiliencia, FAISS real, privacidad de logs, nombres reservados y concurrencia UI/audio.
- Documentación integral de auditoría en `docs/auditoria/` (plan, papeles de trabajo, hallazgos, informe final y reporte consolidado).

## [0.5.0] - 2026-09-26
### Añadido
- Empaquetado formal como librería `jinxas/` con comando CLI `jinx`.
- Pipeline de Integración Continua (CI) en GitHub Actions (`.github/workflows/ci.yml`).
- Atajos deterministas por regex con 0 ms de LLM (`atajos.py`).
- Índice FAISS persistente e incremental en `.jinx_cache/`.
- Registro unificado de tools con decorador `@herramienta` (`registro.py`).
- Herramienta de fecha y hora local (`obtener_fecha_hora`).
- Telemetría real de tokens/s en panel SENTINEL desde métricas de Ollama.
- Sanitización de logs mediante nivel `JINX_LOG` y envoltura defensiva `envolver_resultado_tool`.
- Suite automatizada de pruebas unitarias (188 pruebas en verde).
- Documentación de arquitectura (`docs/ARQUITECTURA.md`) y resolución de problemas (`docs/TROUBLESHOOTING.md`).

### Cambiado
- Panel SENTINEL migrado a `ui/panel.html`, 100% offline sin peticiones a CDNs.
- Despacho de aplicaciones acotado mediante `shutil.which` y `subprocess.Popen(shell=False)` sin `cmd /c start`.
- Optimización de latencia en herramientas de sistema (`psutil.cpu_percent` de 500ms a 100ms).
- Estandarización de importaciones con namespace `jinxas` y eliminación de duplicación de `normalizar` (DRY).
- README reestructurado con tabla de privacidad honesta y licencia MIT formal.

### Corregido
- Corrección de desincronización de IDs en búsqueda semántica FAISS (`buscar_semantica`), resolviendo fragmentos por `_id` de forma exacta.
- Prevención de deadlock en el hilo productor de TTS streaming mediante bloque `try ... finally` garantizando el centinela `cola.put(None)`.
- Eliminación de carreras en reindexación concurrente de bóveda Obsidian con `_lock_construir`.
- Blindaje de llamadas JS hacia el panel SENTINEL con verificación condicional de métodos en `window.jinxUI`.
- Eliminación de lecturas ficticias en el sensor de temperatura en Windows.
- Corrección de condición de carrera en el arranque del panel pywebview.
- Validación estricta contra Path Traversal y nombres reservados de Windows (`CON`, `PRN`, etc.).

## [0.4.0] - 2026-09-21
### Añadido
- Estado previo al Roadmap de Consolidación (etiqueta `v0.4-pre-roadmap`).
