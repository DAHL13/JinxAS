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

---

## H-017 — Concurrencia en panel y reproducción de audio

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/interfaz.py, jinxas/__main__.py, jinxas/percepcion.py, jinxas/voz.py |
| **Condición** | Emergency Flush no purgaba de inmediato la memoria compartida ni cancelaba la escucha centinela; `repetir_audio_ui` lanzaba hilos concurrentes que solapaban audio con el bucle de voz principal. |
| **Criterio** | C2 (ISO 25010 — Fiabilidad y Tolerancia a Fallos), C3 (CWE-362 Concurrency Race Conditions) |
| **Causa** | Falta de tupla de eventos de interrupción en `esperar_palabra_activacion` y ausencia de mutex en `reproducir_voz`. |
| **Efecto** | Audios solapados en parlantes y retención de memoria residual tras presionar Flush. |
| **Severidad** | **ALTO** |
| **CWE** | CWE-362 |
| **En palabras simples** | Si pulsabas Flush o Repetir audio, la voz podía sonar dos veces a la vez o recordar cosas que acababas de borrar. Ahora el audio y la memoria se coordinan con cerrojos y eventos de parada inmediata. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `dbdf313` | Prueba: `tests/test_h017_panel_audio.py` |

---

## H-018 — Integridad del índice FAISS y caché RAG ante bloqueos y fallos parciales

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/memoria_rag.py |
| **Condición** | La escritura de `indice.faiss` y `manifiesto.json` no era atómica; ante un fallo de disco o apagado el índice quedaba corrupto. Además, el hash SHA-1 de cada archivo se recalculaba sin necesidad en cada comprobación, y si fallaba `ntotal` el sistema se desfasaba. |
| **Criterio** | C2 (ISO 25010 — Fiabilidad e Integridad de Datos) |
| **Causa** | Falta de escritura en archivo temporal con reemplazo atómico (`os.replace`) y falta de comprobación lazy con `mtime`/`size`. |
| **Efecto** | Corrupción silenciosa del índice vectorial y latencia innecesaria en CPU. |
| **Severidad** | **ALTO** |
| **En palabras simples** | Si el programa se cerraba a mitad de guardar las notas en la base de datos de búsqueda, el índice se rompía. Ahora se guarda en un archivo temporal seguro y solo se actualiza si el archivo realmente cambió en disco. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `7693082` | Prueba: `tests/test_h018_rag_integridad.py` |

---

## H-019 — Truncado de salida de herramientas y gestión de presupuesto de contexto en LLM

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/config.py, jinxas/__main__.py, jinxas/cerebro.py, jinxas/memoria_rag.py |
| **Condición** | El truncado de 1500 caracteres cortaba notas RAG legítimas de 3 fragmentos (~2700 chars). `LLM_OPCIONES` en `config.py` fijaba `num_ctx: 2048` y `num_predict: 160`, insuficiente para 3 fragmentos de 900 caracteres. No había advertencia al saturar el contexto. |
| **Criterio** | C1 (Alineación con BASELINE.md), C2 (ISO 25010 — Adecuación Funcional) |
| **Causa** | Desajuste histórico entre la configuración de contexto y el presupuesto de caracteres de tools. |
| **Efecto** | El asistente recibía respuestas fragmentadas o incompletas de notas de Obsidian, rompiendo la capacidad de síntesis del LLM. |
| **Severidad** | **ALTO** |
| **En palabras simples** | Cuando el asistente buscaba en tus notas, recortaba la información a la mitad porque el límite era muy chico. Ahora el espacio se duplicó a 4096 tokens y el asistente puede leer notas completas sin desbordar la memoria. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `dfae17e` | Prueba: `tests/test_h019_truncados.py` |

---

## H-020 — Falsos positivos en detección de palabra de activación del Centinela

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/config.py, jinxas/percepcion.py |
| **Condición** | Con umbral de fuzzy matching en 80, palabras monosilábicas o comunes en inglés/español como "links", "sinks", "think" o tokens cortos activaban falsamente a Jinx. |
| **Criterio** | C2 (ISO 25010 — Usabilidad y Fiabilidad) |
| **Causa** | Umbral difuso demasiado permisivo (80%) y comparación sin filtrar tokens de longitud < 3 letras. |
| **Efecto** | El asistente se despertaba espontáneamente por ruido ambiental o palabras no dirigidas a él. |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Jinx se activaba sola cuando alguien decía palabras parecidas como "think" o "links". Subimos la exigencia de coincidencia a 90% y descartamos palabras de 1 o 2 letras para que solo despierte cuando realmente la llamas. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `cf6d476` | Prueba: `tests/test_h020_wakeword.py` |

