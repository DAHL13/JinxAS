# Verificación Manual en Equipo Windows — JinxAS v0.5.3

Esta lista debe ser completada manualmente por el usuario en su equipo con Windows, micrófono, altavoces y aplicaciones instaladas.

| # | Prueba | Resultado esperado | ¿Pasó? (☐/☑) | Fecha | Notas |
|---|--------|--------------------|---------------|-------|-------|
| 1 | Emergency Flush: decir un dato, pulsar Flush, preguntar por ese dato | No lo recuerda | ☐ | | |
| 2 | Pulsar "Repetir" tras una respuesta | Suena una sola vez | ☐ | | |
| 3 | Decir "think", "thanks", "links", "sinks" sin decir "Jinx" | No se activa | ☐ | | |
| 4 | Decir "Jinx" (y variantes como "Jynx"/"Ginx" si Whisper las produce) | Se activa | ☐ | | |
| 5 | Pedir "abre el navegador" y "abre Chrome" | Ambos se abren | ☐ | | |
| 6 | Consulta RAG con 3 fragmentos relevantes | La respuesta usa los tres datos | ☐ | | |
| 7 | Dictar una nota de ~15 s | Se guarda completa | ☐ | | |
| 8 | Revisar `logs/jinx.log` en INFO | No contiene lo que dijiste | ☐ | | |
| 9 | Borrar `indice.faiss` del caché y reiniciar | Se reconstruye y las notas se encuentran | ☐ | | |
| 10 | Vaciar una nota en Obsidian y reiniciar | No reconstruye todo el índice (ver log) | ☐ | | |
| 11 | Arrancar sin internet y hablar | Falla solo el TTS (pitido de respaldo); el resto responde | ☐ | | |

Estado de la CI en GitHub (a completar tras el push): EN VERDE (`success` — run `37374439576` en `windows-latest`, verificado el 2026-10-05)

Veredicto tras verificación manual: ______
