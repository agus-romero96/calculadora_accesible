"""Regresiones de validez: sustitución independiente y restricciones reales."""
import pytest
import sympy as s

from calculo.edo import C, Despeje, MotorEdo
from parser_matematico import ParserMatematico


@pytest.fixture
def motor():
    return MotorEdo(ParserMatematico())


def residuo(entrada, resultado, curva):
    edo = MotorEdo(ParserMatematico())._leer(entrada)
    cambios = {edo.y: curva}
    cambios.update({d: s.diff(curva, edo.x, n) for n, d in enumerate(edo.derivadas, 1)})
    return (edo.izquierda - edo.derecha).xreplace(cambios)


def test_raiz_con_condicion_descarta_signo_espurio(motor):
    entrada = "y' = sqrt(y), y(0) = 1"
    r = motor.resolver(entrada)
    assert not r.es_error, r.texto
    assert len(r.soluciones) == 1
    curva = r.soluciones[0].rhs
    assert curva.subs(r.x, 0) == 1
    assert s.diff(curva, r.x).subs(r.x, 0) == 1
    assert "x/2 + 1 >= 0" in r.texto
    for punto in [-1, 0, 3]:
        assert s.simplify(residuo(entrada, r, curva).subs(r.x, punto)) == 0
    assert s.simplify(residuo(entrada, r, curva).subs(r.x, -3)) != 0


def test_raiz_variable_restringida_y_equilibrio(motor):
    entrada = "y' = 2*x*sqrt(y)"
    r = motor.resolver(entrada)
    assert not r.es_error
    assert s.Eq(r.y, 0) in r.soluciones
    assert "x^2/2 + C >= 0" in r.texto
    curva = next(v.rhs for v in r.soluciones if v.rhs.has(C))
    resto = residuo(entrada, r, curva).subs(C, -2)
    assert resto.subs(r.x, 3).simplify() == 0
    assert resto.subs(r.x, 1).simplify() != 0


def test_raiz_decreciente_conserva_signo_de_constante_y_dominio(motor):
    entrada = "y'=-sqrt(y), y(0)=1"
    r = motor.resolver(entrada)
    assert not r.es_error, r.texto
    assert len(r.soluciones) == 1
    curva = r.soluciones[0].rhs
    assert curva.subs(r.x, 0) == 1
    assert s.diff(curva, r.x).subs(r.x, 0) == -1
    assert "1 - x/2 >= 0" in r.texto
    for punto in [-1, 0, 1]:
        assert residuo(entrada, r, curva).subs(r.x, punto).simplify() == 0
    assert residuo(entrada, r, curva).subs(r.x, 3).simplify() != 0


def test_logaritmo_constante_no_aditiva_y_equilibrio(motor):
    r = motor.resolver("y' = y*log(y)^2")
    assert not r.es_error and "PASO A PASO" in r.texto
    assert s.Eq(r.y, 1) in r.soluciones
    assert s.Eq(r.y, 0) not in r.soluciones
    curva = next(v.rhs for v in r.soluciones if v.rhs.has(C))
    assert s.simplify(curva - s.exp(1/(C-r.x))) == 0
    assert "Ne(" in r.texto  # El polo queda excluido explícitamente.
    resto = residuo("y'=y*log(y)^2", r, curva).subs(C, 2)
    for punto in [0, 1, 3]:
        assert s.simplify(resto.subs(r.x, punto)) == 0


def test_abs_no_absorbe_pendiente(motor):
    x, y = s.symbols("x y", real=True)
    despeje = Despeje(y, [x])
    ramas = despeje.resolver(s.Abs(y), x+C)
    assert set(ramas) == {x+C, -x-C}
    assert s.Ge(x+C, 0) in despeje.restricciones


def test_dominio_excluye_extremo_sin_derivada(motor):
    r = motor.resolver("2*y*y'=1")
    assert not r.es_error, r.texto
    edo = motor._leer("2*y*y'=1")
    assert len(r.soluciones) == 2
    for curva in r.soluciones:
        restricciones = motor._dominio_solucion(curva, edo)
        assert any(s.simplify(cond.subs({C: 0, r.x: 0})) == s.false for cond in restricciones)
        assert all(s.simplify(cond.subs({C: 0, r.x: 1})) == s.true for cond in restricciones)


@pytest.mark.parametrize("entrada,variable", [
    ("y'(x)=2*x", "x"), ("dy(x)/dx=2*x", "x"),
    ("y(x)'=2*x", "x"),
    ("y'(t)=2*t", "t"), ("y'=2*t+0*y(t)", "t"),
    ("d^2y/dx^2=2*x", "x"),
])
def test_notacion_completa(motor, entrada, variable):
    r = motor.resolver(entrada)
    assert not r.es_error, r.texto
    assert str(r.x) == variable
    for curva in r.soluciones:
        assert s.simplify(residuo(entrada, r, curva.rhs)) == 0


@pytest.mark.parametrize("entrada", [
    "d2y/dx3=2*x", "dy/dx2=2*x", "dy(t)/dx=2*x",
    "y'(t)+y(x)=0", "y'''(x+1)=x",
])
def test_notacion_no_reconocida_no_cambia_ecuacion(motor, entrada):
    assert motor.resolver(entrada).es_error


def test_reducida_conserva_constantes_y_condiciones_derivadas(motor):
    r = motor.resolver("y''=y'^2")
    assert not r.es_error
    assert any(not curva.rhs.has(r.x) for curva in r.soluciones)
    assert "Ne(" in r.texto
    for pendiente in [0, 2]:
        entrada = f"y''=y'^2, y(0)=1, y'(0)={pendiente}"
        r = motor.resolver(entrada)
        assert not r.es_error, r.texto
        for curva in r.soluciones:
            assert curva.rhs.subs(r.x, 0) == 1
            # Se deriva log(Abs(u)) en un intervalo que no cruza u=0.
            valor = curva.rhs.replace(
                lambda e: e.func == s.log and e.args[0].func == s.Abs,
                lambda e: s.log(e.args[0].args[0]))
            assert s.diff(valor, r.x).subs(r.x, 0).simplify() == pendiente


def test_clairaut_singular_con_y_sin_condicion_compatible(motor):
    r = motor.resolver("y=x*y'+y'^2, y(2)=-1")
    assert not r.es_error
    assert s.Eq(r.y, -r.x**2/4) in r.soluciones
    for curva in r.soluciones:
        assert curva.rhs.subs(r.x, 2) == -1
        assert residuo("y=x*y'+y'^2", r, curva.rhs).simplify() == 0
    incompatible = motor.resolver("y=x*y'+y'^2, y(2)=0")
    assert s.Eq(incompatible.y, -incompatible.x**2/4) not in incompatible.soluciones