---

## H-021 — Exposición de contenido sensible de usuario en registros de logging a nivel INFO

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/percepcion.py |
| **Condición** | Transcripciones completas de voz del usuario y palabras reconocidas por el centinela se emitían a nivel `INFO` en `logs/jinx.log`. |
| **Criterio** | C3 (OWASP LLM06: Sensitive Information Disclosure, CWE-532) |
| **Causa** | Niveles de log no diferenciados entre metadatos y contenido en percepción. |
| **Efecto** | Los archivos de log almacenaban en texto claro todo lo dictado por el usuario frente al micrófono. |
| **Severidad** | **MEDIO** |
| **CWE** | CWE-532 |
| **En palabras simples** | Las cosas que decías por el micrófono quedaban escritas tal cual en los archivos de registro. Ahora solo se guardan detalles técnicos en modo normal, y el texto exacto solo se guarda si el usuario activa el modo de depuración avanzada (DEBUG). |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `eceda39` | Prueba: `tests/test_h021_logs_privacidad.py` |

---

## H-022 — Riesgo de Cross-Site Scripting (XSS) en panel SENTINEL por interpolación de innerHTML

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/ui/panel.html |
| **Condición** | La función JS `addLog` insertaba registros formateados mediante `innerHTML = ... + content`, permitiendo la inyección de código HTML/JS si un log contenía etiquetas no escapadas. |
| **Criterio** | C3 (OWASP Top 10 / CWE-79 Cross-Site Scripting) |
| **Causa** | Uso de concatenación directa de cadenas HTML con datos no sanitizados en la interfaz. |
| **Efecto** | Potencial ejecución de scripts maliciosos en el motor web de Edge WebView2 ante logs malformados. |
| **Severidad** | **MEDIO** |
| **CWE** | CWE-79 |
| **En palabras simples** | La consola visual de la ventana usaba una técnica que permitía que texto con código malicioso pudiera ejecutarse dentro de la ventana. Se cambió por una técnica segura que trata todo el texto como letras planas sin interpretar código. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `830d5d6` | Prueba: `tests/test_h022_panel.py` |

---

## H-023 — Fallo al abrir navegadores Edge y Chrome en Windows vía App Paths

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/config.py, jinxas/herramientas.py |
| **Condición** | `abrir_aplicacion` resolvía `exe:msedge` y `exe:chrome` con `shutil.which`. En Windows, los navegadores no suelen estar en el PATH global sino en el registro de Windows (App Paths), provocando un fallo "No encontré navegador instalada". |
| **Criterio** | C2 (ISO 25010 — Compatibilidad y Adecuación Funcional en Windows) |
| **Causa** | Falta de soporte de resolución nativa vía ShellExecute para aplicaciones registradas en App Paths. |
| **Efecto** | El usuario no podía abrir Microsoft Edge ni Google Chrome por comando de voz. |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Cuando le pedías abrir Edge o Chrome, Windows decía que no los encontraba porque no estaban en su lista básica de programas. Ahora usa el mecanismo nativo de Windows (ShellExecute) que sabe exactamente dónde están instalados los navegadores. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `56f01bc` | Prueba: `tests/test_h023_abrir_navegadores.py` |

---

## H-024 — Nombres de dispositivos reservados de Windows con extensiones no prefijados

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/memoria.py |
| **Condición** | `_normalizar_nombre_archivo` solo evaluaba el nombre exacto sin considerar que en Windows el nombre reservado es el segmento previo al primer punto (`CON.md`, `nul.txt`, `aux.notas`, `COM1.md`). |
| **Criterio** | C2 (ISO 25010 — Fiabilidad y Robustez en Windows), CWE-22 / CWE-706 |
| **Causa** | Verificación estricta de igualdad en lugar de extraer el radical antes del delimitador `.`. |
| **Efecto** | Intentar guardar notas con esos títulos causaba errores de I/O a nivel de kernel de Windows o fallos en el sistema de archivos. |
| **Severidad** | **ALTO** |
| **CWE** | CWE-706 |
| **En palabras simples** | En Windows no puedes crear archivos que se llamen `CON.md` o `nul.txt` porque son nombres que la computadora tiene reservados para su uso interno. Si el usuario dictaba una nota con ese título, fallaba; ahora el sistema le añade automáticamente el prefijo `nota ` para que se guarde sin problema. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `3b6d6cb` | Prueba: `tests/test_h024_nombres_reservados.py` |

