"""
Paso a paso de Evaluar, Simplificar y Factorizar (pasos_aritmetica.py): formato estándar,
reglas enunciadas, cuentas intermedias y verificación contra SymPy.
"""
import re

import pytest
import sympy

import pasos_aritmetica
from pasos_aritmetica import escribir, leer_cuenta

EVALUAR = ["2+3*4", "10-6/3", "1/3+1/6", "2^3+sqrt(16)", "(2+3)*4-2^2", "2*pi", "sqrt(8)+1", "(1/2)*(3/4)",
           "(2/3)/(4/9)", "sin(pi/2)+cos(0)", "0.5+0.25", "abs(-3)*2", "2(3+4)", "8/2*4", "3-(-2)", "2^10",
           "-2^2", "(-2)^3", "100/7", "log(e)", "e^2", "5"]
SIMPLIFICAR = ["3*x + 2*x - x^2 + 4*x^2", "(x+1)^2 - x^2", "(x^2-1)/(x-1)", "1/x + 1/(x+1)", "sin(x)^2+cos(x)^2",
               "x+1", "2*(x-3)+5*x", "x/(x^2-1) - 1/(x-1)", "(x+2)*(x-2)+4", "(x^2+2*x+1)/(x+1)",
               "2*x*(x+1) - x^2", "exp(log(x))", "(a+b)^2-(a-b)^2", "log(exp(2*x))+x"]
FACTORIZAR = ["2*x^2-18", "x^2-5*x+6", "2*x^2+7*x+3", "x^2+6*x+9", "x^3-8", "x^3+27", "x^3-6*x^2+11*x-6", "x^4-1",
              "x^3+x^2+x+1", "x^2+1", "x^2-9", "4*x^2-25", "x^2-y^2", "x*y+x", "6*x^2-5*x-6", "3*x^2+6*x+3",
              "x^3-2*x^2-5*x+6", "x^2-2", "x^4-5*x^2+4", "2*x^3-8*x"]


def pasos(salida):
    texto = salida.split("PASO A PASO:")[1].split("[!] AVISOS:")[0]
    return re.split(r"\n(?=\d+\. )", texto.strip())


@pytest.mark.parametrize("operacion, expresion", [("Evaluar", e) for e in EVALUAR]
                         + [("Simplificar", e) for e in SIMPLIFICAR] + [("Factorizar", e) for e in FACTORIZAR])
def test_se_explica_con_la_estructura_completa(core, operacion, expresion):
    salida = getattr(core, operacion)(expresion)
    assert salida.startswith("RESULTADO: ")
    assert "No se pudo explicar" not in salida
    for paso in pasos(salida):
        assert "Regla: " in paso and "En este caso: " in paso and "Queda: " in paso, paso


# ---------------- Evaluar ----------------

def test_jerarquia_de_las_operaciones(core):
    salida = core.Evaluar("(2+3)*4-2^2")
    titulos = [p.splitlines()[0] for p in pasos(salida)]
    assert titulos == ["1. Jerarquía de las operaciones.", "2. Suma: 2 + 3.", "3. Potencia: 2^2.",
                       "4. Multiplicación: 5*4.", "5. Resta: 20 - 4."]
    assert "está entre paréntesis o dentro de una función: va primero." in salida
    assert "2^2 = 2*2 = 4." in salida
    assert "Queda: 5*4 - 4" in salida


def test_la_cuenta_se_lee_como_se_escribio():
    # El parser de SymPy reordena (1/3 + 1/6 sería 1/6 + 1/3) y aplana los productos
    assert escribir(leer_cuenta("1/3+1/6")) == "1/3 + 1/6"
    assert escribir(leer_cuenta("(1/2)*(3/4)")) == "(1/2)*(3/4)"
    assert escribir(leer_cuenta("2(3+4)")) == "2*(3 + 4)"
    assert escribir(leer_cuenta("3-(-2)")) == "3 - (-2)"


def test_suma_de_fracciones_con_denominador_comun(core):
    salida = core.Evaluar("1/3+1/6")
    assert "Denominador común: el mínimo común múltiplo de 3 y 6 es 6." in salida
    assert "1/3 = 2/6 (multiplicamos arriba y abajo por 2)." in salida
    assert "Operamos los numeradores: 2 + 1 = 3, así que queda 3/6." in salida
    assert "Simplificamos dividiendo arriba y abajo entre 3: 3/6 = 1/2." in salida


def test_fracciones_y_signos(core):
    assert "(1/2)*(3/4) = (1*3)/(2*4) = 3/8." in core.Evaluar("(1/2)*(3/4)")
    assert "(2/3)/(4/9) = (2/3)*(9/4) = 3/2." in core.Evaluar("(2/3)/(4/9)")
    salida = core.Evaluar("-5+2*(-3)")
    assert "2*(-3) = -6." in salida and "Signos: más por menos da menos." in salida
    assert "(-2)^3 = (-2)*(-2)*(-2) = -8." in core.Evaluar("(-2)^3")
    assert "2^(-2) = 1/2^2 = 1/4." in core.Evaluar("2^(-2)")


def test_raices_y_decimales(core):
    assert "sqrt(16) = 4, porque 4^2 = 16." in core.Evaluar("sqrt(16)+1")
    salida = core.Evaluar("sqrt(8)+1")
    assert "8 = 2^2*2, así que sqrt(8) = 2*sqrt(2)." in salida
    assert "1 + 2*sqrt(2) ≈ 3.8284271247." in salida
    assert "0.5 + 0.25 = 0.75." in core.Evaluar("0.5+0.25")


def test_division_entre_cero(core):
    salida = core.Evaluar("1/(2-2)")
    assert salida.startswith("ERROR") and "No se puede dividir entre 0." in salida


# ---------------- Simplificar ----------------

