# Informe Final de Auditoría Técnica — JinxAS v0.5.0

**Fecha:** 2 de octubre de 2026
**Auditor:** Auditoría técnica independiente (automatizada)
**Rama:** `auditoria-profunda`
**Hash base:** `a197ee99de2aa8b4e3d65ceb7994c7fa896a6e62`

---

## 1. Resumen Ejecutivo

Se auditó el proyecto JinxAS v0.5.0 en modo A (auditoría + pruebas + remediación).
Se identificaron **13 hallazgos**: 1 crítico, 2 altos, 4 medios y 6 bajos.
Se corrigieron **10 hallazgos**, se propuso 1 y se aceptaron 2 como riesgo residual.
El hallazgo crítico (H-001: wheel sin panel.html) y los 2 altos fueron remediados.
La suite pasó de 188 a **205 pruebas** (17 nuevas), todas en verde.
El wheel ahora incluye `jinxas/ui/panel.html` y el empaquetado es funcional.
No se encontraron secretos, credenciales ni rutas personales en el código o historial.
**No quedan hallazgos críticos ni altos abiertos.**

---

## 2. Opinión de Auditoría

### FAVORABLE

No se identificaron hallazgos críticos ni altos abiertos al cierre de la auditoría.
El proyecto JinxAS v0.5.0 se considera apto para publicación como **v0.5.1** con
las correcciones implementadas en la rama `auditoria-profunda`.

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
| `pytest -q -m "not integration"` | 188 passed (0.89s) | **205 passed** (1.89s) |
| `ruff check .` | All checks passed | All checks passed |
| `ruff check . --select F401,F841,F541,E741,E402` | 59 errores | 59 errores* |
| `python -m build --wheel` | ⚠️ sin panel.html | ✅ con panel.html |
| `pip check` | OK | OK |
| `bandit -r jinxas/ -q` | 1 High, 14 Low | 0 High, 14 Low |
| `vulture jinxas/` | 4 resultados | 1 resultado |
| `pip-audit` | 15 vulns (pip + urllib3) | 15 vulns (pip + urllib3)** |
| Secretos en código | Ninguno | Ninguno |
| Secretos en git history | Ninguno | Ninguno |

\* Los 59 errores de reglas silenciadas están en tests/ y no en código de producción.
\** Vulnerabilidades en herramientas del entorno (pip), no en dependencias del proyecto.

---

## 6. Hallazgos (resumen por severidad)

### CRÍTICO (1)
- **H-001**: Wheel no incluía ui/panel.html → ✅ Corregido

### ALTO (2)
- **H-002**: pywebview sin versión fijada + thefuzz faltante → ✅ Corregido
- **H-003**: sys.path hack en __init__.py → ✅ Corregido

### MEDIO (4)
- **H-004**: SHA1 sin usedforsecurity=False → ✅ Corregido
- **H-005**: Imports muertos en producción → ✅ Corregido
- **H-006**: Parámetro tiempo_maximo ignorado → ✅ Corregido
- **H-010**: config_local import silencioso → 📋 Propuesto

### BAJO (6)
- **H-007**: Python 3.11+ en BASELINE.md → ✅ Corregido
- **H-008**: num_ctx 4096 en BASELINE.md → ✅ Corregido
- **H-009**: thefuzz faltante en requirements.in → ✅ Corregido
- **H-011**: Imports no usados en tests → ✔️ Aceptado
- **H-012**: Vulnerabilidades pip/urllib3 → ✔️ Aceptado
- **H-013**: Formato deprecated de licencia → ✅ Corregido

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
| H-013 | `393f0f5` | pyproject.toml | — |
| H-014 | `96a4355` | tests/test_auditoria.py | 16 pruebas nuevas |

---

## 8. Plan de Acción: Propuestas Pendientes

### H-010 — config_local import silencioso
**Prioridad:** Media
**Criterio de corrección:** Implementar validación de la fuente del config_local o reemplazarlo
por variables de entorno exclusivamente.
**Riesgo residual:** Bajo (el archivo está en .gitignore, requiere acceso local al sistema de archivos).

