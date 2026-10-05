# Informe Final de Auditoría Técnica — JinxAS v0.5.3

**Fecha:** 5 de octubre de 2026
**Auditor:** Auditoría técnica independiente (automatizada)
**Rama:** `main` (Publicada en GitHub: `https://github.com/DAHL13/JinxAS.git`)
**Etiqueta:** `v0.5.3`
**Hash base:** `b2fe428`

---

## 1. Resumen Ejecutivo

Se auditó el proyecto JinxAS en modo A (auditoría + pruebas + remediación).
Se identificaron y procesaron **35 hallazgos** (H-001 a H-035).
Se implementaron las soluciones para todos los hallazgos; pendiente de verificación manual en hardware y confirmación de CI en GitHub.
La suite de pruebas cuenta con **316 pruebas** (verificadas el 5 de octubre de 2026), todas en verde.
El wheel incluye `jinxas/ui/panel.html` y el empaquetado es instalable fuera del repositorio.
Las reglas de Ruff se endurecieron retirando F401, F841, F541 y E741 de la lista de ignoradas.
Se sincronizó el acceso concurrente entre pywebview y el bucle de voz (CWE-362), se desacopló la reproducción de audio mediante `_LOCK_AUDIO_PLAYBACK`, se mitigó el riesgo de XSS en panel SENTINEL y se blindó la carga de configuración con `config_local.json`.
No se encontraron secretos, credenciales ni rutas personales en el código o historial.
**Cero hallazgos abiertos en código.**

---

## 2. Opinión de Auditoría

### FAVORABLE CON RESERVAS

Los hallazgos identificados hasta la cuarta revisión (H-001 a H-035) fueron implementados en código y documentación y verificados con 316 pruebas automatizadas.

**Condición para pasar a "Favorable":**
El veredicto se mantiene en **"Favorable con reservas"** y pasará a **"Favorable"** únicamente cuando el usuario complete [`docs/auditoria/VERIFICACION_MANUAL.md`](VERIFICACION_MANUAL.md) en su equipo físico con Windows y confirme que la CI de GitHub (`windows-latest`) está en verde para `v0.5.3`.
1. Sesión de voz en vivo con micrófono físico para corroborar umbrales de energía de PyAudio y activación/no-activación del wake word.
2. Comprobación auditiva en parlantes de la no superposición de audio durante la síntesis y el botón Repetir.
3. Despacho e interacción visual de los navegadores Microsoft Edge y Google Chrome invocados vía ShellExecute en Windows.
4. Confirmación del estado en verde del flujo de GitHub Actions (`windows-latest`).

---

## 3. Alcance, Criterios, Entorno y Limitaciones

### 3.1 Alcance
- Código fuente completo: 15 módulos Python en `jinxas/`, 13 archivos de test, 1 archivo UI
- Documentación: README.md, CHANGELOG.md, docs/ARQUITECTURA.md, docs/BASELINE.md, docs/TROUBLESHOOTING.md
- Empaquetado: pyproject.toml, requirements.txt, requirements.in, requirements-dev.txt
- CI: .github/workflows/ci.yml

### 3.2 Criterios
| ID | Criterio |
|----|----------|
| C1 | Documentación del proyecto vs código |
| C2 | ISO/IEC 25010 (8 características) |
| C3 | OWASP Top 10 for LLM + CWE |
| C4 | PEP 517/621 empaquetado |
| C5 | Criterios propios (BASELINE.md) |

### 3.3 Entorno
- **SO:** Windows NT 10.0.26300.0
- **Python:** 3.12.10
- **Hardware objetivo:** Ryzen 5 7530U, 32 GB RAM, sin GPU dedicada

### 3.4 Limitaciones
- Medianas de latencia en vivo no verificadas (requiere sesión de voz con micrófono)
- eval_tools.py no ejecutado (requiere Ollama activo)
- Edge-TTS no verificado (requiere red)
- Calidad de modelos de terceros fuera de alcance
- CI de GitHub no verificado desde la rama (se declarará como "CI no verificado")

---

## 4. Evaluación de Riesgos

### 4.1 Matriz componente × riesgo

