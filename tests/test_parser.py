import sympy as sp
import pytest

from conftest import primera_linea
from parser_matematico import ParserMatematico

p = ParserMatematico()
x, y = sp.symbols("x y", real=True)


# ---------------- Sintaxis aceptada ----------------

@pytest.mark.parametrize("texto, esperado", [
    ("2x", 2 * x),
    ("2xy", 2 * x * y),
    ("x y", x * y),
    ("3sin(x)", 3 * sp.sin(x)),
    ("2(x+1)", 2 * (x + 1)),
    ("sin x", sp.sin(x)),
    ("x^2", x**2),
    ("sin^2(x)", sp.sin(x)**2),  # antes: error
    ("2sin^2(x)+cos^2(x)", 2 * sp.sin(x)**2 + sp.cos(x)**2),
    ("Sin(X)", sp.sin(x)),  # no distingue mayúsculas
    ("asin(x)", sp.asin(x)),
    ("ln(x)", sp.log(x)),
    ("e^x", sp.exp(x)),
])
def test_sintaxis_aceptada(texto, esperado):
    assert sp.simplify(p.parsear(texto) - esperado) == 0


def test_variables_son_reales():
    expr = p.parsear("x + y")
    assert all(s.is_real for s in expr.free_symbols)


def test_simbolo_coincide_con_el_parser():
    # Cualquier módulo que cree una variable por nombre debe obtener la misma que el parser
    assert p.simbolo(" X ") == p.parsear("x")
    assert p.simbolo("x") != sp.Symbol("x")  # una variable "normal" sería distinta


@pytest.mark.parametrize("texto", ["matrix([[1,2],[3,4]])", "Matrix([[1,2],[3,4]])"])
def test_matrix_en_cualquier_caso(texto):
    # Regresión: el paso a minúsculas hacía imposible escribir Matrix(...)
    assert p.parsear(texto) == sp.Matrix([[1, 2], [3, 4]])


# ---------------- Nombres que parecen funciones mal escritas ----------------
# Regresión: antes 'xsin(x)' se convertía en silencio en i*n*s*x*x y 'sinx' en i*n*s*x

@pytest.mark.parametrize("texto, sugerencia", [
    ("xsin(x)", "x*sin(x)"),
    ("xcos(2*x)+1", "x*cos(2*x)"),
    ("xsqrt(x)", "x*sqrt(x)"),
    ("sinx", "sin(x)"),
    ("xsinx", "x*sin(x)"),
    ("3+lnx", "ln(x)"),
])
def test_funcion_mal_escrita_da_error_con_sugerencia(texto, sugerencia):
    with pytest.raises(ValueError) as exc:
        p.parsear(texto)
    assert f"¿Quiso decir {sugerencia}?" in str(exc.value)


@pytest.mark.parametrize("texto", ["", "   ", "sin(x", "2+"])
def test_entrada_invalida(texto):
    with pytest.raises(ValueError):
        p.parsear(texto)


# ---------------- Efecto de las variables reales en los motores ----------------

def test_derivada_de_abs_es_sign(core):
    # Antes: Piecewise con re(x), im(x) y Derivative(re(x), x)
    assert primera_linea(core.Derivar("abs(x)")) == "RESULTADO: sign(x)"


def test_simplificar_raiz_de_cuadrado(core):
    # Antes: sqrt(x**2) quedaba sin simplificar
    assert core.Simplificar("sqrt(x^2)").splitlines()[-1] == "RESULTADO FINAL: Abs(x)"


def test_integral_de_abs(core):
    # Antes: quedaba sin resolver, Integral(Abs(x), x)
    res = core.calculo.CalcularIntegral("abs(x)")
    assert not res.resultado.has(sp.Integral)
    # simplify no reduce Piecewise - Abs a 0: se compara en varios puntos de cada tramo
    derivada = sp.diff(res.resultado, x)
    for v in (-3, -1, sp.Rational(1, 2), 2):
        assert derivada.subs(x, v) == abs(v)


def test_limite_abs_sin_re_im(core):
    salida = core.CalcularLimite("abs(x)/x", "x", "0")
    assert "re(" not in salida and "im(" not in salida


@pytest.mark.parametrize("variable", ["y", "Y", " y "])
def test_variable_escrita_por_el_usuario_coincide(core, variable):
    # Si la variable del diálogo no coincidiera con la del parser, la derivada daría 0
    assert primera_linea(core.Derivar("x*y^2", variable)) == "RESULTADO: 2*x*y"
    assert primera_linea(core.CalcularLimite("sin(y)/y", variable, "0")) == "RESULTADO: 1"


def test_gauss_con_matrix(core):
    salida = core.ResolverSistemaGauss(["Matrix([[1,1,10],[1,-1,2]])"])
    assert "x = 6" in salida and "y = 4" in salida


def test_gauss_infinitas_soluciones_parametriza_con_variables_reales(core):
    # linsolve recibe variables creadas por nombre: deben ser las mismas del sistema
    salida = core.ResolverSistemaGauss(["x + y = 1", "2x + 2y = 2"])
    assert "x = 1 - y" in salida
