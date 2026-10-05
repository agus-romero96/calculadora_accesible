import pytest

from conftest import primera_linea
from tests_limites import construir_casos, equiv, extraer_metodo, extraer_resultado_txt, parsear_resultado_a_sympy

# ---------------- Auditoría de 65 casos (valor + estrategia) ----------------

CASOS = construir_casos()


@pytest.mark.parametrize("caso", CASOS, ids=[f"{c.categoria}:{c.expr}@{c.tend}" for c in CASOS])
def test_auditoria_limites(core, caso):
    salida = core.CalcularLimite(caso.expr, "x", caso.tend)
    assert caso.esperado_metodo_contains in extraer_metodo(salida)
    if caso.expected_val is not None:
        valor = parsear_resultado_a_sympy(extraer_resultado_txt(salida))
        assert equiv(valor, caso.expected_val)


# ---------------- Límites bilaterales (regresión) ----------------
# sympy.limit() sin dir calcula solo el lateral derecho: antes la app decía
# lim abs(x)/x = 1 y lim 1/x = +Infinito en x -> 0.

@pytest.mark.parametrize("expr, tend, esperado", [
    ("abs(x)/x", "0", "RESULTADO: No existe (los límites laterales no coinciden)"),
    ("abs(x)/x", "0+", "RESULTADO: 1"),
    ("abs(x)/x", "0-", "RESULTADO: -1"),
    ("1/x", "0", "RESULTADO: No existe (diverge a infinitos de distinto signo)"),
    ("1/x", "0+", "RESULTADO: +Infinito"),
    ("1/x", "0-", "RESULTADO: -Infinito"),
    ("1/x**2", "0", "RESULTADO: +Infinito"),
    ("sin(x)/x**2", "0", "RESULTADO: No existe (diverge a infinitos de distinto signo)"),
])
def test_limites_bilaterales_y_laterales(core, expr, tend, esperado):
    assert primera_linea(core.CalcularLimite(expr, "x", tend)) == esperado


def test_simplificacion_solo_gana_si_cancela_0_sobre_0(core):
    salida = core.CalcularLimite("(x^2-1)/(x-1)", "x", "1")
    assert primera_linea(salida) == "RESULTADO: 2"
    assert "MÉTODO: Simplificación y cancelación" in salida

    # Sin indeterminación no hay nada que "cancelar": no debe atribuirse a esta estrategia
    salida = core.CalcularLimite("x^2", "x", "3")
    assert primera_linea(salida) == "RESULTADO: 9"
    assert "Simplificación" not in extraer_metodo(salida)


# ---------------- Continuidad con raíces y potencias (regresión) ----------------
# sqrt(u) se parsea como u**(1/2): antes la estrategia de continuidad lo descartaba
# y el límite caía en el modo general.

@pytest.mark.parametrize("expr, tend, esperado", [
    ("sqrt(x^2+9)", "4", "RESULTADO: 5"),
    ("(x^2+1)^(1/3)", "2", "RESULTADO: 5**(1/3)"),
    ("(x+1)^2", "2", "RESULTADO: 9"),
])
def test_continuidad_con_raices_y_potencias(core, expr, tend, esperado):
    salida = core.CalcularLimite(expr, "x", tend)
    assert primera_linea(salida) == esperado
    assert "Continuidad por composición" in extraer_metodo(salida)


def test_continuidad_no_se_atribuye_division_entre_cero(core):
    # 1/(x-1)^2 es la potencia (x-1)**(-2) con L=0: no es continua ahí
    salida = core.CalcularLimite("1/(x-1)^2", "x", "1")
    assert primera_linea(salida) == "RESULTADO: +Infinito"
    assert "Continuidad" not in extraer_metodo(salida)


# ---------------- Núcleos trigonométricos (regresión) ----------------
# Antes bastaba con que sin(u) o cos(u) apareciera en cualquier parte de la expresión:
# cos(1/x) se explicaba con (1-cos u)/u^2 y exp(sin(x)/x) con sin(u)/u.

@pytest.mark.parametrize("expr, tend, esperado", [
    ("cos(1/x)", "oo", "RESULTADO: 1"),
    ("exp(sin(x)/x)", "0", "RESULTADO: E"),
    ("(sin(x)-x)/x^3", "0", "RESULTADO: -1/6"),
])
def test_trig_no_se_atribuye_si_el_nucleo_no_es_factor(core, expr, tend, esperado):
    salida = core.CalcularLimite(expr, "x", tend)
    assert primera_linea(salida) == esperado
    assert "trigonométricos" not in extraer_metodo(salida)


@pytest.mark.parametrize("expr, tend, esperado", [
    ("x*sin(1/x)", "oo", "RESULTADO: 1"),
    ("sin(x)^2/x^2", "0", "RESULTADO: 1"),
    ("2*(1-cos(x))/x^2", "0", "RESULTADO: 1"),
])
def test_trig_con_nucleo_como_factor(core, expr, tend, esperado):
    salida = core.CalcularLimite(expr, "x", tend)
    assert primera_linea(salida) == esperado
    assert "Límites trigonométricos notables" in extraer_metodo(salida)


# ---------------- Entrada de la tendencia (regresión) ----------------

@pytest.mark.parametrize("tend", ["oo", "inf", "infinito", "∞", "+∞"])
def test_tendencia_infinito_positivo(core, tend):
    assert primera_linea(core.CalcularLimite("1/x", "x", tend)) == "RESULTADO: 0"


@pytest.mark.parametrize("tend", ["-oo", "-inf", "-∞"])
def test_tendencia_infinito_negativo(core, tend):
    assert primera_linea(core.CalcularLimite("x^3", "x", tend)) == "RESULTADO: -Infinito"


@pytest.mark.parametrize("expr, tend", [("sin(x", "0"), ("1/x", ""), ("1/x", "abc(")])
def test_entrada_invalida_devuelve_error_sin_excepcion(core, expr, tend):
    assert core.CalcularLimite(expr, "x", tend).startswith("Error")
