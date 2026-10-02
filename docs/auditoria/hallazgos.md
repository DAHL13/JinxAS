# Hallazgos de Auditoría — JinxAS v0.5.0

## Resumen por severidad

| Severidad | Total | Corregidos | Propuestos | Aceptados |
|-----------|-------|------------|------------|-----------|
| CRÍTICO   | 1     | 1          | 0          | 0         |
| ALTO      | 2     | 2          | 0          | 0         |
| MEDIO     | 5     | 5          | 0          | 0         |
| BAJO      | 7     | 7          | 0          | 0         |
| **Total** | **15**| **15**     | **0**      | **0**     |

---

## H-001 — El wheel no incluye ui/panel.html

| Campo | Detalle |
|-------|---------|
| **Componente** | pyproject.toml, ui/panel.html |
| **Condición** | El wheel generado no incluía `ui/panel.html`, archivo necesario para la GUI SENTINEL. `pyproject.toml` solo incluía `jinxas*` y `ui/` estaba fuera del paquete. |
| **Criterio** | C4 (PEP 517/621), C2 (ISO 25010 — portabilidad, funcionalidad) |
| **Causa** | `[tool.setuptools.packages.find]` con `include = ["jinxas*"]` solo empaqueta módulos Python. |
| **Efecto** | Al instalar desde wheel o PyPI, la ventana SENTINEL no se abre → el asistente no funciona para el usuario objetivo. |
| **Recomendación** | Mover `panel.html` dentro del paquete Python y actualizar las referencias. |
| **Evidencia** | E1 — `python -m build --wheel` y listado del contenido confirman ausencia. |
| **Probabilidad** | Alta | **Impacto** | Alto |
| **Severidad** | **CRÍTICO** |
| **CWE / ISO** | ISO 25010 — Portabilidad, Adecuación funcional |
| **En palabras simples** | Si alguien instala JinxAS con `pip install`, la ventana del asistente no aparece porque le falta el archivo HTML. Sin ventana, el programa no sirve. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `cbe5691` |
| **Prueba asociada** | `tests/test_h001.py` |

---

## H-002 — pywebview sin versión fijada en requirements.txt

| Campo | Detalle |
|-------|---------|
| **Componente** | requirements.txt |
| **Condición** | `pywebview` aparecía sin pin de versión (línea 67). `thefuzz` faltaba. |
| **Criterio** | C4 (PEP 517/621), C2 (ISO 25010 — fiabilidad, compatibilidad) |
| **Causa** | Omisión al generar el requirements.txt fijado. |
| **Efecto** | La instalación puede traer versiones incompatibles de pywebview. La ausencia de thefuzz causa ImportError al importar percepcion.py. |
| **Evidencia** | E1 — `pip freeze` muestra pywebview==6.2.1 y thefuzz==0.22.1 instalados pero no fijados. |
| **Probabilidad** | Alta | **Impacto** | Alto |
| **Severidad** | **ALTO** |
| **En palabras simples** | Si no fijas las versiones, un `pip install` futuro puede traer una versión que rompa algo. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `022428d` |

---

## H-003 — __init__.py manipula sys.path (antipatrón)

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/__init__.py |
| **Condición** | `sys.path.insert(0, _pkg_dir)` inyectaba el directorio del paquete en sys.path. |
| **Criterio** | C4 (PEP 517/621), C2 (ISO 25010 — mantenibilidad) |
| **Causa** | Legado de cuando los módulos vivían en el directorio raíz. |
| **Efecto** | Puede causar conflictos de importación con módulos del mismo nombre en otros paquetes. |
| **Evidencia** | E2 — trazado estático del código en __init__.py:9-12 |
| **Probabilidad** | Media | **Impacto** | Alto |
| **Severidad** | **ALTO** |
| **En palabras simples** | Modificar la lista de carpetas donde Python busca módulos puede hacer que importe el archivo equivocado. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `b78e522` |

---

