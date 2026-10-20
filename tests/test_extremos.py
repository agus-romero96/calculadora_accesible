"""
Puntos críticos, extremos locales e intervalos de crecimiento (calculo/extremos.py): el
resultado coincide con SymPy y el paso a paso sigue el estándar (Regla, En este caso,
cuentas, Queda): dominio, derivada, f'(x) = 0 resuelta, tabla de signos de f', criterio de
la primera derivada con f(x0), y de la segunda derivada.
"""
import re

import pytest
import sympy
from sympy import S

import exportar
from parser_matematico import ParserMatematico

x = ParserMatematico.simbolo("x")
oo = sympy.oo


def pasos(salida):
    texto = salida.split("PASO A PASO:")[1]
    return re.split(r"\n(?=\d+\. )", texto.strip())


def titulos(salida):
    return [p.splitlines()[0].split(". ", 1)[1] for p in pasos(salida)]


# (función, críticos, máximos [(x, f)], mínimos, crece, decrece)
CASOS = [
    ("x^3 - 3*x", [-1, 1], [(-1, 2)], [(1, -2)],
     sympy.Union(sympy.Interval.open(-oo, -1), sympy.Interval.open(1, oo)), sympy.Interval.open(-1, 1)),
    ("x^2 - 4*x + 1", [2], [], [(2, -3)], sympy.Interval.open(2, oo), sympy.Interval.open(-oo, 2)),
    ("-x^2 + 6*x", [3], [(3, 9)], [], sympy.Interval.open(-oo, 3), sympy.Interval.open(3, oo)),
    ("x^4 - 2*x^2", [-1, 0, 1], [(0, 0)], [(-1, -1), (1, -1)],
     sympy.Union(sympy.Interval.open(-1, 0), sympy.Interval.open(1, oo)),
     sympy.Union(sympy.Interval.open(-oo, -1), sympy.Interval.open(0, 1))),
    ("x^3", [0], [], [], S.Reals, S.EmptySet),
    ("x^3 + x", [], [], [], S.Reals, S.EmptySet),
    ("x^4", [0], [], [(0, 0)], sympy.Interval.open(0, oo), sympy.Interval.open(-oo, 0)),
    ("(x^2+1)/x", [-1, 1], [(-1, -2)], [(1, 2)],
     sympy.Union(sympy.Interval.open(-oo, -1), sympy.Interval.open(1, oo)),
     sympy.Union(sympy.Interval.open(-1, 0), sympy.Interval.open(0, 1))),
    ("x^2/(x-1)", [0, 2], [(0, 0)], [(2, 4)],
     sympy.Union(sympy.Interval.open(-oo, 0), sympy.Interval.open(2, oo)),
     sympy.Union(sympy.Interval.open(0, 1), sympy.Interval.open(1, 2))),
    ("x*exp(x)", [-1], [], [(-1, -sympy.exp(-1))], sympy.Interval.open(-1, oo), sympy.Interval.open(-oo, -1)),
    ("2*x^3 - 3*x^2 - 12*x", [-1, 2], [(-1, 7)], [(2, -20)],
     sympy.Union(sympy.Interval.open(-oo, -1), sympy.Interval.open(2, oo)), sympy.Interval.open(-1, 2)),
]


@pytest.mark.parametrize("funcion, criticos, maximos, minimos, crece, decrece", CASOS, ids=[c[0] for c in CASOS])
def test_resultado_y_estructura(core, funcion, criticos, maximos, minimos, crece, decrece):
    res = core.extremos(funcion)
    assert not res.es_error, res.texto
    assert res.operacion == "extremos"
    v = res.valor
    assert sorted(v["criticos"], key=float) == criticos
    assert v["maximos"] == maximos and v["minimos"] == minimos
    assert v["crece"] == crece and v["decrece"] == decrece
    # La verdad de SymPy: f' > 0 exactamente donde crece (dentro del dominio)
    f = ParserMatematico().parsear(funcion).doit()
    dominio = sympy.calculus.util.continuous_domain(f, x, S.Reals)
    positiva = sympy.solveset(sympy.diff(f, x) > 0, x, dominio)
    assert sympy.Complement(positiva, crece) == S.EmptySet
    assert res.texto.startswith("RESULTADO:\nPuntos críticos: ")
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    nombres = titulos(res.texto)
    assert nombres[0] == "Dominio." and nombres[1] == "Derivar la función."
    assert "Intervalos de crecimiento." in nombres
    if criticos:
        assert "Criterio de la primera derivada." in nombres
    propios = {"Dominio.", "Derivar la función.", "Puntos críticos.", "Intervalos de crecimiento.",
               "Criterio de la primera derivada.", "Segunda derivada.", "Criterio de la segunda derivada."}
    for paso in pasos(res.texto):
        if paso.splitlines()[0].split(". ", 1)[1] in propios:
            assert "Regla: " in paso and "Queda: " in paso, paso


