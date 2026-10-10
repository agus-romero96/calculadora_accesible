"""
Traducciones: los catálogos (es.json, en.json) deben cubrir todos los textos del
código, con los mismos {marcadores}, y los resultados en inglés no deben dejar texto
en español.
"""
import json
import os
import re
import string

import pytest

import i18n
from catalogos import textos_marcados
from conftest import RAIZ, primera_linea


def marcadores(texto):
    return {campo for _, campo, _, _ in string.Formatter().parse(texto) if campo}


CATALOGO_EN = json.load(open(os.path.join(RAIZ, "locales", "en.json"), encoding="utf-8"))
CATALOGO_ES = json.load(open(os.path.join(RAIZ, "locales", "es.json"), encoding="utf-8"))
TEXTOS = textos_marcados()


def test_se_encontraron_textos():
    assert len(TEXTOS) > 300  # si baja de golpe, la extracción dejó de funcionar


@pytest.mark.parametrize("texto", sorted(TEXTOS))
def test_texto_tiene_traduccion_inglesa(texto):
    assert texto in CATALOGO_EN, f"Falta traducción ({TEXTOS[texto]}): {texto!r}"


@pytest.mark.parametrize("texto", sorted(CATALOGO_EN))
def test_traduccion_conserva_marcadores(texto):
    assert marcadores(texto) == marcadores(CATALOGO_EN[texto]), texto


def test_catalogo_sin_textos_obsoletos():
    sobrantes = sorted(set(CATALOGO_EN) - set(TEXTOS))
    assert not sobrantes, f"Traducciones que ya no se usan: {sobrantes}"


# ---------------- Catálogo del español (editable) ----------------

def test_catalogo_espanol_completo():
    """Para añadir los textos nuevos y quitar los que sobran: python -X utf8 catalogos.py"""
    faltan = sorted(set(TEXTOS) - set(CATALOGO_ES))
    sobran = sorted(set(CATALOGO_ES) - set(TEXTOS))
    assert not faltan and not sobran, f"Ejecute catalogos.py. Faltan: {faltan}. Sobran: {sobran}"


@pytest.mark.parametrize("texto", sorted(CATALOGO_ES))
def test_espanol_conserva_marcadores(texto):
    assert marcadores(texto) == marcadores(CATALOGO_ES[texto]), texto