## H-004 — hashlib.sha1() sin usedforsecurity=False

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/memoria_rag.py:186 |
| **Condición** | `hashlib.sha1()` sin marcar como no-seguridad. Bandit B324 / CWE-327. |
| **Criterio** | C3 (OWASP/CWE-327), C2 (ISO 25010 — seguridad) |
| **Causa** | Omisión; SHA1 se usa para detectar cambios de archivo, no para seguridad. |
| **Efecto** | Falso positivo de seguridad en análisis estático. En entornos FIPS, podría fallar. |
| **Evidencia** | E1 — bandit detecta B324 severity High. |
| **Probabilidad** | Baja | **Impacto** | Medio |
| **Severidad** | **MEDIO** |
| **CWE** | CWE-327 |
| **En palabras simples** | Python necesita saber que este hash no es para seguridad, o podría bloquearlo en ciertos sistemas. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `580f929` |

---

## H-005 — Imports muertos en código de producción

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/__main__.py, jinxas/percepcion.py |
| **Condición** | `consultar_boveda`, `InterfazAPI` y `PROMPT_INICIAL_WHISPER` importados pero nunca usados. |
| **Criterio** | C2 (ISO 25010 — mantenibilidad) |
| **Causa** | Evolución del código sin limpieza de imports. |
| **Efecto** | Confusión al leer el código; carga innecesaria de símbolos. |
| **Evidencia** | E1 — vulture y ruff --select F401 lo confirman. |
| **Probabilidad** | Alta | **Impacto** | Bajo |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Hay `import`s que no se usan, lo que ensucia el código sin aportar nada. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `80024a0` |

---

## H-006 — Parámetro tiempo_maximo ignorado en escuchar_y_transcribir

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/percepcion.py:210-243 |
| **Condición** | El parámetro `tiempo_maximo` se acepta pero se usa `config.TIEMPO_MAXIMO_ESCUCHA` directamente. |
| **Criterio** | C2 (ISO 25010 — adecuación funcional) |
| **Causa** | Al migrar a la nueva estructura, se olvidó conectar el parámetro. |
| **Efecto** | El caller no puede personalizar el timeout; la API es engañosa. |
| **Evidencia** | E2 — trazado estático: línea 212 (parámetro), línea 242 (usa config directo). |
| **Probabilidad** | Media | **Impacto** | Medio |
| **Severidad** | **MEDIO** |
| **En palabras simples** | La función dice que acepta un tiempo máximo, pero lo ignora y siempre usa el valor de config. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `c26545f` |

---

## H-007 — BASELINE.md dice Python 3.11+ (código requiere 3.12+)

| Campo | Detalle |
|-------|---------|
| **Componente** | docs/BASELINE.md:19 |
| **Condición** | Dice `Python: 3.11+` pero pyproject.toml exige `>=3.12`. |
| **Criterio** | C1 (documentación contradice código) |
| **Evidencia** | E2 — BASELINE.md:19 vs pyproject.toml:10 |
| **Severidad** | **BAJO** |
| **En palabras simples** | La documentación dice una versión de Python y el proyecto exige otra. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `0e0b7f4` |

---

## H-008 — BASELINE.md dice num_ctx: 4096 (config tiene 2048)

| Campo | Detalle |
|-------|---------|
| **Componente** | docs/BASELINE.md:60 |
| **Condición** | Dice `num_ctx: 4096, num_thread: 6` pero config.py tiene `num_ctx: 2048, num_predict: 160`. |
| **Criterio** | C1 (documentación contradice código) |
| **Evidencia** | E2 — BASELINE.md:60 vs config.py:53 |
| **Severidad** | **BAJO** |
| **En palabras simples** | Los números que aparecen en el documento no coinciden con los del código real. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `0e0b7f4` |

---

## H-009 — thefuzz faltaba en requirements.in

| Campo | Detalle |
|-------|---------|
| **Componente** | requirements.in |
| **Condición** | `thefuzz` es una dependencia directa (percepcion.py:7) pero faltaba en requirements.in. |
| **Criterio** | C4 (empaquetado) |
| **Severidad** | **BAJO** |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `022428d` |

---

