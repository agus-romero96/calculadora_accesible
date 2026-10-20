"""Dominios originales: expectativas explícitas, sin simplificar antes de restringir."""
import pytest
import sympy as sp
from sympy import S

from dominios import (comprobar_candidato, dominio_real, restricciones_denominadores)
from parser_matematico import ParserMatematico
from serializacion import a_bytes, de_bytes

p = ParserMatematico()
x, y, a = (p.simbolo(n) for n in ("x", "y", "a"))


@pytest.mark.parametrize("entrada, excluidos", [
    ("(x^2-1)/(x-1)", {1}),
    ("(x-1)/(x-1)+1", {1}),
    ("0/x", {0}),
    ("(x/x)^0", {0}),
    ("1/(1/x)", {0}),
    ("(1/x)/(1/x)", {0}),
    ("1/(x/(x-1))", {0, 1}),
    ("(x^2-2)/(x^2-2)", {-sp.sqrt(2), sp.sqrt(2)}),
    ("1/(x^2+1)", set()),
    ("x^-2", {0}),
    ("abs(x/x)", {0}),
    ("abs(0/x)", {0}),
    ("sin(0/x)", {0}),
])
def test_dominio_antes_de_cancelar(entrada, excluidos):
    condiciones = restricciones_denominadores(p.parsear(entrada))
    assert dominio_real(condiciones, x) == S.Reals - sp.FiniteSet(*excluidos)


@pytest.mark.parametrize("entrada, esperado, condiciones", [
    ("(x^2-1)/(x-1)", x+1, {sp.Ne(x-1, 0)}),
    ("(x-1)/(x-1)+1", 2, {sp.Ne(x-1, 0)}),
    ("0/x", 0, {sp.Ne(x, 0)}),
    ("(x/x)^0", 1, {sp.Ne(x, 0)}),
    ("1/(1/x)", x, {sp.Ne(x, 0)}),
    ("(x*y)/(x*y)", 1, {sp.Ne(x, 0), sp.Ne(y, 0)}),
    ("a*x/a", x, {sp.Ne(a, 0)}),
    ("1/(x/y)", y/x, {sp.Ne(x, 0), sp.Ne(y, 0)}),
    ("0/(x^2+y^2)", 0, {sp.Ne(x**2+y**2, 0)}),
    ("abs(x/x)", 1, {sp.Ne(x, 0)}),
])
@pytest.mark.parametrize("metodo", ["simplificar", "factorizar"])
def test_operacion_conserva_condiciones_originales(core, entrada, esperado, condiciones, metodo):
    dto = getattr(core.aritmetica, metodo)(entrada)
    assert dto.es_exitoso, dto.mensaje_error
    assert sp.simplify(dto.resultado - esperado) == 0
    assert set(dto.restricciones) == condiciones
    assert dto.expresion_original == p.parsear(entrada)
    assert any("Restricciones de los denominadores originales" in aviso for aviso in dto.advertencias)


@pytest.mark.parametrize("entrada", ["x/0", "1/(x-x)", "0/(a-a)"])
def test_denominador_identicamente_nulo(core, entrada):
    raw = p.parsear(entrada)
    assert restricciones_denominadores(raw) == (S.false,)
    for metodo in (core.aritmetica.simplificar, core.aritmetica.factorizar):
        dto = metodo(entrada)
        assert not dto.es_exitoso and dto.resultado is None
        assert "denominador" in dto.mensaje_error and "no hay valores admitidos" in dto.mensaje_error


REALES_SIN_CERO = S.Reals - sp.FiniteSet(0)


