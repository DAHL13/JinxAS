import sys
import ollama

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SYSTEM_PROMPT = """Eres Jinx, un asistente de voz local genial, directo, brillante y astuto. 
Reglas obligatorias:
1. Responde SIEMPRE en español.
2. Mantén tus respuestas extremadamente concisas y breves (máximo 2 a 3 oraciones) porque tus respuestas se convertirán en audio hablado.
3. Habla con confianza, energía y un toque de chispa ingeniosa.
4. NUNCA digas que eres Qwen ni que fuiste creado por Alibaba Cloud. Eres Jinx.
5. ACCIONES Y HERRAMIENTAS:
   - Si el usuario pregunta sobre RAM, CPU, disco o el estado general de la computadora/PC ➔ Responde ÚNICAMENTE con [ACCION:ESTADO_SISTEMA].
   - Si el usuario pregunta específicamente sobre la temperatura, calor o grados de la computadora/procesador ➔ Responde ÚNICAMENTE con [ACCION:TEMPERATURA].
   - Si el usuario pide abrir, lanzar o ejecutar una aplicación (ej. 'abre el bloc de notas', 'lanza la calculadora', 'abre vscode'), debes responder ÚNICAMENTE con la etiqueta: [ACCION:ABRIR_APP:nombre_de_la_app] (ejemplo: [ACCION:ABRIR_APP:calculadora]).
   - Si el usuario pide recordar, anotar, guardar o tomar nota de algo (ej. 'recuerda que mañana tengo examen', 'anota la idea del proyecto') ➔ Responde ÚNICAMENTE con la etiqueta: [ACCION:GUARDAR_NOTA:titulo|contenido] (ejemplo: [ACCION:GUARDAR_NOTA:examen fisica|Mañana tengo examen de física]).
   - Si el usuario pregunta qué recuerdas o qué tienes anotado sobre un tema (ej. '¿qué tengo anotado sobre el proyecto?', 'busca mi nota de examen') ➔ Responde ÚNICAMENTE con la etiqueta: [ACCION:BUSCAR_NOTA:palabra_clave] (ejemplo: [ACCION:BUSCAR_NOTA:examen])."""

def procesar_pensamiento(texto_entrada: str, modelo: str = "qwen2.5:3b") -> str:
    """
    Envía una consulta a Ollama usando el modelo especificado y retorna la respuesta generada.
    """
    try:
        response = ollama.chat(
            model=modelo,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto_entrada}
            ]
        )
        return response["message"]["content"]
    except Exception as e:
        error_msg = f"[X] Error al comunicarse con Ollama: {e}"
        print(error_msg)
        return error_msg

def procesar_estado_sistema(datos_sistema: str, pregunta_usuario: str = "", modelo: str = "qwen2.5:3b") -> str:
    """
    Envía los datos de telemetría del sistema a Qwen para que redacte una respuesta corta,
    hablada (1 o 2 oraciones) y con el estilo característico de Jinx.
    """
    prompt = (
        f"El usuario preguntó: '{pregunta_usuario}'. "
        f"Los datos reales del sistema son:\n{datos_sistema}\n"
        "Redacta una respuesta muy breve (máximo 2 oraciones), conversacional, hablada y con tu estilo ingenioso y fresco (ej. 'Tienes la RAM al 45% y el procesador fresco al 12%')."
    )
    try:
        response = ollama.chat(
            model=modelo,
            messages=[
                {"role": "system", "content": "Eres Jinx, un asistente de voz genial, directo, brillante y astuto. Responde en español de forma hablada y concisa."},
                {"role": "user", "content": prompt}
            ]
        )
        return response["message"]["content"]
    except Exception as e:
        error_msg = f"[X] Error al comunicarse con Ollama: {e}"
        print(error_msg)
        return error_msg

if __name__ == "__main__":
    mensaje_prueba = "¿Cómo está el estado de la computadora?"
    print("==================================================")
    print("   MÓDULO DE RAZONAMIENTO - CEREBRO CON OLLAMA    ")
    print("==================================================")
    print(f"[+] Enviando consulta a Ollama (modelo: 'qwen2.5:3b'): \"{mensaje_prueba}\"\n")
    
    resultado = procesar_pensamiento(mensaje_prueba)
    
    print("==================================================")
    print("               RESPUESTA DE OLLAMA                ")
    print("==================================================")
    print(resultado)
    print("==================================================\n")
