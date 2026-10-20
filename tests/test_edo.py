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
            # log(Abs(u)) tiene la misma derivada que log(u); con el valor absoluto, checkodesol se atasca
            valor = s.rhs.replace(lambda e: isinstance(e, sympy.log) and isinstance(e.args[0], sympy.Abs),
                                  lambda e: sympy.log(e.args[0].args[0]))
            ok, resto = sympy.checkodesol(ecuacion.doit(), sympy.Eq(Y, valor.xreplace({y: Y})), solve_for_func=False)
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


@pytest.mark.parametrize("entrada", ["y' = (2*x + 3*y + 1)^2", "y' = sin(x - y)"])
def test_otras_reducibles(core, entrada):
    res = core.ecuacion_diferencial(entrada)
    assert "PASO A PASO" in res.texto and "AVISO" not in res.texto
    cumple(res)


LINEALES = [
    ("y' + y = x", "y = x - 1 + C*exp(-x)"),
    ("x*y' + 2*y = x^2", "y = x^2/4 + C/x^2"),
    ("y' = x + y", "y = -x - 1 + C*exp(x)"),
    ("y' + y*tan(x) = cos(x)", "y = (x + C)*cos(x)"),
    ("y' + y = sin(x)", "y = sin(x)/2 - cos(x)/2 + C*exp(-x)"),
    ("x*y' - y = x^3", "y = x^3/2 + C*x"),
    ("y' - 2*y = exp(3*x), y(0) = 1", "y = exp(3*x)"),
    ("y' + y/x = 3*x, y(1) = 2", "y = (x^3 + 1)/x"),
]


@pytest.mark.parametrize("entrada, resultado", LINEALES, ids=[c[0] for c in LINEALES])
def test_lineales(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: ecuación lineal de primer orden (factor integrante)" in res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    if "," not in entrada:
        cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: lineal de primer orden.", "Factor integrante.",
                 "Multiplicar por el factor integrante.", "Integrar los dos lados.", "Despejar y.", "Comprobación."):
        assert paso in nombres
    assert "Despejar y'." not in nombres  # se parte de la ecuación escrita, no de y' despejada
    for paso in pasos(res.texto):
        if paso.splitlines()[0].split(". ", 1)[1] in ("Factor integrante.", "Multiplicar por el factor integrante."):
            assert "Regla: " in paso and "Queda: " in paso, paso


def test_lineal_paso_a_paso(core):
    texto = core.ecuacion_diferencial("x*y' + 2*y = x^2").texto
    assert "En este caso: y' + (2/x)*y = x, con P(x) = 2/x y Q(x) = x." in texto
    assert "Dividimos los dos lados entre x, lo que multiplica a y': y' + (2/x)*y = x." in texto
    assert "Integral que da un logaritmo en ∫ 1/x dx (f del factor constante)." in texto  # los pasos de ∫ P
    assert "m(x) = exp(2*log(Abs(x))) = x^2." in texto
    assert "Multiplicamos los dos lados por x^2: x^2*y' + 2*x*y = x^3." in texto
    assert "La derivada de m es 2*x, que es m*P = x^2*(2/x)" in texto
    assert "Queda: (x^2*y)' = x^3" in texto
    assert "Queda: x^2*y = x^4/4 + C" in texto
    assert "Dividimos los dos lados entre x^2: y = x^2/4 + C/x^2." in texto
    assert "Lado izquierdo: x*(x/2 - 2*C/x^3) + 2*(x^2/4 + C/x^2) = x^2." in texto


def test_lineal_sin_valor_absoluto_y_fraccion(core):
    texto = core.ecuacion_diferencial("y' + y*tan(x) = cos(x)").texto
    assert "Tomamos m(x) = 1/cos(x)." in texto
    assert "Multiplicamos los dos lados por 1/cos(x): y'/cos(x) + y*tan(x)/cos(x) = 1." in texto
    assert "Queda: (y/cos(x))' = 1" in texto
    assert "Multiplicamos los dos lados por cos(x): y = x*cos(x) + C*cos(x)." in texto


def test_lineal_agrupa_y_signos(core):
    texto = core.ecuacion_diferencial("y' = x + y").texto
    assert "Dejamos a la izquierda los términos con y' y con y, y a la derecha los demás: y' - y = x." in texto
    assert "Multiplicamos los dos lados por exp(-x): exp(-x)*y' - exp(-x)*y = x*exp(-x)." in texto
    # La sustitución de la comprobación conserva los signos
    assert "Lado derecho: x + (-x - 1 + C*exp(x)) = -1 + C*exp(x)." in texto


HOMOGENEAS = [
    ("y' = (x^2 + y^2)/(x*y)", "y = x*sqrt(2*log(Abs(x)) + C); y = -x*sqrt(2*log(Abs(x)) + C)"),
    ("x*y' = y + x*exp(y/x)", "y = -x*log(-log(Abs(x)) + C)"),
    ("y' = y/x + tan(y/x)", "y = x*asin(C*x); y = pi*k*x (k: cualquier número entero)"),
    ("x^2*y' = x^2 + y^2 + x*y", "y = x*tan(log(Abs(x)) + C)"),
    ("y' = (x^2 + y^2)/(x*y), y(1) = 2", "y = x*sqrt(2*log(Abs(x)) + 4)"),
]


