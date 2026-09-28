import re

from jinxas import config
from jinxas.comandos import normalizar

REGLAS = [
    (re.compile(r"^(como esta la ram|estado del sistema)$"), "obtener_estado_sistema", lambda m: {}),
    (re.compile(r"^(que temperatura tiene|como esta la temperatura)$"), "obtener_temperatura", lambda m: {}),
    (re.compile(r"^(que hora es|dime la hora|que dia es|que dia es hoy|fecha y hora|que fecha es)$"), "obtener_fecha_hora", lambda m: {}),
]

_PATRON_ABRIR = re.compile(r"^abre (?:el |la |los |las )?(?P<app>.+)$")


def resolver_atajo(texto: str) -> tuple[str, dict] | None:
    t = normalizar(texto)
    for patron, tool, args_fn in REGLAS:
        if m := patron.match(t):
            return tool, args_fn(m)

    if m := _PATRON_ABRIR.match(t):
        app = m.group("app").strip()
        if app in config.MAPA_APLICACIONES:
            return "abrir_aplicacion", {"nombre_app": app}

    return None

