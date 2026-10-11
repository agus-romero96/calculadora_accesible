"""
Explicación de las integrales (calculo/integrales.py y la regla de Barrow): cada regla se
enuncia, se identifican sus partes, se muestran la sustitución y las cuentas, y lo que
queda; y la explicación llega siempre a una primitiva correcta, la que se muestra.
"""
import pytest
import sympy

from calculo.integrales import ExplicadorIntegral
from calculo.pasos import texto

x = sympy.Symbol("x", real=True)

EXPRESIONES = [
    "x", "x^3", "3*x^2+2*x", "x^2-4*x+1", "sqrt(x)", "1/x", "1/x^2", "1/sqrt(x)", "exp(x)", "exp(-x)", "exp(3*x)",
    "2^x", "sin(x)", "cos(x)", "cos(2*x)", "sin(x)^2", "cos(x)^2", "tan(x)", "sec(x)^2", "1/(1+x^2)", "1/sqrt(1-x^2)",
    "x*exp(x)", "x^2*exp(x)", "x*sin(x)", "x*cos(x)", "log(x)", "x*log(x)", "exp(x)*sin(x)", "exp(x)*cos(x)",
    "x/(x^2+1)", "2*x*cos(x^2)", "x*exp(x^2)", "1/(2*x+1)", "(x+1)^2", "(2*x+1)^5", "sin(x)*cos(x)", "cos(x)^3",
    "sin(x)^3", "1/(x^2-1)", "x/(x+1)", "(x^2+1)/x", "1/(x^2+2*x+5)", "sqrt(1-x^2)", "atan(x)", "exp(x)/(1+exp(x))",
    "log(x)/x", "1/(x*log(x))", "sinh(x)", "cosh(2*x)", "x*sqrt(x^2+1)", "log(x,10)", "tan(x)^2",
]


def integral(core, expresion):
    res = core.calculo.CalcularIntegral(expresion)
    assert res.es_exitoso, res.mensaje_error
    return res


def lineas(core, expresion):
    return core.Integrar(expresion).split("PASO A PASO:")[1]


@pytest.mark.parametrize("expresion", EXPRESIONES)
def test_toda_integral_se_explica_hasta_el_resultado(core, expresion):
    res = integral(core, expresion)
    assert res.pasos, res.advertencias
    assert not any("No se pudo explicar" in a for a in res.advertencias)
    # El último paso es la constante de integración, sobre la primitiva mostrada
    assert res.pasos[-1].titulo == "Constante de integración"
    assert res.pasos[-1].queda == f"{texto(res.resultado)} + C"
    # Y el anterior deja exactamente esa primitiva
    assert res.pasos[-2].queda == texto(res.resultado)


@pytest.mark.parametrize("expresion", EXPRESIONES)
def test_cada_paso_tiene_la_estructura_completa(core, expresion):
    """Planteamiento: regla y partes; sustitución o resultado: cuentas y lo que queda."""
    for paso in integral(core, expresion).pasos:
        if paso.titulo.endswith((": sustitución", ": resultado")):
            assert paso.calculo and paso.queda and not paso.regla, paso
        elif paso.titulo == "Constante de integración":
            assert paso.regla and paso.queda
        else:
            assert paso.regla and (paso.partes or paso.calculo), paso


def test_regla_de_la_potencia_desglosada(core):
    texto_pasos = lineas(core, "sqrt(x)")
    assert "Regla: la integral de x^n es x^(n+1)/(n+1), si n no es -1" in texto_pasos
    assert "En este caso: la base es x y el exponente n es 1/2, porque sqrt(x) es lo mismo que x^(1/2)." in texto_pasos
    assert "Sumamos 1 al exponente: 1/2 + 1 = 3/2." in texto_pasos
    assert "Dividimos entre el exponente nuevo: x^(3/2)/(3/2)." in texto_pasos
    assert "Dividir entre 3/2 es multiplicar por 2/3." in texto_pasos
    assert "Queda: 2*x^(3/2)/3" in texto_pasos
    orden = [texto_pasos.index(s) for s in ("Regla:", "En este caso:", "Sumamos", "Dividimos", "Queda:")]
    assert orden == sorted(orden)


def test_factor_constante_y_suma(core):
    texto_pasos = lineas(core, "3*x^2+2*x")
    assert "Regla del factor constante en ∫ 3*x^2 dx (término 1 de la suma)" in texto_pasos
    assert "Regla de la potencia en ∫ x^2 dx (f del factor constante)" in texto_pasos
    assert "Multiplicamos los números: 3 * (1/3) = 1." in texto_pasos
    assert "Juntamos las integrales de los términos: x^3 + x^2." in texto_pasos
    assert "Queda: x^3 + x^2 + C" in texto_pasos


def test_sustitucion_muestra_que_parte_es_du(core):
    texto_pasos = lineas(core, "tan(x)")
    assert "En este caso: tan(x) = sin(x)/cos(x)." in texto_pasos
    assert "tomamos u = cos(x), porque su derivada, -sin(x), aparece en el integrando" in texto_pasos
    assert "Derivamos u: du = -sin(x) dx." in texto_pasos
    # El signo de du no se esconde: sin(x) = (-1/cos(x))*(-sin(x))
    assert "Escribimos el integrando como una función de cos(x) por su derivada: " \
           "sin(x)/cos(x) = (-1/cos(x))*(-sin(x))." in texto_pasos
    assert "Cambiamos cos(x) por u y -sin(x) dx por du." in texto_pasos
    assert "Reescribimos la integral en u: ∫ sin(x)/cos(x) dx = ∫ -1/u du." in texto_pasos
    assert "Volvemos a x sustituyendo u = cos(x) en -log(u): -log(cos(x))." in texto_pasos