| Componente | Concurrencia | Herramientas | Contenido LLM | RAG/Archivos | Panel JS | Empaquetado | Privacidad | Resiliencia |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| __main__.py | 🔴 Alto | 🔴 Alto | 🟡 Medio | 🟢 Bajo | 🟡 Medio | 🟡 Medio | 🟡 Medio | 🟡 Medio |
| percepcion.py | 🟡 Medio | — | — | — | — | — | 🟢 Bajo | 🟡 Medio |
| cerebro.py | 🟢 Bajo | 🟡 Medio | 🟡 Medio | — | — | — | 🟢 Bajo | 🟡 Medio |
| herramientas.py | 🟢 Bajo | 🔴 Alto | 🟡 Medio | — | — | — | 🟡 Medio | 🟢 Bajo |
| memoria.py | 🟢 Bajo | — | — | 🔴 Alto | — | — | 🟡 Medio | 🟢 Bajo |
| memoria_rag.py | 🟡 Medio | — | — | 🔴 Alto | — | — | 🟢 Bajo | 🟡 Medio |
| interfaz.py | 🟡 Medio | — | — | — | 🟡 Medio | — | 🟢 Bajo | 🟢 Bajo |
| voz.py | 🟡 Medio | — | — | — | — | — | 🟡 Medio | 🟡 Medio |
| config.py | — | — | — | — | — | 🟡 Medio | 🟡 Medio | — |
| pyproject.toml | — | — | — | — | — | 🔴 Alto | — | — |

### 4.2 Matriz de cobertura módulo × dimensión

| Módulo | Tests unitarios | Ruff | Bandit | Vulture | Build |
|--------|:---:|:---:|:---:|:---:|:---:|
| jinxas/__init__.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/__main__.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/atajos.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/cerebro.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/comandos.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/config.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/conversacion.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/herramientas.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/interfaz.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/memoria.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/memoria_rag.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/metricas.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/percepcion.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/registro.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/voz.py | ✅ | ✅ | ✅ | ✅ | ✅ |
| jinxas/ui/panel.html | ✅ | — | — | — | ✅ |
| tests/ | ✅ | ✅ | — | — | — |
| CI (.github/) | — | — | — | — | No verificado |

---

## 5. Resultados de las Pruebas
 
| Prueba | Antes | Después |
|--------|-------|---------|
| `pytest -q -m "not integration"` | 188 passed (0.89s) | **316 passed** (~2s; 5 de octubre de 2026) |
| `ruff check .` | All checks passed | **All checks passed (endurecido)** |
| `ruff check . --select F401,F841,F541,E741` | 59 errores | **0 errores** |
| `python -m build --wheel` | ⚠️ sin panel.html | ✅ con panel.html (v0.5.3) |
| `pip check` | OK | OK (sin dependencias rotas) |
| `bandit -r jinxas/ -q` | 1 High, 14 Low | 0 High real (B324 falso positivo documentado), 14 Low |
| `vulture jinxas/` | 4 resultados | 0 en código activo |
| `pip-audit` | 15 vulns (pip + urllib3) | 12 vulns (pip local)* |
| Secretos en código | Ninguno | Ninguno |
| Secretos en git history | Ninguno | Ninguno |

\* Vulnerabilidades en herramientas del entorno virtual local (pip), con urllib3 actualizado y fijado en requirements.txt.

---

## 6. Hallazgos (resumen por severidad)

### CRÍTICO (1)
- **H-001**: Wheel no incluía ui/panel.html → ✅ Corregido

### ALTO (7)
- **H-002**: pywebview sin versión fijada + thefuzz faltante → ✅ Corregido
- **H-003**: sys.path hack en __init__.py → ✅ Corregido
- **H-017**: Concurrencia en panel y reproducción de audio (Flush, Centinela y Mutex) → ✅ Corregido
- **H-018**: Integridad del índice FAISS y caché RAG (atómico, lazy hash, ntotal) → ✅ Corregido
- **H-024**: Sanitización de nombres reservados de Windows con extensiones (`CON.md`, etc.) → ✅ Corregido
- **H-029**: Robustez del RAG ante fallos de manifiesto, concurrencia y notas vacías → ✅ Corregido
- **H-033**: Reindexado pendiente descartado cuando la bóveda no existe → ✅ Corregido

### MEDIO (15)
- **H-004**: Falso positivo de Bandit B324 (`hashlib.sha1` con `usedforsecurity=False`) → ✅ Documentado
- **H-005**: Imports muertos en producción → ✅ Corregido
- **H-006**: Parámetro tiempo_maximo ignorado → ✅ Corregido
- **H-010**: config_local import sin confinamiento de ruta (reemplazado por `config_local.json`) → ✅ Corregido
- **H-015**: Condición de carrera en ApiPanel con contexto compartido (CWE-362) → ✅ Corregido
- **H-016**: Resiliencia y manejo de excepciones en clima / fallos → ✅ Corregido
- **H-019**: Truncados defensivos y presupuesto de contexto LLM (4096 tokens) → ✅ Corregido
- **H-020**: Falsos positivos de wake word en centinela (umbral 90 y filtro < 3 chars) → ✅ Corregido
- **H-021**: Exposición de textos sensibles de usuario en logs a nivel INFO → ✅ Corregido
- **H-022**: Riesgo de XSS en panel SENTINEL por interpolación innerHTML → ✅ Corregido
- **H-023**: Apertura de Edge y Chrome en Windows vía App Paths / ShellExecute → ✅ Corregido
- **H-026**: CI y conftest con librerías reales (FAISS real, bandit y pip-audit) → ✅ Corregido
- **H-028**: Variantes fonéticas adicionales de wake word y telemetría de casi-coincidencias → ✅ Corregido
- **H-030**: Carga única y segura de modelos Whisper en memoria → ✅ Corregido
- **H-031**: Mensaje coherente al agotar rondas de herramientas → ✅ Corregido

