"""
Recta tangente y recta normal (calculo/rectas.py): las rectas coinciden con las de SymPy y
el paso a paso sigue el estándar (Regla, En este caso, cuentas, Queda), sin saltos: punto de
tangencia con sus cuentas, la derivada, la pendiente, la ecuación punto-pendiente despejada,
la pendiente de la normal y la comprobación.
"""
import re

import pytest
import sympy

import exportar
from calculo.rectas import ecuacion_recta, recta_texto
from parser_matematico import ParserMatematico

x = ParserMatematico.simbolo("x")
y = ParserMatematico.simbolo("y")


def pasos(salida):
    texto = salida.split("PASO A PASO:")[1]
    return re.split(r"\n(?=\d+\. )", texto.strip())


def titulos(salida):
    return [p.splitlines()[0].split(". ", 1)[1] for p in pasos(salida)]


# (función, punto, tangente, normal) — la normal None si es vertical
CASOS = [
    ("x^3 - 2*x", "1", "y = x - 2", "y = -x"),
    ("x^2", "-2", "y = -4*x - 4", "y = x/4 + 9/2"),
    ("x^2", "0", "y = 0", "x = 0"),
    ("(x^2+1)/(x-1)", "2", "y = -x + 7", "y = x + 3"),
    ("exp(x)", "0", "y = x + 1", "y = -x + 1"),
    ("sin(x)", "pi/4", "y = sqrt(2)*x/2 + sqrt(2)/2 - sqrt(2)*pi/8", "y = -sqrt(2)*x + sqrt(2)/2 + sqrt(2)*pi/4"),
    ("log(x)", "1", "y = x - 1", "y = -x + 1"),
    ("sqrt(x)", "4", "y = x/4 + 1", "y = -4*x + 18"),
    ("1/x", "2", "y = -x/4 + 1", "y = 4*x - 15/2"),
    ("3*x + 1", "5", "y = 3*x + 1", "y = -x/3 + 53/3"),
    ("5", "3", "y = 5", "x = 3"),
    ("t^2 + t", "1", None, None),  # otra variable: y = 3*t - 1
]


@pytest.mark.parametrize("funcion, punto, tangente, normal", CASOS, ids=[f"{c[0]} en {c[1]}" for c in CASOS])
def test_rectas_y_estructura(core, funcion, punto, tangente, normal):
    res = core.recta_tangente(funcion, None, punto)
    assert not res.es_error, res.texto
    assert res.operacion == "tangente"
    lineas = res.texto.splitlines()
    assert lineas[0] == "RESULTADO:"
    if tangente:
        assert lineas[1] == f"Recta tangente: {tangente}"
        assert lineas[2] == f"Recta normal: {normal}"
    assert "AVISO" not in res.texto
    # La verdad: las rectas de SymPy
    variable = ParserMatematico.simbolo(res.parametros["variable"])
    f = ParserMatematico().parsear(funcion).doit()
    x0 = ParserMatematico().parsear(punto).doit()
    y0, m = f.subs(variable, x0), sympy.diff(f, variable).subs(variable, x0)
    t, n = res.valor
    assert sympy.simplify(t.rhs - (y0 + m * (variable - x0))) == 0
    if m == 0:
        assert n == sympy.Eq(variable, x0)
    else:
        assert sympy.simplify(n.rhs - (y0 - (variable - x0) / m)) == 0
    # Estructura: cada paso con regla y resultado; empieza por el punto y acaba comprobando
    nombres = titulos(res.texto)
    assert nombres[0] == "Punto de tangencia." and nombres[1] == "Derivar la función."
    assert nombres[-1] == "Comprobación."
    propios = {"Punto de tangencia.", "Derivar la función.", "Pendiente de la recta tangente.",
               "Ecuación de la recta tangente.", "Pendiente de la recta normal.", "Ecuación de la recta normal.",
               "Recta normal.", "Comprobación."}
    # Los pasos de la derivada son los de Derivar, con su propio formato (lo prueba test_derivadas.py)
    for paso in pasos(res.texto):
        if paso.splitlines()[0].split(". ", 1)[1] in propios:
            assert "Regla: " in paso and "Queda: " in paso, paso
    assert "NO se cumple" not in res.texto