@pytest.mark.parametrize("entrada, esperado", [
    ("(x-2)/(x-2)+x=3", S.EmptySet),
    ("(x^2-1)/(x-1)=2", S.EmptySet),
    ("(x^2-1)/(x-1)=3", sp.FiniteSet(2)),
    ("x/x=1", REALES_SIN_CERO),
    ("x/x=2", S.EmptySet),
    ("0/x=0", REALES_SIN_CERO),
    ("0/x=1", S.EmptySet),
    ("(x/x)^0=1", REALES_SIN_CERO),
    ("abs(x/x)=1", REALES_SIN_CERO),
    ("abs(0/x)=0", REALES_SIN_CERO),
    ("1/(1/x)=0", S.EmptySet),
    ("1/(1/x)=2", sp.FiniteSet(2)),
    ("1/(x-x)=0", S.EmptySet),
    ("(x-1)/(x+2)=0", sp.FiniteSet(1)),
    ("0=(x-1)/(x+2)", sp.FiniteSet(1)),
    ("1/x-2=0", sp.FiniteSet(sp.Rational(1, 2))),
    ("1/x+1/(x+1)=0", sp.FiniteSet(-sp.Rational(1, 2))),
    ("x^2/(x-1)=1/(x-1)", sp.FiniteSet(-1)),
    ("(x^2-4)/(x-2)=0", sp.FiniteSet(-2)),
    ("1/(x^2+1)=1", sp.FiniteSet(0)),
    ("0/(x^2+1)=0", S.Reals),
    ("(x^2+1)/x=0", S.EmptySet),  # las raíces ±I no son soluciones reales
    ("(x^2-2)/(x^2-2)=1", S.Reals - sp.FiniteSet(-sp.sqrt(2), sp.sqrt(2))),
    ("(x^3-x)/(x-1)=0", sp.FiniteSet(-1, 0)),
    ("1/x<0", sp.Interval.open(-sp.oo, 0)),
    ("x/x<2", REALES_SIN_CERO),
    ("(x^2-1)/(x-1)>=2", sp.Interval.open(1, sp.oo)),
    ("0.1*x/(x-1)=0.3", sp.FiniteSet(sp.Rational(3, 2))),
    ("1/(x-0.1)=3", sp.FiniteSet(sp.Rational(13, 30))),
    ("(x-0.1)/(x-0.1)=1", S.Reals - sp.FiniteSet(sp.Rational(1, 10))),
])
def test_soluciones_sobre_dominio_original(core, entrada, esperado):
    res = core.ecuacion(entrada)
    assert not res.es_error, res.texto
    assert res.valor == esperado
    izq, der = entrada.split("=") if "=" in entrada and not any(s in entrada for s in "<>") else (None, None)
    if izq is not None and isinstance(esperado, sp.FiniteSet):
        # Sustitución antes de evaluar; no se usa el verificador de producción.
        for candidato in esperado:
            # sympify(..., rational=True) evita que redondeos decimales contaminen
            # esta comprobación independiente de las rutinas de dominio.
            v_izq = sp.sympify(izq, locals={"x": x}, rational=True, evaluate=False).subs(x, candidato).doit()
            v_der = sp.sympify(der, locals={"x": x}, rational=True, evaluate=False).subs(x, candidato).doit()
            assert v_izq.is_finite and v_der.is_finite
            assert sp.simplify(v_izq - v_der) == 0


@pytest.mark.parametrize("entrada", ["1/x-2=0", "(x-1)/(x+2)=0", "1/x+1/(x+1)=0", "x/x=1"])
def test_racional_con_cero_no_pierde_pasos(core, entrada):
    res = core.ecuacion(entrada)
    assert "PASO A PASO" in res.texto
    assert not any("sin pasos" in aviso or "no llegó" in aviso for aviso in res.texto.splitlines())
    assert "Restricciones del dominio" in res.texto


def test_verificacion_sustituye_antes_de_cancelar():
    raw = p.parsear("x/x")
    assert comprobar_candidato(raw, sp.Integer(1), x, 0) is False
    assert comprobar_candidato(raw, sp.Integer(1), x, 2) is True
    assert comprobar_candidato(p.parsear("x+1"), sp.Integer(3), x, 1) is False


def test_candidato_incorrecto_del_solver_no_se_acepta(core, monkeypatch):
    original = sp.solveset

    def solver(expr, variable, domain):
        return sp.FiniteSet(1) if expr is S.false else original(expr, variable, domain=domain)

    monkeypatch.setattr(sp, "solveset", solver)
    assert core.ecuacion("x/x=2").valor == S.EmptySet


