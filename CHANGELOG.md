# Changelog — Registro de Cambios

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [0.5.0] - 2026-09-26

### 🚀 Añadido
- **Estructura de paquete formal `jinxas/`:** Modularización y empaquetado PEP 621 con punto de entrada en consola CLI `jinx` (`jinxas.__main__:main`) y shim retrocompatible en raíz `main.py`.
- **Pipeline de Integración Continua (CI):** Flujo de trabajo en GitHub Actions en entorno Windows con Python 3.12, validación de estilo con Ruff y ejecución de suite de pruebas unitarias.
- **Capa de Atajos Deterministas (0 ms LLM):** Enrutamiento inmediato por expresiones regulares para apertura de apps, métricas de sistema, sensores térmicos y fecha/hora sin latencia de inferencia.
- **Índice Vectorial FAISS Incremental (`.jinx_cache/`):** Persistencia en disco del índice vectorial y manifiesto MD5; acelera el arranque evitando re-calcular embeddings para notas no modificadas.
- **Registro Unificado de Herramientas (`@herramienta`):** Sistema declarativo en `registro.py` que sincroniza los esquemas de llamadas de Ollama y el catálogo de despacho con validación de argumentos.
- **Nueva Herramienta de Fecha y Hora:** Tool nativa `obtener_fecha_hora` que provee al asistente y a los atajos acceso exacto al reloj y calendario del sistema.
- **Telemetría Honesta en Panel SENTINEL:** Medición y cálculo en tiempo real de tokens por segundo reales de Ollama (`eval_count` / `eval_duration`), Time to First Audio (`TTFA`), y cronómetro total del turno.
- **Higienización de Logs (`JINX_LOG`):** Nivel `INFO` reservado a metadatos, nombres de tools y longitudes en caracteres; contenido sensible de notas y prompts restringido exclusivamente a `DEBUG`.
- **Envoltorio Anti-Inyección de Tools (`envolver_resultado_tool`):** Bloques `<datos_herramienta>` que protegen al LLM contra ejecución de instrucciones maliciosas embebidas en datos no confiables.
- **Suite Integral de Pruebas Unitarias:** 188 pruebas automatizadas con mocks de baja memoria en `tests/conftest.py` ejecutándose en menos de 1 segundo.

### 🔄 Cambiado
- **Arquitectura de Interfaz Nativa 100% Offline:** Reubicación de `panel_sentinel.html` a `ui/panel.html` eliminando dependencias de Node.js, librerías externas y llamadas a CDNs.
- **Apertura Segura de Aplicaciones:** Eliminación del vulnerable `cmd /c start` en favor de `shutil.which` + `subprocess.Popen(shell=False)` para ejecutables y `os.startfile` para URIs seguras (`spotify:`, `obsidian://`).
- **Sincronización de Documentación y README:** Rediseño completo del README con badges honestos de privacidad y matriz de componentes (LLM/STT/RAG locales vs Voz online).

### 🐛 Corregido
- **Sensores de Temperatura en Windows:** Eliminación de alucinaciones térmicas cuando Windows no expone sensores ACPI a través de `psutil`, retornando un estado descriptivo honesto.
- **Condiciones de Carrera en PyWebView:** Sincronización diferida del DOM mediante evento `loaded` en la interfaz nativa para garantizar recepción de satélites y telemetría sin pérdidas.
- **Blindaje contra Path Traversal y Archivos Reservados:** Normalización estricta de rutas con `_ruta_segura` y protección con prefijo para nombres reservados de Windows (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).

---

## [0.4.0] - 2026-09-20 (Pre-Roadmap de Consolidación)

### 📦 Estado Heredado
- Monolito inicial con bucle de voz y orquestación concentrados en un único `main.py` en la raíz.
- Inferencia basada en Ollama con prompts no higienizados y llamadas manuales a `os.system` / `cmd /c`.
- Búsqueda RAG recalculada desde cero en memoria RAM en cada reinicio del asistente.
- Panel visual dependiente de recursos externos y mediciones de latencia no sincronizadas con el streaming de audio.
- Sin suite de pruebas unitarias formal ni pipeline de integración continua.
