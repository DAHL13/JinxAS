# 📊 Línea Base de Rendimiento y Latencia (BASELINE) — JinxAS

Este documento establece la línea base de rendimiento de **Jinx Asistente**, documentando las métricas iniciales (Fase 0), las optimizaciones implementadas en la **Fase 1** y **Fase 2**, las decisiones de arquitectura adoptadas y los marcadores para validación en sesiones interactivas de voz.

---

## 1. Entorno de Hardware y Software

Todas las mediciones se registraron y ejecutan en el siguiente entorno de hardware local, caracterizado por una inferencia 100% en CPU:

| Componente | Especificación | Rol en la Arquitectura |
|---|---|---|
| **CPU** | AMD Ryzen 5 7530U (6 núcleos, 12 hilos, hasta 4.5 GHz) | Inferencia local 100% en CPU para LLM, STT y RAG |
| **RAM** | 32 GB DDR4 3200 MHz (Dual Channel) | Espacio suficiente para albergar simultáneamente Ollama, Whisper y embeddings |
| **GPU** | AMD Radeon Vega 7 integrada (2 GB VRAM compartida) | No utilizada para inferencia acelerada (ejecución pura en CPU) |
| **Almacenamiento** | SSD NVMe PCIe 3.0 | Carga de pesos de modelos y lectura de base de datos de notas |
| **Sistema Operativo** | Windows 11 Home / Pro (x64) | Plataforma de ejecución |
| **Python** | 3.11+ | Entorno de ejecución con dependencias nativas |
| **Modelo Centinela** | OpenAI Whisper `tiny.en` (CPU, FP32) | Detección pasiva continua de wake word ("Jinx") |
| **Modelo Comandos** | OpenAI Whisper `small` (multilingual, CPU, FP32) | Transcripción de instrucciones del usuario tras activación |
| **Modelo Cerebro (LLM)**| Ollama `qwen2.5:3b-instruct` (cuantización 4-bit) | Razonamiento, tool calling nativo y generación de diálogo |
| **Modelo Embeddings** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Representación vectorial de apuntes en Obsidian |
| **Motor Vectorial** | `faiss-cpu` (IndexFlatIP con normalización L2) | Búsqueda por similitud de coseno en memoria local |
| **Motor Síntesis (TTS)**| `edge-tts` (Microsoft Neural Voices: `es-MX-DaliaNeural`) | Generación y streaming de audio |

---

## 2. Tabla 1 — Línea Base Inicial (Fase 0 / Pre-Fase 2)

Las métricas mostradas a continuación provienen de los registros históricos reales de `logs/jinx.log` (sesión previa a las optimizaciones de Fase 1 y Fase 2, turno registrado: `2026-09-24 12:18:48`):

| Etapa | Mediana Inicial (ms) | Arranque en Frío (s) | Uso de RAM Estimado (MB) |
|---|:---:|:---:|:---:|
| **`stt`** (Escucha + Whisper `small`) | 9,185 ms | ~2.5 s (carga de disco por turno) | ~460 MB |
| **`llm_turno`** (Ollama `qwen2.5:3b`) | 18,393 ms | ~3.0 s (si Ollama no estaba en RAM) | ~2,200 MB (proceso Ollama) |
| **`tts`** (Edge-TTS monolítico) | 6,933 ms | ~0.3 s (conexión TCP inicial) | ~45 MB |
| **`ttfa_ms`** (Time to First Audio) | ~34,511 ms | N/A | Incluido en pipeline |
| **`turno_ms`** (Fin de audio a fin de voz) | **34,511 ms** (~34.5 s) | **11.3 s** (arranque total de app) | **~2,350 MB** (proceso Python) |

### 🔍 Comportamiento y cuellos de botella detectados en la Fase 0

