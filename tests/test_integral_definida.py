"""
Integral definida: el valor (de SymPy) y la explicación de clase, regla de Barrow si la
función es continua en un intervalo acotado, o integral impropia por tramos si no.
"""
import pytest
import sympy

import exportar
from calculo.calculo import humanizar_integral
from conftest import primera_linea

x = sympy.Symbol("x", real=True)
k = sympy.Symbol("k", real=True)

# (expresión, inferior, superior, valor, método)
CASOS = [
    ("x^2", "0", "1", sympy.Rational(1, 3), "Regla de Barrow"),
    ("sin(x)", "0", "pi", 2, "Regla de Barrow"),
    ("cos(x)", "0", "pi/2", 1, "Regla de Barrow"),
    ("abs(x)", "-1", "2", sympy.Rational(5, 2), "Regla de Barrow"),
    ("1/x", "-2", "-1", -sympy.log(2), "Regla de Barrow"),
    ("x^2", "1", "0", -sympy.Rational(1, 3), "Regla de Barrow"),
    ("x", "0", "k", k**2 / 2, "Regla de Barrow"),
    ("x", "2", "2", 0, "Límites iguales"),
    # Sin evaluar (log(x, 10)), SymPy integraba log(x) y olvidaba dividir entre log(10)
    ("log(x,10)", "1", "10", 10 - 9 / sympy.log(10), "Regla de Barrow"),
    # Impropias que convergen
    ("1/sqrt(x)", "0", "1", 2, "Integral impropia"),
    ("ln(x)", "0", "1", -1, "Integral impropia"),
    ("exp(-x)", "0", "oo", 1, "Integral impropia"),
    ("1/(1+x^2)", "-oo", "oo", sympy.pi, "Integral impropia"),
    ("exp(-x^2)", "-oo", "oo", sympy.sqrt(sympy.pi), "Integral impropia"),
    ("sin(x)/x", "0", "1", sympy.Si(1), "Integral impropia"),
    # Impropias que divergen
    ("1/x^2", "-1", "1", sympy.oo, "Integral impropia"),
    ("1/x", "1", "oo", sympy.oo, "Integral impropia"),
    ("1/x", "-1", "1", sympy.nan, "Integral impropia"),
    ("tan(x)", "0", "pi", sympy.nan, "Integral impropia"),
    ("x/(x^2+1)", "-oo", "oo", sympy.nan, "Integral impropia"),
    ("sin(x)", "0", "oo", sympy.nan, "Integral impropia"),
]


def _calcular(core, expresion, inferior, superior, variable=None):
    return core.calculo.CalcularIntegralDefinida(expresion, variable, inferior, superior)


@pytest.mark.parametrize("expresion,inferior,superior,valor,metodo", CASOS,
                         ids=[f"{c[0]}[{c[1]},{c[2]}]" for c in CASOS])
def test_valor_y_metodo(core, expresion, inferior, superior, valor, metodo):
    res = _calcular(core, expresion, inferior, superior)
    assert res.es_exitoso, res.mensaje_error
    if valor is sympy.nan:
        assert res.resultado is sympy.nan
    else:
        assert sympy.simplify(res.resultado - valor) == 0 if valor != sympy.oo else res.resultado == sympy.oo
    assert res.estrategia_principal == metodo


def test_discontinuidad_interior_no_aplica_barrow(core):
    """Barrow a ciegas daría F(1) − F(−1) = −1 − 1 = −2: hay que dividir en x = 0."""
    res = _calcular(core, "1/x^2", "-1", "1")
    texto = core.calculo.RenderizarTexto(res)
    assert primera_linea(texto) == "RESULTADO: +Infinito (la integral diverge)"
    assert "no es continua en x = 0" in texto
    assert "Se separa en 2 integrales: de -1 a 0, de 0 a 1." in texto
    assert "-2" not in texto.replace("[-1", "")
    assert "Al menos un tramo diverge" in texto


def test_extremo_infinito_usa_limite(core):
    texto = core.calculo.RenderizarTexto(_calcular(core, "exp(-x)", "0", "oo"))
    assert "el intervalo llega a infinito" in texto
    assert "lim x→oo F(x) − F(0) = 0 − (-1) = 1" in texto
    assert "La integral impropia converge." in texto


