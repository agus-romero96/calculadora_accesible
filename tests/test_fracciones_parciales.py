"""
Integración por fracciones parciales (calculo/fracciones_parciales.py): la primitiva es
correcta y coincide con la de SymPy (salvo una constante), y el paso a paso sigue el método
de clase: grados (y división), factorizar el denominador, planteamiento con coeficientes
indeterminados, multiplicar por el denominador común, sustituir raíces e igualar
coeficientes, e integrar cada fracción simple.
"""
import pytest
import sympy

from calculo import fracciones_parciales
from parser_matematico import ParserMatematico

x = ParserMatematico.simbolo("x")


def titulos(res):
    return [p.titulo for p in res.pasos]


def textos(res):
    return "\n".join(l for p in res.pasos for l in (p.titulo, p.regla, p.partes, *p.calculo, p.queda))


CASOS = [
    "1/(x^2-1)",                 # lineales distintos
    "(x^2+2*x-1)/(x^3-x)",       # tres lineales (la primitiva de SymPy junta los logaritmos)
    "1/((x-1)^2*(x+1))",         # lineal repetido
    "1/((x^2+1)*(x-1))",         # lineal y cuadrático irreducible
    "1/(x*(x^2+1))",
    "(x^3+1)/(x^2-1)",           # simplificar y dividir antes
    "x^2/(x+1)",                 # dividir; queda una fracción simple
    "(2*x^3 + x)/(x^2+1)",       # dividir; el resto sobre un cuadrático
    "(3*x+5)/(x^2+2*x+5)",       # un solo cuadrático: logaritmo y arcotangente
    "1/(2*x^2+2*x+5)",
    "(5*x - 3)/(x^2 - 2*x - 3)",
    "1/(x^3 - x^2)",
]


@pytest.mark.parametrize("funcion", CASOS)
def test_primitiva_correcta_y_explicada(core, funcion):
    res = core.calculo.CalcularIntegral(funcion)
    assert res.es_exitoso
    f = ParserMatematico().parsear(funcion).doit()
    assert sympy.simplify(sympy.diff(res.resultado, x) - f) == 0
    assert res.estrategia_principal == "Fracciones parciales", res.advertencias
    assert res.pasos and not res.advertencias
    for paso in res.pasos:
        assert paso.regla or paso.titulo in ("Constante de integración",), paso


def test_metodo_completo(core):
    res = core.calculo.CalcularIntegral("1/((x-1)^2*(x+1))")
    esperados = ["Comparar los grados", "Tipos de factores del denominador",
                 "Planteamiento con coeficientes indeterminados", "Multiplicar por el denominador común",
                 "Sustituir las raíces", "Igualar coeficientes", "Descomposición en fracciones simples",
                 "Integrar cada fracción simple", "Constante de integración"]
    propios = [t for t in titulos(res) if t in esperados]
    assert propios == esperados
    # Entre medias, la factorización del denominador con los pasos de Factorizar
    assert any(t.startswith("Factor común por grupos") for t in titulos(res))
    texto = textos(res)
    assert "(x - 1)^2: lineal repetido 2 veces" in texto
    assert "1/((x - 1)^2*(x + 1)) = A/(x + 1) + B/(x - 1) + C/(x - 1)^2" in texto
    assert "x = 1 (raíz de x - 1): todos los términos tienen el factor x - 1 y se anulan, salvo el de C." in texto
    assert "Así 2*C = 1, y C = 1/2." in texto
    assert "Con B + 1/4 = 0: Pasamos 1/4 a la derecha" in texto
    assert "regla de la potencia, ∫ u^n du = u^(n+1)/(n+1) con n = -2." in texto


def test_factores_distintos_por_raices(core):
    texto = textos(core.calculo.CalcularIntegral("1/(x^2-1)"))
    assert "Diferencia de cuadrados en x^2 - 1" in texto  # el denominador, con los pasos de Factorizar
    assert "Derecha: A*(1 + 1) = 2*A. Así 2*A = 1, y A = 1/2." in texto
    assert "Así (-2)*B = 1, y B = 1/(-2) = -1/2." in texto
    assert "1/(x^2 - 1) = (1/2)/(x - 1) + (-1/2)/(x + 1)." in texto


def test_cuadratico_irreducible_da_logaritmo_y_arcotangente(core):
    texto = textos(core.calculo.CalcularIntegral("1/((x^2+1)*(x-1))"))
    assert "x^2 + 1: cuadrático irreducible (su discriminante es 0^2 - 4*1*1 = -4, negativo" in texto
    assert "Igualar coeficientes" in texto
    assert "el numerador es la derivada del denominador (cambio de variable u = x^2 + 1)" in texto
    assert "∫ 1/(u^2 + k^2) du = (1/k)*atan(u/k), con u = x y k = sqrt(1) = 1." in texto


def test_completar_el_cuadrado(core):
    texto = textos(core.calculo.CalcularIntegral("(3*x+5)/(x^2+2*x+5)"))
    assert "escribimos 3*x + 5 = (3/2)*(2*x + 2) + 2." in texto
    assert "Completamos el cuadrado: x^2 + 2*x + 5 = (x + 1)^2 + 4 (porque 5 - 1 = 4)." in texto
    texto = textos(core.calculo.CalcularIntegral("1/(2*x^2+2*x+5)"))
    assert "El número que multiplica: (1/2)*(1/(3/2)) = 1/3" in texto


def test_simplificar_y_dividir(core):
    texto = textos(core.calculo.CalcularIntegral("(x^3+1)/(x^2-1)"))
    assert "Factorizamos: x^3 + 1 = (x + 1)*(x^2 - x + 1) y x^2 - 1 = (x - 1)*(x + 1)." in texto
    assert "El factor común x + 1 se cancela." in texto
    assert "Dividimos x^2 entre x: x. Multiplicamos x*(x - 1) = x^2 - x. Restamos: (x^2 - x + 1) - (x^2 - x) = 1." in texto
    assert "Comprobación: (x - 1)*x + 1 = x^2 - x + 1." in texto


def test_logaritmos_que_se_juntan(core):
    res = core.calculo.CalcularIntegral("(x^2+2*x-1)/(x^3-x)")
    texto = textos(res)
    assert "Propiedades de los logaritmos: log(a) + log(b) = log(a*b)" in texto
    assert titulos(res)[-2] == "Simplificación"


@pytest.mark.parametrize("funcion", ["(2*x+3)/(x^2+3*x+2)", "1/(x^2+4)", "1/(x-1)^2", "x/(x^2+4)"])
def test_casos_mas_directos_no_usan_fracciones_parciales(funcion):
    """Si el numerador es la derivada del denominador, o la integral es de la tabla, otro método es más directo."""
    f = ParserMatematico().parsear(funcion).doit()
    assert not fracciones_parciales.aplica(f, x)


def test_raices_irracionales_quedan_para_sympy(core):
    res = core.calculo.CalcularIntegral("1/(x^2-2)")
    assert res.es_exitoso and res.estrategia_principal != "Fracciones parciales"


def test_integral_definida(core):
    res = core.integral_definida("1/(x^2-1)", None, "2", "3")
    assert not res.es_error
    assert "Sustituir las raíces" in res.texto and "Regla de Barrow" in res.texto


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.integrar("1/(x^2-1)").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert "Setup with undetermined coefficients" in texto and "Substitute the roots" in texto
