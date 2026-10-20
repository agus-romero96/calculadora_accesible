"""Regresiones independientes de sustituciones y series laterales de SymPy."""
import pytest
import sympy as sp

from calculo.derivabilidad import cocientes, derivada_bilateral
from parser_matematico import ParserMatematico


@pytest.mark.parametrize("funcion", ["abs(x)", "sqrt(x^2)", "abs(x-1)"])
def test_extremos_no_confunde_esquinas_con_estacionarios(core, funcion):
    res = core.extremos(funcion)
    assert res.es_error
    assert "No soportado" in res.texto
    assert "no derivables" in res.texto
    assert "RESULTADO:" not in res.texto


def test_inflexion_estacionaria_no_es_extremo(core):
    res = core.extremos("x^3")
    assert not res.es_error
    assert res.valor["criticos"] == sp.FiniteSet(0)
    assert res.valor["minimos"] == res.valor["maximos"] == []
    assert res.valor["crece"] == sp.S.Reals
    assert "criterio no decide" in res.texto


@pytest.mark.parametrize("funcion", ["sqrt(x)", "x^(2/3)"])
def test_extremos_declara_alcance_en_bordes(core, funcion):
    res = core.extremos(funcion)
    assert not res.es_error, res.texto
    assert res.valor["criticos"] == sp.S.EmptySet
    assert res.valor["crece"] == sp.Interval.open(0, sp.oo)
    assert "extremos unilaterales del dominio no se clasifican" in res.texto
    assert "Sin extremos locales interiores" in res.texto


@pytest.mark.parametrize("funcion,izq,der", [("abs(x)", -1, 1), ("abs(x)^(2/3)", -sp.oo, sp.oo)])
def test_cocientes_incrementales_reales(funcion, izq, der):
    p = ParserMatematico()
    f = p.parsear(funcion)
    x = p.simbolo("x")
    assert cocientes(f, f.doit(), x, sp.S.Zero) == {"-": izq, "+": der}
    with pytest.raises(ValueError, match="derivada bilateral"):
        derivada_bilateral(f, f.doit(), x, sp.S.Zero)


@pytest.mark.parametrize("funcion,tipo", [("abs(x)", "esquina"), ("abs(x)^(2/3)", "cúspide")])
def test_rectas_rechaza_esquina_y_cuspide(core, funcion, tipo):
    res = core.recta_tangente(funcion, None, "0")
    assert res.es_error and tipo in res.texto
    assert "Recta tangente:" not in res.texto


@pytest.mark.parametrize("funcion", ["sqrt(x)", "x^(2/3)", "x^(1/3)"])
def test_vertical_unilateral_justificada(core, funcion):
    res = core.recta_tangente(funcion, None, "0")
    assert not res.es_error, res.texto
    assert "Recta tangente: x = 0" in res.texto
    assert "Extremo unilateral del dominio" in res.texto
    assert "Cociente incremental: derecha: oo" in res.texto
    assert "por todos los lados reales disponibles" in res.texto
    assert "división entre 0" not in res.texto


@pytest.mark.parametrize("funcion", ["x^2", "x^3"])
def test_rectas_estacionarias(core, funcion):
    res = core.recta_tangente(funcion, None, "0")
    assert not res.es_error, res.texto
    assert "Recta tangente: y = 0" in res.texto
    assert "Recta normal: x = 0" in res.texto
    assert "Cociente incremental: izquierda: 0; derecha: 0" in res.texto


@pytest.mark.parametrize("funcion,orden", [("abs(x)", 1), ("abs(x)", 2), ("x*abs(x)", 2), ("sqrt(x)", 1), ("x^(2/3)", 1)])
def test_taylor_exige_derivadas_bilaterales(core, funcion, orden):
    res = core.taylor(funcion, None, orden, "0")
    assert res.es_error
    assert "derivada bilateral" in res.texto or "No concluyente" in res.texto
    assert "RESULTADO:" not in res.texto
    assert "resultado de SymPy" not in res.texto


def test_taylor_cero_no_necesita_derivada(core):
    res = core.taylor("abs(x)", None, 0, "0")
    assert not res.es_error and res.valor == 0


@pytest.mark.parametrize("funcion", ["exp(x)", "sin(x)", "cos(x)", "x^3"])
def test_taylor_analiticas_conservadas_y_sin_promesa_de_convergencia(core, funcion):
    res = core.taylor(funcion, None, 3, "0")
    assert not res.es_error, res.texto
    assert "no demuestra la convergencia" in res.texto


@pytest.mark.parametrize("funcion,punto", [("(x-1)/(x-1)+x^2", "1"), ("sqrt(x)/sqrt(x)+x", "0"), ("x^(2/3)", "-1")])
def test_conserva_dominio_original_en_rectas_y_taylor(core, funcion, punto):
    assert core.recta_tangente(funcion, None, punto).es_error
    assert core.taylor(funcion, None, 1, punto).es_error


def test_producto_nulo_no_omite_factor_cuadratico(core):
    res = core.extremos("x^4/4-x^2")
    assert not res.es_error, res.texto
    paso = res.texto.split("Aplicar el producto nulo.")[1].split("\n\n")[0]
    assert "x^2 - 2 = 0" in paso
    assert res.valor["criticos"] == sp.FiniteSet(-sp.sqrt(2), 0, sp.sqrt(2))


def test_potencia_principal_no_es_raiz_cubica_real(core):
    p = ParserMatematico()
    f = p.parsear("x^(2/3)").doit()
    x = p.simbolo("x")
    assert f.subs(x, -1).is_real is False
    assert sp.real_root(-1, 3)**2 == 1
    assert "rama compleja principal" in core.recta_tangente("x^(2/3)", None, "0").texto


def test_extremos_conserva_huecos_sin_explicar_dominio_falso(core):
    res = core.extremos("(x-1)/(x-1)+x^2")
    assert not res.es_error, res.texto
    assert res.valor["criticos"] == sp.FiniteSet(0)
    assert not res.valor["crece"].contains(1)
    assert "todos los números reales" not in res.texto
