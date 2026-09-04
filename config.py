import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODELO_LLM = "qwen2.5:3b"
MODELO_WHISPER = "small"
IDIOMA_WHISPER = "es"
TIEMPO_MAXIMO_ESCUCHA = 8
PHRASE_TIME_LIMIT = 8
VOZ_TTS = "es-MX-DaliaNeural"
RUTA_VAULT = os.path.join(_BASE_DIR, "Boveda_Obsidian")
TITULO_NOTA_MAX = 80
PALABRA_ACTIVACION = "jinx"
MODELO_WAKEWORD = "tiny.en"
VARIANTES_WAKEWORD = ["jinx", "jinks", "sphinx"]

PROMPT_INICIAL_WHISPER = (
    "Asistente de voz llamado Jinx. Comandos de código, programación, Python, apagar, salir, consultas técnicas."
)

SYSTEM_PROMPT = """Eres Jinx, un asistente de voz local genial, directo, brillante y astuto.
Reglas obligatorias:
1. Responde SIEMPRE en español.
2. Mantén tus respuestas extremadamente concisas y breves (máximo 2 a 3 oraciones) porque tus respuestas se convertirán en audio hablado.
3. Habla con confianza, energía y un toque de chispa ingeniosa.
4. NUNCA digas que eres Qwen ni que fuiste creado por Alibaba Cloud. Eres Jinx.
5. Si el usuario pide una acción (estado del sistema, temperatura, abrir una app, guardar o buscar una nota), usa las herramientas proporcionadas. No inventes etiquetas de acción."""

MAPA_APLICACIONES = {
    "navegador": "msedge",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "chrome": "chrome",
    "google chrome": "chrome",
    "codigo": "code",
    "código": "code",
    "vscode": "code",
    "visual studio": "code",
    "visual studio code": "code",
    "code": "code",
    "bloc de notas": "notepad",
    "notas": "notepad",
    "notepad": "notepad",
    "calculadora": "calc",
    "calc": "calc",
    "terminal": "cmd",
    "cmd": "cmd",
    "consola": "cmd",
    "simbolo del sistema": "cmd",
    "spotify": "spotify",
    "discord": "discord",
}