@pytest.fixture
def catalogo_es_editado(tmp_path, monkeypatch):
    """Un es.json con un texto cambiado, en una carpeta de locales temporal."""
    editado = dict(CATALOGO_ES, **{"RESULTADO: {valor}": "LA RESPUESTA ES {valor}"})
    (tmp_path / "es.json").write_text(json.dumps(editado, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(i18n, "carpeta_locales", lambda: str(tmp_path))
    monkeypatch.delenv(i18n.TEXTOS_ORIGEN)
    yield tmp_path
    monkeypatch.undo()
    i18n.establecer_idioma("es")


def test_es_json_cambia_el_texto_mostrado(core, catalogo_es_editado):
    i18n.establecer_idioma("es")
    assert primera_linea(core.Derivar("x^3")) == "LA RESPUESTA ES 3*x**2"


def test_es_json_danado_usa_los_textos_del_codigo(core, catalogo_es_editado):
    (catalogo_es_editado / "es.json").write_text('{"RESULTADO: {valor}": ', encoding="utf-8")
    i18n.establecer_idioma("es")
    assert primera_linea(core.Derivar("x^3")) == "RESULTADO: 3*x**2"


def test_es_json_ausente_usa_los_textos_del_codigo(core, catalogo_es_editado):
    (catalogo_es_editado / "es.json").unlink()
    i18n.establecer_idioma("es")
    assert primera_linea(core.Derivar("x^3")) == "RESULTADO: 3*x**2"


def test_marcador_mal_escrito_no_rompe_el_calculo(core, catalogo_es_editado):
    editado = {"RESULTADO: {valor}": "RESULTADO: {valoor}"}
    (catalogo_es_editado / "es.json").write_text(json.dumps(editado), encoding="utf-8")
    i18n.establecer_idioma("es")
    assert primera_linea(core.Derivar("x^3")) == "RESULTADO: 3*x**2"


def test_textos_origen_ignora_es_json(catalogo_es_editado, monkeypatch):
    monkeypatch.setenv(i18n.TEXTOS_ORIGEN, "1")
    assert i18n.cargar_catalogo("es") == {}


def test_ayuda_existe_en_cada_idioma():
    for codigo in i18n.IDIOMAS:
        assert os.path.exists(os.path.join(RAIZ, "locales", f"ayuda_{codigo}.txt"))


@pytest.mark.parametrize("codigo", sorted(i18n.IDIOMAS))
def test_wxwidgets_conoce_cada_idioma(codigo):
    """main.py busca el idioma de wx por su código y setup.py copia su catálogo."""
    wx = pytest.importorskip("wx")
    assert wx.Locale.FindLanguageInfo(codigo) is not None, codigo
    if codigo in i18n.catalogos_wx():
        catalogo = os.path.join(os.path.dirname(wx.__file__), "locale", codigo, "LC_MESSAGES", "wxstd.mo")
        assert os.path.exists(catalogo), f"wxWidgets no trae catálogo para {codigo!r}"


def test_catalogos_wx_excluyen_el_ingles():
    assert i18n.catalogos_wx() == ["es"]


# ---------------- Resultados en inglés ----------------

@pytest.fixture
def ingles():
    i18n.establecer_idioma("en")
    yield
    i18n.establecer_idioma("es")


# Señales de texto en español que no deberían aparecer en inglés
ESPANOL = re.compile(r"[áéíóúñÁÉÍÓÚÑ¿¡]|\b(?:RESULTADO|MÉTODO|Paso|Expresión|Límite|Derivada|Ecuación|"
                     r"Sistema de|Error de|Estrategia|Diagnóstico|Aplicamos|Calculamos|Sustitución|"
                     r"numerador|denominador|Se |Por |para |con )\b")

OPERACIONES = [
    lambda c: c.Evaluar("2+2"), lambda c: c.Evaluar("2*pi"), lambda c: c.Evaluar("x+1"),
    lambda c: c.Simplificar("(x^2-1)/(x-1)"), lambda c: c.Factorizar("x^2-9"), lambda c: c.Factorizar("x^2+1"),
    lambda c: c.Factorizar("x^3-8"), lambda c: c.Factorizar("2*x^2-18"),
    lambda c: c.Derivar("x^2*sin(x)"), lambda c: c.Derivar("sin(x)/x"), lambda c: c.Derivar("x^x"),
    lambda c: c.Derivar("sin(x^2)"), lambda c: c.Derivar("2^x"), lambda c: c.Derivar("xsin(x)"),
    lambda c: c.DerivadaEnecima("x^5", "x", 3), lambda c: c.Integrar("x*exp(x)"), lambda c: c.Integrar("3*x^2+2*x"),
    lambda c: c.Integrar("exp(-x^2)"), lambda c: c.Integrar("5"),
    lambda c: c.CalcularLimite("sin(x)/x", "x", "0"), lambda c: c.CalcularLimite("(sqrt(1+x)-1)/x", "x", "0"),
    lambda c: c.CalcularLimite("(3*x^2+1)/(5*x^2-7)", "x", "oo"), lambda c: c.CalcularLimite("abs(x)/x", "x", "0"),
    lambda c: c.CalcularLimite("(x^2-1)/(x-1)", "x", "1"), lambda c: c.CalcularLimite("log((x^2-1)/(x-1))", "x", "1"),
    lambda c: c.CalcularLimite("x/(sqrt(x^2+1)-x)", "x", "oo"), lambda c: c.CalcularLimite("1/x", "x", "0+"),
    lambda c: c.CalcularLimite("(1+1/x)^x", "x", "infinity"), lambda c: c.CalcularLimite("sin(x", "x", "0"),
    lambda c: c.ResolverSistemaGauss(["x + y = 10", "x - y = 2"]),
    lambda c: c.ResolverSistemaGauss(["x + y = 1", "2x + 2y = 2"]),
    lambda c: c.ResolverSistemaGauss(["x + y = 1", "x + y = 2"]),
    lambda c: c.ResolverSistemaGauss(["x+y=1=2", "x-y=0"]),
    lambda c: c.ResolverSistemaEducativo(["x + y = 10", "x - y = 2"], "sustitucion"),
    lambda c: c.ResolverSistemaEducativo(["2x + 3y = 8", "x - y = -1"], "igualacion"),
    lambda c: c.ResolverSistemaEducativo(["x + y = 10", "x - y = 2"], "reduccion"),
    lambda c: c.ResolverSistemaEducativo(["x + y = 1", "x + y = 2"], "reduccion"),
    lambda c: c.ResolverSistemaEducativo(["x+y+z=1", "x=1"], "sustitucion"),
    lambda c: c.MatrizInversaCofactores("1 2\n3 4"), lambda c: c.MatrizInversaCofactores("5"),
    lambda c: c.MatrizInversaCofactores("1 2\n2 4"),
]


@pytest.mark.parametrize("operacion", OPERACIONES, ids=[str(i) for i in range(len(OPERACIONES))])
def test_resultados_en_ingles_sin_espanol(core, ingles, operacion):
    salida = operacion(core)
    restos = ESPANOL.findall(salida)
    assert not restos, f"Texto en español en la salida inglesa: {restos}\n{salida}"


def test_resultado_en_ingles(core, ingles):
    assert primera_linea(core.Derivar("x^3")) == "RESULT: 3*x**2"
    assert primera_linea(core.CalcularLimite("abs(x)/x", "x", "0")) == \
        "RESULT: Does not exist (the one-sided limits differ)"
    assert "x = 6" in core.ResolverSistemaGauss(["x + y = 10", "x - y = 2"])


def test_idioma_vuelve_a_espanol(core):
    i18n.establecer_idioma("en")
    i18n.establecer_idioma("es")
    assert primera_linea(core.Derivar("x^3")) == "RESULTADO: 3*x**2"


def test_parser_acepta_infinity_en_ingles(core, ingles):
    assert primera_linea(core.CalcularLimite("1/x", "x", "infinity")) == "RESULT: 0"
