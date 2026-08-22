# 🤖 Jinx — Asistente de Voz Local Autónomo

> **Jinx** es un asistente de voz completamente local, modular y sin dependencias de la nube. Escucha tu voz, comprende tus instrucciones con un LLM local (Qwen 2.5 3B via Ollama), ejecuta acciones en tu sistema y te responde con voz sintetizada en tiempo real.

---

## 🏗️ Arquitectura Modular

El proyecto está dividido en **5 módulos independientes**, cada uno con una responsabilidad específica:

### Módulo 1 — Percepción · `percepcion.py`
**Speech-to-Text (STT) con Whisper local**

- Captura audio del micrófono usando `SpeechRecognition` + `PyAudio`.
- Calibra automáticamente el ruido ambiental antes de escuchar.
- Transcribe el audio con **OpenAI Whisper** (`model='small'`, `language='es'`).
- Aplica un `initial_prompt` con vocabulario técnico para mejorar precisión en español.
- Limpia el texto transcrito eliminando artefactos y espacios extra.

### Módulo 2 — Razonamiento · `cerebro.py`
**LLM local con Ollama / Qwen 2.5 3B**

- Mantiene un `SYSTEM_PROMPT` que define la personalidad de Jinx y el sistema de **enrutamiento de acciones** mediante etiquetas estrictas.
- Envía las consultas del usuario a Ollama y recibe la respuesta del modelo.
- Función `procesar_estado_sistema()`: recibe datos de telemetría real y genera respuestas habladas con estilo Jinx.

**Etiquetas de acción reconocidas:**
| Etiqueta | Activador |
|---|---|
| `[ACCION:ESTADO_SISTEMA]` | Preguntas sobre RAM, CPU, disco |
| `[ACCION:TEMPERATURA]` | Preguntas sobre temperatura o calor |
| `[ACCION:ABRIR_APP:nombre]` | Solicitudes de abrir aplicaciones |
| `[ACCION:GUARDAR_NOTA:titulo\|contenido]` | Solicitudes de anotar o recordar algo |
| `[ACCION:BUSCAR_NOTA:clave]` | Preguntas sobre notas guardadas |

### Módulo 3 — Voz · `voz.py`
**Text-to-Speech (TTS) con Edge-TTS**

- Usa **Edge-TTS** (`es-MX-DaliaNeural` por defecto) para sintetizar voz en español de forma local.
- Reproduce el audio generado con `pygame` sin guardar archivos permanentes.
- Soporta velocidad y volumen ajustables.

### Módulo 4 — Herramientas · `herramientas.py`
**Acceso al sistema operativo**

- `obtener_estado_sistema()`: lee CPU, RAM y disco con `psutil` y retorna un resumen formateado.
- `obtener_temperatura()`: intenta leer sensores vía `psutil` o PowerShell/WMI; si no hay acceso, informa el uso actual de CPU.
- `abrir_aplicacion(nombre)`: mapeo estricto de nombres en español/inglés a ejecutables de Windows (`notepad`, `msedge`, `calc`, `code`, etc.). Si no está en el mapa, intenta con `start`.

### Módulo 5 — Memoria · `memoria.py`
**Bóveda de notas Markdown (compatible con Obsidian)**

- `guardar_nota(titulo, contenido)`: crea o actualiza notas `.md` en `Boveda_Obsidian/`, con timestamp automático en cada actualización.
- `buscar_nota(palabra_clave)`: escanea todos los `.md` y retorna extractos de las notas que coinciden en título o contenido.

### Orquestador — `main.py`
Ciclo principal del asistente que:
1. Llama a `percepcion.py` para capturar el comando de voz.
2. Detecta palabras de salida (`salir`, `apagar`, etc.).
3. Envía el texto a `cerebro.py` y detecta la etiqueta de acción en la respuesta.
4. Ejecuta la herramienta o función de memoria correspondiente.
5. Genera la respuesta hablada final y la reproduce con `voz.py`.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| STT | [OpenAI Whisper](https://github.com/openai/whisper) (`small`, local) |
| LLM | [Ollama](https://ollama.com/) + Qwen 2.5 3B |
| TTS | [Edge-TTS](https://github.com/rany2/edge-tts) |
| Audio | PyAudio, SpeechRecognition, pygame |
| Sistema | psutil |
| Notas | Markdown / Obsidian-compatible |

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
├── main.py           # Orquestador principal del asistente
├── percepcion.py     # Módulo STT: escucha y transcripción con Whisper
├── cerebro.py        # Módulo LLM: razonamiento y enrutamiento con Ollama
├── voz.py            # Módulo TTS: síntesis de voz con Edge-TTS
├── herramientas.py   # Módulo de herramientas del sistema (CPU, apps, etc.)
├── memoria.py        # Módulo de memoria con bóveda Obsidian
├── requirements.txt  # Dependencias del proyecto
├── .gitignore        # Exclusiones de Git
└── Boveda_Obsidian/  # Notas guardadas por Jinx (excluida de Git)
```

---

## 🎤 Comandos de ejemplo

| Comando de voz | Acción ejecutada |
|---|---|
| *"¿Cómo está la RAM?"* | Muestra uso de CPU, RAM y disco |
| *"¿Está caliente la compu?"* | Consulta temperatura del sistema |
| *"Abre la calculadora"* | Lanza `calc.exe` |
| *"Abre VS Code"* | Ejecuta `code` |
| *"Recuerda que tengo dentista el jueves"* | Guarda nota en la bóveda |
| *"¿Qué tienes anotado sobre dentista?"* | Busca notas en la bóveda |
| *"Salir"* / *"Apagar"* | Cierra el asistente |

---

## 📜 Licencia

Proyecto personal de desarrollo. Uso libre para aprendizaje y experimentación.