def test_constante_que_completa_la_derivada(core):
    texto_pasos = lineas(core, "x/(x^2+1)")
    assert "la constante c es 1/2 y f = 2*x/(x^2 + 1), porque x/(x^2 + 1) = (1/2)*(2*x/(x^2 + 1))." in texto_pasos


def test_integracion_por_partes(core):
    texto_pasos = lineas(core, "x*exp(x)")
    assert "Regla: ∫ u dv = u*v - ∫ v du." in texto_pasos
    assert "En este caso: u = x y dv = exp(x) dx." in texto_pasos
    assert "Derivamos u: du = 1 dx." in texto_pasos
    assert "Integral de la exponencial en ∫ exp(x) dx (v, la integral de dv)" in texto_pasos
    assert "Sustituimos u, v y du en u*v - ∫ v du: x*exp(x) - ∫ exp(x) dx." in texto_pasos
    assert "Integral de la exponencial en ∫ exp(x) dx (∫ v du de las partes)" in texto_pasos
    assert "Restamos la integral que quedaba, exp(x): x*exp(x) - exp(x)." in texto_pasos


def test_partes_ciclicas_despeja_la_integral(core):
    texto_pasos = lineas(core, "exp(x)*sin(x)")
    assert "Partes 1: u = sin(x), dv = exp(x) dx, así que du = cos(x) dx y v = exp(x)." in texto_pasos
    assert "I = exp(x)*sin(x) - exp(x)*cos(x) + (-1)*I." in texto_pasos
    assert "y 1 - (-1) = 2." in texto_pasos
    assert "Despejamos I dividiendo entre 2: I = exp(x)*sin(x)/2 - exp(x)*cos(x)/2." in texto_pasos


def test_tabla_con_comprobacion(core):
    texto_pasos = lineas(core, "sin(x)")
    assert "En este caso: en la tabla, ∫ sin(x) dx = -cos(x)." in texto_pasos
    assert "Comprobación: la derivada de -cos(x) es sin(x)." in texto_pasos


def test_otra_primitiva_que_difiere_en_una_constante(core):
    res = integral(core, "(x+1)^2")
    otra = next(p for p in res.pasos if p.titulo == "Otra forma de la primitiva")
    assert otra.calculo == ("Se diferencian en una constante: (x + 1)^3/3 - (x^3/3 + x^2 + x) = 1/3.",)


def test_cociente_con_division_se_explica_dividiendo(core):
    """
    (x^2+1)/x: antes se explicaba con las alternativas de SymPy (la primera, u = x^2, daba
    log(x^2)/2); ahora, como en clase, dividiendo los polinomios: x + 1/x.
    """
    res = integral(core, "(x^2+1)/x")
    assert res.pasos and res.pasos[0].titulo == "Dividir los polinomios"
    assert res.pasos[1].titulo == "Fracción simple"


def test_estrategia_es_la_regla_explicada(core):
    assert integral(core, "sin(x)").estrategia_principal == "Integral inmediata"
    assert integral(core, "x*exp(x)").estrategia_principal == "Integración por partes"
    assert integral(core, "exp(x)*sin(x)").estrategia_principal == "Integración por partes"
    assert integral(core, "tan(x)").estrategia_principal == "Reescribir la función"


def test_sin_regla_explicable_da_el_resultado_con_aviso(core):
    res = integral(core, "1/cos(x)")
    assert res.resultado is not None and res.pasos == []
    assert any("No se pudo explicar" in a for a in res.advertencias)


def test_explicacion_incorrecta_no_se_muestra(core, monkeypatch):
    monkeypatch.setattr(ExplicadorIntegral, "explicar", lambda self, regla, integrando=None, rol="": x ** 2)
    res = integral(core, "x^3")
    assert res.resultado == x**4 / 4 and res.pasos == []
    assert any("No se pudo explicar" in a for a in res.advertencias)


# ---------------- Integral definida ----------------

def definida(core, expresion, inferior, superior):
    return core.integral_definida(expresion, None, inferior, superior).texto.split("PASO A PASO:")[1]


def test_barrow_sustituye_cada_extremo(core):
    texto_pasos = definida(core, "x^2", "0", "1")
    assert "Regla: si f es continua en [a, b] y F es una primitiva de f, la integral de a a b es F(b) − F(a)." in texto_pasos
    assert "En este caso: la función es continua en [0, 1], así que a = 0, b = 1" in texto_pasos
    assert "Sustituimos x = 1 en F: F(1) = 1^3/3 = 1/3." in texto_pasos
    assert "Sustituimos x = 0 en F: F(0) = 0^3/3 = 0." in texto_pasos
    assert "Restamos: F(1) − F(0) = 1/3 − 0 = 1/3." in texto_pasos
    # La constante C no se suma en la definida
    assert "Constante de integración" not in texto_pasos


def test_barrow_con_valores_negativos(core):
    texto_pasos = definida(core, "1/x", "-2", "-1")
    assert "Sustituimos x = -1 en F: F(-1) = log(Abs(-1)) = 0." in texto_pasos
    assert "En el intervalo hay valores negativos: se usa log(Abs(u))" in texto_pasos


def test_impropia_explica_cada_extremo(core):
    texto_pasos = definida(core, "1/x^2", "-1", "1")
    assert "En este caso: el extremo impropio de este tramo es 0." in texto_pasos
    assert "Extremo impropio en 0: lim x→0- F(x) = oo." in texto_pasos
    assert "Sustituimos x = -1 en F: F(-1) = -1/(-1) = 1." in texto_pasos
    assert "Este tramo diverge." in texto_pasos
    assert "Regla: una integral impropia solo converge si convergen todos sus tramos." in texto_pasos