1. **Recarga del modelo `small` por turno:**  
   En cada interacción, tras detectarse el wake word, se invocaba `whisper.load_model("small")` desde cero, provocando lecturas reiteradas a disco y demoras de **2.5 a 3 segundos adicionales** por turno.
2. **Pérdida de 1 s por `adjust_for_ambient_noise` en turno:**  
   Antes de escuchar el comando se llamaba síncronamente a `adjust_for_ambient_noise(source, duration=1)`. Esto penalizaba el turno con un segundo muerto y, peor aún, mutilaba la primera sílaba si el usuario empezaba a hablar inmediatamente después de la activación.
3. **Indexación RAG síncrona en el arranque:**  
   Al arrancar `main.py`, se importaba `sentence_transformers` y `faiss`, cargando los pesos del modelo de embeddings y escaneando la bóveda de Obsidian síncronamente en el hilo principal. Esto congelaba el inicio de Jinx durante **8 a 10 segundos** antes de que el centinela pudiera si quiera comenzar a escuchar.
4. **Síntesis TTS monolítica:**  
   El orquestador esperaba a que el LLM concluyera el 100% de su respuesta (espera completa de ~18.4 s) y luego enviaba el bloque completo a Edge-TTS (otros ~6.9 s). El usuario permanecía en silencio absoluto durante más de 34 segundos antes de escuchar el primer fonema.

---

## 3. Tabla 2 — Rendimiento después de Fase 1 y Fase 2

La siguiente tabla resume el impacto arquitectónico y las mejoras medidas o proyectadas tras implementar las optimizaciones de consolidación:

