import sympy as sp
import pytest

from conftest import primera_linea

# Mismas variables reales que crea el parser
x, t, y = sp.symbols("x t y", real=True)


# ---------------- Derivadas ----------------

@pytest.mark.parametrize("expr, esperado, estrategia", [
    ("x^3", 3 * x**2, "Potencia"),
    ("5", 0, "Constante"),
    ("x^2*sin(x)", x**2 * sp.cos(x) + 2 * x * sp.sin(x), "Regla del Producto"),
    ("sin(x)/x", (x * sp.cos(x) - sp.sin(x)) / x**2, "Regla del Cociente"),
    ("sin(x^2)", 2 * x * sp.cos(x**2), "Regla de la Cadena"),
    ("x^x", x**x * (sp.log(x) + 1), "Potencia General (Logarítmica)"),
])
def test_derivada(core, expr, esperado, estrategia):
    res = core.calculo.CalcularDerivada(expr)
    assert res.es_exitoso
    assert sp.simplify(res.resultado - esperado) == 0
    assert res.estrategia_principal == estrategia


def test_regla_potencia_usa_la_variable_real(core):
    # Regresión: antes la fórmula mostraba siempre "x"
    res = core.calculo.CalcularDerivada("t^3")
    assert res.resultado == 3 * t**2
    assert "3*t^(3-1)" in res.pasos[0].expresion_matematica


def test_derivada_multivariable_con_variable_elegida(core):
    res = core.calculo.CalcularDerivada("x*y^2", variable="y")
    assert res.resultado == 2 * x * y


def test_derivada_enecima(core):
    res = core.calculo.DerivadaEnecima("x^5", "x", 3)
    assert res.es_exitoso
    assert res.resultado == 60 * x**2


def test_derivada_enecima_orden_invalido(core):
    assert not core.calculo.DerivadaEnecima("x^2", "x", 0).es_exitoso


# ---------------- Integrales ----------------

@pytest.mark.parametrize("expr", ["2*x", "sin(x)", "x*exp(x)", "1/x", "3*x^2+2*x"])
def test_integral_es_antiderivada(core, expr):
    res = core.calculo.CalcularIntegral(expr)
    assert res.es_exitoso
    assert res.requiere_constante
    original = core.parser_comun.parsear(expr)
    assert sp.simplify(sp.diff(res.resultado, x) - original) == 0


def test_integral_renderiza_constante(core):
    texto = core.calculo.RenderizarTexto(core.calculo.CalcularIntegral("2*x"))
    assert primera_linea(texto) == "RESULTADO: x**2 + C"


def test_integral_de_constante_sin_variable_es_error(core):
    res = core.calculo.CalcularIntegral("5")
    assert not res.es_exitoso
    assert "Ambigüedad" in res.mensaje_error