@pytest.mark.parametrize("entrada, resultado", HOMOGENEAS, ids=[c[0] for c in HOMOGENEAS])
def test_homogeneas(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: ecuación homogénea (cambio y = u*x)" in res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    if "," not in entrada:
        cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: homogénea.", "Cambio de variable.", "Tipo de ecuación: separable.",
                 "Deshacer el cambio.", "Comprobación."):
        assert paso in nombres


def test_homogenea_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y' = (x^2 + y^2)/(x*y)").texto
    assert ("Cambiamos x por t*x e y por t*y: f(t*x, t*y) = ((t*x)^2 + (t*y)^2)/((t*x)*(t*y)) = "
            "(x^2 + y^2)/(x*y).") in texto
    assert "Con y = u*x (es decir, u = y/x): f = (x^2 + (u*x)^2)/(x*(u*x)) = u + 1/u." in texto
    assert "y = u*x; derivamos con la regla del producto (u también depende de x): y' = u + x*u'." in texto
    assert "Pasamos u a la derecha cambiando de signo: x*u' = u + 1/u - u = 1/u." in texto
    assert "Dividimos los dos lados entre x: u' = 1/(u*x)." in texto
    assert "Multiplicamos los dos lados por x: y = x*sqrt(2*log(Abs(x)) + C)." in texto
    # La comprobación, sin sign(x) ni trozos
    assert "sign(" not in texto and "Piecewise" not in texto


def test_homogenea_implicita_junta_logaritmos(core):
    res = core.ecuacion_diferencial("y' = (x + y)/(x - y)")
    assert res.texto.splitlines()[0] == "RESULTADO: log(sqrt(x^2 + y^2)) - atan(y/x) = C"
    assert "NOTA: la solución queda en forma implícita (sin despejar y)." in res.texto
    assert "Pasamos -log(Abs(x)) a la izquierda y juntamos los logaritmos" in res.texto


EXACTAS = [
    ("(2*x*y + 3) dx + (x^2 - 1) dy = 0", "y = (-3*x + C)/(x^2 - 1)"),
    ("(3*x^2 + y*cos(x)) dx + (sin(x) - 4*y^3) dy = 0", "x^3 - y^4 + y*sin(x) = C"),
    ("2*x*y + (x^2 + 2*y)*y' = 0", "x^2*y + y^2 = C"),
    ("(exp(x) + y) dx + (x + exp(y)) dy = 0", "x*y + exp(x) + exp(y) = C"),
    ("(2*x*y + 3) dx + (x^2 - 1) dy = 0, y(0) = 2", "y = (-3*x - 2)/(x^2 - 1)"),
    # Con factor integrante que solo depende de x o de y
    ("(x*y - 1) dx + (x^2 - x*y) dy = 0", "x*y - y^2/2 - log(Abs(x)) = C"),
    ("y dx - x dy = 0", "y = C*x"),
    ("y dx + (2*x - y*exp(y)) dy = 0", "x*y^2 + (-y^2 + 2*y - 2)*exp(y) = C"),
]


@pytest.mark.parametrize("entrada, resultado", EXACTAS, ids=[c[0] for c in EXACTAS])
def test_exactas(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: ecuación exacta" in res.texto
    assert "AVISO" not in res.texto
    if "," not in entrada:
        cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Forma diferencial.", "Tipo de ecuación: ¿exacta?.", "Integrar M respecto a x.", "Hallar g(y).",
                 "Solución general."):
        assert paso in nombres
    for paso in pasos(res.texto):
        if paso.splitlines()[0].split(". ", 1)[1] in ("Tipo de ecuación: ¿exacta?.", "Hallar g(y).",
                                                        "Factor integrante."):
            assert "Regla: " in paso and "Queda: " in paso, paso


def test_exacta_paso_a_paso(core):
    texto = core.ecuacion_diferencial("(2*x*y + 3) dx + (x^2 - 1) dy = 0").texto
    assert "M_y es la derivada de M respecto a y, con x como constante: M_y = 2*x." in texto
    assert "N_x es la derivada de N respecto a x, con y como constante: N_x = 2*x." in texto
    assert "Son iguales: la ecuación es exacta." in texto
    assert "Regla del factor constante en ∫ 2*x*y dx (término 1 de la suma)." in texto  # pasos de Integrar
    assert "Queda: F = x^2*y + 3*x + g(y)" in texto
    assert "Igualamos a N: x^2 + g'(y) = x^2 - 1." in texto
    assert "Despejamos: g'(y) = x^2 - 1 - x^2 = -1." in texto
    assert "Queda: x^2*y + 3*x - y = C" in texto
    assert "Sacamos y factor común: x^2*y - y = y*(x^2 - 1)." in texto