def test_cuentas_sin_saltos(core):
    texto = core.recta_tangente("x^3 - 2*x", None, "1").texto
    # Punto de tangencia, operación a operación
    assert "Sustituimos x = 1: 1^3 - 2*1." in texto
    assert "1^3 = 1*1*1 = 1. Queda 1 - 2*1." in texto
    assert "2*1 = 2. Queda 1 - 2." in texto
    assert "Queda: f(1) = -1: el punto es (1, -1)." in texto
    # La derivada, con el paso a paso de Derivar
    assert "Regla de la potencia en x^3 (término 1 de la suma)." in texto
    assert "Queda: f'(x) = 3*x^2 - 2" in texto
    # Pendiente
    assert "Sustituimos x = 1: 3*1^2 - 2." in texto and "Queda: m = 1" in texto
    # Ecuación punto-pendiente
    assert "Sustituimos: y - (-1) = 1*(x - 1)." in texto
    assert "Operamos: y - (-1) = y + 1." in texto
    assert "Multiplicar por 1 no cambia nada: 1*(x - 1) = x - 1." in texto
    # Normal
    assert "m_n = -1/1 = -1." in texto
    assert "Quitamos paréntesis (propiedad distributiva): -(x - 1) = -x + 1." in texto
    # Comprobación
    assert "Tangente (y = x - 2): con x = 1, y = 1 - 2 = -1, que es -1: se cumple." in texto
    assert "Perpendiculares: m*m_n = 1*(-1) = -1: se cumple." in texto


def test_ordena_como_m_x_mas_b(core):
    texto = core.recta_tangente("(x^2+1)/(x-1)", None, "2").texto
    assert "Operamos cada lado: y = 7 - x." in texto
    assert "Ordenamos como y = m*x + b: y = -x + 7." in texto


def test_sin_parentesis_innecesarios(core):
    texto = core.recta_tangente("sin(x)", None, "pi/4").texto
    assert "Sustituimos: y - sqrt(2)/2 = (sqrt(2)/2)*(x - pi/4)." in texto
    assert "sin(pi/4) = sqrt(2)/2 (valor exacto conocido)." in texto


def test_tangente_horizontal_y_normal_vertical(core):
    texto = core.recta_tangente("x^2", None, "0").texto
    assert "Multiplicar por 0 da 0: 0*x = 0." in texto
    assert "No se puede dividir entre 0, así que -1/m no existe" in texto
    assert "Perpendiculares: la tangente es horizontal y la normal vertical: se cumple." in texto


@pytest.mark.parametrize("funcion", ["sqrt(x)", "x^(1/3)"])
def test_tangente_vertical(core, funcion):
    res = core.recta_tangente(funcion, None, "0")
    assert not res.es_error, res.texto
    assert res.texto.splitlines()[1:3] == ["Recta tangente: x = 0", "Recta normal: y = 0"]
    assert "la pendiente es infinita y la tangente es vertical" in res.texto


@pytest.mark.parametrize("funcion, punto, mensaje", [
    ("abs(x)", "0", "no es derivable en x = 0 (la derivada vale -1 por la izquierda y 1 por la derecha)"),
    ("1/x", "0", "no está definida en x = 0"),
    ("log(x)", "-1", "no está definida en x = -1"),
    ("x^2", "", "Falta el punto"),
    ("x^2", "a", "debe ser un número real"),
    ("x^2", "oo", "debe ser un número real"),
])
def test_errores(core, funcion, punto, mensaje):
    res = core.recta_tangente(funcion, None, punto)
    assert res.es_error and mensaje in res.texto, res.texto


def test_variable_elegida_con_varias(core):
    res = core.recta_tangente("a*x^2", "x", "1")
    assert not res.es_error
    assert res.texto.splitlines()[1] == "Recta tangente: y = 2*a*x - a"


def test_recta_texto():
    assert recta_texto(7 - x, x) == "-x + 7"
    assert recta_texto(sympy.Integer(5), x) == "5"
    assert recta_texto(2 * x, x) == "2*x"
    assert ecuacion_recta(sympy.Eq(x, 3), x) == "x = 3"
    assert ecuacion_recta(sympy.Eq(y, 1 - x / 2), x) == "y = -x/2 + 1"


def test_exportar(core):
    res = core.recta_tangente("x^3 - 2*x", None, "1")
    assert exportar.resultado_corto(res) == "tangente: y = x - 2; normal: y = -x"
    assert exportar.latex(res) == r"\text{Tangente: } y = x - 2,\quad \text{Normal: } y = - x"
    assert "<mtext>Tangente: </mtext>" in exportar.mathml(res)
    resumen = exportar.resumen(res)
    assert resumen.splitlines()[:3] == ["RESULTADO:", "Recta tangente: y = x - 2", "Recta normal: y = -x"]
    assert "Punto: 1" in resumen


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.recta_tangente("x^2", None, "1").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert texto.splitlines()[:3] == ["RESULT:", "Tangent line: y = 2*x - 1", "Normal line: y = -x/2 + 3/2"]
    assert "Point of tangency" in texto and "Slope of the normal line" in texto
