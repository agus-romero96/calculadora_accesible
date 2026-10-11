"""
Polinomio de Taylor (calculo/taylor.py): el polinomio coincide con series() de SymPy y el
paso a paso sigue el estándar (Regla, En este caso, cuentas, Queda): la fórmula, cada
derivada a partir de la anterior, cada término con f^(k)(x0), k! y su coeficiente, y la suma.
"""
import re

import pytest
import sympy

import exportar
from calculo.taylor import suma_terminos, taylor_latex, taylor_texto, termino_texto
from parser_matematico import ParserMatematico

x = ParserMatematico.simbolo("x")


def pasos(salida):
    texto = salida.split("PASO A PASO:")[1]
    return re.split(r"\n(?=\d+\. )", texto.strip())


def titulos(salida):
    return [p.splitlines()[0].split(". ", 1)[1] for p in pasos(salida)]


# (función, orden, punto, resultado)
CASOS = [
    ("exp(x)", 3, "0", "P_3(x) = 1 + x + x^2/2 + x^3/6"),
    ("sin(x)", 5, "0", "P_5(x) = x - x^3/6 + x^5/120"),
    ("cos(x)", 4, "0", "P_4(x) = 1 - x^2/2 + x^4/24"),
    ("log(x)", 3, "1", "P_3(x) = (x - 1) - (x - 1)^2/2 + (x - 1)^3/3"),
    ("sqrt(x)", 2, "4", "P_2(x) = 2 + (x - 4)/4 - (x - 4)^2/64"),
    ("cos(x)", 4, "pi", "P_4(x) = -1 + (x - pi)^2/2 - (x - pi)^4/24"),
    ("1/(1-x)", 3, "0", "P_3(x) = 1 + x + x^2 + x^3"),
    ("x^3", 2, "1", "P_2(x) = 1 + 3*(x - 1) + 3*(x - 1)^2"),
    ("x^3", 5, "1", "P_5(x) = 1 + 3*(x - 1) + 3*(x - 1)^2 + (x - 1)^3"),
    ("exp(x)", 0, "0", "P_0(x) = 1"),
    ("sin(x)", 2, "pi/4", "P_2(x) = sqrt(2)/2 + (sqrt(2)/2)*(x - pi/4) - (sqrt(2)/4)*(x - pi/4)^2"),
    ("exp(2*x)", 2, "0", "P_2(x) = 1 + 2*x + 2*x^2"),
    ("atan(x)", 3, "0", "P_3(x) = x - x^3/3"),
]


@pytest.mark.parametrize("funcion, orden, punto, resultado", CASOS, ids=[f"{c[0]} n={c[1]} en {c[2]}" for c in CASOS])
def test_resultado_y_estructura(core, funcion, orden, punto, resultado):
    res = core.taylor(funcion, None, orden, punto)
    assert not res.es_error, res.texto
    assert res.operacion == "taylor"
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}"
    assert "AVISO" not in res.texto
    f = ParserMatematico().parsear(funcion).doit()
    x0 = ParserMatematico().parsear(punto).doit()
    verdad = sympy.series(f, x, x0, orden + 1).removeO()
    assert sympy.simplify(sympy.expand(res.valor - verdad)) == 0
    nombres = titulos(res.texto)
    assert nombres[0] == "Fórmula de Taylor." and nombres[-1] == "Sumar los términos."
    for k in range(orden + 1):
        assert f"Término {k} (orden {k})." in nombres
    propios = {"Fórmula de Taylor.", "Sumar los términos."} | {f"Término {k} (orden {k})." for k in range(orden + 1)}
    for paso in pasos(res.texto):
        if paso.splitlines()[0].split(". ", 1)[1] in propios:
            assert "Regla: " in paso and "Queda: " in paso, paso


