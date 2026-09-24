from main import _extraer_llamada


def test_extraer_llamada_dict():
    nombre, args = _extraer_llamada({"function": {"name": "obtener_clima", "arguments": {}}})
    assert nombre == "obtener_clima" and args == {}
