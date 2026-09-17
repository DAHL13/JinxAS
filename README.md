# 🤖 Jinx (JinxAS) — Asistente de Voz Local Autónomo

> **Jinx** es un asistente de voz completamente local, modular y sin dependencias de la nube. Escucha tu voz, razona con un LLM local (Qwen 2.5 3B vía Ollama) usando **tool calling nativo**, ejecuta acciones en tu sistema de forma segura, recuerda la conversación mientras hablas con él, y te responde con voz sintetizada en tiempo real.

---

## 🏗️ Arquitectura Modular

El proyecto está dividido en **6 archivos**, cada uno con una responsabilidad específica:

### Configuración — `config.py`
**Punto único de configuración del proyecto**

- Centraliza modelo de LLM, modelo de Whisper, idioma, tiempos de escucha, voz de TTS, ruta de la bóveda de notas y el `SYSTEM_PROMPT`.
- Define `MAPA_APLICACIONES`: el *allowlist* de aplicaciones que Jinx tiene permitido abrir.
- Todos los demás módulos importan sus valores desde aquí — no hay configuración duplicada ni hardcodeada en otros archivos.

### Módulo 1 — Percepción · `percepcion.py`
**Wake Word ultraligero + Speech-to-Text (STT) con Whisper local**

- **Wake Word ("Jinx")**: Modo Centinela con Whisper tiny.en de ultrabajo consumo para escucha pasiva continua 24/7 en segundo plano, detectando la palabra de activación o variantes fonéticas antes de activar el modelo principal Whisper.
- Captura audio del micrófono usando `SpeechRecognition` + `PyAudio`.
- Calibra automáticamente el ruido ambiental antes de escuchar.
- Transcribe el audio con **OpenAI Whisper** (modelo y parámetros definidos en `config.py`).
- Aplica un `initial_prompt` con vocabulario técnico para mejorar precisión en español.
- Limpia el texto transcrito eliminando artefactos y espacios extra.

### Módulo 2 — Razonamiento · `cerebro.py`
**LLM local con Ollama / Qwen 2.5 3B — Tool Calling nativo**

- Define `ESQUEMAS_HERRAMIENTAS`: los 5 tools disponibles para el modelo, declarados con JSON Schema (no etiquetas de texto).
- `procesar_pensamiento(mensajes)` envía el historial de conversación completo a Ollama con `tools=ESQUEMAS_HERRAMIENTAS` y devuelve la respuesta del modelo, incluyendo las llamadas a herramientas que decida hacer.
- El modelo decide **por sí mismo, de forma estructurada**, cuándo y con qué argumentos llamar a cada herramienta — ya no depende de que escriba un formato de texto exacto.

**Herramientas disponibles para el modelo:**
| Herramienta | Qué hace |
|---|---|
| `obtener_estado_sistema` | Consulta uso de CPU, RAM y disco |
| `obtener_temperatura` | Consulta temperatura de sensores o uso de CPU como referencia |
| `abrir_aplicacion(nombre_app)` | Abre una aplicación permitida |
| `guardar_nota(titulo, contenido)` | Guarda o actualiza una nota en la bóveda |
| `buscar_nota(palabra_clave)` | Busca notas por palabra clave |
| `obtener_clima` | Consulta estrictamente el clima exterior y la temperatura ambiente en Tehuacán |

### Módulo 3 — Voz · `voz.py`
**Text-to-Speech (TTS) con Edge-TTS**

- Usa **Edge-TTS** (voz configurable en `config.py`, por defecto `es-MX-DaliaNeural`) para sintetizar voz en español de forma local.
- Genera un **archivo temporal único por reproducción** (`tempfile`), evitando colisiones si el proceso se ejecuta más de una vez.
- Reproduce el audio con `pygame.mixer` de forma bloqueante y limpia el archivo temporal al terminar.

### Módulo 4 — Herramientas · `herramientas.py`
**Acceso al sistema operativo, con seguridad como prioridad**

- `obtener_estado_sistema()`: lee CPU, RAM y disco con `psutil` y retorna un resumen formateado.
- `obtener_temperatura()`: intenta leer sensores vía `psutil` o PowerShell/WMI; si no hay acceso, mide el uso de CPU de forma independiente como referencia.
- `abrir_aplicacion(nombre_app)`: **valida contra un allowlist estricto** (`MAPA_APLICACIONES` en `config.py`) antes de ejecutar nada. Si la aplicación no está en la lista, se rechaza — no hay fallback de ejecución arbitraria. Usa `subprocess.Popen([...], shell=False)`, nunca `os.system` ni `shell=True`.
- `obtener_clima()`: consulta el clima exterior y temperatura actual en Tehuacán mediante la API de wttr.in con validación de errores.

### Módulo 5 — Memoria · `memoria.py`
**Bóveda de notas Markdown (compatible con Obsidian)**

- `guardar_nota(titulo, contenido)`: crea o actualiza notas `.md` en `Boveda_Obsidian/`, con timestamp automático en cada actualización. Los nombres de archivo se normalizan y truncan a una longitud segura.
- `buscar_nota(palabra_clave)`: escanea todos los `.md` y retorna extractos de las notas que coinciden en título o contenido.