def test_exacta_desde_y_prima(core):
    texto = core.ecuacion_diferencial("2*x*y + (x^2 + 2*y)*y' = 0").texto
    assert "y' es dy/dx: multiplicando por dx y pasando todo a la izquierda, 2*x*y dx + (x^2 + 2*y) dy = 0." in texto


def test_factor_integrante_de_exactas(core):
    texto = core.ecuacion_diferencial("(x*y - 1) dx + (x^2 - x*y) dy = 0").texto
    assert "No son iguales: la ecuación no es exacta." in texto
    assert "(M_y - N_x)/N = (x - (2*x - y))/(x*(x - y)) = -1/x: solo depende de x." in texto
    assert "m(x) = exp(-log(Abs(x))) = 1/x." in texto
    assert "Ahora M_y = 1 y N_x = 1: son iguales, la ecuación ya es exacta." in texto
    assert "m(y) = " in core.ecuacion_diferencial("y dx + (2*x - y*exp(y)) dy = 0").texto


def test_forma_diferencial_mal_escrita(core):
    res = core.ecuacion_diferencial("dx*dy = 0")
    assert res.es_error and "cada término debe llevar dx o dy una sola vez" in res.texto


BERNOULLI = [
    ("y' + y = x*y^2", "y = 1/(x + 1 + C*exp(x)); y = 0"),
    ("x*y' + y = x^2*y^2", "y = 1/(-x^2 + C*x); y = 0"),
    ("y' = y + x*y^3", "y = 1/sqrt(-x + 1/2 + C*exp(-2*x)); y = -1/sqrt(-x + 1/2 + C*exp(-2*x)); y = 0"),
    ("y' - 2*y = exp(x)*y^2", "y = 1/(-exp(x)/3 + C*exp(-2*x)); y = 0"),
    ("y' + y/x = y^2, y(1) = 1", "y = -1/(x*(log(Abs(x)) - 1))"),
]


@pytest.mark.parametrize("entrada, resultado", BERNOULLI, ids=[c[0] for c in BERNOULLI])
def test_bernoulli(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: ecuación de Bernoulli (cambio v = y^(1 - n))" in res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    if "," not in entrada:
        cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: de Bernoulli.", "Cambio de variable.", "Tipo de ecuación: lineal de primer orden.",
                 "Factor integrante.", "Deshacer el cambio.", "Comprobación."):
        assert paso in nombres
    assert "Despejar y'." not in nombres


def test_bernoulli_paso_a_paso(core):
    texto = core.ecuacion_diferencial("x*y' + y = x^2*y^2").texto
    assert "En este caso: y' + y/x = x*y^2: P(x) = 1/x, Q(x) = x y n = 2." in texto
    assert "Dividimos los dos lados entre x, lo que multiplica a y': y' + y/x = x*y^2." in texto
    assert "Dividimos los dos lados entre y^2: y'/y^2 + 1/(x*y) = x." in texto
    assert "Con v = 1/y, la regla de la cadena da v' = -y'/y^2; así y'/y^2 = -v'." in texto
    assert "Sustituimos: -v' + v/x = x." in texto
    assert "Multiplicamos los dos lados por -1: v' - v/x = -x." in texto
    assert "Tomamos el inverso de los dos lados: y = 1/(-x^2 + C*x)." in texto
    assert "Ningún valor de C da y = 0: se añade aparte (es una solución singular)." in texto


def test_bernoulli_con_raiz(core):
    # n = 1/2: y = v^2 con v = sqrt(y), que no puede ser negativa; la solución vale donde v >= 0
    res = core.ecuacion_diferencial("y' + y = x*sqrt(y)")
    assert res.texto.splitlines()[0] == "RESULTADO: y = (x - 2 + C*exp(-x/2))^2; y = 0"
    assert "AVISO" not in res.texto
    assert "Con v = sqrt(y), la regla de la cadena da v' = y'/(2*sqrt(y)); así y'/sqrt(y) = 2*v'." in res.texto
    assert ("Los dos lados valen lo mismo donde x - 2 + C*exp(-x/2) >= 0 (v = sqrt(y) no puede ser negativa)"
            in res.texto)


HOMOGENEAS_CONSTANTES = [
    ("y'' - 3*y' + 2*y = 0", "y = C1*exp(x) + C2*exp(2*x)"),
    ("y'' + 4*y = 0", "y = C1*cos(2*x) + C2*sin(2*x)"),
    ("y'' + 2*y' + y = 0", "y = C1*exp(-x) + C2*x*exp(-x)"),
    ("y'' + 2*y' + 5*y = 0", "y = C1*exp(-x)*cos(2*x) + C2*exp(-x)*sin(2*x)"),
    ("y''' - y = 0", "y = C1*exp(x) + C2*exp(-x/2)*cos(sqrt(3)*x/2) + C3*exp(-x/2)*sin(sqrt(3)*x/2)"),
    ("y'''' - y = 0", None),
    ("y''' - 3*y'' + 3*y' - y = 0", "y = C1*exp(x) + C2*x*exp(x) + C3*x^2*exp(x)"),
    ("2*y'' - 5*y' - 3*y = 0", "y = C1*exp(-x/2) + C2*exp(3*x)"),
]


