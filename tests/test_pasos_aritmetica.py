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


@pytest.mark.parametrize("cuenta", ["0/(-1)", "0*(-3)", "(-3)*0"])
def test_con_un_cero_no_hay_regla_de_los_signos(core, cuenta):
    """0 por o entre cualquier número da 0, que no tiene signo: antes decía 'más por menos da más'."""
    salida = core.Evaluar(cuenta)
    assert salida.startswith("RESULTADO: 0") and "Signos" not in salida


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


@pytest.mark.parametrize("expresion, esperado, explicacion", [
    ("-6/2", -3, "Signos: menos entre más da menos."),
    ("sqrt(4/9)", sympy.Rational(2, 3), "sqrt(4/9) = 2/3, porque (2/3)^2 = 4/9."),
    ("log10(2)", sympy.log(2)/sympy.log(10), "log10(2) no tiene un valor exacto sencillo"),
    ("log10(100)", 2, "log10(100) = 2 (valor exacto conocido)."),
    ("2^(-1)", sympy.Rational(1, 2), "2^(-1) = 1/2 = 1/2."),
    ("5^1", 5, "5^1 = 5."),
    ("1e-3", sympy.Rational(1, 1000), "0.001"),
])
def test_regresiones_evaluar_pasos(core, expresion, esperado, explicacion):
    dto = core.aritmetica.evaluar(expresion)
    assert dto.es_exitoso
    assert abs(float(dto.resultado - esperado)) < 1e-15
    salida = core.Evaluar(expresion)
    assert explicacion in salida
    assert "No se pudo explicar" not in salida


@pytest.mark.parametrize("expresion, esperado", [
    ("(x-1)/(x-1)", "1"),
    ("(2*x+2)/(2*x+4)", "(x+1)/(x+2)"),
    ("(2*x+4)/2", "x+2"),
])
def test_regresiones_cancelar_fracciones(core, expresion, esperado):
    dto = core.aritmetica.simplificar(expresion)
    assert dto.es_exitoso
    assert sympy.simplify(dto.resultado - core.parser_comun.parsear(esperado)) == 0
    assert "Factorizar y cancelar" in core.Simplificar(expresion)


def test_producto_de_binomio_y_trinomio_no_es_suma_por_diferencia(core):
    x = core.parser_comun.simbolo("x")
    dto = core.aritmetica.simplificar("(x+1)*(x^2-x+1)")
    assert sympy.expand(dto.resultado) == x**3 + 1
    assert "suma por diferencia" not in core.Simplificar("(x+1)*(x^2-x+1)")


@pytest.mark.parametrize("expresion, esperado", [
    ("2*(sin(x)+1)", lambda x: 2*sympy.sin(x) + 2),
    ("3*(cos(x)-2)", lambda x: 3*sympy.cos(x) - 6),
    ("(sin(x)+1)^2", lambda x: sympy.sin(x)**2 + 2*sympy.sin(x) + 1),
])
def test_distributiva_con_funciones(core, expresion, esperado):
    x = core.parser_comun.simbolo("x")
    dto = core.aritmetica.simplificar(expresion)
    assert dto.es_exitoso
    assert sympy.simplify(dto.resultado - esperado(x)) == 0
    desarrollo = [p for p in dto.pasos if p.titulo == "Desarrollar"]
    assert desarrollo
    assert not any(p.titulo == "Aplicar identidades" for p in dto.pasos)


def test_cubos_de_grado_seis_conservan_factorizacion_correcta(core):
    x = core.parser_comun.simbolo("x")
    esperado = (x**2 + 4)*(x**4 - 4*x**2 + 16)
    propuesta_erronea = (x**2 + 4)*(x**2 - 2*x + 4)*(x**2 + 2*x + 4)
    assert sympy.expand(esperado) == x**6 + 64
    assert sympy.expand(propuesta_erronea) == x**6 + 8*x**4 + 32*x**2 + 64
    dto = core.aritmetica.factorizar("x^6+64")
    assert dto.es_exitoso
    assert dto.resultado == esperado
    assert sympy.expand(dto.resultado) == x**6 + 64
    # Cada factor es irreducible sobre Q; no basta con que el producto sea equivalente.
    assert all(sympy.Poly(f, x, domain=sympy.QQ).is_irreducible for f in dto.resultado.args)
    cubos = next(p for p in dto.pasos if p.titulo.startswith("Suma o diferencia de cubos"))
    assert not any("discriminante" in linea for linea in cubos.calculo)


def test_factorizar_conserva_signo_de_los_pasos(core):
    x = core.parser_comun.simbolo("x")
    dto = core.aritmetica.factorizar("-x^2+4")
    assert dto.resultado == (2-x)*(x+2)
    assert sympy.expand(dto.resultado) == 4-x**2
    assert "RESULTADO: (2 - x)*(x + 2)" in core.Factorizar("-x^2+4")


def test_ruffini_reparte_factor_sin_cambiar_el_producto(core):
    x = core.parser_comun.simbolo("x")
    original = 6*x**3 + x**2 + 8*x - 5
    lineal, cuadratico = 2*x-1, 3*x**2+2*x+5
    assert sympy.expand(lineal*cuadratico) == original
    dto = core.aritmetica.factorizar("6*x^3+x^2+8*x-5")
    assert dto.es_exitoso
    assert dto.resultado == lineal*cuadratico
    assert sympy.expand(dto.resultado) == original
    paso = next(p for p in dto.pasos if p.titulo.startswith("Raíz y Ruffini"))
    assert any("El resto es 0 y el cociente es 6*x^2 + 4*x + 10." in linea for linea in paso.calculo)
    assert any("Pasamos el factor 2" in linea for linea in paso.calculo)


@pytest.mark.parametrize("expresion, esperado", [
    ("12e-3", sympy.Rational(12, 1000)),
    ("1.2e+3", 1200),
    (".5e-2", sympy.Rational(1, 200)),
    ("2pi", 2*sympy.pi),
    ("2log10(100)", 4),
    ("(2)(3)", 6),
    ("(2)3", 6),
])
def test_lector_numerico_conserva_tokens(core, expresion, esperado):
    dto = core.aritmetica.evaluar(expresion)
    assert dto.es_exitoso
    assert abs(float(dto.resultado - esperado)) < 1e-15
    assert "No se pudo explicar" not in core.Evaluar(expresion)