## H-010 — config_local import silencioso podría ejecutar código arbitrario

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/config.py:40-44 |
| **Condición** | `import config_local` se ejecutaba al importar config.py desde cualquier ruta de sys.path. |
| **Criterio** | C3 (OWASP — Exceso de agencia), C2 (seguridad) |
| **Causa** | Diseño para personalización local sin confinamiento de ruta. |
| **Efecto** | Riesgo teórico de ejecución de código si el atacante coloca un archivo en PYTHONPATH. |
| **Evidencia** | E2 — trazado estático de config.py:40-44. |
| **Probabilidad** | Baja | **Impacto** | Medio |
| **Severidad** | **MEDIO** |
| **CWE** | CWE-94 (Improper Control of Code Generation) |
| **En palabras simples** | El programa intentaba importar un archivo externo. Ahora se confina estrictamente a la ruta de la base de la aplicación con importlib. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `2409137` |

---

## H-011 — Imports no usados y variables muertas en tests

| Campo | Detalle |
|-------|---------|
| **Componente** | tests/*.py, jinxas/*.py, pyproject.toml |
| **Condición** | 59 avisos de ruff con reglas silenciadas (F401, F841, E402, E741, F541). |
| **Criterio** | C2 (ISO 25010 — mantenibilidad) |
| **Severidad** | **BAJO** (agrupado) |
| **En palabras simples** | Se depuraron todos los imports y variables no usadas, endureciendo ruff al retirar F401, F841, F541 y E741 del ignore. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `ad328bb` |

---

## H-012 — Vulnerabilidades en urllib3 del requirements.txt

| Campo | Detalle |
|-------|---------|
| **Componente** | requirements.txt (urllib3==2.7.0) |
| **Condición** | pip-audit detectó 3 vulnerabilidades en urllib3 2.7.0 (PYSEC-2026-4175/6/7). |
| **Criterio** | C3 (seguridad de dependencias) |
| **Severidad** | **BAJO** |
| **En palabras simples** | Se actualizó el pin a urllib3==2.8.0 solventando las vulnerabilidades reportadas. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `589c07c` |

---

## H-013 — Formato deprecated de licencia en pyproject.toml

| Campo | Detalle |
|-------|---------|
| **Componente** | pyproject.toml:11 |
| **Condición** | `license = { text = "MIT" }` está deprecated según PEP 639 desde setuptools≥77. |
| **Criterio** | C4 (PEP 621/639) |
| **Severidad** | **BAJO** |
| **En palabras simples** | El formato de la licencia en la configuración se estandarizó a cadena SPDX. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `393f0f5` |

---

## H-015 — Condición de carrera en ApiPanel con contexto compartido

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/interfaz.py: ApiPanel |
| **Condición** | El estado de `contexto` se compartía entre el hilo de voz y el hilo de la UI (pywebview) sin bloqueo sincronizado. |
| **Criterio** | C2 (ISO 25010 — fiabilidad), C3 (CWE-362 Concurrency Race Condition) |
| **Causa** | Falta de primitivas de sincronización en métodos de acceso JS → Python. |
| **Efecto** | Mutaciones simultáneas durante flush o repetición de audio podían causar inconsistencias de memoria. |
| **Severidad** | **MEDIO** |
| **CWE** | CWE-362 |
| **En palabras simples** | El botón de limpiar memoria de la ventana podía chocar con la voz del asistente. Ahora un cerrojo (Lock) protege el historial. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `aeb52e7` |

---

## H-016 — Falta de resiliencia ante excepciones imprevistas en clima y fallos

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/herramientas.py: obtener_clima |
| **Condición** | `obtener_clima` solo capturaba `RequestException`, pudiendo escapar otras excepciones de red o socket. Faltaba suite formal de inyección de fallos. |
| **Criterio** | C2 (ISO 25010 — fiabilidad y tolerancia a fallos) |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Si ocurría un fallo de red inesperado al pedir el clima, podía fallar feo. Ahora captura cualquier excepción y hay 11 pruebas de resiliencia. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commits `43fb721` y `31efa64` |