@pytest.mark.parametrize("entrada, resultado", HOMOGENEAS_CONSTANTES, ids=[c[0] for c in HOMOGENEAS_CONSTANTES])
def test_coeficientes_constantes_homogeneas(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    if resultado:
        assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: lineal con coeficientes constantes (ecuación característica)" in res.texto, res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: lineal con coeficientes constantes.", "Ecuación característica.",
                 "Raíces de la ecuación característica.", "Solución general.", "Comprobación."):
        assert paso in nombres


def test_caracteristica_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y'' + 2*y' + 5*y = 0").texto
    assert "Probamos y = exp(r*x): y' = r*exp(r*x); y'' = r^2*exp(r*x)." in texto
    assert "Queda: r^2 + 2*r + 5 = 0" in texto
    assert "r^2 + 2*r + 5 = 0: a = 1, b = 2, c = 5; D = b^2 - 4*a*c = 2^2 - 4*1*5 = -16." in texto
    assert "D < 0: no hay raíces reales; sqrt(-16) = sqrt(16)*i = 4*i, y r = (-2 ± 4*i)/2 = -1 ± 2*i." in texto
    assert "r = -1 ± 2*i (simple): aporta exp(-x)*cos(2*x), exp(-x)*sin(2*x)." in texto
    doble = core.ecuacion_diferencial("y'' + 2*y' + y = 0").texto
    assert "D = 0: una raíz doble, r = -b/(2*a) = -2/2 = -1." in doble
    assert "r = -1 (doble): aporta exp(-x), x*exp(-x)." in doble
    cubica = core.ecuacion_diferencial("y''' - 3*y'' + 3*y' - y = 0").texto
    assert "Cada factor igualado a 0 (producto nulo):" in cubica  # factorizada con los pasos de Factorizar


def test_condiciones_iniciales_de_orden_2(core):
    res = core.ecuacion_diferencial("y'' + 4*y = 0, y(0) = 1, y'(0) = 2")
    assert res.texto.splitlines()[0] == "RESULTADO: y = sin(2*x) + cos(2*x)"
    assert "Derivamos: y' = -2*C1*sin(2*x) + 2*C2*cos(2*x)." in res.texto
    assert "y'(0) = 2: -2*C1*sin(2*0) + 2*C2*cos(2*0) = 2, es decir 2*C2 = 2." in res.texto
    assert "Con C1 = 1, C2 = 1: y = sin(2*x) + cos(2*x)." in res.texto
    res = core.ecuacion_diferencial("y'' - 3*y' + 2*y = 0, y(0) = 0, y'(0) = 1")
    assert res.texto.splitlines()[0] == "RESULTADO: y = exp(2*x) - exp(x)"
    assert "Volvemos atrás: C1 = -C2 = -1." in res.texto


NO_HOMOGENEAS = [
    ("y'' - y = x^2", "y = -x^2 - 2 + C1*exp(-x) + C2*exp(x)"),
    ("y'' + y = sin(x)", "y = -x*cos(x)/2 + C1*cos(x) + C2*sin(x)"),
    ("y'' - 3*y' + 2*y = exp(x)", "y = -x*exp(x) + C1*exp(x) + C2*exp(2*x)"),
    ("y'' - 2*y' + y = x*exp(x)", "y = x^3*exp(x)/6 + C1*exp(x) + C2*x*exp(x)"),
    ("y'' + y' = 3", "y = 3*x + C1*exp(-x) + C2"),
    ("y'' + 3*y' + 2*y = 4*x + exp(2*x) + cos(x)", None),
    ("y'' + 4*y = 8*x*sin(2*x)", None),
    ("y'' + y = x, y(0) = 1, y'(0) = 0", "y = x - sin(x) + cos(x)"),
]


@pytest.mark.parametrize("entrada, resultado", NO_HOMOGENEAS, ids=[c[0] for c in NO_HOMOGENEAS])
def test_coeficientes_indeterminados(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    if resultado:
        assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "coeficientes indeterminados" in res.texto, res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    if "," not in entrada:
        cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Solución de la homogénea.", "Forma de la solución particular.", "Sustituir y_p en la ecuación.",
                 "Igualar coeficientes.", "Solución general.", "Comprobación."):
        assert paso in nombres


