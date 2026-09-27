# Guía de Solución de Problemas (Troubleshooting) — JinxAS

Esta guía contiene soluciones prácticas y comandos exactos para diagnosticar y resolver los problemas más comunes en **Windows 10 y Windows 11**.

---

## 1. 🎤 Fallo al Instalar PyAudio en Windows

### Causa
PyAudio requiere cabeceras de `portaudio.h`. Si tu sistema no cuenta con las herramientas de compilación de Microsoft Visual C++ instaladas, `pip install pyaudio` fallará al compilar el paquete desde el código fuente.

### Solución
Instala las ruedas (*wheels*) precompiladas oficiales para Windows (64 bits):

```powershell
# Opción A (Recomendada): Usar pipwin para instalar la rueda oficial de Windows
python -m pip install pipwin
pipwin install pyaudio

# Opción B: Si usas Python 3.12, instala directamente la rueda compilada
python -m pip install PyAudio>=0.2.14
```

Si continúas experimentando problemas, descarga la rueda `.whl` correspondiente a tu versión de Python (por ejemplo `PyAudio-0.2.14-cp312-cp312-win_amd64.whl`) e instálala con:
```powershell
pip install .\ruta\al\archivo.whl
```

---

## 2. 🔒 Permisos de Micrófono Bloqueados en Windows

### Causa
Las directivas de privacidad de Windows 10/11 bloquean por defecto el acceso al hardware de captura de audio a aplicaciones clásicas o consolas de terminal.

### Solución
1. Abre **Configuración** de Windows (`Win + I`).
2. Dirígete a **Privacidad y seguridad** > **Micrófono**.
3. Asegúrate de activar las siguientes opciones:
   - *Acceso al micrófono*: **Activado**.
   - *Permitir que las aplicaciones accedan al micrófono*: **Activado**.
   - *Permitir que las aplicaciones de escritorio accedan al micrófono*: **Activado** (verifica que `python.exe` o tu terminal aparezca permitida).
4. Reinicia la consola donde ejecutas Jinx.

---

## 3. 🦙 Ollama no Responde o Falta Modelo

### Causa
El servicio daemon de Ollama no está ejecutándose en segundo plano, o el modelo `qwen2.5:3b` aún no ha sido descargado.

### Solución
1. **Validar si Ollama está en ejecución:**
   Abre una terminal o tu navegador y visita:
   ```text
   http://localhost:11434
   ```
   Debe responder con: `Ollama is running`.

2. **Iniciar el servicio si está detenido:**
   Abre la app de escritorio de Ollama o ejecuta en PowerShell:
   ```powershell
   ollama serve
   ```

3. **Descargar el modelo obligatorio:**
   En otra ventana de consola, ejecuta:
   ```powershell
   ollama pull qwen2.5:3b
   ```

4. **Verificar modelos instalados:**
   ```powershell
   ollama list
   ```
   Asegúrate de que `qwen2.5:3b` aparezca listado.

---

## 4. 🦻 Centinela no Detecta Wake Word ("Jinx")

### Síntomas
La consola muestra `Esperando palabra de activación 'Jinx'...'`, pero al hablar el sistema no responde ni cambia de estado.

### Solución
1. **Verificar micrófono predeterminado en Windows:**
   - Ve a **Configuración** > **Sistema** > **Sonido** > **Entrada**.
   - Comprueba que tu micrófono activo esté seleccionado como *Dispositivo predeterminado*.
   - Verifica que la barra de volumen de entrada se mueva por encima del 50% al hablar.

2. **Calibración de Ruido Ambiental:**
   - Durante los primeros 2 segundos de arranque, Jinx calibra el umbral de energía (`energy_threshold`). Guarda silencio durante este breve intervalo inicial.

3. **Pronunciación y Variantes Fonéticas:**
   - El centinela evalúa fonéticamente variantes como `"jinx"`, `"jinks"`, `"sphinx"`. Pronuncia de forma clara y pausada: *"Jinx"*.

---

## 5. 🔇 Síntesis de Voz sin Audio

### Causa
`edge-tts` requiere conexión saliente a internet hacia los servidores de voz neuronal de Microsoft, o el mezclador de audio de `pygame` tiene el canal silenciado o en conflicto.

### Solución
1. **Comprobar salida de audio:**
   - Verifica que el volumen general no esté silenciado y que el dispositivo de reproducción sea el correcto.

2. **Verificar conectividad para Edge-TTS:**
   - Comprueba tu conexión a internet y prueba la síntesis manualmente con:
     ```powershell
     python -c "import edge_tts, asyncio; asyncio.run(edge_tts.Communicate('Hola, prueba de voz', 'es-MX-DaliaNeural').save('prueba.mp3'))"
     ```
   - Si genera el archivo `prueba.mp3`, Edge-TTS funciona con normalidad.

3. **Desbloqueo de Pygame Mixer:**
   - Si otra aplicación (como un DAW o juego) bloqueó el dispositivo WASAPI en modo exclusivo, ciérrala y reinicia Jinx.

---

## 6. ⏳ Primer Arranque Lento

### Causa
Durante el primer inicio absoluto, las librerías descargan y guardan en caché los pesos de los modelos locales:
- **Whisper small:** ~460 MB descargados a `~/.cache/whisper`.
- **Whisper tiny.en:** ~75 MB descargados para el modo centinela.
- **Sentence-Transformers MiniLM:** ~470 MB descargados a `~/.cache/huggingface/hub`.

### Diagnóstico y Solución
- Esta demora inicial de descarga **ocurre únicamente una vez**.
- En arranques posteriores, todos los modelos se cargan directamente desde el disco NVMe/SSD local en pocos segundos, operando 100% desconectados de la red para la inferencia.