def test_restricciones_sobreviven_al_transporte(core):
    for res in (core.simplificar("(x*y)/(x*y)"), core.ecuacion("x/x=1")):
        copia = de_bytes(a_bytes(res))
        assert copia.parametros["restricciones"] == res.parametros["restricciones"]
        assert copia.expresion == res.expresion
        assert copia.valor == res.valor


def test_parametros_son_legibles(core):
    assert core.simplificar("(x*y)/(x*y)").parametros["restricciones"] == "x ≠ 0; y ≠ 0"


@pytest.mark.parametrize("metodo, explicador", [
    ("simplificar", "ExplicadorSimplificar"),
    ("factorizar", "ExplicadorFactorizar"),
])
def test_restricciones_no_dependen_del_explicador(core, monkeypatch, metodo, explicador):
    import aritmetica

    def sin_pasos(*args):
        raise aritmetica.SinExplicacion()

    monkeypatch.setattr(getattr(aritmetica, explicador), "explicar", sin_pasos)
    dto = getattr(core.aritmetica, metodo)("x/x")
    assert dto.es_exitoso and dto.resultado == 1
    assert dto.restricciones == (sp.Ne(x, 0),)
    assert any("Restricciones de los denominadores originales" in aviso for aviso in dto.advertencias)


def test_no_inferir_parametros_como_si_fueran_constantes(core):
    res = core.ecuacion("(x-a)/(x-a)=1")
    assert res.es_error and "varias variables" in res.texto


def test_otra_incognita_real(core):
    res = core.ecuacion("y/y=1")
    assert not res.es_error and res.valor == REALES_SIN_CERO
    assert res.parametros["variable"] == "y"


def test_restricciones_en_ingles(core):
    import i18n
    import exportar

    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        res = core.simplificar("x/x")
        assert "Original denominator restrictions" in res.texto
        assert "Domain restrictions: x ≠ 0" in exportar.a_html(res)
        assert "Original denominator restrictions: x ≠ 0" in exportar.a_texto(res)
        assert "no admissible values" in core.simplificar("1/(x-x)").texto
    finally:
        i18n.establecer_idioma(anterior)


@pytest.mark.parametrize("entrada, esperado", [
    ("log(x)/log(x)=1", sp.Union(sp.Interval.open(0, 1), sp.Interval.open(1, sp.oo))),
    ("sqrt(x)/sqrt(x)=1", sp.Interval.open(0, sp.oo)),
    ("log(x)/log(x)+x=-1", S.EmptySet),
    ("sqrt(x)/sqrt(x)+x=-1", S.EmptySet),
    ("log(x)/log(x)+x=3", sp.FiniteSet(2)),
    ("sqrt(x)/sqrt(x)+x=3", sp.FiniteSet(2)),
    ("0*log(x)=0", sp.Interval.open(0, sp.oo)),
    ("sqrt(x)^0=1", sp.Interval(0, sp.oo)),
    ("sqrt(log(x))/sqrt(log(x))=1", sp.Interval.open(1, sp.oo)),
    ("log(x)/log(x)<2", sp.Union(sp.Interval.open(0, 1), sp.Interval.open(1, sp.oo))),
    ("sqrt(x)/sqrt(x)<2", sp.Interval.open(0, sp.oo)),
    ("sqrt(-x^2-1)^2=-x^2-1", S.EmptySet),
])
def test_funciones_canceladas_respetan_dominio_real(core, entrada, esperado):
    # Conjuntos explícitos, independientes del cálculo de dominio de producción.
    res = core.ecuacion(entrada)
    assert not res.es_error, res.texto
    assert res.valor == esperado


def test_dominio_no_soportado_se_rechaza(core, monkeypatch):
    from sympy.calculus import util

    def no_soportado(*args):
        raise NotImplementedError()

    monkeypatch.setattr(util, "continuous_domain", no_soportado)
    res = core.ecuacion("log(x)/log(x)=1")
    assert res.es_error
    assert "No se puede validar el dominio real" in res.texto