def test_paso_a_paso_completo(core):
    texto = core.taylor("exp(x)", None, 3, "0").texto
    assert "Alrededor de 0 se llama polinomio de Maclaurin." in texto
    assert "Queda: P_3(x) = f(0) + f'(0)/1!*x + f''(0)/2!*x^2 + f'''(0)/3!*x^3" in texto
    # Cada derivada a partir de la anterior, con su regla
    assert "Derivada 2: f''(x)." in texto
    assert "Derivada de la exponencial en exp(x)." in texto
    # Cada término: el valor en x0, el factorial y el coeficiente
    assert "exp(0) = 1 (valor exacto conocido)." in texto
    assert "3! = 1*2*3 = 6." in texto
    assert "Coeficiente: f'''(0)/3! = 1/6." in texto
    assert "Término: (1/6)*x^3 = x^3/6." in texto
    assert "0! = 1 (por definición)." in texto


def test_terminos_nulos_no_aparecen(core):
    texto = core.taylor("sin(x)", None, 5, "0").texto
    assert "f(0) = 0: el término vale 0 y no aparece en el polinomio." in texto
    assert "f^(4)(0) = 0: el término vale 0 y no aparece en el polinomio." in texto
    assert "Coeficiente: f'''(0)/3! = (-1)/6 = -1/6." in texto


def test_punto_distinto_de_cero_conserva_x_menos_x0(core):
    texto = core.taylor("sqrt(x)", None, 2, "4").texto
    assert "Término: (1/4)*(x - 4) = (x - 4)/4." in texto
    assert "Coeficiente: f''(4)/2! = (-1/32)/2 = -1/64." in texto
    assert "Maclaurin" not in texto


@pytest.mark.parametrize("funcion, orden, punto, mensaje", [
    ("log(x)", 2, "0", "f(x) no está definida en x = 0"),
    ("x^2", 20, "0", "El orden debe estar entre 0 y 15"),
    ("x^2", -1, "0", "El orden debe estar entre 0 y 15"),
    ("x^2", "a", "0", "El orden debe ser un número entero"),
    ("x^2", 2, "", "Falta el punto"),
    ("x^2", 2, "oo", "debe ser un número real"),
])
def test_errores(core, funcion, orden, punto, mensaje):
    res = core.taylor(funcion, None, orden, punto)
    assert res.es_error and mensaje in res.texto, res.texto


def test_texto_de_los_terminos():
    assert termino_texto(sympy.Rational(1, 4), x, 4, 1) == "(x - 4)/4"
    assert termino_texto(sympy.Rational(-1, 2), x, 1, 2) == "-(x - 1)^2/2"
    assert termino_texto(sympy.Integer(3), x, 1, 2) == "3*(x - 1)^2"
    assert termino_texto(sympy.Integer(1), x, 0, 1) == "x"
    assert suma_terminos(["1", "x", "-x^3/6"]) == "1 + x - x^3/6"
    assert taylor_texto(1 + x - x ** 3 / 6, x, 0) == "1 + x - x^3/6"


def test_exportar(core):
    res = core.taylor("sqrt(x)", None, 2, "4")
    assert exportar.resultado_corto(res) == "P_2(x) = 2 + (x - 4)/4 - (x - 4)^2/64"
    assert exportar.latex(res) == (r"P_{2}\left(x\right) = 2 + \frac{\left(x - 4\right)}{4} - "
                                   r"\frac{\left(x - 4\right)^{2}}{64}")
    assert taylor_latex(x - x ** 3 / 6, x, 0, 3) == r"P_{3}\left(x\right) = x - \frac{x^{3}}{6}"
    resumen = exportar.resumen(res)
    assert "Orden: 2" in resumen and "Punto: 4" in resumen
    import xml.dom.minidom
    xml.dom.minidom.parseString(exportar.mathml(res))


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.taylor("exp(x)", None, 2, "0").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert texto.splitlines()[0] == "RESULT: P_2(x) = 1 + x + x^2/2"
    assert "Taylor formula" in texto and "Maclaurin polynomial" in texto
