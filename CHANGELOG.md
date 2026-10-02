# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.
El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]
### Corregido
- **(H-001)** `ui/panel.html` no se incluía en el wheel; movido a `jinxas/ui/` con resolución de ruta por `__file__`.
- **(H-002)** `pywebview` sin versión fijada en `requirements.txt`; `thefuzz` faltante en `requirements.in`.
- **(H-003)** Eliminada manipulación de `sys.path` en `__init__.py` (antipatrón PEP 517).
- **(H-004)** `hashlib.sha1()` sin `usedforsecurity=False` en caché RAG (CWE-327).
- **(H-005)** Imports muertos en `__main__.py` y `percepcion.py`.
- **(H-006)** Parámetro `tiempo_maximo` ignorado en `escuchar_y_transcribir()`.
- **(H-007/H-008)** Discrepancias en `BASELINE.md`: versión de Python y `num_ctx`.
- **(H-010)** Confinamiento estricto de ruta en carga de `config_local.py` mediante importlib (CWE-94).
- **(H-011)** Limpieza de 59 avisos en suite de pruebas y endurecimiento de Ruff retirando F401, F841, F541 y E741 de `ignore`.
- **(H-012)** Pin de `urllib3==2.8.0` en `requirements.txt` para mitigar vulnerabilidades reportadas por pip-audit.
- **(H-013)** Formato deprecated de licencia en `pyproject.toml` migrado a especificación PEP 639.
- **(H-015)** Sincronización de acceso a `contexto` en `ApiPanel` mediante `threading.Lock` eliminando condición de carrera (CWE-362).
- **(H-016)** Manejo robusto de excepciones de red en `obtener_clima`.

### Añadido
- 30 pruebas unitarias nuevas (218 en total) cubriendo lógica crítica de herramientas, recorte de contexto, sanitización de rutas, chunking RAG, TTS, concurrencia y suite formal de inyección de fallos y resiliencia (`tests/test_resiliencia.py`).
- Documentación integral de auditoría en `docs/auditoria/` (plan, papeles de trabajo, hallazgos, informe final).

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
