"""
tests/test_f3_memoria.py
========================
Pruebas unitarias para las tareas F3-03 (buscar_nota recursivo) y
F3-04 (nombres seguros y prevencion de path traversal) del roadmap
de consolidacion de JinxAS.

Usa tmp_path y monkeypatch para aislar RUTA_VAULT sin tocar la
boveda real ni percepcion.py.
"""
import importlib
import os

import pytest

# ---------------------------------------------------------------------------
# Fixture: aisla RUTA_VAULT apuntando a un directorio temporal de prueba
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def vault_temporal(tmp_path, monkeypatch):
    """
    Redirige RUTA_VAULT (en config y en memoria) a un directorio
    temporal para que los tests no toquen Boveda_Obsidian real.
    Recarga memoria para que el modulo adopte el nuevo RUTA_VAULT.
    """
    vault = tmp_path / "vault"
    vault.mkdir()

    monkeypatch.setenv("JINX_VAULT", str(vault))

    import config
    importlib.reload(config)
    monkeypatch.setattr(config, "RUTA_VAULT", str(vault))

    import memoria
    importlib.reload(memoria)
    monkeypatch.setattr(memoria, "RUTA_VAULT", str(vault))

    yield vault

    importlib.reload(config)
    importlib.reload(memoria)


# ===========================================================================
# F3-04 -- _normalizar_nombre_archivo
# ===========================================================================

class TestNormalizarNombreArchivo:

    def test_titulo_normal(self):
        from memoria import _normalizar_nombre_archivo
        assert _normalizar_nombre_archivo("Mi nota de Python") == "Mi nota de Python.md"

    def test_titulo_con_extension_md(self):
        """Si el titulo ya termina en .md no debe duplicar la extension."""
        from memoria import _normalizar_nombre_archivo
        result = _normalizar_nombre_archivo("Mi nota.md")
        assert result.lower().endswith(".md")
        assert result.count(".md") == 1

    def test_nombre_reservado_CON(self):
        """'CON' es un nombre reservado de Windows -> debe prefijarse."""
        from memoria import _normalizar_nombre_archivo
        result = _normalizar_nombre_archivo("CON")
        assert result.lower() != "con.md"
        assert result.lower().endswith(".md")

    def test_nombre_reservado_minusculas(self):
        """Insensible a mayusculas para los reservados."""
        from memoria import _normalizar_nombre_archivo
        for reservado in ("con", "prn", "aux", "nul", "com1", "lpt9"):
            result = _normalizar_nombre_archivo(reservado)
            assert result.lower() != f"{reservado}.md", f"Fallo con: {reservado}"
            assert result.lower().endswith(".md")

    def test_titulo_solo_espacios(self):
        """Un titulo de solo espacios debe producir un nombre valido, no vacio."""
        from memoria import _normalizar_nombre_archivo
        result = _normalizar_nombre_archivo("   ")
        assert result.lower().endswith(".md")
        assert len(result) > 3

    def test_titulo_con_slash(self):
        """Los slashes deben eliminarse para evitar subdirectorios."""
        from memoria import _normalizar_nombre_archivo
        result = _normalizar_nombre_archivo("a/b:c")
        assert "/" not in result
        assert ":" not in result
        assert result.lower().endswith(".md")

    def test_titulo_con_punto_final(self):
        """Nombres terminados en punto son invalidos en Windows."""
        from memoria import _normalizar_nombre_archivo
        result = _normalizar_nombre_archivo("nota.")
        base = result[:-3]  # quitar ".md"
        assert not base.endswith(".")

    def test_titulo_con_path_traversal(self):
        """El path traversal debe eliminarse de caracteres ilegales."""
        from memoria import _normalizar_nombre_archivo
        result = _normalizar_nombre_archivo("..\\..\\x")
        assert "\\" not in result
        assert result.lower().endswith(".md")

    def test_truncado_a_max(self):
        """El nombre base no debe superar TITULO_NOTA_MAX caracteres."""
        from memoria import _normalizar_nombre_archivo
        from config import TITULO_NOTA_MAX
        titulo_largo = "A" * (TITULO_NOTA_MAX + 50)
        result = _normalizar_nombre_archivo(titulo_largo)
        base = result[:-3]
        assert len(base) <= TITULO_NOTA_MAX

    def test_caracteres_de_control(self):
        """Caracteres de control (\x00-\x1f) deben eliminarse."""
        from memoria import _normalizar_nombre_archivo
        result = _normalizar_nombre_archivo("nota\x00con\x1fcontrol")
        assert "\x00" not in result
        assert "\x1f" not in result
        assert result.lower().endswith(".md")


