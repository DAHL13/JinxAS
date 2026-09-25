import re

from comandos import normalizar

REGLAS = [
    (re.compile(r"^abre (?:el |la |los |las )?(?P<app>.+)$"), "abrir_aplicacion", lambda m: {"nombre_app": m.group("app")}),
    (re.compile(r"^(como esta la ram|estado del sistema)$"), "obtener_estado_sistema", lambda m: {}),
    (re.compile(r"^(que temperatura tiene|como esta la temperatura)$"), "obtener_temperatura", lambda m: {}),
]


def resolver_atajo(texto: str) -> tuple[str, dict] | None:
    t = normalizar(texto)
    for patron, tool, args_fn in REGLAS:
        if m := patron.match(t):
            return tool, args_fn(m)
    return None
