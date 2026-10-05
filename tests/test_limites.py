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
