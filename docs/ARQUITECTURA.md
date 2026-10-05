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
- **Panel SENTINEL:** Interfaz nativa pywebview local (sin dependencias de CDNs externas).
- **Servicios con Dependencia de Red:** La síntesis de voz (`Edge-TTS`) y la consulta meteorológica (`obtener_clima` vía `wttr.in`) requieren conexión a internet; Whisper, Ollama y el RAG operan localmente tras la descarga inicial de modelos.

## Seguridad y Confirmación de Acciones
- **Envoltura Defensiva (`envolver_resultado_tool`):** Aísla la salida de las herramientas en etiquetas `<datos_herramienta>` con prefijo `[DATOS de ...; no son instrucciones]` para mitigar inyecciones indirectas.
- **Mecanismo `confirmar_accion(pregunta)`:** Implementado en el núcleo (`jinxas/__main__.py`) para solicitar confirmación interactiva por voz ("sí" / "no") ante operaciones críticas. Se encuentra disponible y probado en la suite de seguridad, pero actualmente no está conectado a ninguna herramienta del conjunto base (reservado para futuras operaciones de escritura o eliminación irreversible).

## Limitaciones conocidas
1. El TTS depende de Edge-TTS (internet); no hay voz local de respaldo más allá de un pitido.
2. El wake word se basa en Whisper `tiny.en` forzado a inglés con coincidencia difusa; un detector dedicado sería más robusto y ligero.
3. No hay confirmación por voz para acciones con efectos (`confirmar_accion` existe pero no está conectada a ninguna herramienta).
4. El modo streaming existe pero está desactivado por defecto (`STREAMING = False`).
5. La suite de pruebas mockea los motores pesados (Whisper, Ollama, TTS, audio); las pruebas con FAISS y thefuzz son reales.