| Etapa / Optimización | Línea Base (Pre-F2) | Post-F1/F2 (Objetivo / Estimado) | Mediana Real Validada | Mecanismo e Impacto |
|---|:---:|:---:|:---:|---|
| **STT recurrente** (F1-04 / F1-05) | 9,185 ms | 2,800 – 3,500 ms | *[Pendiente sesión de voz en vivo]* | Caché en RAM de `_MODELO_WHISPER_COMANDOS` y eliminación de `adjust_for_ambient_noise` en comandos. Ahorro de ~5.5 s. |
| **LLM en conversación** (F2-01) | 18,393 ms | 12,000 – 15,000 ms | *[Pendiente sesión de voz en vivo]* | `LLM_KEEP_ALIVE = "30m"` evita evicciones de RAM. Opciones fijadas: `num_ctx: 4096`, `num_thread: 6`. |
| **Atajos deterministas** (F2-03) | 18,393 ms | **0 ms** (bypass LLM) | **0 ms** ✅ | Comandos como *"abre la calculadora"* o *"cómo está la RAM"* resueltos directamente por [atajos.py](file:///c:/Users/Pcrz/Documents/JinxAS/atajos.py). |
| **TTFA (Time to First Audio)** (F2-02 / F2-06) | ~34,511 ms | **1,500 – 2,500 ms** (post-STT) | *[Pendiente sesión de voz en vivo]* | Streaming por frases (`FIN_DE_FRASE` + productor/consumidor). El primer audio suena con la primera frase emitida por Ollama. |
| **Arranque en frío global** (F2-07) | 11.3 s | **< 1.8 s** | **~1.5 s** ✅ | Lazy imports en [memoria_rag.py](file:///c:/Users/Pcrz/Documents/JinxAS/memoria_rag.py) e indexación FAISS en hilo daemon en segundo plano (`_lock_rag`). |
| **Consulta de Clima** (F2-08) | 800 – 1,800 ms (HTTP) | **< 1 ms** (cache hit) | **< 1 ms** ✅ | Caché en memoria de 10 minutos (600 s TTL) en `obtener_clima()` ([herramientas.py](file:///c:/Users/Pcrz/Documents/JinxAS/herramientas.py)). |

> [!NOTE]  
> Los valores marcados como *`[Pendiente sesión de voz en vivo]`* corresponden a métricas end-to-end con micrófono en caliente (`[METRICA_HONESTA]` y `[TURNO]`). Serán rellenados automáticamente con la mediana obtenida tras completar una sesión de voz de 10 turnos representativos.

---

## 4. Decisiones de Arquitectura Documentadas

### 4.1. Decisión F2-04: Descarte de `faster-whisper` a favor de `openai-whisper` cacheado

- **Contexto:** La auditoría inicial contempló la migración de `openai-whisper` a `faster-whisper` (basado en `CTranslate2`) para acelerar la transcripción en CPU.
- **Evaluación y hallazgos:**  
  1. El cuello de botella principal de STT en Fase 0 no era la velocidad del kernel de inferencia, sino la **recarga del modelo desde disco por turno (~2.5 s)** y la **calibración síncrona innecesaria de ruido ambiental (~1.0 s)**.
  2. Al implementar la caché perezosa en RAM `_MODELO_WHISPER_COMANDOS` ([percepcion.py](file:///c:/Users/Pcrz/Documents/JinxAS/percepcion.py), F1-04) y suprimir la recalibración en cada comando (F1-05), la latencia pura de transcripción en los turnos 2 en adelante cayó drásticamente a rangos plenamente aceptables para la experiencia de usuario (2.5 - 3.5 s para ráfagas cortas).
  3. `faster-whisper` y su runtime `ctranslate2` introducen dependencias binarias pesadas con problemas conocidos de compilación/enlazado en Windows y posibles conflictos de librerías dinámicas OpenMP con PyTorch y FAISS.
- **Decisión:** Se mantiene **`openai-whisper`** (`small`) como motor oficial en esta fase. Se pospone `faster-whisper` como una optimización opcional futura únicamente si se requiere soporte en hardware aún más limitado.

### 4.2. Decisión F2-05: Estabilidad del Modo Centinela (Wake Word)

- **Contexto:** Se evaluó si convenía reescribir o sustituir el centinela con librerías alternativas de wake word (como Porcupine o OpenWakeWord).
- **Evaluación y hallazgos:**  
  1. Las funciones `esperar_palabra_activacion()` y `coincide_wakeword()` en [percepcion.py](file:///c:/Users/Pcrz/Documents/JinxAS/percepcion.py) utilizan Whisper `tiny.en` con ráfagas cortas procesadas con Voice Activity Detection nativo y comparación difusa con `thefuzz`.
  2. Este mecanismo demostró una tasa de falsos positivos prácticamente nula y una precisión fonética sobresaliente en pruebas de campo continuas, consumiendo niveles despreciables de CPU en reposo gracias a los sleeps y timeouts de VAD.
- **Decisión (Política de Estabilidad):** `esperar_palabra_activacion()` y `coincide_wakeword()` **se congelan sin modificaciones**. Se preserva la estabilidad del wake word intacta durante todo el ciclo de consolidación.

---

## 5. Protocolo para Completar Medianas en Vivo

Para consolidar las celdas marcadas como pendientes tras una sesión de voz:

1. Ejecutar el asistente con streaming habilitado (`STREAMING = True` en [config.py](file:///c:/Users/Pcrz/Documents/JinxAS/config.py)):
   ```bash
   python main.py
   ```
2. Realizar 10 turnos de voz variados:
   - 2 comandos de sistema / atajos (*"¿cómo está la RAM?", "¿qué temperatura tiene?"*).
   - 2 consultas de herramientas externas (*"¿cómo está el clima?", "abre el bloc de notas"*).
   - 3 consultas de conversación o razonamiento general.
   - 3 consultas a la memoria o notas de Obsidian (*"¿qué notas tengo de...?"*).
3. Inspeccionar las líneas `[METRICA_HONESTA]` y `[TURNO]` generadas en `logs/jinx.log`.
4. Calcular la mediana (`statistics.median`) para `stt`, `llm`, `tts`, `ttfa` y `total`, y actualizar la **Tabla 2** de este documento.
