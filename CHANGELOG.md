# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.
El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

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
- README reestructurado con tabla de privacidad honesta y licencia MIT formal.

### Corregido
- Eliminación de lecturas ficticias en el sensor de temperatura en Windows.
- Corrección de condición de carrera en el arranque del panel pywebview.
- Validación estricta contra Path Traversal y nombres reservados de Windows (`CON`, `PRN`, etc.).

## [0.4.0] - 2026-09-21
### Añadido
- Estado previo al Roadmap de Consolidación (etiqueta `v0.4-pre-roadmap`).
