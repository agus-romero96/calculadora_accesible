"""
Ecuaciones diferenciales (calculo/edo.py): cada solución cumple la ecuación (checkodesol de
SymPy) y el paso a paso sigue el estándar: planteamiento, tipo, separar, integrar con los pasos
de Integrar, despejar (con la constante renombrada), soluciones constantes, condición inicial y
comprobación.
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


def cumple(res):
    """Cada solución explícita cumple la ecuación (sin condiciones: con cualquier C)."""
    ecuacion = res.planteamiento[0]
    Y = ecuacion.atoms(sympy.core.function.AppliedUndef).pop()
    for s in res.valor:
        if s.lhs == y:
            ok, resto = sympy.checkodesol(ecuacion.doit(), sympy.Eq(Y, s.rhs.xreplace({y: Y})), solve_for_func=False)
            assert ok, (s, resto)


SEPARABLES = [
    ("y' = 2*x*y", "y = C*exp(x^2)"),
    ("dy/dx = (1 + y^2)/(1 + x^2)", "y = tan(atan(x) + C)"),
    ("x*y' = y", "y = C*x"),
    ("y' = y*(1 - y)", "y = C*exp(x)/(1 + C*exp(x)); y = 1"),
    ("y' = x^2", "y = x^3/3 + C"),
    ("y' = x/y", "y = sqrt(x^2 + C); y = -sqrt(x^2 + C)"),
    ("y' = exp(x - y)", "y = log(exp(x) + C)"),
    ("y' = y^2", "y = -1/(x + C); y = 0"),
    ("y' = 3*x^2*(1 + y^2)", "y = tan(x^3 + C)"),
    ("y' = k*y", "y = C*exp(k*x)"),
    ("y' = sqrt(y)", "y = (x/2 + C)^2; y = 0"),
    ("2*y' + y' = 6", "y = 2*x + C"),
]


@pytest.mark.parametrize("entrada, resultado", SEPARABLES, ids=[c[0] for c in SEPARABLES])
def test_separables(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert not res.es_error, res.texto
    assert res.operacion == "edo"
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}"
    assert "AVISO" not in res.texto and "NOTA" not in res.texto, res.texto
    cumple(res)
    nombres = titulos(res.texto)
    assert nombres[0] == "Planteamiento."
    assert nombres[-1] == "Comprobación."
    assert any(n.startswith("Tipo de ecuación: ") for n in nombres)
    for paso in pasos(res.texto):
        if paso.splitlines()[0].split(". ", 1)[1] in ("Separar las variables.", "Integrar los dos lados.",
                                                        "Despejar y.", "Comprobación."):
            assert "Regla: " in paso and "Queda: " in paso, paso


def test_separable_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y' = 2*x*y").texto
    assert "Método: ecuación separable" in texto
    assert "En este caso: y' = 2*x*y, con g(x) = 2*x y h(y) = y." in texto
    assert "dy/dx = 2*x*y" in texto and "Queda: (1/y) dy = 2*x dx" in texto
    # Las integrales, con el paso a paso de Integrar
    assert "Integral que da un logaritmo en ∫ 1/y dy." in texto
    assert "Regla de la potencia en ∫ x dx (f del factor constante)." in texto
    assert "Así, log(y) se escribe log(Abs(y))." in texto
    assert "Queda: log(Abs(y)) = x^2 + C" in texto
    # El despeje, con la constante renombrada
    assert "Aplicamos la exponencial a los dos lados (exp deshace log): Abs(y) = exp(x^2 + C)." in texto
    assert "Propiedad de las potencias: exp(x^2 + C) = exp(C)*exp(x^2)." in texto
    assert "±exp(C) es cualquier número distinto de 0. Lo llamamos C." in texto
    # La solución constante y = 0, que sale de la general con C = 0
    assert "y = 0: y' = 0 y g(x)*h(0) = (2*x)*(0) = 0." in texto
    assert "Con C = 0, la solución general da y = 0: está incluida." in texto
    assert "Derivamos: y' = 2*C*x*exp(x^2)." in texto
    assert "Los dos lados valen lo mismo: y = C*exp(x^2) cumple la ecuación." in texto


def test_valor_absoluto_y_constante(core):
    texto = core.ecuacion_diferencial("x*y' = y").texto
    assert "Dividimos los dos lados entre x: y' = y/x." in texto  # despejar y'
    assert "Así, log(y) se escribe log(Abs(y)); log(x) se escribe log(Abs(x))." in texto
    assert "En cada intervalo en que x no cambia de signo, Abs(x) es x o -x: el signo lo absorbe C." in texto


def test_constante_renombrada_y_dos_signos(core):
    texto = core.ecuacion_diferencial("y' = x/y").texto
    assert "Multiplicamos los dos lados por 2: y^2 = x^2 + 2*C." in texto
    assert "2*C es también una constante cualquiera: la seguimos llamando C." in texto
    assert "Sacamos la raíz cuadrada de los dos lados (deshace el cuadrado); hay dos signos: y = ±sqrt(x^2 + C)." \
        in texto


def test_logistica_fracciones_parciales(core):
    texto = core.ecuacion_diferencial("y' = y*(1 - y)").texto
    assert "Sustituir las raíces." in titulos(texto)  # fracciones parciales, con sus pasos
    assert "Propiedades de los logaritmos" in texto
    assert "-C es también una constante cualquiera: cambiando C por -C" in texto
    assert "Ningún valor de C da y = 1: se añade aparte (es una solución singular)." in texto


@pytest.mark.parametrize("entrada, resultado", [
    ("y' = 2*x*y, y(0) = 3", "y = 3*exp(x^2)"),
    ("y' = x/y, y(0) = 2", "y = sqrt(x^2 + 4)"),
    ("y' = x/y, y(0) = -2", "y = -sqrt(x^2 + 4)"),
    ("y' = y^2; y(0) = 1", "y = -1/(x - 1)"),
    ("dy/dx = x*(y - 1), y(0) = 3", "y = 2*exp(x^2/2) + 1"),
    ("y' - 2 = 0, y(1) = 5", "y = 2*x + 3"),
    ("y' = cos(y)^(-1), y(0) = 0", "y = asin(x)"),
    ("y' = y + x*y, y(0) = -1", "y = -exp(x*(x + 2)/2)"),
])
def test_condicion_inicial(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Condición inicial." in titulos(res.texto)
    ecuacion, condicion = res.planteamiento
    Y = condicion.lhs.func(x)
    (s,) = res.valor
    assert sympy.simplify(s.rhs.subs(x, condicion.lhs.args[0]) - condicion.rhs) == 0
    assert sympy.checkodesol(ecuacion.doit(), sympy.Eq(Y, s.rhs), solve_for_func=False)[0]


def test_condicion_elige_el_signo(core):
    texto = core.ecuacion_diferencial("y' = x/y, y(0) = -2").texto
    assert "Sustituimos x = 0, y = -2 en y = sqrt(x^2 + C): -2 = sqrt(0^2 + C)." in texto
    assert "Con C = 4, y = sqrt(x^2 + 4) no cumple la condición: se descarta." in texto
    assert "Con C = 4: y = -sqrt(x^2 + 4)." in texto


def test_reducible_a_separable(core):
    res = core.ecuacion_diferencial("y' = (x + y)^2")
    assert res.texto.splitlines()[0] == "RESULTADO: y = -x + tan(x + C)"
    cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: reducible a separable.", "Cambio de variable.", "Tipo de ecuación: separable.",
                 "Despejar u.", "Deshacer el cambio."):
        assert paso in nombres
    assert "Derivamos el cambio respecto a x: u' = y' + 1." in res.texto
    assert "Sustituimos y' en u': u' = 1 + u^2." in res.texto
    assert "Método: reducible a separable (cambio u = a*x + b*y + c)" in res.texto


@pytest.mark.parametrize("entrada", ["y' = (2*x + 3*y + 1)^2", "y' = x + y"])
def test_otras_reducibles(core, entrada):
    res = core.ecuacion_diferencial(entrada)
    assert "PASO A PASO" in res.texto and "AVISO" not in res.texto
    cumple(res)


def test_implicita_y_familia_de_constantes(core):
    res = core.ecuacion_diferencial("y' = sin(x)*cos(y)")
    assert not res.es_error
    assert "NOTA: la solución queda en forma implícita (sin despejar y)." in res.texto
    assert res.texto.splitlines()[0].endswith("y = pi*k + pi/2 (k: cualquier número entero)")
    assert "PASO A PASO" in res.texto


def test_otras_letras(core):
    res = core.ecuacion_diferencial("dx/dt = k*x")
    assert res.texto.splitlines()[0] == "RESULTADO: x = C*exp(k*t)"
    assert res.parametros == {"variable": "t", "dependiente": "x", "metodo": "ecuación separable"}


def test_sin_pasos_lo_resuelve_sympy(core):
    res = core.ecuacion_diferencial("y'' + y = 0")
    assert not res.es_error
    assert res.texto.splitlines()[0] == "RESULTADO: y = C1*sin(x) + C2*cos(x)"
    assert "NOTA: por ahora hay explicación paso a paso" in res.texto
    assert "PASO A PASO" not in res.texto


@pytest.mark.parametrize("entrada, mensaje", [
    ("x^2 + 3 = 1", "No hay ninguna derivada"),
    ("y' + z' = 1", "Hay derivadas de varias funciones (y, z)"),
    ("y' = x = 2", "un solo signo ="),
    ("y' = x, y''(0) = 1", "en una ecuación de orden 1 las condiciones llegan hasta la derivada 0"),
    ("y' = 2*x*y, z(0) = 1", "No se entiende la condición 'z(0) = 1'"),
    ("y' = x, y(0) = 1, y(1) = 2", "Hay dos condiciones para y"),
    ("= y'", "Falta uno de los dos lados"),
])
def test_errores(core, entrada, mensaje):
    res = core.ecuacion_diferencial(entrada)
    assert res.es_error and mensaje in res.texto, res.texto


def test_exportar(core):
    res = core.ecuacion_diferencial("y' = 2*x*y, y(0) = 3")
    assert exportar.resultado_corto(res) == "y = 3*exp(x^2)"
    assert exportar.latex(res) == (r"\begin{cases} \frac{d}{d x} y{\left(x \right)} = 2 x y{\left(x \right)} \\ "
                                   r"y{\left(0 \right)} = 3 \end{cases}\quad\Longrightarrow\quad y = 3 e^{x^{2}}")
    assert "Método: ecuación separable" in exportar.resumen(res)
    import xml.dom.minidom
    xml.dom.minidom.parseString(exportar.mathml(res))
    general = core.ecuacion_diferencial("y' = x^2")
    assert exportar.resultado_corto(general) == "y = x^3/3 + C"


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.ecuacion_diferencial("y' = 2*x*y").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert texto.splitlines()[0] == "RESULT: y = C*exp(x^2)"
    assert "Separate the variables" in texto and "Method: separable equation" in texto
