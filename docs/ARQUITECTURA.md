# Arquitectura de JinxAS

```mermaid
flowchart LR
  MIC[Micrófono] --> C[Centinela · Whisper tiny.en]
  C --> W[Whisper small]
  W --> R{¿Atajo?}
  R -- sí --> T[Herramientas]
  R -- no --> L[Ollama · qwen2.5:3b]
  L <--> T
  T --> M[(Bóveda + FAISS)]
  L --> V[Edge-TTS + pygame]
  L --> P[Panel SENTINEL]
```

## Subsistemas Principales
- **Pipeline de Audio Concurrente:** Desacopla el hilo principal (bucle de pywebview) del bucle secundario daemon para escucha centinela y síntesis de voz.
- **Capa de Atajos Deterministas:** Resolución inmediata mediante expresiones regulares (0 ms de inferencia LLM) para comandos de hardware, apps y hora.
- **Motor Cognitivo Local:** Inferencia local con Qwen 2.5 3B vía Ollama, registro declarativo `@herramienta` y envoltura defensiva contra inyecciones de datos.
- **Memoria Semántica y RAG:** Bóveda Markdown compatible con Obsidian indexada con FAISS e embeddings de SentenceTransformers en `.jinx_cache/`.
- **Panel SENTINEL:** Interfaz nativa pywebview 100% offline, sin dependencias de CDNs externas.