---

## H-025 — Mejoras menores de ciclo de vida, dependencias y consistencia de UI

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/percepcion.py, jinxas/__main__.py, jinxas/config.py, jinxas/ui/panel.html, requirements.txt |
| **Condición** | Primer comando sufría retrasos por carga síncrona de Whisper; bucles de rondas de herramientas podían dejar `tool_calls` colgados sin respuesta al alcanzar el límite; `config_local.py` usaba importación dinámica innecesaria; botón en UI decía "Regenerar" cuando solo repetía audio; dependencia redundante `python-Levenshtein`. |
| **Criterio** | C2 (ISO 25010 — Eficiencia y Mantenibilidad), C4 (Dependencias limpias) |
| **Causa** | Falta de hilo de precarga en arranque y ajustes menores de arquitectura. |
| **Efecto** | Retardos innecesarios en primer turno y acumulación de advertencias. |
| **Severidad** | **BAJO** |
| **En palabras simples** | Ajustamos varios detalles pequeños: Whisper ahora se carga en silencio mientras se abre la ventana para responder más rápido, se saneó la memoria si el modelo pedía demasiadas acciones seguidas, y se eliminaron paquetes repetidos. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `cab7f53` | Prueba: `tests/test_h025_menores.py` |

---

## H-026 — Entorno de pruebas y CI desacoplado de dependencias reales

| Campo | Detalle |
|-------|---------|
| **Componente** | tests/conftest.py, requirements-dev.txt, .github/workflows/ci.yml, tests/test_rag_faiss_real.py |
| **Condición** | Mocks incondicionales de `faiss` y `thefuzz` en CI impedían detectar fallos reales de indexación o coincidencia fonética. Faltaba escaneo automatizado de seguridad en el pipeline de GitHub Actions. |
| **Criterio** | C2 (ISO 25010 — Calidad de Pruebas y Fiabilidad), C3 (Seguridad en Pipeline) |
| **Causa** | Configuración de pruebas orientada a mocks sin fallback a librerías instaladas. |
| **Efecto** | Falsa sensación de cobertura si las librerías reales cambiaban de comportamiento. |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Las pruebas usaban simuladores en lugar de las librerías reales de búsqueda matemática. Ahora se instalaron las librerías reales y se agregaron escáneres automáticos de seguridad en GitHub para revisar el código cada vez que se sube un cambio. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `de671da` | Prueba: `tests/test_rag_faiss_real.py` |

---

## H-028 — Wake word: variantes reales y diagnóstico de casi-coincidencias

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/config.py, jinxas/percepcion.py |
| **Condición** | Con umbral 90 el centinela no activaba ante transcripciones plausibles como "jynx", "ginx", "gynx", "jinxe" o "jinex", y no existía telemetría de casi-coincidencias para diagnosticar falsos negativos. |
| **Criterio** | C2 (ISO 25010 — Usabilidad y Fiabilidad de Percepción) |
| **Causa** | Lista reducida de variantes explícitas y ausencia de métrica diagnóstica en nivel DEBUG. |
| **Efecto** | Falta de activación ante pronunciaciones válidas y carencia de visibilidad técnica ante palabras cercanas. |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Si el reconocedor entendía "jynx" o "ginx" en lugar de "jinx", el asistente no respondía. Se añadieron esas variantes (verificando que no activen falsos positivos) y se registró un log en DEBUG cuando casi coincide. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `1ae8665` | Prueba: `tests/test_h028_wakeword.py` |

---

