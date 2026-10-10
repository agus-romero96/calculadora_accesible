"""
Explicación de las derivadas (calculo/derivadas.py): cada regla se enuncia, se
identifican sus partes, se muestran la sustitución y las cuentas, y lo que queda;
y la explicación llega siempre al mismo resultado que SymPy.
"""
import pytest
import sympy

from calculo.derivadas import ExplicadorDerivada, texto
from calculo.pasos import PasoCalculo, texto_paso

x = sympy.Symbol("x", real=True)

EXPRESIONES = [
    "x", "5", "pi", "x^3", "-x^2", "3*x^4-2*x^2+5*x-7", "x^2*sin(x)", "sin(x)/x", "sin(x^2)", "x^x", "2^x",
    "exp(x)", "exp(-x)", "e^(2*x)", "x*exp(x)", "ln(x)", "ln(x^2+1)", "sqrt(x)", "sqrt(x^2+1)", "1/x", "1/x^2",
    "3/x", "1/(x^2+1)", "(x^2+1)^3", "(2*x+1)^5", "tan(x)", "cos(3*x)", "sin(x)*cos(x)", "x*sin(x)*cos(x)",
    "asin(x)", "atan(x^2)", "sinh(x)", "abs(x)", "sin(x)^2", "sin(cos(x))", "exp(sin(x))", "x^2*exp(-x)/(x+1)",
    "(x+1)/(x-1)", "x/(x^2+1)^2", "x^(1/3)", "5*sqrt(x)", "x^sin(x)", "a*x^2+b*x+c", "k*sin(x)", "pi*x^2",
    "log(x)/x", "x^3*ln(x)", "sec(x)", "x^n", "2^(x^2)", "sqrt(x)*ln(x)", "3*x^2*sin(x)", "log(x,10)",
]


def pasos_de(core, expresion):
    res = core.calculo.CalcularDerivada(expresion)
    assert res.es_exitoso, res.mensaje_error
    return res, res.pasos


@pytest.mark.parametrize("expresion", EXPRESIONES)
def test_toda_derivada_se_explica_hasta_el_resultado(core, expresion):
    res, pasos = pasos_de(core, expresion)
    assert pasos, res.advertencias
    assert not any("No se pudo explicar" in a for a in res.advertencias)
    # El último paso deja exactamente el resultado mostrado
    assert pasos[-1].queda == texto(res.resultado)


@pytest.mark.parametrize("expresion", EXPRESIONES)
def test_cada_paso_tiene_la_estructura_completa(core, expresion):
    """Planteamiento: regla y partes; sustitución: cuentas y lo que queda; regla simple: las cuatro."""
    _, pasos = pasos_de(core, expresion)
    for paso in pasos:
        if paso.titulo == "Simplificación":
            assert paso.regla and paso.calculo and paso.queda
        elif paso.titulo.endswith(": sustitución"):
            assert paso.calculo and paso.queda and not paso.regla
        else:
            assert paso.regla and paso.partes, paso
            if not paso.queda:  # planteamiento de una regla compuesta: le sigue su sustitución
                assert any(p.titulo == f"{paso.titulo}: sustitución" for p in pasos), paso


def lineas(core, expresion):
    return core.Derivar(expresion).split("PASO A PASO:")[1]


def test_regla_de_la_potencia_desglosada(core):
    texto_pasos = lineas(core, "x^3")
    assert "Regla: la derivada de x^n es n*x^(n-1)" in texto_pasos
    assert "En este caso: la base es x y el exponente n es 3." in texto_pasos
    assert "Sustituimos n = 3: 3*x^(3 - 1)." in texto_pasos
    assert "Restamos 1 al exponente: 3 - 1 = 2." in texto_pasos
    assert "Queda: 3*x^2" in texto_pasos
    # En ese orden: regla, partes, sustitución, cuenta, resultado
    orden = [texto_pasos.index(s) for s in ("Regla:", "En este caso:", "Sustituimos", "Restamos", "Queda:")]
    assert orden == sorted(orden)


def test_coeficiente_y_cuentas(core):
    texto_pasos = lineas(core, "3*x^4-2*x^2+5*x-7")
    assert "Multiplicamos los números: 3 * 4 = 12." in texto_pasos
    assert "Multiplicamos los números: (-2) * 2 = -4." in texto_pasos
    # 5*x: el exponente implícito y la potencia que desaparece
    assert "el exponente n es 1, porque x es lo mismo que x^1." in texto_pasos
    assert "Restamos 1 al exponente: 1 - 1 = 0." in texto_pasos
    assert "Cualquier base elevada a 0 vale 1" in texto_pasos
    # La constante, sin "-1*7" (forma sin evaluar del parser)
    assert "Derivada de una constante en -7 (término 4 de la suma)" in texto_pasos
    assert "Juntamos las derivadas de los términos: 12*x^3 - 4*x + 5 + 0." in texto_pasos


def test_raiz_y_exponente_negativo(core):
    texto_pasos = lineas(core, "sqrt(x^2+1)")
    assert "porque sqrt(x^2 + 1) es lo mismo que (x^2 + 1)^(1/2)" in texto_pasos
    assert "Restamos 1 al exponente: 1/2 - 1 = -1/2." in texto_pasos
    assert "Un exponente negativo pasa la potencia al denominador: (x^2 + 1)^(-1/2) = 1/(x^2 + 1)^(1/2)." in texto_pasos
    assert "Elevar a 1/2 es sacar la raíz cuadrada: (x^2 + 1)^(1/2) = sqrt(x^2 + 1)." in texto_pasos
    assert "Multiplicamos los números: (1/2) * 2 = 1." in texto_pasos


