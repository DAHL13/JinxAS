# 🛠️ Guía de Solución de Problemas (Troubleshooting) — JinxAS

Esta guía contiene soluciones prácticas y comandos exactos para diagnosticar y resolver los problemas más comunes en **Windows 10 y Windows 11**.

---

## 1. 🎤 PyAudio Falla al Instalar en Windows

### Causa
PyAudio requiere las cabeceras de compilación de `portaudio.h`. Si tu sistema no cuenta con las herramientas de compilación de Microsoft Visual C++ instaladas, `pip install pyaudio` fallará al compilar el paquete desde el código fuente.

### Solución
Instala las ruedas (*wheels*) precompiladas oficiales para tu versión de Python (64 bits):

```powershell
# Opción A (Recomendada): Usar pipwin para instalar la rueda oficial de Windows
python -m pip install pipwin
pipwin install pyaudio

# Opción B: Si usas Python 3.12, instala directamente la rueda compilada
python -m pip install PyAudio>=0.2.14
```

Si continúas experimentando problemas, descarga la rueda `.whl` correspondiente a tu versión de Python (por ejemplo `PyAudio-0.2.14-cp312-cp312-win_amd64.whl`) desde los repositorios comunitarios de ruedas precompiladas e instálala con:
```powershell
pip install .\ruta\al\archivo.whl
```

---

## 2. 🔒 Permisos de Micrófono Bloqueados en Windows

### Causa
Las directivas de privacidad de Windows 10/11 bloquean por defecto el acceso al hardware de captura de audio a las aplicaciones clásicas o consolas de terminal.

### Solución
1. Abre **Configuración** de Windows (`Win + I`).
2. Dirígete a **Privacidad y seguridad** > **Micrófono**.
3. Asegúrate de que las siguientes opciones estén activadas en **Activado**:
   - *Acceso al micrófono*.
   - *Permitir que las aplicaciones accedan al micrófono*.
   - *Permitir que las aplicaciones de escritorio accedan al micrófono* (asegúrate de que `python.exe` o tu terminal aparezca permitida).
4. Reinicia la terminal donde ejecutas Jinx.

---

## 3. 🦙 Ollama no Responde o Falta el Modelo

### Causa
El servicio daemon de Ollama no está en ejecución en segundo plano, o el modelo `qwen2.5:3b` aún no ha sido descargado en el equipo.

### Solución
1. **Comprobar si Ollama está corriendo:**
   Abre una terminal o tu navegador web y visita:
   ```text
   http://localhost:11434
   ```
   Debe responder con el mensaje: `Ollama is running`.

2. **Iniciar el servicio si está detenido:**
   Abre la aplicación de escritorio de Ollama desde el menú inicio o ejecuta en PowerShell:
   ```powershell
   ollama serve
   ```

3. **Descargar el modelo obligatorio:**
   En otra ventana de consola, descarga el modelo con:
   ```powershell
   ollama pull qwen2.5:3b
   ```

4. **Verificar modelos disponibles:**
   ```powershell
   ollama list
   ```
   Asegúrate de que `qwen2.5:3b` aparezca listado.

---

## 4. 🦻 Jinx no me Oye (Wake Word "Jinx" no Detectada)

### Síntomas
La consola muestra `Esperando palabra de activación 'Jinx'...'`, pero al pronunciar la palabra el sistema no responde ni cambia de estado en el panel.

### Solución
1. **Verificar el dispositivo de entrada predeterminado en Windows:**
   - Ve a **Configuración** > **Sistema** > **Sonido** > **Entrada**.
   - Comprueba que tu micrófono activo esté seleccionado como *Dispositivo predeterminado*.
   - Habla frente al micrófono y verifica que la barra de volumen de entrada se mueva por encima del 50%.

2. **Calibración de Ruido Ambiental:**
   - Al iniciar, Jinx toma 1 segundo para medir el ruido de fondo. Asegúrate de guardar silencio absoluto durante los primeros 2 segundos de arranque mientras calibra el umbral de energía acústica.

3. **Ajuste de Pronunciación y Variantes Fonéticas:**
   - El centinela evalúa fonéticamente variantes como `"jinx"`, `"jinks"`, `"sphinx"`. Pronuncia la palabra de forma clara y pausada: *"Jinx"*.

---

## 5. 🔇 La Síntesis de Voz no Suena

### Causa
`edge-tts` requiere conexión saliente a internet hacia los servidores de voz neuronal de Microsoft, o el mezclador de audio de `pygame` tiene el canal silenciado o redirigido a una salida incorrecta.

### Solución
1. **Comprobar salida de audio en Windows:**
   - Verifica que el volumen general no esté silenciado y que el dispositivo de salida sea el correcto (auriculares o altavoces).

2. **Verificar conexión de red para Edge-TTS:**
   - Prueba que tu conexión a internet esté activa y que tu firewall no bloquee las conexiones HTTPS y WebSocket salientes de Python.
   - Puedes probar la síntesis manualmente con:
     ```powershell
     python -c "import edge_tts, asyncio; asyncio.run(edge_tts.Communicate('Hola, prueba de voz', 'es-MX-DaliaNeural').save('prueba.mp3'))"
     ```
   - Si genera el archivo `prueba.mp3`, Edge-TTS funciona con normalidad.

3. **Conflicto de Pygame Mixer:**
   - Si otra aplicación (como un DAW o juego exclusivo) tiene bloqueado el dispositivo de audio WASAPI en modo exclusivo, ciérrala y reinicia Jinx.

---

## 6. ⏳ Primer Arranque Extremadamente Lento

### Causa
Durante el primer inicio absoluto del asistente, las librerías locales deben descargar y almacenar en caché los pesos de los modelos de inteligencia artificial:
- **Whisper `small`:** ~460 MB descargados desde HuggingFace/OpenAI a `~/.cache/whisper`.
- **Whisper `tiny.en`:** ~75 MB descargados para el modo centinela.
- **Sentence-Transformers `paraphrase-multilingual-MiniLM-L12-v2`:** ~470 MB descargados a `~/.cache/huggingface/hub`.

### Diagnóstico y Solución
- Esta demora inicial de descarga **ocurre únicamente una vez**.
- En arranques posteriores, todos los modelos se cargan directamente desde el disco NVMe/SSD local en pocos segundos, operando 100% desconectados de la red para la inferencia.
