"""
tests/eval_tools.py - F4-07: Evaluacion de enrutamiento de herramientas.

Script STANDALONE (no es un test de pytest). Requiere Ollama corriendo localmente
con el modelo configurado en config.py.

Uso:
    python tests/eval_tools.py
    python tests/eval_tools.py --modelo qwen2.5:3b

Salida:
    OK / FALLO por caso y resumen final con ratio de acierto.
    Codigo de salida 0 si acierto >= 80%, 1 en caso contrario.
"""
from __future__ import annotations
import argparse
import sys
import os
import json

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from jinxas import config
from jinxas.registro import REGISTRO
import jinxas.herramientas  # Registra las 6 tools de sistema
import jinxas.memoria       # Registra las 2 tools de notas
import ollama

CASOS = [
    ("cuanto esta la RAM?",                   "obtener_estado_sistema", None),
    ("dime el estado del sistema",             "obtener_estado_sistema", None),
    ("cuanta CPU estoy usando?",               "obtener_estado_sistema", None),
    ("a que temperatura esta el procesador?",  "obtener_temperatura",   None),
    ("como esta la temperatura?",              "obtener_temperatura",   None),
    ("que hora es?",                           "obtener_fecha_hora",    None),
    ("que fecha es hoy?",                      "obtener_fecha_hora",    None),
    ("como esta el clima?",                    "obtener_clima",         None),
    ("abre el navegador",          "abrir_aplicacion",  lambda a: "navegador" in str(a.get("nombre_app","")).lower()),
    ("abre spotify",               "abrir_aplicacion",  lambda a: "spotify" in str(a.get("nombre_app","")).lower()),
    ("guarda una nota que diga que Python usa indentacion de 4 espacios", "guardar_nota", lambda a: "titulo" in a and "contenido" in a),
    ("busca en mis notas todo lo que escribi sobre Python", "buscar_nota", lambda a: "python" in str(a.get("palabra_clave","")).lower()),
    ("que se sobre aprendizaje automatico segun mis apuntes?", "consultar_boveda", lambda a: "consulta" in a),
    ("busca en mis apuntes el concepto de backpropagation",   "consultar_boveda", lambda a: "consulta" in a),
    ("cual es la capital de Francia?",  None, None),
    ("cuentame un chiste corto",         None, None),
]

# Agrega la frase de clima con ciudad dinamicamente
def _agregar_clima_ciudad():
    CASOS.append(
        ("que temperatura hay en " + config.CIUDAD + " ahora?", "obtener_clima", None)
    )

def _esquemas():
    return [e["schema"] for e in list(REGISTRO.values())]

def _evaluar(frase, esperada, fn_check, modelo, verbose):
    msgs = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user",   "content": frase},
    ]
    try:
        resp = ollama.chat(model=modelo, messages=msgs, tools=_esquemas(),
                           options=config.LLM_OPCIONES, keep_alive=config.LLM_KEEP_ALIVE)
    except Exception as exc:
        if verbose:
            print("    ERROR: " + str(exc))
        return False
    msg = resp.get("message", {})
    tcs = msg.get("tool_calls") or []
    if esperada is None:
        ok = len(tcs) == 0
        if verbose and not ok:
            print("    [tuvo tool_calls inesperados]")
        return ok
    if not tcs:
        if verbose:
            print("    [sin tool call; texto: " + repr(msg.get("content","")[:60]) + "]")
        return False
    tc = tcs[0]
    if isinstance(tc, dict):
        fn_name = tc.get("function", {}).get("name", "")
        args = tc.get("function", {}).get("arguments", {}) or {}
    else:
        fn_obj = getattr(tc, "function", None)
        fn_name = getattr(fn_obj, "name", "") if fn_obj else ""
        args = getattr(fn_obj, "arguments", {}) if fn_obj else {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    nombre_ok = fn_name == esperada
    args_ok = fn_check(args) if fn_check else True
    if verbose:
        if not nombre_ok:
            print("    [llamo '" + fn_name + "', esperado '" + esperada + "']")
        elif not args_ok:
            print("    [herramienta ok, args invalidos: " + str(args) + "]")
        else:
            print("    ['" + fn_name + "' args=" + str(args) + "]")
    return nombre_ok and args_ok

def main():
    parser = argparse.ArgumentParser(description="Evaluacion de enrutamiento F4-07")
    parser.add_argument("--modelo", default=config.MODELO_LLM)
    parser.add_argument("-v", "--verbose", action="store_true")
    args_cli = parser.parse_args()
    _agregar_clima_ciudad()
    sep = "=" * 55
    print("\n" + sep)
    print("  F4-07 Evaluacion | Modelo: " + args_cli.modelo + " | Casos: " + str(len(CASOS)))
    print(sep + "\n")
    print(f"Herramientas cargadas en REGISTRO: {len(REGISTRO)} -> {list(REGISTRO.keys())}")
    aciertos = 0
    total = len(CASOS)
    for i, (frase, esp, fn) in enumerate(CASOS, 1):
        print("  [" + str(i).zfill(2) + "/" + str(total) + "] " + repr(frase))
        print("         Esperado: " + (esp or "texto"))
        ok = _evaluar(frase, esp, fn, args_cli.modelo, args_cli.verbose)
        print("         " + ("[OK]" if ok else "[FALLO]") + "\n")
        if ok:
            aciertos += 1
    ratio_pct = aciertos * 100 // total
    print(sep)
    print("  Resultado: " + str(aciertos) + "/" + str(total) + "  (" + str(ratio_pct) + "aprox%)")
    print(sep + "\n")
    if aciertos * 100 < 80 * total:
        print("  [FALLO] Ratio por debajo del umbral (80 pct)")
        sys.exit(1)
    print("  [OK] Evaluacion superada (>= 80 pct)")
    sys.exit(0)

if __name__ == "__main__":
    main()