# ===========================================================================
# F3-04 -- _ruta_segura: confinamiento dentro de la boveda
# ===========================================================================

class TestRutaSegura:

    def test_nombre_valido_dentro_vault(self, vault_temporal):
        """Un nombre valido debe devolver una ruta dentro de la boveda."""
        import memoria
        ruta = memoria._ruta_segura("mi_nota.md")
        assert ruta.startswith(os.path.realpath(str(vault_temporal)))

    def test_path_traversal_lanza_valueerror(self, vault_temporal):
        """'..\\fuera.md' debe lanzar ValueError."""
        import memoria
        with pytest.raises(ValueError, match="fuera de la b"):
            memoria._ruta_segura("..\\fuera.md")

    def test_path_traversal_unix(self, vault_temporal):
        """'../fuera.md' tambien debe lanzar ValueError."""
        import memoria
        with pytest.raises(ValueError, match="fuera de la b"):
            memoria._ruta_segura("../fuera.md")

    def test_titulo_slash_normalizado_es_seguro(self, vault_temporal):
        """Un titulo normalizado (sin slash ni ..) siempre debe ser seguro."""
        from memoria import _normalizar_nombre_archivo, _ruta_segura
        nombre = _normalizar_nombre_archivo("a/b:c")
        ruta = _ruta_segura(nombre)
        assert os.path.realpath(str(vault_temporal)) in ruta

    def test_titulo_backslash_normalizado_es_seguro(self, vault_temporal):
        """Un titulo con backslash normalizado debe quedar dentro del vault."""
        from memoria import _normalizar_nombre_archivo, _ruta_segura
        nombre = _normalizar_nombre_archivo("..\\..\\x")
        ruta = _ruta_segura(nombre)
        assert os.path.realpath(str(vault_temporal)) in ruta


# ===========================================================================
# F3-03 -- buscar_nota: comportamiento recursivo e inteligente
# ===========================================================================