def test_potencia_simbolica_cancelada_no_se_acepta_sin_validar(core):
    res = core.ecuacion("x^x/x^x=1")
    assert res.es_error
    assert "No se puede validar el dominio real" in res.texto


@pytest.mark.parametrize("base, derecho, solucion", [
    ("x", "2", 4), ("(x-1)", "2", 5),
])
@pytest.mark.parametrize("potencia", ["sqrt({base})", "{base}^(1/2)", "{base}^0.5"])
def test_raices_equivalentes_api_publica(core, base, derecho, solucion, potencia):
    res = core.ecuacion(f"{potencia.format(base=base)}={derecho}")
    assert not res.es_error, res.texto
    assert res.valor == sp.FiniteSet(solucion)


@pytest.mark.parametrize("exponente", ["(-1/2)", "(-0.5)"])
def test_raiz_inversa_equivalente_api_publica(core, exponente):
    res = core.ecuacion(f"(x-1)^{exponente}=1")
    assert not res.es_error, res.texto
    assert res.valor == sp.FiniteSet(2)


@pytest.mark.parametrize("entrada, esperado", [
    ("sqrt(x)^0=1", sp.Interval(0, sp.oo)),
    ("(x^(1/2))^0=1", sp.Interval(0, sp.oo)),
    ("(x^0.5)^0=1", sp.Interval(0, sp.oo)),
    ("((x-1)^(1/2))^0=1", sp.Interval(1, sp.oo)),
    ("((x-1)^(-1/2))^0=1", sp.Interval.open(1, sp.oo)),
    ("((x-1)^(-0.5))^0=1", sp.Interval.open(1, sp.oo)),
    ("x^(1/2+0/(x-4))=2", S.EmptySet),
    ("(x^(1/2+0/x))^0=1", sp.Interval.open(0, sp.oo)),
    ("(x^(1/2+log(x)/log(x)-1))^0=1",
     sp.Union(sp.Interval.open(0, 1), sp.Interval.open(1, sp.oo))),
    ("x^(2/3)=4", sp.FiniteSet(8)),
    ("x^(-2/3)=1", sp.FiniteSet(1)),
    ("x^(2/3)/x^(2/3)=1", sp.Interval.open(0, sp.oo)),
    ("(x^(2/3))^3=x^2", sp.Interval(0, sp.oo)),
    ("(x^(1/3))^0=1", sp.Interval(0, sp.oo)),
])
def test_dominio_potencias_racionales_originales(core, entrada, esperado):
    # Oráculos explícitos: no se calculan con las rutinas de dominio.
    res = core.ecuacion(entrada)
    assert not res.es_error, res.texto
    assert res.valor == esperado


def test_potencia_principal_no_es_raiz_real_impar():
    # Sustitución independiente del parser y del verificador de producción.
    potencia = sp.Pow(-8, sp.Rational(2, 3))
    assert potencia.is_real is False
    assert potencia != 4
    assert sp.real_root(-8, 3)**2 == 4


@pytest.mark.parametrize("entrada, esperado", [
    ("sqrt(x)", sp.Interval(0, sp.oo)),
    ("x^(1/2)", sp.Interval(0, sp.oo)),
    ("x^0.5", sp.Interval(0, sp.oo)),
    ("(x-1)^(1/2)", sp.Interval(1, sp.oo)),
    ("(x-1)^(-1/2)", sp.Interval.open(1, sp.oo)),
    ("x^(2/3)", sp.Interval(0, sp.oo)),
    ("x^(-2/3)", sp.Interval.open(0, sp.oo)),
])
def test_dominio_exponente_crudo_no_modifica_arbol(entrada, esperado):
    from dominios import dominio_funciones_originales

    crudo = p.parsear(entrada)
    antes = sp.srepr(crudo)
    assert dominio_funciones_originales(x, crudo) == esperado
    assert sp.srepr(crudo) == antes