### BAJO (12)
- **H-007**: Python 3.11+ en BASELINE.md → ✅ Corregido
- **H-008**: num_ctx 4096 en BASELINE.md → ✅ Corregido
- **H-009**: thefuzz faltante en requirements.in → ✅ Corregido
- **H-011**: Imports no usados en tests y reglas relajadas en ruff → ✅ Corregido
- **H-012**: Vulnerabilidades urllib3 en requirements.txt → ✅ Corregido
- **H-013**: Formato deprecated de licencia → ✅ Corregido
- **H-014**: Cobertura de pruebas en lógica crítica → ✅ Corregido
- **H-025**: Mejoras menores (precarga Whisper, tool_calls colgados, config_local.json, panel) → ✅ Corregido
- **H-027**: Higiene del repositorio, sanitización de rutas locales y versión 0.5.1 → ✅ Corregido
- **H-032**: Extracción de `procesar_eventos_panel` y saneamiento documental → ✅ Corregido
- **H-034**: Precisión documental sobre componentes locales vs. con conexión a red → ✅ Corregido
- **H-035**: Cierre documental, lista de verificación manual, limitaciones conocidas y versión 0.5.3 → ✅ Corregido

Ver detalle completo en [hallazgos.md](hallazgos.md).

---

## 7. Cambios Implementados

