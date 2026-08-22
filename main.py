import re
import sys
import time
from percepcion import escuchar_y_transcribir
from cerebro import procesar_pensamiento, procesar_estado_sistema
from voz import reproducir_voz
from herramientas import obtener_estado_sistema, obtener_temperatura, abrir_aplicacion
from memoria import guardar_nota, buscar_nota

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def iniciar_asistente():
    print("==================================================")
    print("       JINX ASISTENTE - ASISTENTE DE VOZ LOCAL    ")
    print("==================================================")
    print("[*] Di 'salir', 'cancelar', 'apagar', 'detener' o presiona Ctrl+C para salir.\n")

    while True:
        try:
            print("\n[🎤] Escuchando tu comando...")
            texto_usuario = escuchar_y_transcribir(modelo="small", tiempo_maximo=8, phrase_time_limit=8)

            if texto_usuario and texto_usuario.strip():
                texto_limpio = texto_usuario.strip().lower()
                palabras_salida = ["salir", "cancelar", "apagar", "detener"]

                if any(palabra in texto_limpio for palabra in palabras_salida):
                    print("\n[+] Cerrando asistente Jinx...")
                    reproducir_voz("Hasta luego, apagando sistema.")
                    break

                print(f"\n[🧠] Procesando respuesta para: \"{texto_usuario.strip()}\"...")
                respuesta = procesar_pensamiento(texto_usuario.strip(), modelo="qwen2.5:3b")

                # Detección y ejecución de acciones de telemetría y herramientas
                if "[ACCION:ESTADO_SISTEMA]" in respuesta:
                    print("\n[⚙️] Acción detectada: Obteniendo estado general del sistema...")
                    datos_sistema = obtener_estado_sistema()
                    print(f"[📊] Telemetría capturada:\n{datos_sistema}")
                    
                    print("\n[🧠] Jinx adaptando respuesta con estilo hablado...")
                    respuesta = procesar_estado_sistema(datos_sistema, pregunta_usuario=texto_usuario.strip(), modelo="qwen2.5:3b")

                elif "[ACCION:TEMPERATURA]" in respuesta:
                    print("\n[🌡️] Acción detectada: Obteniendo temperatura del sistema...")
                    datos_temp = obtener_temperatura()
                    print(f"[📊] Datos de temperatura capturados:\n{datos_temp}")
                    
                    print("\n[🧠] Jinx adaptando respuesta con estilo hablado...")
                    respuesta = procesar_estado_sistema(datos_temp, pregunta_usuario=texto_usuario.strip(), modelo="qwen2.5:3b")

                elif "[ACCION:ABRIR_APP:" in respuesta:
                    print("\n[🚀] Acción detectada: Abrir aplicación...")
                    match = re.search(r"\[ACCION:ABRIR_APP:([^\]]+)\]", respuesta)
                    if match:
                        nombre_app = match.group(1).strip()
                    else:
                        nombre_app = respuesta.split("[ACCION:ABRIR_APP:")[1].replace("]", "").strip()

                    print(f"[📂] Solicitando apertura de: '{nombre_app}'...")
                    resultado_apertura = abrir_aplicacion(nombre_app)
                    print(f"[✓] Resultado: {resultado_apertura}")

                    print("\n[🧠] Jinx generando confirmación hablada...")
                    prompt_app = (
                        f"El usuario pidió abrir '{nombre_app}'. El resultado fue: '{resultado_apertura}'. "
                        f"Genera una confirmación muy corta (1 oración), hablada y con estilo Jinx (ej. 'Abriendo {nombre_app} de inmediato')."
                    )
                    respuesta = procesar_pensamiento(prompt_app, modelo="qwen2.5:3b")

                elif "[ACCION:GUARDAR_NOTA:" in respuesta:
                    print("\n[📝] Acción detectada: Guardar nota en la bóveda...")
                    match = re.search(r"\[ACCION:GUARDAR_NOTA:([^|\]]+)\|([^\]]+)\]", respuesta)
                    if match:
                        titulo_nota = match.group(1).strip()
                        contenido_nota = match.group(2).strip()
                    else:
                        # Fallback: extraer todo el bloque
                        bloque = respuesta.split("[ACCION:GUARDAR_NOTA:")[1].replace("]", "").strip()
                        partes = bloque.split("|", 1)
                        titulo_nota = partes[0].strip()
                        contenido_nota = partes[1].strip() if len(partes) > 1 else texto_usuario.strip()

                    print(f"[💾] Guardando nota: '{titulo_nota}'...")
                    resultado_nota = guardar_nota(titulo_nota, contenido_nota)
                    print(f"[✓] {resultado_nota}")

                    print("\n[🧠] Jinx generando confirmación hablada...")
                    prompt_nota = (
                        f"El usuario pidió guardar una nota con título '{titulo_nota}'. "
                        f"El resultado fue: '{resultado_nota}'. "
                        f"Genera una confirmación muy corta (1 oración), hablada y con estilo Jinx."
                    )
                    respuesta = procesar_pensamiento(prompt_nota, modelo="qwen2.5:3b")

                elif "[ACCION:BUSCAR_NOTA:" in respuesta:
                    print("\n[🔍] Acción detectada: Buscar en la bóveda...")
                    match = re.search(r"\[ACCION:BUSCAR_NOTA:([^\]]+)\]", respuesta)
                    palabra_clave = match.group(1).strip() if match else texto_usuario.strip()

                    print(f"[📖] Buscando notas sobre: '{palabra_clave}'...")
                    resultado_busqueda = buscar_nota(palabra_clave)
                    print(f"[📄] Resultado:\n{resultado_busqueda}")

                    print("\n[🧠] Jinx generando respuesta hablada con los resultados...")
                    prompt_busqueda = (
                        f"El usuario preguntó qué tienes anotado sobre '{palabra_clave}'. "
                        f"El resultado de la búsqueda fue:\n{resultado_busqueda}\n"
                        f"Genera una respuesta muy breve (máximo 2 oraciones), conversacional y con estilo Jinx."
                    )
                    respuesta = procesar_pensamiento(prompt_busqueda, modelo="qwen2.5:3b")

                print("\n==================================================")
                print("                  RESPUESTA JINX                  ")
                print("==================================================")
                print(respuesta)
                print("==================================================")

                print("\n[🔊] Jinx respondiendo con voz...")
                reproducir_voz(respuesta)
                time.sleep(0.8)  # Purga el buffer del micrófono y evita captura de eco
            else:
                print("[!] No se detectó ninguna instrucción clara. Reintentando...")
                continue

        except KeyboardInterrupt:
            print("\n\n[+] Cerrando asistente Jinx...")
            break
        except Exception as e:
            print(f"\n[X] Ocurrió un error en el ciclo principal: {e}")

if __name__ == "__main__":
    try:
        iniciar_asistente()
    except KeyboardInterrupt:
        print("\n\n[+] Cerrando asistente Jinx...")


