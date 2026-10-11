"""
Derivada implícita (calculo/implicita.py): dy/dx coincide con idiff de SymPy y el paso a paso
sigue el estándar: planteamiento, cada término (la cadena añade y'; el producto cuando hay x e
y), la derivada de cada lado y el despeje de y' sin saltos (factor común, división, simplificar).
"""
import re

import pytest
import sympy

import exportar
from parser_matematico import ParserMatematico

x, y = ParserMatematico.simbolo("x"), ParserMatematico.simbolo("y")


def pasos(salida):
    texto = salida.split("PASO A PASO:")[1]
    return re.split(r"\n(?=\d+\. )", texto.strip())


def titulos(salida):
    return [p.splitlines()[0].split(". ", 1)[1] for p in pasos(salida)]


CASOS = [
    ("x^2 + y^2 = 25", "-x/y"),
    ("x^3 + y^3 = 6*x*y", "(2*y - x^2)/(y^2 - 2*x)"),
    ("x*y = 1", "-y/x"),
    ("x^2*y^3 + x = 5", "-(2*x*y^3 + 1)/(3*x^2*y^2)"),
    ("y^2 = x", "1/(2*y)"),
    ("sin(y) + x = 1", "-1/cos(y)"),
    ("x*exp(y) = 2", "-1/x"),
    ("x/y = 3", "y/x"),
    ("y^3 + 2*y = x^2", "2*x/(3*y^2 + 2)"),
    ("x^2 - x*y + y^2 = 3", "(y - 2*x)/(2*y - x)"),
]


@pytest.mark.parametrize("entrada, resultado", CASOS, ids=[c[0] for c in CASOS])
def test_resultado_y_estructura(core, entrada, resultado):
    res = core.derivada_implicita(entrada)
    assert not res.es_error, res.texto
    assert res.operacion == "implicita"
    assert res.texto.splitlines()[0] == f"RESULTADO: dy/dx = {resultado}"
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    izq, der = (ParserMatematico().parsear(lado).doit() for lado in entrada.split("="))
    assert sympy.simplify(res.valor - sympy.idiff(izq - der, y, x)) == 0
    nombres = titulos(res.texto)
    assert nombres[0] == "Planteamiento." and nombres[-1] == "Despejar y'."
    assert "Derivada del lado izquierdo." in nombres and "Derivada del lado derecho." in nombres
    propios = {"Planteamiento.", "Derivada del lado izquierdo.", "Derivada del lado derecho.", "Despejar y'."}
    for paso in pasos(res.texto):
        nombre = paso.splitlines()[0].split(". ", 1)[1]
        if nombre in propios or nombre.startswith(("Regla de la cadena en", "Regla del producto en")):
            assert "Regla: " in paso and "Queda: " in paso, paso


def test_circunferencia_paso_a_paso(core):
    texto = core.derivada_implicita("x^2 + y^2 = 25").texto
    assert "Regla de la potencia en y^2." in texto  # la derivada respecto a y, con su regla
    assert "Como y depende de x, se multiplica por y': d/dx(y^2) = (2*y)*y' = 2*y*y'." in texto
    assert "25 es una constante: su derivada es 0." in texto
    assert "Queda 2*y*y' = -2*x." in texto
    assert "Dividimos los dos lados entre 2*y (suponiendo que no vale 0): y' = (-2*x)/(2*y)." in texto
    assert "El numerador y el denominador tienen el factor común 2: se simplifica." in texto


def test_producto_y_factor_comun_de_y_prima(core):
    texto = core.derivada_implicita("x^3 + y^3 = 6*x*y").texto
    assert "Regla del producto en 6*x*y." in titulos(texto)
    assert "u = 6*x (con u' = 6) y v = y (con v' = y', por la regla de la cadena)." in texto
    assert "Pasamos 6*x*y' a la izquierda cambiando de signo" in texto
    assert "Sacamos y' factor común: 3*y^2*y' - 6*x*y' = y'*(3*y^2 - 6*x)." in texto
    assert "y' = (6*y - 3*x^2)/(3*y^2 - 6*x)." in texto
    # La simplificación se ve: no cambia de signo sin decirlo
    assert "y' = (2*y - x^2)/(y^2 - 2*x)." in texto


def test_dividir_entre_una_fraccion(core):
    texto = core.derivada_implicita("x/y = 3").texto
    assert "Dividir entre -x/y^2 es multiplicar por su inverso, -y^2/x: (-1/y)*(-y^2/x) = y/x." in texto


def test_otras_variables(core):
    res = core.derivada_implicita("t^2 + s^2 = 4")
    assert res.texto.splitlines()[0] == "RESULTADO: dt/ds = -s/t"
    assert "Se toma t como función de s" in res.texto


def test_sin_explicacion_lo_resuelve_sympy(core):
    res = core.derivada_implicita("sin(x*y) = x")
    assert not res.es_error
    assert "NOTA: hay explicación paso a paso cuando cada término es un producto" in res.texto
    assert "PASO A PASO" not in res.texto


@pytest.mark.parametrize("entrada, mensaje", [
    ("x^2 + y^2", "Escriba una ecuación con un signo ="),
    ("x^2 + 3 = 1", "necesita una ecuación con dos variables"),
    ("x + y + z = 1", "esta tiene 3 (x, y, z)"),
    ("= 3", "Falta uno de los dos lados"),
    ("y + x - y = 2", "necesita una ecuación con dos variables"),
])
def test_errores(core, entrada, mensaje):
    res = core.derivada_implicita(entrada)
    assert res.es_error and mensaje in res.texto, res.texto


def test_exportar(core):
    res = core.derivada_implicita("x^2 + y^2 = 25")
    assert exportar.resultado_corto(res) == "dy/dx = -x/y"
    assert exportar.latex(res) == r"\frac{dy}{dx} = - \frac{x}{y}"
    assert "Variable dependiente: y" in exportar.resumen(res)
    import xml.dom.minidom
    xml.dom.minidom.parseString(exportar.mathml(res))


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.derivada_implicita("x^2 + y^2 = 25").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert texto.splitlines()[0] == "RESULT: dy/dx = -x/y"
    assert "Chain rule on y^2" in texto and "Solve for y'" in texto