### Orquestador — `main.py`
Ciclo principal del asistente, con **memoria de conversación persistente**:

1. Mantiene un historial de conversación (`contexto`) que **vive durante toda la sesión**, no solo un turno — Jinx recuerda lo que hablaron antes.
2. El historial se recorta a un tamaño máximo por turno, cuidando no romper pares de llamada/resultado de herramientas.
3. Llama a `percepcion.py` para capturar el comando de voz.
4. Detecta palabras de salida (`salir`, `apagar`, `cancelar`, `detener`) y frases de reinicio de memoria (`olvida todo`, `borra la memoria`, `nueva conversación`).
5. Envía el historial a `cerebro.py`; si el modelo solicita herramientas, las ejecuta, agrega los resultados al historial y le pide al modelo una respuesta final hablada.
6. Reproduce la respuesta con `voz.py`.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| STT | [OpenAI Whisper](https://github.com/openai/whisper) (local) |
| LLM | [Ollama](https://ollama.com/) + Qwen 2.5 3B, con **tool calling nativo** |
| TTS | [Edge-TTS](https://github.com/rany2/edge-tts) |
| Audio | PyAudio, SpeechRecognition, pygame |
| Sistema | psutil |
| Notas | Markdown / Obsidian-compatible |
| Logging | Módulo `logging` estándar de Python (sin `print()`) |

---

## 🚀 Instalación y ejecución

### Prerrequisitos

- Python 3.12+
- [Ollama](https://ollama.com/) instalado y corriendo con el modelo `qwen2.5:3b`:
  ```bash
  ollama pull qwen2.5:3b
  ```

### Instalar dependencias

```bash
python -m venv venv
.\venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### Ejecutar el asistente

```bash
python main.py
```

---

## 📁 Estructura del Proyecto

```
JinxAS/
├── main.py           # Orquestador: loop principal, memoria de conversación, ejecución de tools
├── config.py         # Configuración centralizada (modelo, voz, tiempos, allowlist de apps)
├── percepcion.py     # Módulo STT: escucha y transcripción con Whisper
├── cerebro.py        # Módulo LLM: tool calling nativo con Ollama
├── voz.py            # Módulo TTS: síntesis de voz con Edge-TTS
├── herramientas.py   # Herramientas del sistema (CPU, temperatura, abrir apps con allowlist)
├── memoria.py        # Módulo de memoria con bóveda Obsidian
├── requirements.txt  # Dependencias del proyecto
├── .gitignore        # Exclusiones de Git
└── Boveda_Obsidian/  # Notas guardadas por Jinx (excluida de Git)
```

---

## 🎤 Comandos de ejemplo

| Comando de voz | Acción ejecutada |
|---|---|
| *"¿Cómo está la RAM?"* | Consulta uso de CPU, RAM y disco |
| *"¿Está caliente la compu?"* | Consulta temperatura del sistema |
| *"¿Cómo está el clima?"* | Consulta el clima exterior y temperatura en Tehuacán |
| *"Abre la calculadora"* | Lanza la calculadora (si está en el allowlist) |
| *"Abre VS Code"* | Ejecuta VS Code (si está en el allowlist) |
| *"Recuerda que tengo dentista el jueves"* | Guarda nota en la bóveda |
| *"¿Qué tienes anotado sobre dentista?"* | Busca notas en la bóveda |
| *"Olvida todo"* / *"Nueva conversación"* | Borra la memoria de la sesión actual |
| *"Salir"* / *"Apagar"* | Cierra el asistente |

---

## 🔒 Seguridad

- Todas las aperturas de aplicaciones pasan por un **allowlist explícito** (`MAPA_APLICACIONES` en `config.py`) — Jinx nunca ejecuta un nombre de aplicación arbitrario.
- Las llamadas a procesos usan `subprocess` con lista de argumentos y `shell=False`, nunca `os.system` ni cadenas de shell interpoladas.
- El razonamiento usa tool calling estructurado en vez de parseo de texto libre, reduciendo el riesgo de que una respuesta inesperada del modelo se interprete como un comando no intencionado.

---

## 🗺️ Roadmap

- ✅ **Fase 1** — Memoria de conversación persistente durante la sesión.
- ✅ **Fase 2** — Tool calling nativo, configuración centralizada, logging.
- ✅ **Fase 3** — Completada: Wake Word ("Jinx") con Modo Centinela (Whisper tiny.en), consulta de clima exterior en Tehuacán (wttr.in) y memoria de contexto ampliada.
- ⏳ **Fase 4** — Planeada: proactividad, recordatorios/calendario, control de música, interfaz visual simple, memoria semántica (RAG) sobre la bóveda.

---

## 📜 Licencia y Créditos

**Desarrollador:** DAHL ([@DAHL13](https://github.com/DAHL13))
Proyecto personal, diseñado y dirigido con metodología VibeCoding
(Cursor, Google Antigravity) y asistencia de IA para la implementación.

Proyecto personal de desarrollo. Uso libre para aprendizaje y experimentación.