### Medianas de latencia en vivo
**Prioridad:** Media
**Criterio de corrección:** Completar el protocolo de la sección 5 de BASELINE.md con una sesión
de 10 turnos de voz y actualizar las celdas pendientes.

---

## 9. Lo que No Se Pudo Verificar y Por Qué

| Elemento | Razón |
|----------|-------|
| Medianas de latencia en vivo (TTFA, STT, LLM) | Requiere sesión de voz con micrófono activo |
| eval_tools.py (16/17 del BASELINE) | Requiere Ollama daemon activo con modelo descargado |
| Edge-TTS funcional | Requiere conexión a internet a servidores Microsoft |
| CI en GitHub Actions | No se verificó el resultado del pipeline en la rama |
| Importación de cada módulo sin Ollama ni ventana | Los mocks de conftest.py ya cubren este escenario |

---

## 10. Riesgos Residuales y Recomendaciones

1. **config_local.py (H-010):** Considerar migrar a variables de entorno exclusivamente.
2. **Reglas silenciadas de ruff:** Los 59 avisos en tests/ son deuda técnica aceptada.
   Recomendación: limpiar progresivamente y reducir la lista de `ignore` en pyproject.toml.
3. **pip y urllib3 desactualizados (H-012):** Actualizar pip y urllib3 en el venv regularmente.
4. **Bandit Low findings (14):** Los `except: pass` en código de limpieza (voz.py, interfaz.py)
   son patrones defensivos justificados. Los subprocess en herramientas.py usan allowlist.
5. **Concurrencia:** El estado compartido entre el hilo de voz y pywebview
   (`detener`, `contexto`, `api_js`) se gestiona con eventos y reasignación atómica de listas.
   No se detectaron data races, pero sería recomendable documentar las garantías de thread-safety.

---

## 11. Métricas Antes y Después

| Métrica | Antes | Después | Δ |
|---------|-------|---------|---|
| Tests pasando | 188 | **205** | +17 |
| Tests fallando | 0 | 0 | = |
| Avisos ruff (config actual) | 0 | 0 | = |
| Bandit High | 1 | **0** | -1 |
| Bandit Low | 14 | 14 | = |
| Vulture resultados | 4 | 1 | -3 |
| Archivos en wheel | 16 | **18** | +2 |
| Hallazgos abiertos CRÍTICO | 1 | **0** | -1 |
| Hallazgos abiertos ALTO | 2 | **0** | -2 |

---

## 12. Aspectos Bien Resueltos que No Deben Tocarse

1. **Allowlist de aplicaciones (MAPA_APLICACIONES):** Diseño sólido con `shutil.which` + `subprocess.Popen(shell=False)`. No usar `shell=True` ni `cmd /c`.
2. **Envoltura de resultados de herramientas (`envolver_resultado_tool`):** Truncado a 1500 chars con cabecera anti-inyección. Eficaz contra prompt injection indirecta.
3. **SYSTEM_PROMPT:** La directiva de solo lectura para `<datos_herramienta>` es una buena defensa en profundidad.
4. **Centinela de wake word (percepcion.py):** Mecanismo estable con Whisper tiny.en + fuzzy matching. Zona protegida respetada.
5. **Recorte de contexto (conversacion.py):** Lógica pura sin I/O, elimina mensajes `tool` huérfanos. Bien diseñado.
6. **Caché incremental RAG (memoria_rag.py):** IndexIDMap2 con caché de manifiesto por SHA1. Diseño robusto.
7. **Sanitización de nombres de archivo (memoria.py):** Prevención de path traversal y nombres reservados de Windows.
8. **Panel SENTINEL offline:** Sin dependencias de CDN, JS seguro vía `json.dumps()`, `_eval` con manejo de errores.
9. **Streaming TTS por frases (voz.py):** Productor/consumidor con cola bounded y centinela None.
10. **Registro único de herramientas (registro.py):** Single source of truth con decorador `@herramienta`.

---

## Información de Cierre

- **Hash final:** (pendiente de publicación)
- **Enlace a la rama:** https://github.com/DAHL13/JinxAS/compare/main...auditoria-profunda
- **Estado del CI:** No verificado
