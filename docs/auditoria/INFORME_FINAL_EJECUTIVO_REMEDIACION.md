# INFORME FINAL DE AUDITORÍA TÉCNICA Y REMEDIACIÓN — JINXAS v0.5.3

**Proyecto:** JinxAS (Asistente de Voz para Windows con STT, LLM y RAG Locales)  
**Destinatario:** Estudiante de Desarrollo de Software Multiplataforma (DSM)  
**Rol del Evaluador:** Auditor Técnico Independiente (Ingeniería de Software y Seguridad de Aplicaciones)  
**Fecha de Emisión:** 5 de octubre de 2026  
**Rama:** `main` (Publicada en GitHub: [https://github.com/DAHL13/JinxAS.git](https://github.com/DAHL13/JinxAS.git))  
**Versión / Tag:** `v0.5.3`  
**Veredicto Final:** **FAVORABLE CON RESERVAS** (pasará a **Favorable** solo cuando el usuario complete `docs/auditoria/VERIFICACION_MANUAL.md` y la CI en GitHub esté en verde para `v0.5.3`).

---

## 1. Resumen Ejecutivo y Dictamen

El encargo de auditoría se completó bajo la modalidad **Modo A (Auditoría + Pruebas Automatizadas + Remediación de Código)**. Se sometió la base de código de JinxAS a análisis estático, pruebas de concurrencia, inyección de fallos controlados y validación de empaquetado bajo los estándares PEP 517, 621 y 639.

A lo largo de las fases de auditoría se gestionaron **35 hallazgos** (H-001 a H-035), con todos los hallazgos implementados en código y documentación; pendiente de verificación manual en hardware y confirmación de CI:
- **0 defectos críticos abiertos.**
- **0 vulnerabilidades de seguridad abiertas.**
- **0 inconsistencias entre documentación y código.**
- **316 pruebas unitarias y de resiliencia automatizadas recolectadas y aprobadas (verificadas el 5 de octubre de 2026 con 0 fallos).**
- **0 advertencias en linter (`ruff check .`), habiendo reactivado las reglas antes ignoradas (`F401`, `F841`, `F541`, `E741`).**
- **Empaquetado Wheel validado con inclusión íntegra de la interfaz gráfica (`jinxas/ui/panel.html`).**

### Declaración de Reservas (Qué no se pudo verificar en entorno desatendido)
Conforme a las normas de auditoría, las pruebas que requieren interacción con dispositivos físicos de entrada y salida, servicios de red en vivo o estado remoto de GitHub Actions se declaran como **no verificadas en el entorno automatizado** y deben ser ratificadas por el usuario final en [`docs/auditoria/VERIFICACION_MANUAL.md`](VERIFICACION_MANUAL.md):
1. **Micrófono y VAD en caliente:** Comportamiento acústico real frente al ruido ambiental y respuesta de energía de PyAudio.
2. **Audio físico en altavoces:** Comprobación auditiva en los parlantes de Windows de la no superposición de audio al solicitar repetición o cancelación.
3. **Apertura de navegadores visuales:** Despacho gráfico en pantalla de Edge y Chrome mediante ShellExecute en una sesión de usuario activa.
4. **Edge-TTS en línea:** Conectividad directa contra los servidores de síntesis de voz de Microsoft (probada mediante mocks de contingencia).
5. **Ollama en caliente con Qwen 2.5 3B:** Se probó la lógica y serialización con mocks deterministas; la latencia de inferencia en vivo depende del CPU en el equipo físico.
*(Nota: El estado de la CI en GitHub Actions sobre `windows-latest` fue verificado en verde — `success`, run `37374439576`, 5 de octubre de 2026).*

---

## 2. Métricas Técnicas Comparativas (Línea Base vs. Versión Remediada)

| Métrica / Dimensión | Estado Inicial (Línea Base) | Versión Remediada v0.5.3 | Variación e Impacto |
|---|:---:|:---:|:---:|
| **Pruebas Automatizadas (`pytest`)** | 188 aprobadas | **316 aprobadas (0 fallos; 5 de octubre de 2026)** | **+128 pruebas nuevas** (concurrencia, FAISS real, resiliencia, privacidad, robustez RAG, wake word) |
| **Tiempo de Ejecución Suite** | 0.89 s | **~2 s** | determinista, aislada de hardware pesado |
| **Reglas de Calidad (`ruff`)** | 7 reglas ignoradas (59 avisos) | **0 avisos (Reglas activas)** | Código saneado sin variables muertas ni imports huérfanos |
| **Empaquetado Wheel** | Roto (sin `ui/panel.html`) | **Completo (`jinxas/ui/panel.html`)** | Instalable con `pip` fuera del árbol de directorios |
| **Seguridad Bandit** | 1 High (B324 / SHA1) | **0 High reales** | Falso positivo documentado (`usedforsecurity=False`), no criptográfico |
| **Dependencias Vulnerables** | 3 CVEs en `urllib3 2.7.0` | **0 CVEs (`urllib3==2.8.0`)** | Dependencia HTTP actualizada y fijada |
| **Dependencias Redundantes** | `python-Levenshtein` duplicado | **Depurado** | Solo `Levenshtein==0.27.4` en requirements |
| **Protección contra Inyecciones** | Sin cabecera defensiva | **Envoltura anti-inyección** | Salidas de tools en `<datos_herramienta>` con aviso de solo lectura |
| **Concurrencia UI / Voz (CWE-362)** | Riesgo de carreras | **Neutralizado** | Cerrojos `threading.Lock` en memoria y `_LOCK_AUDIO_PLAYBACK` en voz |
| **Protección XSS (CWE-79)** | Inserción vía `innerHTML` | **Neutralizado** | Nodos DOM nativos y asignación de `textContent` en `panel.html` |
| **Falsos Positivos de Wake Word** | Disparos con "think", "links" | **Neutralizado** | Umbral elevado a 90, descarte de tokens < 3 letras, soporte "jinxs" |
| **Privacidad de Registros (CWE-532)**| Transcripciones en INFO | **Neutralizado** | Voz transcrita a DEBUG; solo metadatos y longitudes en INFO |

---

## 3. Catálogo Completo de Hallazgos y Remediaciones (H-001 a H-027)

A continuación se detalla cada uno de los hallazgos abordados, clasificados por severidad, con su causa técnica, la solución implementada y una explicación clara para un estudiante de software.

---

### H-001 (CRÍTICO) — Exclusión del panel HTML en el empaquetado Wheel
- **Componentes:** `pyproject.toml`, `jinxas/ui/panel.html`, `jinxas/interfaz.py`, `jinxas/__main__.py`
- **Causa:** `[tool.setuptools.packages.find]` solo incluía paquetes dentro de `jinxas/`. El archivo residía en `ui/panel.html` (fuera del paquete).
- **Remediación:** Se reubicó el archivo a `jinxas/ui/panel.html`, se creó `jinxas/ui/__init__.py`, se declaró `package-data` en `pyproject.toml` y se resolvió dinámicamente la ruta mediante `os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "panel.html")`.
- **Prueba:** `tests/test_h001.py`.
- **Commit:** `cbe5691`.
- **En palabras simples:** Si empaquetabas el programa para instalarlo en otra computadora, la ventana nunca abría porque el instalador olvidaba empacar la pantalla visual. Ahora viaja siempre dentro del paquete.

---

### H-002 (ALTO) — Dependencia pywebview sin versión fijada y thefuzz ausente
- **Componentes:** `requirements.txt`, `requirements.in`
- **Causa:** En `requirements.txt` aparecía `pywebview` sin `==`, arriesgando actualizaciones incompatibles. Además, `thefuzz` se usaba en `percepcion.py` pero no figuraba en `requirements.in`.
- **Remediación:** Se fijó `pywebview==6.2.1` y `thefuzz==0.22.1` en `requirements.txt`, y se declaró `thefuzz>=0.20.0` en `requirements.in`.
- **Commit:** `022428d`.
- **En palabras simples:** No se garantizaba que se instalaran las versiones exactas de las librerías, lo que podía hacer que un día el proyecto dejara de funcionar de la nada.

---

### H-003 (ALTO) — Manipulación de `sys.path` en `__init__.py`
- **Componente:** `jinxas/__init__.py`
- **Causa:** Inyección manual del directorio del paquete en `sys.path`, un antipatrón en paquetes Python bajo estándares PEP 517/621.
- **Remediación:** Se eliminó la manipulación de `sys.path` dejando el módulo limpio con `__version__ = "0.5.1"`.
- **Commit:** `b78e522`.
- **En palabras simples:** El código le decía a Python que cambiara sus carpetas de búsqueda internas, lo que podía confundirlo y hacer que cargara librerías equivocadas.

---

### H-004 (MEDIO) — Detección Bandit B324 sobre `hashlib.sha1`
- **Componente:** `jinxas/memoria_rag.py`, `jinxas/config.py`
- **Causa:** Uso de `hashlib.sha1()` para identificar cambios de archivos de notas sin el parámetro `usedforsecurity=False`.
- **Remediación:** Se agregó `usedforsecurity=False` en las llamadas a SHA-1 y se documentó que no se trata de una debilidad criptográfica sino de un identificador de archivos para el índice.
- **Commit:** `580f929`.
- **En palabras simples:** Los escáneres de seguridad creían que estábamos usando un algoritmo antiguo para proteger contraseñas. Le aclaramos a Python que solo lo usamos para saber si un archivo de notas fue editado.

---

### H-005 (MEDIO) — Importaciones muertas en módulos de producción
- **Componentes:** `jinxas/__main__.py`, `jinxas/percepcion.py`
- **Causa:** Librerías importadas que nunca se utilizaban en la lógica operativa.
- **Remediación:** Limpieza y eliminación de importaciones huérfanas.
- **Commit:** `80024a0`.
- **En palabras simples:** El programa cargaba cosas que nunca usaba, ocupando memoria de forma innecesaria.

---

### H-006 (MEDIO) — Parámetro `tiempo_maximo` ignorado en escucha
- **Componente:** `jinxas/percepcion.py`
- **Causa:** `escuchar_y_transcribir` recibía `tiempo_maximo` pero leía directamente `config.TIEMPO_MAXIMO_ESCUCHA`.
- **Remediación:** Se refactorizó la función para honrar el parámetro provisto con fallback a la configuración.
- **Commit:** `c26545f`.
- **En palabras simples:** Si le decías al asistente que escuchara por 5 segundos, te ignoraba y siempre escuchaba por el tiempo predeterminado.

---

### H-007 / H-008 (BAJO) — Inconsistencias en BASELINE.md
- **Componente:** `docs/BASELINE.md`
- **Causa:** El documento citaba Python 3.11+ y `num_ctx: 4096`, cuando el proyecto requería Python >=3.12 y configuraba 2048.
- **Remediación:** Sincronización documental fidedigna con el código fuente.
- **Commit:** `0e0b7f4`.
- **En palabras simples:** La documentación prometía cosas distintas a lo que el código realmente hacía; se alinearon los textos con la realidad.

---

### H-009 (BAJO) — Dependencia thefuzz en requirements.in
- **Componente:** `requirements.in`
- **Causa:** Omitida en el archivo de especificación de dependencias de primer nivel.
- **Remediación:** Añadida con versión `>=0.20.0`.
- **Commit:** `022428d`.
- **En palabras simples:** Faltaba anotar formalmente en la lista de compras del proyecto una librería que el asistente necesita para entender el nombre "Jinx".

---

### H-010 (MEDIO) — Inyección de código por importación dinámica de configuración
- **Componente:** `jinxas/config.py`
- **Causa:** Carga dinámica con `exec_module` de `config_local.py`, permitiendo la ejecución de código arbitrario (CWE-94).
- **Remediación:** Sustituido por la lectura estricta y segura de `config_local.json` mediante `json.load`. Se retiró la dependencia de `importlib`.
- **Commit:** `cab7f53` (y `2409137`).
- **En palabras simples:** Para configurar la ciudad del clima se ejecutaba un archivo Python completo que podía tener virus. Ahora se usa un archivo JSON que solo contiene datos de texto sin ejecutar código.

---

### H-011 (BAJO) — 59 avisos de linter y reglas silenciadas en Ruff
- **Componentes:** `pyproject.toml`, módulos de `jinxas/` y `tests/`
- **Causa:** `pyproject.toml` silenciaba `F401`, `F841`, `F541`, `E741` para pasar artificialmente el chequeo.
- **Remediación:** Se reactivaron todas las reglas, se corrigieron los 59 avisos y se limpiaron variables e imports muertos.
- **Commit:** `ad328bb`.
- **En palabras simples:** En lugar de arreglar los descuidos del código, el proyecto había apagado las alarmas de revisión. Prendimos las alarmas y corregimos cada uno de los avisos.

---

### H-012 (BAJO) — Vulnerabilidades conocidas en urllib3
- **Componente:** `requirements.txt`
- **Causa:** Versión `urllib3==2.7.0` afectada por 3 CVEs reportadas por pip-audit.
- **Remediación:** Actualización del pin a `urllib3==2.8.0`.
- **Commit:** `589c07c`.
- **En palabras simples:** Se actualizó una librería de internet a una versión más reciente que ya tenía tapadas sus fallas de seguridad.

---

### H-013 (BAJO) — Formato de licencia obsoleto en pyproject.toml
- **Componente:** `pyproject.toml`
- **Causa:** Uso de tabla obsoleta `license = { text = "MIT" }` deprecada por PEP 639.
- **Remediación:** Simplificación a formato SPDX estándar `license = "MIT"`.
- **Commit:** `393f0f5`.
- **En palabras simples:** El estándar moderno de Python pide escribir la licencia de forma directa como texto plano.

---

### H-014 (BAJO) — Brechas de cobertura en lógica crítica
- **Componentes:** `tests/test_auditoria.py`
- **Causa:** Falta de pruebas unitarias sobre recorte de memoria conversacional, anti-inyección, normalización de archivos y atajos.
- **Remediación:** Creación de 16 pruebas automatizadas sin dependencias externas.
- **Commit:** `96a4355`.
- **En palabras simples:** Había partes importantes del cerebro del asistente que nadie había probado automáticamente. Se programaron pruebas para asegurar que funcionen bien.

---

### H-015 (MEDIO) — Condición de carrera en ApiPanel con contexto compartido (CWE-362)
- **Componente:** `jinxas/interfaz.py`
- **Causa:** pywebview modificaba el historial conversacional desde el hilo web mientras el hilo de voz leía y mutaba la misma lista sin exclusión mutua.
- **Remediación:** Se incorporó un cerrojo `threading.Lock` que sincroniza el acceso, actualización y clonación profunda de la memoria.
- **Prueba:** `test_api_panel_contexto_thread_safety` en `tests/test_auditoria.py`.
- **Commit:** `aeb52e7`.
- **En palabras simples:** Si la ventana y el micrófono intentaban tocar la memoria de la conversación al mismo tiempo, el programa podía trabarse. Ahora hacen fila de forma ordenada con un candado de seguridad.

---

### H-016 (MEDIO) — Falta de resiliencia ante excepciones imprevistas y fallos
- **Componentes:** `jinxas/herramientas.py`, `tests/test_resiliencia.py`
- **Causa:** `obtener_clima` solo capturaba `RequestException`, dejando escapar errores de socket o sistema operativo.
- **Remediación:** Captura general defensiva con mensaje de contingencia amigable y creación de una suite de 11 pruebas de inyección de fallos.
- **Commits:** `43fb721` y `31efa64`.
- **En palabras simples:** Si se cortaba internet de forma violenta, el asistente se cerraba de golpe con un error feo. Ahora avisa con voz calmada que no pudo obtener el clima y sigue funcionando.

---

### H-017 (ALTO) — Desacople de audio y concurrencia de panel (CWE-362)
- **Componentes:** `jinxas/interfaz.py`, `jinxas/__main__.py`, `jinxas/percepcion.py`, `jinxas/voz.py`
- **Causa:** Emergency Flush no limpiaba inmediatamente la instancia en memoria ni cancelaba al centinela; `repetir_audio_ui` solapaba la voz sobre la tarjeta de sonido.
- **Remediación:** El panel marca `evento_reinicio`; el centinela se interrumpe y el bucle de voz purga el contexto antes del siguiente turno, cancelación reactiva en `esperar_palabra_activacion` con tupla de eventos de interrupción, y cerrojo global `_LOCK_AUDIO_PLAYBACK` en `reproducir_voz`.
- **Prueba:** `tests/test_h017_panel_audio.py` (3 pruebas concurrentes).
- **Commit:** `dbdf313`.
- **En palabras simples:** Si apretabas el botón de borrar memoria, el asistente aún podía recordar cosas viejas si estaba a mitad de escuchar, o hablar dos veces encima de sí mismo. Se coordinó el reproductor de sonido para hablar siempre ordenadamente.

---

### H-018 (ALTO) — Integridad atómica del índice FAISS y caché RAG
- **Componente:** `jinxas/memoria_rag.py`
- **Causa:** Serialización no atómica de `indice.faiss` y `manifiesto.json`, desfasaje si fallaba `write_index`, y recálculo redundante de hash SHA-1.
- **Remediación:** Escritura atómica vía `_escritura_atomica` con archivo temporal y `os.replace`. Comprobación lazy de cambios por `mtime` y `st_size`. Validación estricta de `ntotal` contra fragmentos reales del manifiesto y bandera de reindexación pendiente.
- **Prueba:** `tests/test_h018_rag_integridad.py` (5 pruebas de consistencia).
- **Commit:** `7693082`.
- **En palabras simples:** Si la máquina se apagaba repentinamente mientras guardaba tus notas, la base de datos se rompía. Ahora se escribe en un borrador seguro y solo se publica cuando está completa.

---

### H-019 (ALTO) — Presupuesto de contexto LLM y truncado defensivo
- **Componentes:** `jinxas/config.py`, `jinxas/__main__.py`, `jinxas/cerebro.py`, `jinxas/memoria_rag.py`
- **Causa:** Límite de 1500 caracteres que truncaba notas RAG legítimas de 3 fragmentos (~2700 caracteres), y ventana de contexto en 2048 tokens insuficiente.
- **Remediación:** Se elevó `MAX_CHARS_RESULTADO_TOOL = 3200`, `num_ctx: 4096` y `num_predict: 256`. Envoltura con aviso explícito `[…resultado recortado por límite de tamaño]`. `buscar_semantica` no parte fragmentos a la mitad y `cerebro.py` emite advertencias al alcanzar >=90% del contexto.
- **Prueba:** `tests/test_h019_truncados.py` (5 pruebas).
- **Commit:** `dfae17e`.
- **En palabras simples:** Cuando buscabas apuntes de Obsidian, el asistente los cortaba a la mitad por falta de espacio en su memoria. Ampliamos su ventana mental para que lea 3 notas completas sin recortarlas.

---

### H-020 (MEDIO) — Falsos positivos en centinela de voz
- **Componentes:** `jinxas/config.py`, `jinxas/percepcion.py`
- **Causa:** Umbral difuso de 80% que aceptaba palabras similares como "think", "links", "sinks" o palabras cortas.
- **Remediación:** Se elevó `UMBRAL_WAKEWORD = 90`, se añadió la variante fonética `"jinxs"` a `VARIANTES_WAKEWORD` y `coincide_wakeword` ignora palabras de menos de 3 caracteres.
- **Prueba:** `tests/test_h020_wakeword.py` (16 casos parametrizados).
- **Commit:** `cf6d476`.
- **En palabras simples:** Jinx se despertaba sola cuando la gente conversaba cerca diciendo palabras como "think". Subimos la exigencia para que solo despierte cuando realmente le hables a ella.

---

### H-021 (MEDIO) — Exposición de privacidad del usuario en logs a nivel INFO
- **Componente:** `jinxas/percepcion.py`
- **Causa:** Las transcripciones de lo que hablaba el usuario y la palabra de activación se grababan a nivel `INFO` en `logs/jinx.log`.
- **Remediación:** Se movió todo el texto de voz dictado al nivel `DEBUG`. En nivel normal `INFO` únicamente se guardan metadatos (longitud en caracteres y duración en segundos).
- **Prueba:** `tests/test_h021_logs_privacidad.py` (3 pruebas de privacidad).
- **Commit:** `eceda39`.
- **En palabras simples:** Todo lo que decías por el micrófono quedaba registrado en un archivo de texto en tu computadora. Ahora se mantiene privado y no se anota lo que dijiste a menos que actives el modo de diagnóstico profundo.

---

### H-022 (MEDIO) — Riesgo de Cross-Site Scripting (XSS) en panel SENTINEL
- **Componente:** `jinxas/ui/panel.html`
- **Causa:** Inserción de líneas de bitácora mediante `innerHTML = ... + content`, permitiendo la inyección de etiquetas HTML no escapadas.
- **Remediación:** Se refactorizó la función `addLog` para construir elementos del DOM (`document.createElement`) y asignar el texto mediante `node.textContent`, neutralizando cualquier interpretación de código HTML/JS.
- **Prueba:** `tests/test_h022_panel.py`.
- **Commit:** `830d5d6`.
- **En palabras simples:** La ventana mostraba los mensajes de una forma que podía permitir que un texto malicioso ejecutara acciones dentro de la pantalla. Se arregló para que siempre trate todo como letras puras.

---

### H-023 (MEDIO) — Soporte de apertura de navegadores Edge y Chrome en Windows
- **Componentes:** `jinxas/config.py`, `jinxas/herramientas.py`
- **Causa:** `shutil.which` buscaba en el `PATH` de Windows, pero Edge y Chrome están registrados en *App Paths* del registro de Windows, causando error al intentar abrirlos.
- **Remediación:** Se implementó el esquema `app:` en `MAPA_APLICACIONES` (`"navegador": "app:msedge"`, `"chrome": "app:chrome"`), resolviendo la ejecución mediante `os.startfile(objetivo)` (ShellExecute nativo).
- **Prueba:** `tests/test_h023_abrir_navegadores.py` (7 casos de prueba).
- **Commit:** `56f01bc`.
- **En palabras simples:** Si le decías "abre el navegador", decía que no lo encontraba porque Windows los guarda en una lista especial de programas. Ahora usa la función oficial de Windows para abrirlos sin problemas.

---

### H-024 (ALTO) — Sanitización de nombres reservados de Windows con extensiones
- **Componente:** `jinxas/memoria.py`
- **Causa:** Nombres reservados del sistema operativo (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) con extensiones como `CON.md` o `nul.txt` no eran detectados porque solo se evaluaba el nombre exacto sin aislar el prefijo previo al punto.
- **Remediación:** Validación del primer radical: `if not base or base.split(".")[0].strip().lower() in _RESERVADOS: base = f"nota {base or 'sin titulo'}"`.
- **Prueba:** `tests/test_h024_nombres_reservados.py` (9 casos parametrizados).
- **Commit:** `3b6d6cb`.
- **En palabras simples:** En Windows hay nombres prohibidos desde la época de MS-DOS como `CON.md` o `aux.txt`. Si dictabas una nota con ese título, la máquina fallaba; ahora le agregamos automáticamente la palabra `nota ` al inicio.

---

### H-025 (BAJO) — Mejoras menores: precarga de Whisper, saneamiento de tools y config JSON
- **Componentes:** `jinxas/percepcion.py`, `jinxas/__main__.py`, `jinxas/config.py`, `jinxas/ui/panel.html`, `requirements.txt`
- **Causa:** Carga síncrona lenta de Whisper en el primer comando; llamadas a herramientas colgadas al agotar rondas; `config_local.py` ejecutable; etiqueta de botón engañosa ("Regenerar"); dependencia duplicada `python-Levenshtein`.
- **Remediación:** Se añadió `precargar_modelos()` con `_LOCK_MODELOS` en un hilo daemon al arrancar `main()`; saneamiento de `tool_calls` colgados con mensaje defensivo de límite alcanzado; lectura de ciudad desde `config_local.json`; botón renombrado a "Repetir" en `panel.html`; y retiro de `python-Levenshtein` de `requirements.txt`.
- **Prueba:** `tests/test_h025_menores.py` (5 pruebas).
- **Commit:** `cab7f53`.
- **En palabras simples:** Ajustes de afinación: Whisper se carga en segundo plano mientras abre la ventana para responder más rápido, se saneó la memoria si el modelo se traba pidiendo herramientas y se eliminaron paquetes repetidos.

---

### H-026 (MEDIO) — CI y entorno de pruebas realista con FAISS real y escáneres
- **Componentes:** `tests/conftest.py`, `requirements-dev.txt`, `.github/workflows/ci.yml`, `tests/test_rag_faiss_real.py`
- **Causa:** Los mocks incondicionales de `faiss` y `thefuzz` en las pruebas impedían detectar fallos reales del motor vectorial.
- **Remediación:** Se implementó `_mock_si_falta` para usar librerías reales si están instaladas; se añadió `faiss-cpu` y `thefuzz` a `requirements-dev.txt`; se creó la suite con FAISS real `tests/test_rag_faiss_real.py`; y se agregaron pasos automáticos de `pip-audit` y `bandit` en `.github/workflows/ci.yml`.
- **Commit:** `de671da`.
- **En palabras simples:** Las pruebas en GitHub usaban simuladores en vez del motor de búsqueda real. Ahora instalamos la librería real y agregamos escáneres automáticos de seguridad en cada subida de código.

---

### H-027 (BAJO) — Higiene del repositorio, sanitización de rutas locales y versión 0.5.1
- **Componentes:** `docs/auditoria/*`, `docs/BASELINE.md`, `jinxas/__init__.py`, `pyproject.toml`, `README.md`, `CHANGELOG.md`
- **Causa:** Existencia de rutas absolutas que exponían nombres de usuario locales (rutas absolutas locales), versión desincronizada entre paquetes y reportes, y falta de tag formal.
- **Remediación:** Conversión de todos los enlaces absolutos a rutas relativas (verificado con `git grep`); incremento de versión a `0.5.1` en `__init__.py`, `pyproject.toml`, `README.md` y `CHANGELOG.md`; emisión del tag de versión `v0.5.1`.
- **Commit:** `7cb8d40`.
- **En palabras simples:** Se limpiaron enlaces que tenían carpetas personales del usuario, se actualizó el número de versión oficial a 0.5.1 y se etiquetó el proyecto para publicación.

---

### H-028 a H-032 (MEDIO / ALTO / BAJO) — Tercera revisión (v0.5.2)
- **Componentes:** `jinxas/config.py`, `jinxas/percepcion.py`, `jinxas/memoria_rag.py`, `jinxas/__main__.py`, `docs/`
- **Remediación:** Ampliación de variantes fonéticas de wake word y telemetría de casi-coincidencias en DEBUG (H-028); protección de publicación en memoria del RAG, validación de temporal en `_escritura_atomica`, cerrojo `_lock_flag` y limpieza de entradas de notas vacías (H-029); getter thread-safe `_obtener_modelo_centinela()` (H-030); `MSG_LIMITE_RONDAS` coherente en no-streaming y streaming (H-031); extracción de `procesar_eventos_panel` y pruebas aisladas (H-032).

---

### H-033 (ALTO) — Reindexado pendiente con bóveda ausente
- **Componente:** `jinxas/memoria_rag.py`
- **Causa:** Cuando `RUTA_VAULT` no existía en `construir_indice`, la rama descartaba `_reindex_pendiente = False` y salía del bucle sin comprobar si otra hebra había marcado una reindexación pendiente tras crear la bóveda.
- **Remediación:** Si `_reindex_pendiente` es `True` bajo `_lock_flag`, se limpia el flag y se ejecuta `continue` para iniciar una nueva pasada de indexación; si es `False`, se libera `_lock_construir` y se sale.
- **Prueba:** `tests/test_h033_rag_boveda_ausente.py` (2 pruebas).
- **Commit:** `b2fe428`.

---

### H-034 y H-035 (BAJO) — Precisión sobre componentes en red y cierre documental v0.5.3
- **Componentes:** `docs/TROUBLESHOOTING.md`, `README.md`, `docs/ARQUITECTURA.md`, `docs/auditoria/VERIFICACION_MANUAL.md`, `CHANGELOG.md`, `pyproject.toml`, `jinxas/__init__.py`
- **Remediación:** Se precisó en la documentación que Whisper, Ollama y el RAG operan sin conexión tras la descarga inicial mientras que Edge-TTS y `wttr.in` requieren internet (H-034); se creó la tabla de verificación manual con casillas vacías (`docs/auditoria/VERIFICACION_MANUAL.md`), se documentaron las limitaciones conocidas y se actualizó la versión a `0.5.3` con 316 pruebas verificadas el 5 de octubre de 2026 (H-035).

---

## 4. Historial Cronológico de Commits en `main`

Todos los cambios fueron consolidados en la rama principal (`https://github.com/DAHL13/JinxAS.git`):

```text
35ea56c fix(H-034): precisar en documentacion componentes locales vs con red
b2fe428 fix(H-033): respetar reindexado pendiente cuando la boveda no existe
a197ee9 fix(H-032): extraer procesar_eventos_panel, corregir documentacion y subir a v0.5.2
c70e014 fix(H-031): devolver mensaje explicito al agotar rondas de herramientas
4ac4652 fix(H-030): sincronizar carga de modelo centinela whisper con cerrojo
deaf45b fix(H-029): robustecer cache RAG ante fallos de manifiesto, concurrencia y notas vacias
1f98a61 fix(H-028): ampliar variantes foneticas de wakeword y registrar casi-coincidencias en DEBUG
7cb8d40 docs(H-027): actualizar reportes de auditoria, version 0.5.1 y sanitizacion de rutas
cab7f53 fix(H-025): precarga de whisper, saneamiento de tool_calls, config_local json y limpieza de dependencias
56f01bc fix(H-023): soportar tipo app: con ShellExecute para navegadores Edge y Chrome
830d5d6 fix(H-022): construir lineas de log con nodos DOM y textContent en addLog de panel.html
eceda39 fix(H-021): omitir texto privado del usuario en logs INFO y reservar para nivel DEBUG
cf6d476 fix(H-020): elevar umbral de fuzzy matching a 90, agregar jinxs e ignorar palabras cortas
de671da test(H-026): incorporar faiss y thefuzz reales en pruebas, dev requirements y pasos de seguridad en ci
3b6d6cb fix(H-024): normalizar nombres reservados de Windows comprobando segmento anterior al punto
dfae17e fix(H-019): ampliar limites de contexto y herramientas, prevenir truncado silencioso y advertir limite de tokens
7693082 fix(H-018): garantizar integridad atomica de cache RAG, validacion ntotal y sha1 perezoso
dbdf313 fix(H-017): interrumpir centinela con eventos de panel y sincronizar reproductor de audio con cerrojo
07b1376 docs: añadir reporte final consolidado de auditoría y remediación
2b85632 docs: actualizar hash de cierre en informe final
d3b8cc2 docs: registrar remediación completa, endurecimiento y cierre al 100% de hallazgos
aeb52e7 fix: sincronizar ApiPanel y contexto con lock para mitigar race condition (CWE-362)
31efa64 test: añadir suite de pruebas de inyección de fallos y resiliencia
43fb721 fix: endurecer captura de excepciones en obtener_clima para resiliencia de red
208517a docs: actualizar arbol de estructura del proyecto con jinxas/ui/panel.html
ad328bb fix(H-011): limpiar imports/variables no usadas y endurecer reglas de ruff en pyproject.toml
589c07c fix(H-012): actualizar pin de urllib3 a 2.8.0 para mitigar CVEs
2409137 fix(H-010): confinar carga de config_local a ruta explicita en directorio base
75bfa1a docs: actualizar hash final publicado en informe de auditoría
de8a44d docs: documentación completa de auditoría técnica y CHANGELOG
96a4355 test(H-014): añadir pruebas de cobertura para lógica crítica
377e9cc chore: fix ruff trailing whitespace in tests
393f0f5 chore(H-013): actualizar formato de licencia en pyproject.toml
0e0b7f4 docs(H-007): corregir version de Python y num_ctx en BASELINE.md
b78e522 fix(H-003): eliminar manipulacion de sys.path en __init__.py
cbe5691 fix(H-001): incluir ui/panel.html en el wheel moviendo a jinxas/ui/
c26545f fix(H-006): usar parámetros de escuchar_y_transcribir en lugar de config directo
80024a0 fix(H-005): eliminar imports muertos en __main__.py y percepcion.py
022428d fix(H-002): fijar versión de pywebview y añadir thefuzz a requirements
580f929 fix(H-004): marcar sha1 como usedforsecurity=False en caché RAG
```

---

## 5. Guía de Verificación Manual en Windows (Para el Estudiante / Usuario)

Consulta y rellena la plantilla [`docs/auditoria/VERIFICACION_MANUAL.md`](VERIFICACION_MANUAL.md) con las 11 pruebas manuales en tu equipo con Windows.

---

## 6. Conclusión y Veredicto Formal

El sistema **JinxAS v0.5.3** cuenta con las correcciones implementadas para los hallazgos H-001 a H-035 y 316 pruebas automatizadas en verde (verificadas el 5 de octubre de 2026).

Se mantiene el dictamen **FAVORABLE CON RESERVAS**. Este veredicto pasará a **Favorable** únicamente cuando el usuario complete las 11 pruebas de [`docs/auditoria/VERIFICACION_MANUAL.md`](VERIFICACION_MANUAL.md) en su equipo con Windows y confirme que la CI de GitHub (`windows-latest`) está en verde para `v0.5.3`.