def test_coeficientes_indeterminados_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y'' - y = x^2").texto
    assert "x^2: es un polinomio de grado 2; se prueba A*x^2 + B*x + F." in texto
    assert "Sustituimos en el lado izquierdo, y'' - y, y agrupamos: (2*A - F) - A*x^2 - B*x = x^2." in texto
    assert "De los términos constantes: 2*A - F = 0." in texto
    assert "Sustituimos A = -1 en las demás: -F - 2 = 0; -B = 0." in texto
    assert "y = C1*exp(-x) + C2*exp(x) - x^2 - 2" in texto  # el signo de y_p, bien
    resonancia = core.ecuacion_diferencial("y'' + y = sin(x)").texto
    assert ("Pero ±i es raíz (simple) de la ecuación característica: esas funciones ya están en y_h, y se multiplica "
            "por x.") in resonancia
    assert "Queda: y_p = x*(A*cos(x) + B*sin(x))" in resonancia
    varios = core.ecuacion_diferencial("y'' + 3*y' + 2*y = 4*x + exp(2*x) + cos(x)").texto
    assert "Volvemos atrás: F = 1 - 3*G = 1 - 3*(3/10) = 1/10." in varios


VARIACION = [
    ("y'' + y = 1/cos(x)", "y = x*sin(x) + log(Abs(cos(x)))*cos(x) + C1*cos(x) + C2*sin(x)"),
    ("y'' + y = tan(x)", None),
    ("y'' - 2*y' + y = exp(x)/x", "y = x*(log(Abs(x)) - 1)*exp(x) + C1*exp(x) + C2*x*exp(x)"),
    ("y'' + 4*y = 1/sin(2*x)", None),
]


@pytest.mark.parametrize("entrada, resultado", VARIACION, ids=[c[0] for c in VARIACION])
def test_variacion_de_parametros(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    if resultado:
        assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: lineal con coeficientes constantes, no homogénea (variación de parámetros)" in res.texto
    assert "AVISO" not in res.texto
    cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Solución de la homogénea.", "Variación de parámetros.", "Integrar u1' y u2'.", "Solución general.",
                 "Comprobación."):
        assert paso in nombres


def test_variacion_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y'' + y = 1/cos(x)").texto
    assert "y1 = cos(x); y1' = -sin(x)." in texto
    assert ("El wronskiano: W = y1*y2' - y2*y1' = cos(x)*cos(x) - sin(x)*(-sin(x)) = sin(x)^2 + cos(x)^2 = 1."
            in texto)
    assert "u1' = -y2*f/W = -sin(x)*(1/cos(x)) = -tan(x)." in texto
    assert "u1 = ∫ (-tan(x)) dx = log(cos(x))." in texto
    assert "Así, log(cos(x)) se escribe log(Abs(cos(x)))." in texto
    assert "No hace falta sumar constantes: darían términos que ya están en y_h." in texto


EULER = [
    ("x^2*y'' - 2*x*y' + 2*y = 0", "y = C1*x + C2*x^2"),
    ("x^2*y'' + x*y' - y = 0", "y = C1/x + C2*x"),
    ("x^2*y'' - x*y' + y = 0", "y = C1*x + C2*x*log(x)"),
    ("x^2*y'' + x*y' + 4*y = 0", "y = C1*cos(2*log(x)) + C2*sin(2*log(x))"),
    ("x^2*y'' - 3*x*y' + 4*y = 0", "y = C1*x^2 + C2*x^2*log(x)"),
    ("x^2*y'' - 2*y = x^3", "y = x^3/4 + C1/x + C2*x^2"),
    ("x^2*y'' - 2*x*y' + 2*y = x^3, y(1) = 1, y'(1) = 0", "y = x*(x^2 - 4*x + 5)/2"),
]


@pytest.mark.parametrize("entrada, resultado", EULER, ids=[c[0] for c in EULER])
def test_cauchy_euler(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: ecuación de Cauchy-Euler" in res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    if "," not in entrada:
        cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: de Cauchy-Euler.", "Ecuación indicial.", "Raíces de la ecuación indicial.",
                 "Comprobación."):
        assert paso in nombres


def test_cauchy_euler_paso_a_paso(core):
    texto = core.ecuacion_diferencial("x^2*y'' - 2*y = x^3").texto
    assert "Probamos y = x^r: y' = r*x^(r - 1); y'' = r*(r - 1)*x^(r - 2)." in texto
    assert "r*(r - 1) - 2 = 0." in texto
    assert "Operamos: r^2 - r - 2 = 0." in texto
    assert "r = -1 (simple): aporta 1/x." in texto
    assert "La ecuación se divide entre x^2, lo que multiplica a y'': f = x^3/x^2 = x." in texto
    assert "El wronskiano: W = y1*y2' - y2*y1' = (1/x)*2*x - x^2*(-1/x^2) = 3." in texto
    doble = core.ecuacion_diferencial("x^2*y'' - x*y' + y = 0").texto
    assert "r = 1 (doble): aporta x, x*log(x)." in doble
    compleja = core.ecuacion_diferencial("x^2*y'' + x*y' + 4*y = 0").texto
    assert "r = ±2*i (simple): aporta cos(2*log(x)), sin(2*log(x))." in compleja


