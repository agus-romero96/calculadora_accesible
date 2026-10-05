"""
Traducciones: el catálogo inglés debe cubrir todos los textos del código, con los
mismos {marcadores}, y los resultados en inglés no deben dejar texto en español.
"""
import ast
import json
import os
import re
import string

import pytest

import i18n
from conftest import RAIZ, primera_linea

CARPETAS_CODIGO = ["", "algebra", "calculo", os.path.join("calculo", "lim_estrategias")]
EXCLUIR = {"setup.py", "compilar.py", "tests_limites.py"}


def archivos_codigo():
    for carpeta in CARPETAS_CODIGO:
        base = os.path.join(RAIZ, carpeta)
        for nombre in sorted(os.listdir(base)):
            if nombre.endswith(".py") and nombre not in EXCLUIR:
                yield os.path.join(base, nombre)


def textos_marcados():
    """Primer argumento literal de cada llamada tr("...") o N_("...") del código."""
    textos = {}
    for ruta in archivos_codigo():
        arbol = ast.parse(open(ruta, encoding="utf-8").read())
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                    and nodo.func.id in ("tr", "N_") and nodo.args
                    and isinstance(nodo.args[0], ast.Constant) and isinstance(nodo.args[0].value, str)):
                textos.setdefault(nodo.args[0].value, os.path.relpath(ruta, RAIZ))
    return textos


def marcadores(texto):
    return {campo for _, campo, _, _ in string.Formatter().parse(texto) if campo}


CATALOGO_EN = json.load(open(os.path.join(RAIZ, "locales", "en.json"), encoding="utf-8"))
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


def test_ayuda_existe_en_cada_idioma():
    for codigo in i18n.IDIOMAS:
        assert os.path.exists(os.path.join(RAIZ, "locales", f"ayuda_{codigo}.txt"))


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