def test_regla_de_la_cadena(core):
    texto_pasos = lineas(core, "sin(x^2)")
    assert "Regla: la derivada de f(u) es f'(u)*u'" in texto_pasos
    assert "la derivada de sin(u) es cos(u)" in texto_pasos
    assert "la función de fuera es sin y la de dentro es u = x^2." in texto_pasos
    assert "Regla de la potencia en x^2 (u, la función de dentro)" in texto_pasos
    assert "Multiplicamos por u' = 2*x: cos(x^2)*(2*x)." in texto_pasos


def test_producto_y_cociente_nombran_sus_partes(core):
    texto_pasos = lineas(core, "x*exp(x)/(x+1)")
    # Las partes anidadas dicen a qué regla pertenecen: no hay dos "u" sin contexto
    assert "Regla del producto en x*exp(x) (u del cociente)" in texto_pasos
    assert "Derivada de la variable en x (u del producto)" in texto_pasos
    assert "Regla de la suma en x + 1 (v del cociente)" in texto_pasos
    assert "Sustituimos u' = x*exp(x) + exp(x) y v' = 1 en (u'*v - u*v')/v^2" in texto_pasos


def test_simplificacion_final_explicita(core):
    res, pasos = pasos_de(core, "x^2*sin(x)")
    assert pasos[-1].titulo == "Simplificación"
    assert pasos[-1].calculo == ("x^2*cos(x) + 2*x*sin(x) = x*(x*cos(x) + 2*sin(x))",)


def test_estrategias(core):
    res, _ = pasos_de(core, "3*x^2*sin(x)")
    assert res.estrategia_principal == "Multiplicación por Constante"
    assert res.estrategias_secundarias == ["Regla del Producto", "Potencia"]
    assert core.calculo.CalcularDerivada("1/x^2").estrategia_principal == "Potencia Negativa"
    assert core.calculo.CalcularDerivada("exp(x^2)").estrategias_secundarias == ["Regla de la Cadena", "Potencia"]


def test_explicacion_que_no_coincide_no_se_muestra(core, monkeypatch):
    """Si las reglas llegan a otro resultado (un error), mejor el de SymPy sin pasos que pasos falsos."""
    monkeypatch.setattr(ExplicadorDerivada, "derivar", lambda self, expr, rol="": expr)
    res = core.calculo.CalcularDerivada("x^3")
    assert res.es_exitoso and res.resultado == 3 * x**2
    assert res.pasos == []
    assert any("No se pudo explicar" in a for a in res.advertencias)


def test_derivada_enesima_explica_cada_derivada(core):
    res = core.calculo.DerivadaEnecima("x^5", "x", 3)
    titulos = [p.titulo for p in res.pasos]
    assert titulos == ["Derivada de orden 3", "Derivada 1: f'(x)", "Regla de la potencia en x^5", "Derivada 2: f''(x)",
                       "Regla de la potencia con coeficiente en 5*x^4", "Derivada 3: f'''(x)",
                       "Regla de la potencia con coeficiente en 20*x^3"]
    assert res.pasos[0].partes == "f(x) = x^5; hay que derivar 3 veces: f'(x), f''(x), f'''(x)."
    assert res.pasos[3].partes == "derivamos f'(x) = 5*x^4."
    assert res.pasos[-1].queda == "60*x^2"


def test_derivada_enesima_larga_sigue_sin_pasos(core):
    res = core.calculo.DerivadaEnecima("exp(x)*sin(x)", "x", 12)
    assert res.es_exitoso and sympy.simplify(res.resultado - sympy.diff(sympy.exp(x) * sympy.sin(x), x, 12)) == 0
    assert any("se muestra solo el resultado" in a for a in res.advertencias)
    # Sin el detalle de las reglas, cada derivada sigue diciendo de cuál sale y cuánto vale
    assert res.pasos[-1].titulo == "Derivada 12: f^(12)(x)"
    assert res.pasos[-1].regla == "f^(12)(x) es la derivada de f^(11)(x)."
    assert res.pasos[-1].queda == "f^(12)(x) = -64*exp(x)*sin(x)"


def test_terminos_semejantes_no_se_juntan_sin_avisar(core):
    pasos = core.DerivadaEnecima("x^3*sin(x)", "x", 2)
    assert "Agrupamos términos semejantes: 3*x^2*cos(x) + 3*x^2*cos(x) = 6*x^2*cos(x)." in pasos


def test_texto_de_un_paso():
    paso = PasoCalculo("Regla de la potencia en x^3", regla="r", partes="p", calculo=("c1", "c2"), queda="q")
    assert texto_paso(2, paso) == "2. Regla de la potencia en x^3.\n   Regla: r\n   En este caso: p\n   c1\n   c2\n   Queda: q"
    # Pasos de integrales: descripción y fórmula, como antes
    assert texto_paso(1, PasoCalculo("Linealidad", "Separamos.", "a + b")) == "1. Linealidad. Separamos.\n   [Fórmula]: a + b"
