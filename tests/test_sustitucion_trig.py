"""
Integración por sustitución trigonométrica (calculo/sustitucion_trig.py): la primitiva es
correcta (su derivada es la función) y el paso a paso sigue el método de clase: el caso según
la raíz, dx, la raíz simplificada con la identidad pitagórica, la integral en θ, y la vuelta a x
con el triángulo rectángulo.
"""
import pytest
import sympy

from calculo import sustitucion_trig
from parser_matematico import ParserMatematico

x = ParserMatematico.simbolo("x")


def titulos(res):
    return [p.titulo for p in res.pasos]


def textos(res):
    return "\n".join(l for p in res.pasos for l in (p.titulo, p.regla, p.partes, *p.calculo, p.queda))


# (función, cambio esperado)
CASOS = [
    ("sqrt(4-x^2)", "x = 2*sin(θ)"),
    ("x^2/sqrt(9-x^2)", "x = 3*sin(θ)"),
    ("1/(x^2*sqrt(9-x^2))", "x = 3*sin(θ)"),
    ("sqrt(4-9*x^2)", "x = 2*sin(θ)/3"),
    ("1/sqrt(x^2+4)", "x = 2*tan(θ)"),
    ("1/(4+x^2)^(3/2)", "x = 2*tan(θ)"),
    ("sqrt(1+x^2)", "x = tan(θ)"),
    ("sqrt(x^2-9)/x", "x = 3*sec(θ)"),
    ("1/sqrt(x^2-1)", "x = sec(θ)"),
]


@pytest.mark.parametrize("funcion, cambio", CASOS, ids=[c[0] for c in CASOS])
def test_primitiva_correcta_y_explicada(core, funcion, cambio):
    res = core.calculo.CalcularIntegral(funcion)
    assert res.es_exitoso
    assert res.estrategia_principal == "Sustitución trigonométrica"
    f = ParserMatematico().parsear(funcion).doit()
    positiva = sympy.Dummy("x", positive=True)  # el caso de la secante vale para x >= a
    resta = sympy.diff(res.resultado, x) - f
    assert sympy.simplify(resta) == 0 or sympy.simplify(resta.subs(x, positiva)) == 0
    assert not res.resultado.has(sympy.I, sympy.Piecewise)
    nombres = titulos(res)
    assert nombres[:4] == ["Elegir la sustitución trigonométrica", "Calcular dx", "Simplificar la raíz",
                           "Escribir la integral en θ"]
    assert "Volver a x con el triángulo rectángulo" in nombres
    assert res.pasos[0].queda == cambio


def test_caso_seno_completo(core):
    texto = textos(core.calculo.CalcularIntegral("sqrt(4-x^2)"))
    assert "la raíz es sqrt(4 - x^2), del tipo a^2 - x^2: A = 4 y B = -1." in texto
    assert "k = sqrt(|A|/|B|) = sqrt(4/1) = 2." in texto
    assert "La derivada de 2*sin(θ) es 2*cos(θ)." in texto
    assert "Sacamos 4 factor común: 4 - 4*sin(θ)^2 = 4*(1 - sin(θ)^2)." in texto
    assert "Identidad pitagórica: 1 - sin(θ)^2 = cos(θ)^2, así que queda 4*cos(θ)^2." in texto
    assert "La raíz: sqrt(4*cos(θ)^2) = 2*cos(θ) (con θ entre -pi/2 y pi/2, donde cos(θ) >= 0)." in texto
    assert "Sustituimos: ∫ sqrt(4 - x^2) dx = ∫ (2*cos(θ))*(2*cos(θ)) dθ." in texto
    # La integral en θ, con el explicador de integrales (cos^2 se reescribe)
    assert "cos(θ)^2 = cos(2*θ)/2 + 1/2." in texto
    # La vuelta con el triángulo
    assert "sin(2*θ) = 2*sin(θ)*cos(θ)" in texto
    assert "Cateto adyacente, por Pitágoras: sqrt(2^2 - x^2) = sqrt(4 - x^2)." in texto
    assert "cos(θ) = adyacente/hipotenusa = sqrt(4 - x^2)/2." in texto
    assert "El ángulo: θ = asin(x/2)." in texto
    assert "Sustituimos en 2*θ + 2*sin(θ)*cos(θ): 2*asin(x/2) + 2*(x/2)*(sqrt(4 - x^2)/2)." in texto


def test_caso_tangente_y_definicion_de_asinh(core):
    res = core.calculo.CalcularIntegral("1/sqrt(x^2+4)")
    texto = textos(res)
    assert "Identidad pitagórica: 1 + tan(θ)^2 = sec(θ)^2" in texto
    assert "Integral trigonométrica de la tabla" in texto or "log(tan(θ) + sec(θ))" in texto
    assert "Hipotenusa, por Pitágoras: sqrt(x^2 + 2^2) = sqrt(x^2 + 4)." in texto
    assert "Por definición, asinh(u) = log(u + sqrt(u^2 + 1))" in texto


def test_caso_secante_da_una_primitiva_real(core):
    res = core.calculo.CalcularIntegral("sqrt(x^2-9)/x")
    texto = textos(res)
    assert res.resultado == sympy.sqrt(x ** 2 - 9) - 3 * sympy.acos(3 / x)
    assert "θ entre 0 y pi/2 (x >= 3), donde tan(θ) >= 0" in texto
    assert "sec(θ) = x/3, es decir, cos(θ) = 3/x" in texto
    assert any("NOTA: la primitiva de SymPy tiene trozos o números complejos" in a for a in res.advertencias)


def test_tabla_trigonometrica(core):
    texto = textos(core.calculo.CalcularIntegral("1/(x^2*sqrt(9-x^2))"))
    assert "Integral trigonométrica de la tabla" in texto
    assert "Comprobación: la derivada de -cot(θ) es" in texto
    texto = textos(core.calculo.CalcularIntegral("sqrt(1+x^2)"))
    assert "∫ sec(θ)^3 dθ" in texto


@pytest.mark.parametrize("funcion", ["x/sqrt(4-x^2)", "1/sqrt(4-x^2)", "x*sqrt(x^2+1)", "sqrt(x)", "sqrt(x^2+2*x)"])
def test_casos_que_van_por_otro_metodo(funcion):
    """Impar en x (cambio u = A + B*x^2), arcoseno de la tabla, o raíces que no son de la forma A + B*x^2."""
    assert not sustitucion_trig.aplica(ParserMatematico().parsear(funcion).doit(), x)


def test_integral_definida(core):
    res = core.integral_definida("sqrt(4-x^2)", None, "0", "2")
    assert not res.es_error
    assert res.valor == sympy.pi
    assert "Elegir la sustitución trigonométrica" in res.texto


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.integrar("sqrt(4-x^2)").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert "Choose the trigonometric substitution" in texto and "Back to x with the right triangle" in texto
    assert "cos(θ) = adjacent/hypotenuse" in texto