class TestBuscarNota:

    def _crear_nota(self, vault, relpath, contenido):
        ruta = vault / relpath
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    # -- Busqueda en subcarpetas --------------------------------------------

    def test_encuentra_en_subcarpeta(self, vault_temporal):
        """buscar_nota debe encontrar archivos .md dentro de subcarpetas."""
        import memoria
        self._crear_nota(
            vault_temporal, "subcarpeta/python.md",
            "# Python\n\nLenguaje de programacion orientado a objetos.",
        )
        resultado = memoria.buscar_nota("python")
        assert "python" in resultado.lower()

    def test_encuentra_en_subcarpeta_anidada(self, vault_temporal):
        """Debe funcionar con anidamiento de multiples niveles."""
        import memoria
        self._crear_nota(
            vault_temporal, "nivel1/nivel2/nota_profunda.md",
            "Contenido sobre recursividad.",
        )
        resultado = memoria.buscar_nota("recursividad")
        assert "recursividad" in resultado.lower()

    # -- Ignorar carpetas ocultas -------------------------------------------

    def test_ignora_carpeta_obsidian(self, vault_temporal):
        """No debe indexar archivos dentro de .obsidian/."""
        import memoria
        self._crear_nota(
            vault_temporal, ".obsidian/config.md",
            "Configuracion privada de obsidian con termino_oculto.",
        )
        resultado = memoria.buscar_nota("termino_oculto")
        assert "termino_oculto" not in resultado.lower()

    def test_ignora_carpeta_trash(self, vault_temporal):
        """No debe indexar archivos dentro de .trash/."""
        import memoria
        self._crear_nota(
            vault_temporal, ".trash/borrada.md",
            "Esta nota fue eliminada. Contiene palabra_borrada.",
        )
        resultado = memoria.buscar_nota("palabra_borrada")
        assert "palabra_borrada" not in resultado.lower()

    def test_ignora_cualquier_carpeta_oculta(self, vault_temporal):
        """Cualquier carpeta que empiece con '.' debe ignorarse."""
        import memoria
        self._crear_nota(
            vault_temporal, ".oculta/secreto.md",
            "Dato secreto sobre algoritmos_secretos.",
        )
        resultado = memoria.buscar_nota("algoritmos_secretos")
        assert "algoritmos_secretos" not in resultado.lower()

    # -- Priorizacion: coincidencias en el titulo primero ------------------

    def test_prioriza_coincidencia_en_titulo(self, vault_temporal):
        """Las notas cuyo titulo contiene el termino deben aparecer antes."""
        import memoria
        # Nota con coincidencia solo en contenido
        self._crear_nota(
            vault_temporal, "otro_tema.md",
            "Texto que menciona django en el contenido.",
        )
        # Nota con coincidencia en el titulo
        self._crear_nota(
            vault_temporal, "django.md",
            "Framework web para Python.",
        )
        resultado = memoria.buscar_nota("django")
        pos_titulo = resultado.lower().find("**django**")
        pos_contenido = resultado.lower().find("**otro_tema**")
        assert pos_titulo != -1, "Debe encontrar la nota cuyo titulo es 'django'"
        assert pos_titulo < pos_contenido, "La nota con coincidencia en titulo debe aparecer primero"

    # -- Limite de 5 resultados --------------------------------------------

    def test_maximo_5_resultados(self, vault_temporal):
        """No debe devolver mas de 5 notas aunque haya mas coincidencias."""
        import memoria
        for i in range(8):
            self._crear_nota(
                vault_temporal, f"nota_{i}.md",
                "Texto que contiene el termino_comun.",
            )
        resultado = memoria.buscar_nota("termino_comun")
        # Cada resultado empieza con el emoji de documento
        total = resultado.count("\U0001f4c4 **")
        assert total <= 5, f"Se devolvieron {total} notas, maximo permitido: 5"

    # -- Truncado de extractos a ~200 caracteres ---------------------------

    def test_trunca_extracto_largo(self, vault_temporal):
        """Los extractos de lineas largas deben truncarse a ~200 caracteres."""
        import memoria
        linea_larga = "termino_largo " + ("X" * 300)
        self._crear_nota(
            vault_temporal, "nota_larga.md",
            f"# Nota\n\n{linea_larga}\n",
        )
        resultado = memoria.buscar_nota("termino_largo")
        assert "..." in resultado
        lineas = resultado.splitlines()
        for linea in lineas:
            if linea.startswith("  →"):
                extracto = linea[4:]  # quitar "  -> "
                assert len(extracto) <= 203, (
                    f"Extracto demasiado largo ({len(extracto)} chars): {extracto[:50]}..."
                )

    # -- Casos borde -------------------------------------------------------

    def test_vault_vacio(self, vault_temporal):
        """Si no hay notas, debe retornar un mensaje claro."""
        import memoria
        resultado = memoria.buscar_nota("cualquier_cosa")
        assert "vac" in resultado or "no se encontraron" in resultado.lower()

    def test_termino_inexistente(self, vault_temporal):
        """Si no hay coincidencias, mensaje adecuado."""
        import memoria
        self._crear_nota(vault_temporal, "nota.md", "Contenido irrelevante.")
        resultado = memoria.buscar_nota("xyzzy_inexistente")
        assert "no se encontraron" in resultado.lower()

    def test_termino_vacio(self, vault_temporal):
        """Termino vacio debe retornar mensaje de error."""
        import memoria
        resultado = memoria.buscar_nota("   ")
        assert "no se proporcion" in resultado.lower() or "palabra clave" in resultado.lower()