def test_paso_a_paso_completo(core):
    texto = core.extremos("x^3 - 3*x").texto
    # f'(x) = 0, sin saltarse el factor 3
    assert "Queda: 3*x^2 - 3 = 0" in texto
    assert "Dividir entre el coeficiente principal" in texto
    # Tabla de signos, factor a factor
    assert "Factorizamos con las raíces: f'(x) = 3*(x - 1)*(x + 1)." in texto
    assert "Intervalo (-1, 1): probamos con x = 0." in texto
    assert "El número 3: positivo." in texto
    assert "x - 1 = 0 - 1 = -1: negativo." in texto
    assert "Signo de f'(x): (+)*(+)*(-) = -. La función es decreciente en (-1, 1)." in texto
    # Primera derivada y f(x0) con sus cuentas
    assert "En x = -1, f' pasa de + a -: la función sube y luego baja, así que es un máximo local." in texto
    assert "(-1)^3 = (-1)*(-1)*(-1) = -1. Queda -1 - 3*(-1)." in texto
    assert "f(-1) = 2." in texto
    # Segunda derivada
    assert "Queda: f''(x) = 6*x" in texto
    assert "f''(-1) = -6, negativo: máximo local, como dijo la primera derivada." in texto


def test_cociente_dominio_y_sin_segunda_derivada(core):
    texto = core.extremos("x^2/(x-1)").texto
    assert "x - 1 = 0: Pasamos -1 a la derecha" in texto
    assert "f'(x) es una fracción: vale 0 cuando su numerador vale 0" in texto
    assert ("Los puntos críticos y los que no están en el dominio (0, 1, 2) dividen la recta en 4 intervalos: "
            "(-∞, 0), (0, 1), (1, 2), (2, ∞).") in texto
    assert "(x - 1)^2 = ((1/2) - 1)^2 = 1/4: positivo." in texto
    assert "En un cociente, la segunda derivada exige otra regla del cociente" in texto
    assert "Segunda derivada." not in titulos(texto)
    assert "Dominio: (-∞, 1) ∪ (1, ∞)" in texto


def test_exponencial_nunca_vale_cero(core):
    texto = core.extremos("x*exp(x)").texto
    assert "exp(x) nunca vale 0 (una exponencial siempre es positiva): no da puntos críticos." in texto
    assert "exp(x): siempre positivo." in texto
    assert "Mínimo local en x = -1: f(-1) = -exp(-1) (aproximadamente -0.367879)" in texto


def test_grado_tres_se_factoriza_antes(core):
    texto = core.extremos("x^4 - 2*x^2").texto
    assert "Sacar factor común." in titulos(texto)
    assert "Aplicar el producto nulo." in titulos(texto)


def test_potencia_igual_a_cero(core):
    texto = core.extremos("x^4").texto
    assert "Potencia igual a 0." in titulos(texto)
    assert "f''(0) = 0: el criterio no decide; vale lo que dice la primera derivada." in texto


def test_punto_critico_que_no_es_extremo(core):
    texto = core.extremos("x^3").texto
    assert "Sin extremos locales" in texto
    assert ("En x = 0, f' no cambia de signo (+ a los dos lados): no es un extremo, y la función sigue creciendo a "
            "través de ese punto.") in texto
    assert "Creciente en (-∞, ∞)" in texto and "Decreciente en ningún intervalo" in texto


def test_sin_puntos_criticos(core):
    texto = core.extremos("x^3 + x").texto
    assert "Puntos críticos: ninguno" in texto
    assert "Un cuadrado nunca es negativo" in texto
    assert "No hay puntos críticos ni puntos fuera del dominio" in texto


def test_sin_explicacion_lo_resuelve_sympy(core):
    res = core.extremos("x*log(x)")
    assert not res.es_error
    assert "Mínimo local en x = exp(-1)" in res.texto
    assert "NOTA: hay explicación paso a paso para cocientes de polinomios" in res.texto
    assert "PASO A PASO" not in res.texto


def test_derivada_infinita_en_un_extremo_del_dominio_no_importa(core):
    res = core.extremos("sqrt(x)")
    assert not res.es_error and "Creciente en (0, ∞)" in res.texto


@pytest.mark.parametrize("funcion, mensaje", [
    ("5", "La función es constante"),
    ("sin(x)", "infinitos puntos"),
])
def test_errores(core, funcion, mensaje):
    res = core.extremos(funcion)
    assert res.es_error and mensaje in res.texto


def test_con_un_parametro_lo_dice(core):
    res = core.extremos("a*x^2 - 2*x", "x")
    assert res.es_error and "La función tiene otras letras (a)" in res.texto


def test_exportar(core):
    res = core.extremos("x^3 - 3*x")
    assert exportar.resultado_corto(res) == ("Puntos críticos: x = -1, x = 1; Máximo local en x = -1: f(-1) = 2; "
                                             "Mínimo local en x = 1: f(1) = -2; Creciente en (-∞, -1) ∪ (1, ∞); "
                                             "Decreciente en (-1, 1)")
    latex = exportar.latex(res)
    assert r"\left(-\infty, -1\right) \cup \left(1, \infty\right)" in latex and "∞" not in latex
    assert exportar.resumen(res).splitlines()[:2] == ["RESULTADO:", "Puntos críticos: x = -1, x = 1"]
    import xml.dom.minidom
    xml.dom.minidom.parseString(exportar.mathml(res))


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.extremos("x^2 - 4*x + 1").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert texto.splitlines()[:3] == ["RESULT:", "Critical points: x = 2", "Local minimum at x = 2: f(2) = -3"]
    assert "First derivative test" in texto and "Intervals of increase and decrease" in texto
