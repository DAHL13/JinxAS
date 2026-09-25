# 🤖 Jinx (JinxAS) — Asistente de Voz Inteligente

![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20%2F%20Qwen2.5-000000?logo=ollama&logoColor=white)
![Whisper](https://img.shields.io/badge/STT-OpenAI%20Whisper-412991?logo=openai&logoColor=white)
![Edge TTS](https://img.shields.io/badge/TTS-Edge--TTS-0078D4?logo=microsoftedge&logoColor=white)
![FAISS](https://img.shields.io/badge/RAG-FAISS%20%2B%20SentenceTransformers-4B8BBE)
![Obsidian](https://img.shields.io/badge/Notas-Obsidian-7C3AED?logo=obsidian&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![Arquitectura](https://img.shields.io/badge/Arquitectura-N%C3%BAcleo%20IA%20Local%20%7C%20Servicios%20de%20Red%20Espec%C3%ADficos-2EA043)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/DAHL13/JinxAS/actions/workflows/ci.yml/badge.svg)](https://github.com/DAHL13/JinxAS/actions)

> ⚡ **Jinx combina un núcleo de Inteligencia Artificial que procesa, recuerda y razona 100% en local con servicios de red específicos para tareas auxiliares.**  Reconoce su propia palabra de activación,  mantiene el hilo de la conversación,  ejecuta acciones reales en tu sistema con validación de seguridad estricta, y  puede consultar tus propios apuntes de Obsidian por significado — todo corriendo en tu máquina sin enviar tus datos a nubes de inferencia. 

> **Jinx** es un asistente de voz modular con procesamiento local para STT (Whisper), razonamiento LLM (Qwen 2.5 3B vía Ollama) usando **tool calling nativo**, y memoria semántica RAG (FAISS). Ejecuta acciones en tu sistema de forma segura, recuerda la conversación mientras hablas con él, consulta tus notas de Obsidian por significado y te responde con voz sintetizada en tiempo real.

---

## 🌐 Privacidad y Conexiones de Red

Para mantener total transparencia sobre el flujo de datos y la arquitectura técnica de JinxAS:

### 🔒 100% Local y Privado (Sin conexión a internet)
- **Transcripción de Voz (STT):** OpenAI Whisper ejecuta sus modelos (`tiny.en` para centinela y `small` para comandos) directamente en tu procesador/GPU local. Tu voz nunca sale de tu equipo.
- **Cerebro y Razonamiento (LLM):** Ollama corre localmente con Qwen 2.5 3B. Las conversaciones, contexto y decisiones estructuradas de tool calling se procesan en tu memoria local.
- **Memoria Semántica RAG:** La vectorización de notas con `SentenceTransformers` (`paraphrase-multilingual-MiniLM-L12-v2`) y la base de datos vectorial `FAISS` operan íntegramente de forma local en disco y memoria RAM.
- **Bóveda de Notas:** Archivos Markdown almacenados en tu sistema de archivos local (`Boveda_Obsidian/`).

### 🌐 Requiere Conexión a Internet
- **Síntesis de Voz (TTS):** Utiliza `edge-tts`, que envía las cadenas de texto de respuesta a los servidores de Microsoft Edge TTS para generar audio neural fluido en español (`es-MX-DaliaNeural`).
- **Consulta de Clima:** La herramienta `obtener_clima` consulta la API pública de `wttr.in`.
- **Panel Visual SENTINEL:** Los recursos de diseño (Tailwind CSS) y tipografías (Google Fonts) se cargan vía CDN dentro de la vista `pywebview`.
- **Descarga Inicial de Modelos:** La primera ejecución requiere conexión para descargar los pesos de Ollama, Whisper y SentenceTransformers.

---

## 🏗️ Arquitectura Modular

El proyecto está diseñado con separación de responsabilidades y modularidad limpia:

### ⚙️ Configuración — `config.py`
**Punto único de configuración del proyecto**

- Centraliza modelo de LLM, modelo de Whisper, idioma, tiempos de escucha, voz de TTS, ruta de la bóveda de notas y el `SYSTEM_PROMPT`.
- Define `MAPA_APLICACIONES`: el *allowlist* de aplicaciones que Jinx tiene permitido abrir.
- Configura ubicación por defecto (`CIUDAD_POR_DEFECTO`), permitiendo sobrescritura por variable de entorno `JINX_CIUDAD` o archivo `config_local.py`.
- Expone `configurar_consola()` para garantizar encoding UTF-8 en streams de entrada/salida bajo Windows.
- `STREAMING = False` — bandera para activar el pipeline TTS por frases con TTFA reducido (F2-02). En `True`, el LLM y el TTS trabajan en paralelo frase a frase.

### 👂 Módulo 1 — Percepción · `percepcion.py`
**Wake Word ultraligero + Speech-to-Text (STT) con Whisper local**

- **Wake Word ("Jinx")**: Modo Centinela con Whisper `tiny.en` para escucha pasiva continua en segundo plano. Utiliza el umbral de energía calibrado de `SpeechRecognition` para segmentar el habla y coincidencia difusa (`thefuzz`) sobre la transcripción para detectar la palabra de activación o variantes fonéticas antes de activar el modelo principal Whisper.
- Captura audio del micrófono usando `SpeechRecognition` + `PyAudio`.
- Calibra automáticamente el ruido ambiental antes de escuchar.
- Transcribe el audio con **OpenAI Whisper** (modelo y parámetros definidos en `config.py`).
- Aplica un `initial_prompt` con vocabulario técnico para mejorar precisión en español.
- Limpia el texto transcrito eliminando artefactos y espacios extra.

### 🧠 Módulo 2 — Razonamiento · `cerebro.py`
**LLM local con Ollama / Qwen 2.5 3B — Tool Calling nativo**

- Define `ESQUEMAS_HERRAMIENTAS`: las **7 herramientas disponibles** para el modelo, declaradas con JSON Schema estructurado.
- `procesar_pensamiento(mensajes)` — modo clásico: envía el historial completo a Ollama con `tools=ESQUEMAS_HERRAMIENTAS` y devuelve la respuesta consolidada del modelo.
- `procesar_pensamiento_stream(mensajes)` — modo streaming (F2-02): invoca `ollama.chat` con `stream=True` y emite los chunks en tiempo real. En excepción emite un chunk con `_error=True` sin colapsar el hilo de voz.
- El modelo decide de forma estructurada cuándo y con qué argumentos llamar a cada herramienta.

**Herramientas activas disponibles para el modelo:**
| Herramienta | Qué hace |
|---|---|
| `obtener_estado_sistema` | Consulta uso de CPU, RAM y disco (GB usados/totales) |
| `obtener_temperatura` | Consulta temperatura de sensores CPU/térmicos o uso de CPU |
| `abrir_aplicacion(nombre_app)` | Abre una aplicación permitida del allowlist |
| `guardar_nota(titulo, contenido)` | Guarda o actualiza una nota en la bóveda de Obsidian |
| `buscar_nota(palabra_clave)` | Búsqueda literal por palabra clave en títulos y contenidos |
| `obtener_clima` | Consulta el clima exterior y temperatura en la ciudad configurada |
| `consultar_boveda(consulta)` | Busca información semántica en la bóveda usando el índice RAG (FAISS) |

### 🔊 Módulo 3 — Voz · `voz.py`
**Text-to-Speech (TTS) con Edge-TTS — modo clásico y streaming**

- Usa **Edge-TTS** (voz configurable en `config.py`, por defecto `es-MX-DaliaNeural`) para sintetizar audio neural conectándose al servicio de Microsoft.
- Genera un archivo temporal dinámico por invocación (`tempfile`), evitando colisiones de concurrencia.
- Reproduce el audio con `pygame.mixer` de forma bloqueante y elimina el archivo temporal de forma garantizada.
- `on_start: callable` — callback opcional invocado justo antes de `pygame.play()` para registrar el TTFA con precisión de milisegundos (F2-06).
- `FIN_DE_FRASE` — expresión regular que detecta `.`, `!`, `?`, `…` seguidos de espacio para segmentar texto en frases (F2-02).
- `extraer_frases(flujo_texto)` — generador que consume chunks del LLM y emite frases completas una a una (F2-02).
- `reproducir_frases_streaming(frases_iter, on_start)` — pipeline streaming con hilo productor de síntesis y consumidor de reproducción comunicados por `queue.Queue(maxsize=4)`. Cada `.mp3` se elimina inmediatamente tras reproducirlo (F2-02).

### 🧰 Módulo 4 — Herramientas · `herramientas.py`
**Acceso al sistema operativo con seguridad reforzada**

- `obtener_estado_sistema()`: lee CPU, RAM y disco con `psutil` y retorna un resumen claro en GB usados y totales.
- `obtener_temperatura()`: lee sensores térmicos vía `psutil` o PowerShell/WMI (zona térmica); si no hay acceso directo por permisos, ofrece el uso de CPU como referencia.
- `abrir_aplicacion(nombre_app)`: **valida contra un allowlist estricto** (`MAPA_APLICACIONES` en `config.py`). Resuelve la ruta segura en el PATH con `shutil.which` y la ejecuta con `subprocess.Popen([ruta], shell=False)` **sin usar shell ni el comando `cmd`**, eliminando riesgos de inyección de comandos. Si no está en el PATH (como apps nativas `calc` o `spotify`), utiliza `os.startfile`.
- `obtener_clima()`: consulta el clima exterior codificando la URL con `urllib.parse.quote` y manejando timeouts y errores de red.
- `consultar_boveda(consulta)`: interfaz directa con el motor RAG.

### 🗒️ Módulo 5 — Memoria · `memoria.py`
**Bóveda de notas Markdown (compatible con Obsidian)**

- `guardar_nota(titulo, contenido)`: crea o actualiza notas `.md` en `Boveda_Obsidian/`, con timestamp automático en cada actualización. Normaliza los nombres de archivo sanitizando caracteres prohibidos de Windows (`\ / : * ? " < > |`), previniendo nombres reservados de sistema (`CON`, `PRN`, `AUX`, `NUL`, etc.) y sincroniza el índice RAG en tiempo real.
- `buscar_nota(palabra_clave)`: búsqueda literal por palabra clave en títulos y contenidos de todas las notas.

### 🔎 Módulo 6 — Memoria RAG · `memoria_rag.py`
**Búsqueda semántica local sobre la bóveda (FAISS + sentence-transformers)**

- Modelo de embeddings multilingüe `paraphrase-multilingual-MiniLM-L12-v2` cargado de forma perezosa.
- `construir_indice()`: recorre recursivamente la bóveda, divide notas en fragmentos con solapamiento y genera un índice FAISS con similitud coseno normalizada (`IndexFlatIP`).
- `buscar_en_notas(consulta, top_k)`: vectoriza la consulta y recupera los fragmentos con mayor similitud semántica por encima del umbral `UMBRAL_SIMILITUD_RAG`.
- `agregar_nota_al_indice(ruta, contenido)`: indexación incremental al crear o actualizar notas.

### 🎛️ Orquestador — `main.py`
**Ciclo de vida principal del asistente**

1. Mantiene un historial de conversación que preserva contexto durante la sesión.
2. Normaliza el texto del usuario (elimina acentos, puntuación y mayúsculas) para evaluar comandos de salida y reinicio sin falsos positivos.
3. Despacha turnos a `cerebro.py`, resolviendo llamadas recursivas de herramientas hasta un límite seguro (`MAX_RONDAS_TOOLS`).
4. Protege el LLM contra inyecciones de prompt indirectas mediante etiquetas estructuradas `<datos_herramienta>`.
5. Corre el bucle de audio en un hilo secundario (`threading`), manteniendo la ventana gráfica fluida en el hilo principal.
6. **Modo streaming** (`config.STREAMING = True`, F2-02): `ejecutar_turno_streaming()` consume el stream de Ollama en tiempo real con un generador en vivo; el primer fragmento de texto se sintetiza y reproduce mientras el LLM sigue generando el resto, reduciendo el TTFA de forma medible.
7. **Métricas honestas** (F2-06): `CronometroTurno` mide con `time.perf_counter()` los hitos de cada turno (inicio, fin STT, primer audio, fin TTS). El panel SENTINEL muestra `TTFA` en lugar de la latencia E2E inflada.
8. **Índice RAG no bloqueante** (F2-07): `construir_indice()` se lanza en un hilo daemon al arrancar, de forma que el micrófono queda disponible de inmediato.

### 🖥️ Interfaz Visual — `interfaz.py` + `panel_sentinel.html`
**Panel "SENTINEL // PIPELINE GRAPH"**

- Interfaz visual nativa con **pywebview** (sin dependencias pesadas de Node.js o Electron).
- `ControladorPanel` (Python → JS): visualiza en tiempo real las etapas del pipeline (Centinela, Transcripción, Núcleo LLM, Ejecución de Tools, Síntesis y Latencia).
- `InterfazAPI` (JS → Python): puente seguro que expone acciones de control al usuario (p. ej. "Emergency Flush" de memoria o repetición de respuesta).

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.10 / 3.11 / 3.12 |
| STT | [OpenAI Whisper](https://github.com/openai/whisper) (local) |
| LLM | [Ollama](https://ollama.com/) + Qwen 2.5 3B, con **tool calling nativo** |
| TTS | [Edge-TTS](https://github.com/rany2/edge-tts) (Microsoft Edge Service) |
| RAG | [FAISS](https://github.com/facebookresearch/faiss) + [SentenceTransformers](https://sbert.net/) (local) |
| Audio | PyAudio, SpeechRecognition, pygame |
| Monitoreo | psutil |
| Almacenamiento | Markdown / Compatible con Obsidian |
| Interfaz visual | [pywebview](https://pywebview.flowrl.com/) (ventana nativa) + Tailwind CSS + Google Fonts |
| Testing y CI | `pytest` + GitHub Actions |

---

## 🚀 Instalación y ejecución

### ✅ Prerrequisitos

- Python 3.10 o superior (recomendado 3.11 o 3.12).
- [Ollama](https://ollama.com/) instalado y corriendo con el modelo `qwen2.5:3b`:
  ```bash
  ollama pull qwen2.5:3b
  ```

### 📦 Instalar dependencias

```bash
python -m venv venv
.\venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

*(Si deseas compilar o actualizar las dependencias directas desde `requirements.in`, puedes usar `pip-compile requirements.in`).*

### 🧪 Ejecutar tests

La suite de pruebas unitarias está aislada de cargas pesadas de Machine Learning, ejecutándose en fracciones de segundo:

```bash
pytest tests/ -v
```

### ▶️ Ejecutar el asistente

```bash
python main.py
```

Esto despliega la ventana del panel "SENTINEL" e inicializa el asistente de voz en segundo plano de forma integrada.

---

## 📁 Estructura del Proyecto

```
JinxAS/
├── .github/
│   └── workflows/
│       └── ci.yml          # Pipeline de Integración Continua (GitHub Actions)
├── tests/
│   └── test_logica.py      # Tests unitarios de lógica pura aislados de ML
├── main.py                 # Orquestador: ciclo de voz (hilo secundario), tools y panel pywebview
├── config.py               # Configuración centralizada (modelos, ubicación, allowlist de apps)
├── percepcion.py           # Módulo STT: Centinela (wake word difuso) + Whisper local
├── cerebro.py              # Módulo LLM: esquemas de 7 herramientas y tool calling nativo
├── voz.py                  # Módulo TTS: síntesis de voz con Edge-TTS
├── herramientas.py         # Herramientas del sistema (CPU/RAM, temperatura, apps seguras, clima, RAG)
├── memoria.py              # Bóveda de notas Markdown compatibles con Obsidian
├── memoria_rag.py          # Motor RAG local: indexación FAISS + búsqueda semántica
├── interfaz.py             # Controlador y API bidireccional entre Python y la interfaz gráfica
├── panel_sentinel.html     # Panel visual del pipeline (SENTINEL // PIPELINE GRAPH)
├── requirements.in         # Dependencias directas de primer nivel (pip-tools)
├── requirements.txt        # Dependencias fijadas del proyecto
├── LICENSE                 # Licencia de código abierto MIT
├── .gitignore              # Exclusiones de Git (cachés, índices FAISS, notas, .env)
└── Boveda_Obsidian/        # Directorio de notas de Obsidian (excluida de Git)
```

---

## 🎤 Comandos de ejemplo

| Comando de voz | Acción ejecutada |
|---|---|
| *"¿Cómo está la RAM?"* | Consulta uso de CPU, RAM y disco en GB usados/totales |
| *"¿Está caliente la compu?"* | Consulta temperatura de sensores o uso de CPU |
| *"¿Cómo está el clima?"* | Consulta el clima exterior y temperatura en la ciudad configurada |
| *"Abre la calculadora"* | Lanza la calculadora (si está en el allowlist de forma segura) |
| *"Abre VS Code"* | Ejecuta VS Code mediante búsqueda en PATH sin intermediación de shell |
| *"Recuerda que tengo dentista el jueves"* | Guarda o actualiza la nota en la bóveda de Obsidian |
| *"¿Qué notas tengo de dentista?"* | Búsqueda literal por palabra clave |
| *"Explícame lo que apunté sobre bases de datos"* | Consulta conceptual en la bóveda vía RAG (FAISS) |
| *"Olvida todo"* / *"Nueva conversación"* | Reinicia la memoria de la sesión actual |
| *"Salir"* / *"Apagar"* | Cierra ordenadamente el asistente |

---

## 🔒 Seguridad

- **Ejecución segura de aplicaciones:** Las solicitudes de apertura pasan por `MAPA_APLICACIONES` en `config.py`. Se valida el binario con `shutil.which` y se ejecuta mediante `subprocess.Popen([ruta], shell=False)`, eliminando por completo el uso de `shell=True` o `cmd /c` para anular cualquier vector de inyección de comandos.
- **Protección contra Inyecciones Indirectas:** La información retornada por herramientas se envuelve en etiquetas delimitadoras `<datos_herramienta>`, reforzado por el `SYSTEM_PROMPT` para instruir al modelo a tratarlas estrictamente como solo lectura.
- **Normalización estricta de archivos:** Los nombres de notas en Obsidian son sanitizados frente a nombres reservados de Windows (`CON`, `PRN`, `AUX`, `NUL`, etc.) y caracteres ilegales del sistema de archivos.
- **Superficie de ataque reducida en UI:** El puente bidireccional `pywebview.api` solo expone métodos específicos predeterminados.

---

## 🗺️ Roadmap

### Roadmap histórico (completado)

- ✅ **Fase 1** — Memoria de conversación persistente durante la sesión.
- ✅ **Fase 2** — Tool calling nativo, configuración centralizada, logging estructurado.
- ✅ **Fase 3** — Wake Word ("Jinx") con Modo Centinela y coincidencia difusa, clima dinámico y memoria semántica RAG (FAISS + embeddings multilingües).
- ✅ **Fase 4** — Seguridad en ejecución de herramientas (sin inyecciones de shell), mitigación de inyecciones de prompt indirectas y opciones optimizadas de Ollama.
- ✅ **Fase 5** — Panel visual SENTINEL e interfaz nativa con `pywebview`, visualización del pipeline en tiempo real y API bidireccional.
- ✅ **Fase 6** — Higiene y robustez: centralización UTF-8 en Windows, suite de tests unitarios de lógica pura (`pytest`), CI automatizado en GitHub Actions y documentación transparente.

### 🔧 Roadmap de Consolidación (en curso)

A partir de una auditoría externa del repositorio (21 de septiembre de 2026), el proyecto entró en una etapa de **consolidación** antes de seguir sumando funciones nuevas: cerrar bugs conocidos del bucle de voz, medir y mejorar el rendimiento en CPU, blindar la memoria/RAG, hacer que cada herramienta y el panel SENTINEL digan la verdad sobre lo que hacen, y dejar pruebas + CI reales. 8 fases (0 a 7), documentadas y ejecutadas una a la vez:

| Fase | Objetivo | Estado |
|---|---|:-:|
| 0 | Línea base: rama, tests, métricas, log a archivo | ✅ |
| 1 | Correcciones críticas del bucle de voz | ✅ |
| 2 | Rendimiento y latencia | 🚧 |
| 3 | Memoria y RAG | ⏳ |
| 4 | Herramientas confiables | ⏳ |
| 5 | Seguridad, privacidad y documentación veraz | ⏳ |
| 6 | Panel SENTINEL honesto y funcional | ⏳ |
| 7 | Pruebas, CI y empaquetado (cierre) | ⏳ |

*El Whisper Centinela (wake word) no se toca durante esta consolidación — ya funciona y se queda como está.*

#### Detalle de tareas completadas

**Fase 0 — Línea base**
- ✅ Rama de consolidación creada, suite de `pytest` funcional, log rotativo a archivo (`logs/jinx.log`).
- ✅ Mock de `thefuzz` en `conftest.py` para entornos sin la dependencia instalada.

**Fase 1 — Correcciones críticas del bucle de voz**
- ✅ **F1-11** Corrección del formato `tool_name` en mensajes de herramienta para Ollama.
- ✅ **F1-13** Texto de respuesta visible en el panel antes de que arranque el TTS.
- *(Resto de F1 pendiente de revisión)*

**Fase 2 — Rendimiento y latencia** *(en curso)*
- ✅ **F2-07 — Arranque no bloqueante de RAG:** `construir_indice()` se lanza en hilo daemon al iniciar. `buscar_semantica()` devuelve un mensaje amigable si el índice aún no está listo. Lock de hilo en `memoria_rag.py` para proteger el estado compartido (`_indice`, `_fragmentos`).
- ✅ **F2-06 — Métricas honestas y TTFA:** Clase `CronometroTurno` en `metricas.py` con `time.perf_counter()`. Callback `on_start` en `reproducir_voz()` disparado justo antes de `pygame.play()`. El panel SENTINEL muestra `TTFA` (tiempo entre fin de STT y primer sample de audio) en lugar de la latencia E2E inflada por el TTS completo. Log estructurado `[METRICA_HONESTA]`.
- ✅ **F2-02 — Streaming LLM + TTS por frases (primera y segunda mitad):**
  - `procesar_pensamiento_stream()` en `cerebro.py` con `stream=True`.
  - `extraer_frases()` y `reproducir_frases_streaming()` en `voz.py`: pipeline productor/consumidor con `queue.Queue(maxsize=4)`, limpieza garantizada de `.mp3` temporales.
  - `ejecutar_turno_streaming()` en `main.py`: generador en vivo que emite chunks al TTS en tiempo real sin esperar el fin de la respuesta del LLM. Manejo correcto de `tool_calls` intermedios.
  - Activable con `config.STREAMING = True`; en `False` el flujo clásico es 100% intacto.
  - 75 tests unitarios pasando en verde, sin dependencias de red ni audio real.

---

## 📜 Licencia y Créditos

**Desarrollador:** DAHL ([@DAHL13](https://github.com/DAHL13))  
Proyecto personal, diseñado y dirigido con metodología VibeCoding (Cursor, Google Antigravity) y asistencia de IA para la implementación.

Distribuido bajo la **Licencia MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.