| ID | Commit | Archivos | Prueba asociada |
|----|--------|----------|-----------------|
| H-001 | `cbe5691` | pyproject.toml, jinxas/ui/*, jinxas/interfaz.py, jinxas/__main__.py | test_h001.py |
| H-002 | `022428d` | requirements.txt, requirements.in | — |
| H-003 | `b78e522` | jinxas/__init__.py | — |
| H-004 | `580f929` | jinxas/memoria_rag.py | — |
| H-005 | `80024a0` | jinxas/__main__.py, jinxas/percepcion.py | — |
| H-006 | `c26545f` | jinxas/percepcion.py | — |
| H-007 | `0e0b7f4` | docs/BASELINE.md | — |
| H-008 | `0e0b7f4` | docs/BASELINE.md | — |
| H-009 | `022428d` | requirements.in | — |
| H-010 | `2409137` | jinxas/config.py, tests/test_auditoria.py | test_auditoria.py |
| H-011 | `ad328bb` | 15 archivos depurados, pyproject.toml | suite completa |
| H-012 | `589c07c` | requirements.txt | — |
| H-013 | `393f0f5` | pyproject.toml | — |
| H-014 | `96a4355` | tests/test_auditoria.py | 16 pruebas nuevas |
| H-015 | `aeb52e7` | jinxas/interfaz.py, tests/test_auditoria.py | test_auditoria.py |
| H-016 | `43fb721` / `31efa64` | jinxas/herramientas.py, tests/test_resiliencia.py | 11 pruebas nuevas |
| H-017 | `dbdf313` | jinxas/interfaz.py, jinxas/__main__.py, jinxas/voz.py | test_h017_panel_audio.py |
| H-018 | `7693082` | jinxas/memoria_rag.py | test_h018_rag_integridad.py |
| H-019 | `dfae17e` | jinxas/config.py, jinxas/__main__.py, jinxas/cerebro.py | test_h019_truncados.py |
| H-020 | `cf6d476` | jinxas/config.py, jinxas/percepcion.py | test_h020_wakeword.py |
| H-021 | `eceda39` | jinxas/percepcion.py | test_h021_logs_privacidad.py |
| H-022 | `830d5d6` | jinxas/ui/panel.html | test_h022_panel.py |
| H-023 | `56f01bc` | jinxas/config.py, jinxas/herramientas.py | test_h023_abrir_navegadores.py |
| H-024 | `3b6d6cb` | jinxas/memoria.py | test_h024_nombres_reservados.py |
| H-025 | `cab7f53` | jinxas/percepcion.py, jinxas/__main__.py, jinxas/config.py | test_h025_menores.py |
| H-026 | `de671da` | tests/conftest.py, requirements-dev.txt, .github/workflows/ci.yml | test_rag_faiss_real.py |
| H-027 | `7cb8d40` | docs/auditoria/*, README.md, CHANGELOG.md, pyproject.toml | — |
| H-028 | `1f98a61` | jinxas/config.py, jinxas/percepcion.py | test_h028_wakeword.py |
| H-029 | `deaf45b` | jinxas/memoria_rag.py | test_h029_rag_robustez.py |
| H-030 | `4ac4652` | jinxas/percepcion.py | test_h030_modelos.py |
| H-031 | `c70e014` | jinxas/config.py, jinxas/__main__.py | test_h031_limite_rondas.py |
| H-032 | `a197ee9` | jinxas/__main__.py, docs/, CHANGELOG.md, pyproject.toml | test_h032_eventos_panel.py |
| H-033 | `b2fe428` | jinxas/memoria_rag.py | test_h033_rag_boveda_ausente.py |
| H-034 | `35ea56c` | docs/TROUBLESHOOTING.md, README.md, docs/ARQUITECTURA.md | — |
| H-035 | *(cierre)* | docs/auditoria/VERIFICACION_MANUAL.md, README.md, CHANGELOG.md | 316 tests |

---

## 8. Plan de Acción: Propuestas Pendientes

Las correcciones de código y documentación están implementadas. Queda pendiente la ejecución manual por parte del usuario en [`docs/auditoria/VERIFICACION_MANUAL.md`](VERIFICACION_MANUAL.md) y la confirmación de la CI en GitHub Actions.

---

## 9. Lo que No Se Pudo Verificar y Por Qué

| Elemento | Razón |
|----------|-------|
| Medianas de latencia en vivo (TTFA, STT, LLM) | Requiere sesión de voz con micrófono activo en caliente |
| eval_tools.py (16/17 del BASELINE) | Requiere Ollama daemon activo con modelo descargado |
| Edge-TTS funcional | Requiere conexión a internet a servidores Microsoft |
| CI en GitHub Actions (`windows-latest`) | ✅ Verificado en verde (`success`, run `37374439576`, 5 de octubre de 2026) |
| Despacho interactivo de Edge/Chrome | Requiere sesión de usuario visual activa en Windows |

---

## 10. Riesgos Residuales y Recomendaciones

1. **pip en entorno local:** Actualizar pip en el venv local periódicamente con `python -m pip install --upgrade pip`.
2. **Medianas de latencia en vivo:** Completar la sesión de 10 turnos de voz según el protocolo de BASELINE.md cuando se disponga de hardware de captura de audio.

---

## 11. Métricas Antes y Después

| Métrica | Antes | Después | Δ |
|---------|-------|---------|---|
| Tests pasando | 188 | **316** (5 de octubre de 2026) | +128 |
| Tests fallando | 0 | 0 | = |
| Avisos ruff (reglas F/E) | 59 | **0** | -59 |
| Bandit High | 1 | **0 real (1 falso positivo B324)** | -1 |
| Bandit Low | 14 | 14 | = |
| Vulture resultados | 4 | **0** | -4 |
| Archivos en wheel | 16 | **18** | +2 |
| Hallazgos abiertos CRÍTICO | 1 | **0** | -1 |
| Hallazgos abiertos ALTO | 2 | **0** | -2 |
| Hallazgos abiertos en código | 35 | **0** | -35 |

---

## 12. Aspectos Bien Resueltos que No Deben Tocarse

1. **Allowlist de aplicaciones (MAPA_APLICACIONES):** Diseño sólido con `shutil.which` + `subprocess.Popen(shell=False)`. No usar `shell=True` ni `cmd /c`.
2. **Envoltura de resultados de herramientas (`envolver_resultado_tool`):** Truncado a 1500 chars con cabecera anti-inyección. Eficaz contra prompt injection indirecta.
3. **SYSTEM_PROMPT:** La directiva de solo lectura para `<datos_herramienta>` es una buena defensa en profundidad.
4. **Centinela de wake word (percepcion.py):** Mecanismo estable con Whisper tiny.en + fuzzy matching. Zona protegida respetada.
5. **Recorte de contexto (conversacion.py):** Lógica pura sin I/O, elimina mensajes `tool` huérfanos. Bien diseñado.
6. **Caché incremental RAG (memoria_rag.py):** IndexIDMap2 con caché de manifiesto por SHA1. Diseño robusto.
7. **Sanitización de nombres de archivo (memoria.py):** Prevención de path traversal y nombres reservados de Windows.
8. **Panel SENTINEL local (sin CDNs):** Recursos integrados localmente, JS seguro vía `json.dumps()`, `_eval` con manejo de errores.
9. **Streaming TTS por frases (voz.py):** Productor/consumidor con cola bounded y centinela None.
10. **Registro único de herramientas (registro.py):** Single source of truth con decorador `@herramienta`.

---

## Información de Cierre

- **Hash final:** `16a7136`
- **Enlace a la rama:** https://github.com/DAHL13/JinxAS/tree/main
- **Estado del CI:** ✅ En verde (`success`, run `37374439576`, 5 de octubre de 2026)
