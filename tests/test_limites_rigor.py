"""Regresiones independientes: el valor correcto no valida un procedimiento falso."""
import pytest
import sympy as sp

from calculo.lim_estrategias._base import es_limite_evaluable
from calculo.lim_estrategias.continuidad import ContinuidadComposicion
from calculo.lim_estrategias.general import signo_cerca


@pytest.mark.parametrize("expr,tend,valor", [
    ("sqrt(x)+1", "4", "3"), ("(sqrt(x)-1)/(x+1)", "0", "-1"),
    ("sin(x)", "0", "0"), ("tan(x)", "0", "0"),
    ("1-cos(x)", "0", "0"),
    ("x^3", "2", "8"),
])
def test_sustitucion_suficiente(core, expr, tend, valor):
    salida = core.CalcularLimite(expr, "x", tend)
    assert salida.startswith("RESULTADO: " + valor + "\n")
    assert "MÉTODO: Modo General (sustitución directa)" in salida
    assert "Sustituimos:" in salida
    for innecesario in ("conjugado", "notable", "Hôpital"):
        assert innecesario not in salida


@pytest.mark.parametrize("expr,tend", [
    ("sin(x)", "oo"), ("sin(x^2)", "oo"), ("cos(x)", "-oo"),
    ("2+sin(x)", "oo"), ("sin(1/x)", "0+"),
])
def test_oscilacion_no_es_valor(core, expr, tend):
    salida = core.CalcularLimite(expr, "x", tend)
    assert salida.startswith("RESULTADO: No existe (comportamiento oscilatorio)")
    assert "AccumBounds" not in salida
    assert "Continuidad" not in salida
    assert "No se pudo explicar" in salida
    assert "PASO A PASO:" not in salida


@pytest.mark.parametrize("valor", [sp.AccumBounds(-1, 1), sp.Limit(sp.sin(sp.Symbol('x')), sp.Symbol('x'), sp.oo), sp.nan, sp.zoo])
def test_conjunto_o_limite_no_evaluado_no_es_valor(valor):
    assert not es_limite_evaluable(valor)


@pytest.mark.parametrize("funcion", [sp.sin, sp.cos, sp.exp, sp.Abs])
def test_continuidad_exige_punto_real_finito(funcion):
    est = ContinuidadComposicion()
    for punto in (sp.oo, -sp.oo, sp.I, sp.AccumBounds(-1, 1)):
        assert not est._verificar_continuidad_y_dominio(funcion, punto)[0]


@pytest.mark.parametrize("expr,tend,valor", [
    ("sin(x)/x", "0", "1"), ("sin(7*x)/x", "0", "7"),
    ("(1-cos(x))/x^2", "0", "1/2"),
])
def test_notable_justifica_nucleo_y_resto(core, expr, tend, valor):
    salida = core.CalcularLimite(expr, "x", tend)
    assert salida.startswith("RESULTADO: " + valor + "\n")
    assert "Límite trigonométrico notable" in salida
    assert "Multiplicamos los dos límites:" in salida
    assert "R es la expresión dividida entre el núcleo" in salida
    assert "Hôpital" not in salida


@pytest.mark.parametrize("expr,punto,factor,valor", [
    ("exp((x^2-1)/(x-1))", "1", "x - 1", "exp(2)"),
    ("cos((x^2-4)/(x-2))", "2", "x - 2", "cos(4)"),
])
def test_indeterminacion_interna_se_resuelve_antes(core, expr, punto, factor, valor):
    salida = core.CalcularLimite(expr, "x", punto)
    assert salida.startswith("RESULTADO: " + valor + "\n")
    assert salida.index("Cancelamos " + factor) < salida.index("Continuidad de una composición")
    assert "0/0, una forma indeterminada" in salida
    assert "no cambia el límite" in salida or "no vale 0" in salida or "distinto" in salida


def test_constante_y_tendencia_simbolica(core):
    salida = core.CalcularLimite("5", "x", "oo")
    assert "Límite de una constante" in salida
    assert "grados" not in salida
    salida = core.CalcularLimite("1/(x-a)", "x", "a+")
    assert salida.startswith("RESULTADO: +Infinito")
    assert "cuando x -> a+" in salida
    salida = core.CalcularLimite("x^3+2*x", "x", "-oo")
    assert salida.startswith("RESULTADO: -Infinito")
    assert "Término de mayor grado" in salida
    assert "Comparación de grados" not in salida


def test_signo_local_no_se_infiere_de_muestras():
    x = sp.Symbol("x", real=True)
    assert signo_cerca(x*(x-sp.Rational(1, 10**12)), x, sp.S.Zero, "+") == -1
    assert signo_cerca(sp.sin(1/x), x, sp.S.Zero, "+") == 0


@pytest.mark.parametrize("tend,valor", [
    ("0+", "+Infinito"), ("0-", "-Infinito"),
    ("0", "No existe (diverge a infinitos de distinto signo)"),
])
def test_polo_respeta_lado(core, tend, valor):
    salida = core.CalcularLimite("1/x", "x", tend)
    assert salida.startswith("RESULTADO: " + valor + "\n")
    assert "Hôpital" not in salida


def test_oscilacion_amortiguada_tiene_limite(core):
    salida = core.CalcularLimite("sin(x)/x", "x", "oo")
    assert salida.startswith("RESULTADO: 0\n")
    assert "No se pudo explicar" in salida
    assert "PASO A PASO:" not in salida


def test_composicion_sin_desarrollo_verificable_usa_respaldo(core):
    salida = core.CalcularLimite("exp((exp(x)-1)/x)", "x", "0")
    assert salida.startswith("RESULTADO: E\n")
    assert "No se pudo explicar" in salida
    assert "PASO A PASO:" not in salida


@pytest.mark.parametrize("tend,encabezado", [("1/2", "1/2"), ("pi/2", "pi/2")])
def test_tendencia_exacta_se_evalua_en_encabezado(core, tend, encabezado):
    assert "cuando x -> " + encabezado + "\n" in core.CalcularLimite("x", "x", tend)
