import re
import sys
# pyrefly: ignore [missing-import]
import speech_recognition as sr

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROMPT_INICIAL_DEFAULT = (
    "Asistente de voz llamado Jinx. Comandos de código, programación, Python, apagar, salir, consultas técnicas."
)

def limpiar_texto_transcrito(texto: str) -> str:
    """
    Limpia el texto transcrito eliminando espacios duplicados,
    caracteres no imprimibles y signos extraños al inicio/final.
    """
    if not texto:
        return ""
    
    # Eliminar caracteres de control no imprimibles
    texto = "".join(ch for ch in texto if ch.isprintable())
    
    # Normalizar espacios en blanco múltiples a uno solo
    texto = re.sub(r"\s+", " ", texto).strip()
    
    # Eliminar signos de puntuación o caracteres extraños al inicio o final
    texto = re.sub(r"^[\s\-_~`\"'«»“”„*#]+|[\s\-_~`\"'«»“”„*#]+$", "", texto)
    
    return texto.strip()

def escuchar_y_transcribir(
    modelo="small",
    tiempo_maximo=8,
    phrase_time_limit=8,
    initial_prompt=PROMPT_INICIAL_DEFAULT
):
    """
    Inicializa el micrófono, calibra el ruido ambiental y escucha por un máximo de tiempo_maximo segundos.
    Transcribe el audio usando el modelo Whisper local optimizado en español ('es')
    con un prompt inicial de contexto técnico.
    """
    recognizer = sr.Recognizer()
    
    # Ajustes finos de reconocimiento
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    recognizer.pause_threshold = 0.8  # Pausa tras la cual se considera finalizada la frase

    print("==================================================")
    print("   MÓDULO DE PERCEPCIÓN - ASISTENTE DE VOZ LOCAL  ")
    print("==================================================")

    try:
        with sr.Microphone() as source:
            print("\n[+] Calibrando ruido ambiental... Por favor guarda silencio un momento.")
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            print(f"[+] Umbral de energía establecido en: {recognizer.energy_threshold:.2f}")

            print(f"\n[🎤] Escuchando... (habla ahora, máximo {phrase_time_limit} segundos)")
            try:
                # Escuchar con límite de tiempo y tiempo máximo de frase
                audio = recognizer.listen(
                    source,
                    timeout=tiempo_maximo,
                    phrase_time_limit=phrase_time_limit
                )
                print("[✓] Audio capturado exitosamente. Procesando con Whisper...")

            except sr.WaitTimeoutError:
                print("[!] Tiempo de espera agotado: no se detectó voz dentro del tiempo límite.")
                return None

    except OSError as e:
        print(f"\n[X] Error de PyAudio / Micrófono: {e}")
        print("    -> Verifica que tu micrófono esté conectado y que Windows tenga activados los permisos de micrófono.")
        return None
    except Exception as e:
        print(f"\n[X] Error al inicializar el micrófono: {e}")
        return None

    # Transcripción con Whisper local a través de SpeechRecognition
    try:
        print(f"[+] Transcribiendo audio con Whisper (modelo '{modelo}', idioma 'es')...")
        texto_transcrito = recognizer.recognize_whisper(
            audio,
            model=modelo,
            language="es",
            initial_prompt=initial_prompt
        )
        
        texto_limpio = limpiar_texto_transcrito(texto_transcrito)
        print("\n==================================================")
        print("           RESULTADO DE LA TRANSCRIPCIÓN          ")
        print("==================================================")
        print(f"Texto reconocido: \"{texto_limpio}\"")
        print("==================================================\n")
        return texto_limpio if texto_limpio else None

    except sr.UnknownValueError:
        print("[!] Whisper no pudo entender el audio.")
        return None
    except sr.RequestError as e:
        print(f"[X] Error en el motor de Whisper: {e}")
        return None
    except Exception as e:
        print(f"[X] Error inesperado durante la transcripción: {e}")
        return None

if __name__ == "__main__":
    # Usa 'small' para mejor precisión en español y reconocimiento de contexto
    escuchar_y_transcribir(modelo="small", tiempo_maximo=7)