REDUCCION = [
    ("x^2*y'' - 3*x*y' + 4*y = 0, y1 = x^2", "y = C1*x^2 + C2*x^2*log(Abs(x))"),
    ("(1 - x^2)*y'' - 2*x*y' + 2*y = 0, y1 = x", "y = C1*x + C2*(x*(log(Abs(x - 1)) - log(Abs(x + 1)))/2 + 1)"),
    ("y'' - 2*y' + y = 0, y1 = exp(x)", "y = C1*exp(x) + C2*x*exp(x)"),
    ("x^2*y'' - 3*x*y' + 4*y = x^2, y1 = x^2", "y = x^2*log(Abs(x))^2/2 + C1*x^2 + C2*x^2*log(Abs(x))"),
]


@pytest.mark.parametrize("entrada, resultado", REDUCCION, ids=[c[0] for c in REDUCCION])
def test_reduccion_de_orden(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: reducción de orden" in res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    cumple(res)
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: reducción de orden.", "Cambio y2 = u*y1.", "Hallar y2.", "Comprobación."):
        assert paso in nombres


def test_reduccion_paso_a_paso(core):
    texto = core.ecuacion_diferencial("x^2*y'' - 3*x*y' + 4*y = 0, y1 = x^2").texto
    assert "Comprobamos y1 en la homogénea: x^2*2 - 3*x*(2*x) + 4*x^2 = 0." in texto
    assert "Dividimos entre x^2, lo que multiplica a y'': P(x) = -3/x." in texto
    assert "u' = x^3/x^4 = 1/x." in texto
    res = core.ecuacion_diferencial("y'' + y = 0, y1 = x")
    assert "NOTA: x no es solución de la parte homogénea" in res.texto


LAPLACE = [
    ("y'' + y = 0, y(0) = 1, y'(0) = 0, laplace", "y = cos(x)"),
    ("y'' - 3*y' + 2*y = exp(3*t), y(0) = 0, y'(0) = 0, laplace", "y = exp(3*t)/2 - exp(2*t) + exp(t)/2"),
    ("y'' + 2*y' + 5*y = 0, y(0) = 1, y'(0) = 0, laplace", "y = (sin(2*x)/2 + cos(2*x))*exp(-x)"),
    ("y' + 2*y = heaviside(t - 1), y(0) = 0", "y = (1/2 - exp(2 - 2*t)/2)*Heaviside(t - 1)"),
    ("y'' + y = dirac(t - 2), y(0) = 0, y'(0) = 0", "y = sin(t - 2)*Heaviside(t - 2)"),
    ("y'' + 4*y = heaviside(t - 3), y(0) = 1, y'(0) = 0", "y = (1/4 - cos(2*t - 6)/4)*Heaviside(t - 3) + cos(2*t)"),
]


@pytest.mark.parametrize("entrada, resultado", LAPLACE, ids=[c[0] for c in LAPLACE])
def test_laplace(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: transformada de Laplace" in res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    nombres = titulos(res.texto)
    for paso in ("Transformada de Laplace.", "Despejar Y(s).", "Transformada inversa."):
        assert paso in nombres
    assert ("Comprobación por tramos." if "heaviside" in entrada or "dirac" in entrada else "Comprobación.") in nombres


def test_laplace_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y'' + 4*y = heaviside(t - 3), y(0) = 1, y'(0) = 0").texto
    assert "L{y''} = s^2*Y - s*y(0) - y'(0) = s^2*Y - s." in texto
    assert "L{Heaviside(t - 3)} = exp(-3*s)/s" in texto
    assert "Dividimos entre s^2 + 4: Y = s/(s^2 + 4) + exp(-3*s)/(s*(s^2 + 4))." in texto
    assert "Sustituir las raíces." in titulos(texto)  # las fracciones simples, con sus pasos
    assert "Traslación por exp(-3*s)." in titulos(texto)
    assert "Para t > 3: y = cos(2*t) - cos(2*t - 6)/4 + 1/4 y g = 1" in texto
    assert "L{{" not in texto and "{{" not in texto
    cuadrado = core.ecuacion_diferencial("y'' + 2*y' + 5*y = 0, y(0) = 1, y'(0) = 0, laplace").texto
    assert "s^2 + 2*s + 5 = (s + 1)^2 + 2^2; el numerador, s + 2 = 1*(s + 1) + 1" in cuadrado


def test_laplace_sin_condiciones_en_0(core):
    res = core.ecuacion_diferencial("y'' + y = 0, y(1) = 0, y'(1) = 1, laplace")
    assert "NOTA: la transformada de Laplace necesita las condiciones en 0: y(0), y'(0)." in res.texto


SISTEMAS = [
    ("x' = x + 2*y; y' = 3*x + 2*y", "x = -C1*exp(-t) + 2*C2*exp(4*t); y = C1*exp(-t) + 3*C2*exp(4*t)"),
    ("x' = x + 2*y; y' = 3*x + 2*y; x(0) = 1; y(0) = 0",
     "x = 2*exp(4*t)/5 + 3*exp(-t)/5; y = 3*exp(4*t)/5 - 3*exp(-t)/5"),
    ("x' = -y; y' = x", "x = -C1*sin(t) + C2*cos(t); y = C1*cos(t) + C2*sin(t)"),
    ("x' = 3*x - y; y' = x + y", "x = C1*exp(2*t) + C2*(t*exp(2*t) + exp(2*t)); y = C1*exp(2*t) + C2*t*exp(2*t)"),
    ("x' = x; y' = 2*y; z' = x + y + 3*z", None),
    ("dx/dt = x - 2*y, dy/dt = 2*x + y", None),
]


@pytest.mark.parametrize("entrada, resultado", SISTEMAS, ids=[c[0] for c in SISTEMAS])
def test_sistemas(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert not res.es_error, res.texto
    if resultado:
        assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: sistema lineal (valores y vectores propios)" in res.texto
    assert "NOTA" not in res.texto
    nombres = titulos(res.texto)
    for paso in ("Planteamiento.", "Ecuación característica del sistema.", "Valores propios.", "Vectores propios.",
                 "Solución general.", "Comprobación."):
        assert paso in nombres
    # Cada función cumple su ecuación
    t = ParserMatematico.simbolo("t")
    valores = {s.lhs: s.rhs for s in res.valor}
    for ecuacion in res.planteamiento:
        if isinstance(ecuacion.lhs, sympy.Derivative):
            f = ParserMatematico.simbolo(ecuacion.lhs.expr.func.__name__)
            lado = ecuacion.rhs.replace(lambda e: isinstance(e, sympy.core.function.AppliedUndef),
                                        lambda e: valores[ParserMatematico.simbolo(e.func.__name__)])
            assert sympy.simplify(sympy.diff(valores[f], t) - lado) == 0


def test_sistema_paso_a_paso(core):
    texto = core.ecuacion_diferencial("x' = x + 2*y; y' = 3*x + 2*y; x(0) = 1; y(0) = 0").texto
    assert "En este caso: X = (x, y); A = [[1, 2]; [3, 2]] (una fila por ecuación)." in texto
    assert "det(A - r*I) = (1 - r)*(2 - r) - 2*3 = r^2 - 3*r - 4." in texto
    assert "De la primera fila: 2*v1 + 2*v2 = 0; con v = (-1, 1) se cumple: 2*(-1) + 2*1 = 0." in texto
    assert "x(0) = 1: -C1*exp(-0) + 2*C2*exp(4*0) = 1, es decir -C1 + 2*C2 = 1." in texto
    complejo = core.ecuacion_diferencial("x' = -y; y' = x").texto
    assert "Es complejo: v = (0, 1) + (1, 0)*i." in complejo
    doble = core.ecuacion_diferencial("x' = 3*x - y; y' = x + y").texto
    assert "r = 2 es doble pero solo tiene un vector propio" in doble


def test_sistema_no_lineal(core):
    res = core.ecuacion_diferencial("x' = x*y; y' = x")
    assert res.es_error and "sistemas lineales homogéneos con coeficientes constantes" in res.texto


SERIES = [
    ("y'' - x*y = 0", "y = C1*(1 + x^3/6 + x^6/180) + C2*(x + x^4/12) + O(x^7)"),
    ("y'' - 2*x*y' + 4*y = 0", "y = C1*(1 - 2*x^2) + C2*(x - x^3/3 - x^5/30) + O(x^7)"),
    ("y'' + y = 0, serie", "y = C1*(1 - x^2/2 + x^4/24 - x^6/720) + C2*(x - x^3/6 + x^5/120) + O(x^7)"),
    ("y'' - x*y = 0, y(0) = 1, y'(0) = 0", "y = 1 + x^3/6 + x^6/180 + O(x^7)"),
    ("y'' + x^2*y' = 0", "y = C1 + C2*(x - x^4/12) + O(x^7)"),
]


@pytest.mark.parametrize("entrada, resultado", SERIES, ids=[c[0] for c in SERIES])
def test_series(core, entrada, resultado):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert "Método: serie de potencias alrededor de x = 0" in res.texto
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    nombres = titulos(res.texto)
    for paso in ("Tipo de ecuación: solución en serie de potencias.", "Sustituir la serie.",
                 "Coeficientes de la serie.", "Comprobación."):
        assert paso in nombres
    assert nombres.count("Comprobación.") == 1


def test_serie_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y'' - x*y = 0").texto
    assert "-x*y: Σ -c[n]*x^(n + 1); con n = m - 1 queda Σ (-c[m - 1])*x^m." in texto
    assert "El coeficiente de x^m tiene que valer 0: (m + 1)*(m + 2)*c[m + 2] - c[m - 1] = 0." in texto
    assert "Queda: c[m + 2] = c[m - 1]/((m + 1)*(m + 2))" in texto
    assert "m = 1: c[3] = c[0]/6 = C1/6." in texto
    assert "m = 0: c[2] = c[-1]/2 = 0." in texto


RICCATI_CLAIRAUT_REDUCIBLES = [
    ("y' = y^2 - 2*x*y + x^2 + 1, y1 = x", "y = x - 1/(x + C)", "ecuación de Riccati (cambio y = y1 + 1/v)"),
    ("y' = -y^2 + 1 + x^2, y1 = x", "y = x + exp(-x^2)/(sqrt(pi)*erf(x)/2 + C)", "ecuación de Riccati"),
    ("y = x*y' + y'^2", "y = C^2 + C*x; y = -x^2/4", "ecuación de Clairaut"),
    ("y = x*y' - y'^3", "y = -C^3 + C*x; y = 2*sqrt(3)*x^(3/2)/9; y = -2*sqrt(3)*x^(3/2)/9", "ecuación de Clairaut"),
    ("y = x*y' + sqrt(1 + y'^2)", "y = C*x + sqrt(1 + C^2)", "ecuación de Clairaut"),
    ("y'' = y'^2", "y = C2 - log(Abs(x + C1)); y = C2", "reducible de orden (p = y')"),
    ("x*y'' = y'", "y = C1*x^2/2 + C2", "reducible de orden (p = y')"),
    ("y*y'' = y'^2", "y = C2*exp(C1*x)", "reducible de orden (p = y')"),
    ("y*y'' = y'^2, y(0) = 1, y'(0) = 2", "y = exp(2*x)", "reducible de orden (p = y')"),
]


@pytest.mark.parametrize("entrada, resultado, metodo", RICCATI_CLAIRAUT_REDUCIBLES,
                         ids=[c[0] for c in RICCATI_CLAIRAUT_REDUCIBLES])
def test_riccati_clairaut_y_reducibles_de_orden(core, entrada, resultado, metodo):
    res = core.ecuacion_diferencial(entrada)
    assert res.texto.splitlines()[0] == f"RESULTADO: {resultado}", res.texto
    assert f"Método: {metodo}" in res.texto
    assert "AVISO" not in res.texto
    if "," not in entrada or "y1" in entrada:
        cumple(res)
    assert "Comprobación." in titulos(res.texto)


def test_riccati_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y' = y^2 - 2*x*y + x^2 + 1, y1 = x").texto
    assert "P = x^2 + 1, Q = -2*x, R = 1; y1 = x." in texto
    assert "Comprobamos y1: y1' = 1 y el lado derecho con y = y1 vale 1: es solución." in texto
    assert "Multiplicamos por -v^2: v' + (Q + 2*R*y1)*v = -R, con Q + 2*R*y1 = 0 y -R = -1." in texto
    assert "Tipo de ecuación: integración directa." in titulos(texto)
    res = core.ecuacion_diferencial("y' = y^2 + 1, y1 = x")
    assert "NOTA: x no es solución de la ecuación" in res.texto


def test_clairaut_paso_a_paso(core):
    texto = core.ecuacion_diferencial("y = x*y' + y'^2").texto
    assert "En este caso: y = x*p + f(p), con f(p) = p^2." in texto
    assert "Derivamos: p = p + x*p' + f'(p)*p', con f'(p) = 2*p." in texto
    assert "Queda: p'*(x + 2*p) = 0" in texto
    assert "Con p = -x/2: y = x*p + f(p) = -x^2/4." in texto
    raiz = core.ecuacion_diferencial("y = x*y' + sqrt(1 + y'^2)").texto
    assert "NOTA: además está la solución singular en forma paramétrica: x = -p/sqrt(p^2 + 1), y = 1/sqrt(p^2 + 1)." \
        in raiz


def test_reducibles_de_orden_paso_a_paso(core):
    sin_y = core.ecuacion_diferencial("x*y'' = y'").texto
    assert "Tipo de ecuación: reducible de orden (sin y)." in titulos(sin_y)
    assert "En este caso: la ecuación en p es p'*x = p." in sin_y
    sin_x = core.ecuacion_diferencial("y*y'' = y'^2").texto
    assert "Tipo de ecuación: reducible de orden (sin x)." in titulos(sin_x)
    assert "En este caso: la ecuación en p es p*p'*y = p^2 (p' es dp/dy)." in sin_x
    assert "La constante C de p pasa a llamarse C1." in sin_x


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
    res = core.ecuacion_diferencial("x*y'' + y' + x*y = 0")  # Bessel: x = 0 no es un punto ordinario
    assert not res.es_error
    assert res.texto.splitlines()[0] == "RESULTADO: y = C1*besselj(0, x) + C2*bessely(0, x)"
    assert "NOTA: por ahora hay explicación paso a paso" in res.texto
    assert "PASO A PASO" not in res.texto


def test_si_un_metodo_de_sympy_falla_prueba_otro(core):
    # dsolve se rompía por dentro con el método de Riccati ("bad operand type for unary -")
    res = core.ecuacion_diferencial("y' = y^2 + x^2")
    assert not res.es_error, res.texto
    assert "NOTA: SymPy da la solución como una serie de potencias" in res.texto


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