def test_desarrollar_y_agrupar(core):
    salida = core.Simplificar("2*(x-3)+5*x")
    assert "2*(x - 3) = 2*x - 6." in salida
    assert "2*x + 5*x = (2 + 5)*x = 7*x." in salida
    salida = core.Simplificar("(x+1)^2 - x^2")
    assert "Regla: cuadrado de una suma: (a + b)^2 = a^2 + 2*a*b + b^2." in salida
    assert "x^2 - x^2 = (1 - 1)*x^2 = 0." in salida


def test_cancelar_dice_donde_no_vale(core):
    salida = core.Simplificar("(x^2-1)/(x-1)")
    assert "Factorizamos el numerador: x^2 - 1 = (x - 1)*(x + 1)." in salida
    assert "El factor común es x - 1; lo cancelamos: x + 1." in salida
    assert "Vale para x distinto de 1" in salida


def test_denominador_comun_es_el_minimo_comun_multiplo(core):
    salida = core.Simplificar("x/(x^2-1) - 1/(x-1)")
    assert "Denominador común: (x - 1)*(x + 1)." in salida
    assert "-1/(x - 1) = (-x - 1)/((x - 1)*(x + 1)): multiplicamos arriba y abajo por (x + 1)." in salida
    assert "Sumamos los numeradores: x + (-x - 1) = -1." in salida


def test_identidades(core):
    assert "exp(log(x)) = x." in core.Simplificar("exp(log(x))")
    assert "log(exp(2*x)) = 2*x." in core.Simplificar("log(exp(2*x))+x")
    assert "sin(x)^2 + cos(x)^2 = 1." in core.Simplificar("sin(x)^2+cos(x)^2")


# ---------------- Factorizar ----------------

def test_factor_comun_y_diferencia_de_cuadrados(core):
    salida = core.Factorizar("2*x^2-18")
    assert "2*x^2 entre 2 = x^2." in salida and "-18 entre 2 = -9." in salida
    assert "x^2 = x^2 y 9 = 3^2, así que a = x y b = 3." in salida
    assert "Multiplicando: 2*(x - 3)*(x + 3) = 2*x^2 - 18, que es la expresión original." in salida


def test_trinomios(core):
    salida = core.Factorizar("x^2-5*x+6")
    assert "Buscamos dos números que multiplicados den 6 y sumados den -5: -3 y -2." in salida
    assert "Comprobación: (-3)*(-2) = 6 y (-3) + (-2) = -5." in salida
    salida = core.Factorizar("2*x^2+7*x+3")
    assert "Discriminante: b^2 - 4*a*c = 7^2 - 4*2*3 = 25." in salida
    assert "x1 = (-b + 5)/(2*a) = (-7 + 5)/4 = -1/2." in salida
    assert "2*(x + 1/2) = 2*x + 1" in salida
    assert "Comprobamos el término central: 2*a*b = 2*x*3 = 6*x" in core.Factorizar("x^2+6*x+9")


def test_cubos_agrupacion_y_ruffini(core):
    assert "x^3 = x^3 y 8 = 2^3, así que a = x y b = 2." in core.Factorizar("x^3-8")
    assert "Segundo grupo: x + 1 = 1*(x + 1)." in core.Factorizar("x^3+x^2+x+1")
    salida = core.Factorizar("x^3-6*x^2+11*x-6")
    assert "P(1) = 1*1^3 + (-6)*1^2 + 11*1^1 + (-6) = 1 - 6 + 11 - 6 = 0, así que (x - 1) es un factor." in salida
    assert "(-5)*1 = -5; 11 + (-5) = 6." in salida
    assert "El resto es 0 y el cociente es x^2 - 5*x + 6." in salida
    # Y el cociente se sigue factorizando
    assert "Trinomio x^2 + b*x + c en x^2 - 5*x + 6" in salida


def test_cada_factor_se_vuelve_a_factorizar(core):
    salida = core.Factorizar("x^4-1")
    assert "x^4 = (x^2)^2 y 1 = 1^2" in salida
    assert "Diferencia de cuadrados en x^2 - 1" in salida
    assert "Discriminante: b^2 - 4*a*c = 0^2 - 4*1*1 = -4." in salida


def test_irreducible_explica_el_discriminante(core):
    salida = core.Factorizar("x^2-2")
    assert salida.startswith("RESULTADO: x**2 - 2")
    assert "8 no es un cuadrado perfecto" in salida
    assert "Comprobación" not in salida


# ---------------- Verificación contra SymPy ----------------

def test_explicacion_de_factorizar_que_no_coincide_no_se_muestra(core, monkeypatch):
    monkeypatch.setattr(pasos_aritmetica.ExplicadorFactorizar, "explicar", lambda self, expr: expr + 1)
    salida = core.Factorizar("x^2-9")
    assert salida.startswith("RESULTADO: (x - 3)*(x + 3)")
    assert "No se pudo explicar paso a paso" in salida and "PASO A PASO" not in salida


def test_explicacion_de_evaluar_que_no_coincide_no_se_muestra(core, monkeypatch):
    original = pasos_aritmetica.operar
    monkeypatch.setattr(pasos_aritmetica, "operar",
                        lambda nodo: (lambda r: (r[0] + 1,) + r[1:])(original(nodo)))
    salida = core.Evaluar("2+3*4")
    assert salida.startswith("RESULTADO: 14")
    assert "No se pudo explicar paso a paso" in salida


def test_evaluar_sigue_dando_el_valor_de_sympy(core):
    for expresion in EVALUAR:
        dto = core.aritmetica.evaluar(expresion)
        exacto = sympy.simplify(core.parser_comun.parsear(expresion))
        assert abs(complex(sympy.N(dto.resultado - exacto))) < 1e-9, expresion