def test_extremo_discontinuo_usa_limite_lateral(core):
    texto = core.calculo.RenderizarTexto(_calcular(core, "1/sqrt(x)", "0", "1"))
    assert "F(1) − lim x→0+ F(x) = 2 − 0 = 2" in texto


def test_barrow_con_logaritmo_de_negativos_usa_valor_absoluto(core):
    """La primitiva de 1/x es ln|x|: los pasos no deben mostrar ln(−1) = iπ."""
    texto = core.calculo.RenderizarTexto(_calcular(core, "1/x", "-2", "-1"))
    assert "F(x) = log(Abs(x))" in texto
    assert "I*pi" not in texto and "log(-" not in texto
    assert primera_linea(texto) == "RESULTADO: -log(2) (≈ -0.693147)"


def test_limites_invertidos(core):
    texto = core.calculo.RenderizarTexto(_calcular(core, "x^2", "1", "0"))
    pasos = texto.split("PASO A PASO:")[1]
    assert pasos.index("Primitiva") < pasos.index("Invertir los límites") < pasos.index("Regla de Barrow")
    assert "−(1/3) = -1/3" in pasos


def test_limites_con_parametro(core):
    res = _calcular(core, "x", "0", "k")
    assert res.resultado == k**2 / 2
    assert "se supone que la función es continua" in core.calculo.RenderizarTexto(res)


def test_sin_primitiva_elemental_da_aproximacion(core):
    res = _calcular(core, "exp(x^3)", "0", "1")
    assert isinstance(res.resultado, sympy.Float)
    assert abs(float(res.resultado) - 1.341904418) < 1e-8
    assert any("aproximado" in a for a in res.advertencias)
    # Sin pasos de Barrow con números complejos
    assert "exp_polar" not in core.calculo.RenderizarTexto(res)


def test_constante_con_variable_indicada(core):
    res = _calcular(core, "5", "0", "2", variable="t")
    assert res.resultado == 10 and str(res.variable) == "t"


@pytest.mark.parametrize("inferior,superior,mensaje", [
    ("0", "", "Falta un límite de integración"),
    ("x", "1", "no pueden contener la variable de integración"),
    ("0", "1/0", "debe ser un número real"),
])
def test_errores_de_datos(core, inferior, superior, mensaje):
    res = _calcular(core, "x^2", inferior, superior)
    assert not res.es_exitoso
    assert mensaje in res.mensaje_error


def test_constante_sin_variable_es_error(core):
    assert not _calcular(core, "5", "0", "1").es_exitoso


def test_fachada_planteamiento_y_exportacion(core):
    res = core.integral_definida("x^2", None, "0", "1")
    assert res.operacion == "integral_definida" and not res.mas_constante
    assert res.planteamiento == sympy.Integral(x**2, (x, 0, 1))
    assert res.parametros == {"variable": "x", "inferior": "0", "superior": "1"}
    assert exportar.latex(res) == r"\int\limits_{0}^{1} x^{2}\, dx = \frac{1}{3}"
    assert exportar.resultado_corto(res) == "1/3"


def test_exportacion_de_una_integral_divergente(core):
    res = core.integral_definida("1/x", None, "-1", "1")
    assert exportar.resultado_corto(res) == "No existe (la integral diverge)"
    assert r"\text{No existe (la integral diverge)}" in exportar.latex(res)
    assert exportar.latex(core.integral_definida("1/x", None, "1", "oo")).endswith(r"= \infty")


@pytest.mark.parametrize("valor,texto", [
    (sympy.Rational(1, 3), "1/3"),
    (sympy.pi / 4, "pi/4 (≈ 0.785398)"),
    (sympy.oo, "+Infinito (la integral diverge)"),
    (-sympy.oo, "-Infinito (la integral diverge)"),
    (sympy.nan, "No existe (la integral diverge)"),
    (k**2 / 2, "k**2/2"),
])
def test_humanizar_integral(valor, texto):
    assert humanizar_integral(valor) == texto


@pytest.mark.parametrize("expresion", ["exp(-x)", "1/x^2"])
def test_reglas_alternativas_y_potencias_anidadas_tienen_nombre(core, expresion):
    """AlternativeRule y NestedPowRule ya no salen como 'Regla detectada: ...Rule'."""
    texto = core.Integrar(expresion)
    assert "Rule" not in texto