## H-029 — Robustez del RAG (manifiesto, escrituras atómicas, concurrencia y notas vacías)

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/memoria_rag.py |
| **Condición** | Fallo de I/O en `_guardar_manifiesto` abortaba la publicación del índice en memoria; `_escritura_atomica` creaba archivos vacíos para mocks; existía ventana de carrera en `_reindex_pendiente`; vaciar notas dejaba IDs viejos en el manifiesto causando reconstrucciones innecesarias en reinicios. |
| **Criterio** | C2 (ISO 25010 — Fiabilidad, Tolerancia a Fallos e Integridad de Datos) |
| **Causa** | Falta de captura defensiva en serialización de manifiesto, cerrojo único sin cerrojo auxiliar de flag y omisión de limpieza de entradas en notas vacías. |
| **Efecto** | Pérdida de búsquedas semánticas en la sesión o descarte innecesario del caché al reiniciar. |
| **Severidad** | **ALTO** |
| **En palabras simples** | Si fallaba el guardado del manifiesto en disco, el asistente dejaba de buscar notas en esa sesión. Además, vaciar una nota provocaba que al reiniciar se recalculase todo desde cero. Ahora es completamente robusto y tolerante a fallos. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `deaf45b` | Prueba: `tests/test_h029_rag_robustez.py` |

---

## H-030 — Carga única y segura de modelos Whisper en memoria

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/percepcion.py |
| **Condición** | `esperar_palabra_activacion` cargaba `_MODELO_CENTINELA` sin `_LOCK_MODELOS`, compitiendo con `precargar_modelos()` y provocando doble carga en memoria; `precargar_modelos()` retenía un cerrojo unificado prolongado. |
| **Criterio** | C2 (ISO 25010 — Eficiencia y Concurrencia segura), CWE-362 |
| **Causa** | Falta de getter thread-safe con doble comprobación para el centinela y cerrojo monolítico compartido. |
| **Efecto** | Consumo duplicado de memoria RAM y CPU al arrancar el asistente si el usuario hablaba de inmediato. |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Si el usuario hablaba nada más abrir el programa, Whisper podía cargarse dos veces en la memoria. Se implementó una carga protegida con cerrojo para garantizar una única instancia. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `4ac4652` | Prueba: `tests/test_h030_modelos.py` |

---

## H-031 — Mensaje coherente al agotar rondas de herramientas

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/config.py, jinxas/__main__.py |
| **Condición** | En modo no-streaming, al agotarse `MAX_RONDAS_TOOLS` con `tool_calls` pendientes, el asistente respondía `"Listo."` a pesar de no haber completado la acción solicitada. |
| **Criterio** | C1 (ISO 25010 — Exactitud y Veracidad Funcional) |
| **Causa** | Fallback a `"Listo."` cuando `content` venía vacío en respuestas truncadas por límite de pasos. |
| **Efecto** | Confirmación engañosa de acciones que no fueron completadas. |
| **Severidad** | **MEDIO** |
| **En palabras simples** | Si el asistente alcanzaba el límite de herramientas, decía "Listo" como si hubiera terminado la tarea. Ahora informa transparentemente que no pudo completar la acción debido al límite de pasos. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido — commit `c70e014` | Prueba: `tests/test_h031_limite_rondas.py` |

---

## H-032 — Prueba de flush de punta a punta y saneamiento de documentación

| Campo | Detalle |
|-------|---------|
| **Componente** | jinxas/__main__.py, docs/, CHANGELOG.md, pyproject.toml, jinxas/__init__.py |
| **Condición** | Manejo de eventos del panel (`evento_reinicio`, `evento_regenerar`) incrustado dentro del bucle de voz sin prueba unitaria aislada; descripciones inexactas de H-017 y presencia de rutas locales y métricas sin verificar. |
| **Criterio** | C2 (ISO 25010 — Mantenibilidad y Calidad de Pruebas), C5 (Documentación Verificable) |
| **Causa** | Acoplamiento de la lógica de eventos en el cuerpo del bucle de voz secundario. |
| **Efecto** | Imposibilidad de probar de forma aislada la purga de contexto y afirmaciones no sustentadas en la documentación. |
| **Severidad** | **BAJO** |
| **En palabras simples** | Se extrajo la función de eventos del panel para probar directamente el botón de vaciar memoria y repetir audio, y se corrigieron todos los reportes técnicos con cifras reales y verificadas. |
| **Decisión** | Corregir |
| **Estado** | ✅ Corregido | Prueba: `tests/test_h032_eventos_panel.py` |

