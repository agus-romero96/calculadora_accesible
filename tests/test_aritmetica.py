import sympy as sp
import pytest

# Mismas variables reales que crea el parser
x = sp.Symbol("x", real=True)


# ---------------- Evaluar ----------------

@pytest.mark.parametrize("expr, esperado", [
    ("2+2", 4),
    ("1/3+1/6", sp.Rational(1, 2)),
    ("2^10", 1024),
    ("sqrt(16)", 4),
])
def test_evaluar_resultado_exacto(core, expr, esperado):
    dto = core.aritmetica.evaluar(expr)
    assert dto.es_exitoso
    assert dto.es_trivial
    assert dto.resultado == esperado


def test_evaluar_irracional_da_decimal_y_conserva_exacto(core):
    dto = core.aritmetica.evaluar("2*pi")
    assert dto.es_exitoso
    assert not dto.es_trivial
    assert abs(float(dto.resultado) - 6.283185307179586) < 1e-12
    assert dto.pasos[-1].titulo == "Aproximación decimal" and "2*pi" in dto.pasos[-1].partes


def test_evaluar_rechaza_variables(core):
    dto = core.aritmetica.evaluar("x+1")
    assert not dto.es_exitoso
    assert "x" in dto.mensaje_error


def test_evaluar_sintaxis_invalida(core):
    assert not core.aritmetica.evaluar("2+").es_exitoso


@pytest.mark.parametrize("expr", ["sqrt(-4)", "asin(2)", "log(-1)"])
def test_evaluar_no_real_da_error_claro(core, expr):
    dto = core.aritmetica.evaluar(expr)
    assert not dto.es_exitoso
    assert "real" in dto.mensaje_error


@pytest.mark.parametrize("expr", ["log(0)", "tan(pi/2)", "0^(-1)"])
def test_evaluar_indefinido_da_error_claro(core, expr):
    dto = core.aritmetica.evaluar(expr)
    assert not dto.es_exitoso


@pytest.mark.parametrize("expr, esperado", [
    ("sqrt(-4)^2", -4),
    ("sqrt(-4)*sqrt(-9)", -6),
    ("(-1)^(1/2)*(-1)^(1/2)", -1),
    ("abs(sqrt(-4))", 2),
    ("log(-1)^2", -sp.pi**2),
])
def test_resultado_real_con_intermedios_complejos(core, expr, esperado):
    dto = core.aritmetica.evaluar(expr)
    assert dto.es_exitoso
    assert abs(float(dto.resultado - esperado)) < 1e-15
    # No se presentan reglas reales para justificar las operaciones complejas.
    assert any("No se pudo explicar paso a paso" in aviso for aviso in dto.advertencias)


# ---------------- Simplificar ----------------

def test_simplificar_cancela_factor_comun(core):
    dto = core.aritmetica.simplificar("(x^2-1)/(x-1)")
    assert dto.es_exitoso
    assert sp.simplify(dto.resultado - (x + 1)) == 0


# ---------------- Factorizar ----------------

@pytest.mark.parametrize("expr, caso", [
    ("x^2+2*x+1", "Trinomio cuadrado perfecto"),
    ("x^2-9", "Diferencia de cuadrados"),
    ("x^2+5*x+6", "Trinomio x^2 + bx + c"),
    ("2*x^2+7*x+3", "Trinomio ax^2 + bx + c"),
    ("3*x^2+6*x+3", "Trinomio cuadrado perfecto"),  # con factor común numérico
    ("x^3-8", "Suma/diferencia de cubos"),  # regresión: antes fallaba con excepción
    ("x^3+27", "Suma/diferencia de cubos"),
    ("(x+1)*(x+2)", "Trinomio x^2 + bx + c"),  # regresión: antes se marcaba como Irreducible
    ("(x+1)^2", "Trinomio cuadrado perfecto"),
])
def test_factorizar_reconoce_caso(core, expr, caso):
    dto = core.aritmetica.factorizar(expr)
    assert dto.es_exitoso
    assert dto.estrategia == caso
    # El resultado siempre debe ser equivalente a la entrada
    assert sp.expand(dto.resultado - core.parser_comun.parsear(expr)) == 0


def test_factorizar_irreducible(core):
    # Regresión: con la expresión sin evaluar del parser, nunca se detectaba irreducible
    dto = core.aritmetica.factorizar("x^2+1")
    assert dto.es_exitoso
    assert dto.estrategia == "Irreducible"


def test_factorizar_no_inventa_factor_comun(core):
    # Regresión: antes mostraba "Extracción de factor común: x**2 - 9" y "x**2 - 1*9"
    dto = core.aritmetica.factorizar("x^2-9")
    assert not any("factor común" in p.titulo for p in dto.pasos)
    assert str(dto.expresion_original) == "x**2 - 9"


def test_factorizar_extrae_factor_comun_real(core):
    dto = core.aritmetica.factorizar("2*x^2-18")
    assert dto.pasos[0].titulo == "Sacar factor común"
    assert dto.estrategia == "Diferencia de cuadrados"
    assert sp.expand(dto.resultado - (2 * x**2 - 18)) == 0


@pytest.mark.parametrize("expr, coeficiente, lineal, expandida", [
    ("2*x+2", 2, x+1, 2*x+2),
    ("2*(x+1)", 2, x+1, 2*x+2),
    ("-2*x-2", 2, -x-1, -2*x-2),
    ("3*x+6", 3, x+2, 3*x+6),
])
def test_factor_comun_conserva_producto(core, expr, coeficiente, lineal, expandida):
    dto = core.aritmetica.factorizar(expr)
    assert dto.es_exitoso
    assert dto.resultado.is_Mul
    assert dto.resultado.args == (coeficiente, lineal)
    assert sp.expand(dto.resultado) == expandida
    assert dto.estrategia == "Factor común"
    assert not any("No se encontraron factores" in aviso for aviso in dto.advertencias)
