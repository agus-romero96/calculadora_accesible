"""
Ecuaciones e inecuaciones de una variable (algebra/resolucion.py): el conjunto solución
coincide con solveset de SymPy y el paso a paso sigue el estándar (Regla, En este caso,
cuentas, Queda), sin saltos y con comprobación en la ecuación original.
"""
import re

import pytest
import sympy
from sympy import S

import exportar
from algebra.ecuaciones import despejar, invertir
from algebra.resolucion import describir_conjunto, intervalo_texto, mismo_conjunto
from parser_matematico import ParserMatematico

x = ParserMatematico.simbolo("x")


def pasos(salida):
    """Los pasos numerados, cada uno con sus líneas."""
    texto = salida.split("PASO A PASO:")[1]
    return re.split(r"\n(?=\d+\. )", texto.strip())


def titulos(salida):
    return [p.splitlines()[0] for p in pasos(salida)]


def verdad(entrada):
    """solveset de SymPy sobre la entrada (con la misma variable real que el parser)."""
    parser = ParserMatematico()
    izq, rel, der = re.split(r"(<=|>=|<|>|=)", entrada)
    clase = {"=": sympy.Eq, "<": sympy.Lt, "<=": sympy.Le, ">": sympy.Gt, ">=": sympy.Ge}[rel]
    return sympy.solveset(clase(parser.parsear(izq).doit(), parser.parsear(der).doit()), x, domain=S.Reals)


# ---------------- Todos los tipos: el conjunto es el de SymPy ----------------

CASOS = [
    # Primer grado
    ("2*x + 1 = 7", "Ecuación de primer grado", "x = 3"),
    ("2*(x+1) - 3 = x/2 + 1", "Ecuación de primer grado", "x = 4/3"),
    ("5 = 3 - x", "Ecuación de primer grado", "x = -2"),
    ("2*(x+1) = 2*x + 2", "Ecuación de primer grado", "todos los números reales"),
    ("x + 1 = x + 2", "Ecuación de primer grado", "no tiene solución real"),
    # Segundo grado
    ("x^2 - 5*x + 6 = 0", "Ecuación de segundo grado", "x = 2 o x = 3"),
    ("x^2 - 6*x + 9 = 0", "Ecuación de segundo grado", "x = 3"),
    ("2*x^2 - 4*x - 1 = 0", "Ecuación de segundo grado", "x = 1 - sqrt(6)/2"),
    ("x^2 + x + 1 = 0", "Ecuación de segundo grado", "no tiene solución real"),
    ("x^2 = 3*x", "Ecuación de segundo grado", "x = 0 o x = 3"),
    ("2*x^2 - 8 = 0", "Ecuación de segundo grado", "x = -2 o x = 2"),
    ("(x+1)^2 = 2*x + 5", "Ecuación de segundo grado", "x = -2 o x = 2"),
    ("2*x^2 - 10*x + 12 = 0", "Ecuación de segundo grado", "x = 2 o x = 3"),
    ("3*x^2 + 2*x - 1 = 0", "Ecuación de segundo grado", "x = -1 o x = 1/3"),
    # Racionales
    ("3/(x-2) = x/(x-2)", "Ecuación racional", "x = 3"),
    ("x/(x-1) = 1/(x-1)", "Ecuación racional", "no tiene solución real"),
    ("1/x + 1/(x+1) = 1", "Ecuación racional", "x = 1/2 - sqrt(5)/2"),
    ("x/(x^2-4) = 1/(x-2)", "Ecuación racional", "no tiene solución real"),
    ("x^2/(x-1) = 1/(x-1)", "Ecuación racional", "x = -1"),
    ("x/2 + 1/x = 3/2", "Ecuación racional", "x = 1 o x = 2"),
    # Inecuaciones de primer grado
    ("3 - 2*x > 7", "Inecuación de primer grado", "x < -2"),
    ("2*x + 1 <= 7", "Inecuación de primer grado", "x <= 3"),
    ("x/3 - 1 >= 2*x", "Inecuación de primer grado", "x <= -3/5"),
    ("3*x + 1 < 3*x", "Inecuación de primer grado", "no tiene solución real"),
    # Inecuaciones de segundo grado
    ("x^2 - 4 <= 0", "Inecuación de segundo grado", "-2 <= x <= 2"),
    ("-x^2 + 2*x + 3 < 0", "Inecuación de segundo grado", "x < -1 o x > 3"),
    ("x^2 + 1 > 0", "Inecuación de segundo grado", "todos los números reales"),
    ("x^2 + 1 < 0", "Inecuación de segundo grado", "no tiene solución real"),
    ("x^2 - 6*x + 9 > 0", "Inecuación de segundo grado", "x < 3 o x > 3"),
    ("x^2 - 6*x + 9 <= 0", "Inecuación de segundo grado", "x = 3"),
    ("x^2 >= 2", "Inecuación de segundo grado", "x <= -sqrt(2) o x >= sqrt(2)"),
    ("x^2 - 3*x > 0", "Inecuación de segundo grado", "x < 0 o x > 3"),
    ("2*x^2 + 3*x - 2 >= 0", "Inecuación de segundo grado", "x <= -2 o x >= 1/2"),
]


@pytest.mark.parametrize("entrada, tipo, resultado", CASOS, ids=[c[0] for c in CASOS])
def test_resultado_tipo_y_pasos(core, entrada, tipo, resultado):
    res = core.ecuacion(entrada)
    assert not res.es_error, res.texto
    assert res.operacion == "ecuacion"
    assert mismo_conjunto(res.valor, verdad(entrada))
    lineas = res.texto.splitlines()
    assert lineas[0].startswith("RESULTADO: ") and resultado in lineas[0]
    assert "AVISO" not in res.texto and "NOTA" not in res.texto, "debe explicarse paso a paso"
    assert f"TIPO: {tipo}" in res.texto
    # Formato estándar: cada paso con su regla y lo que queda; el último, la comprobación
    for paso in pasos(res.texto):
        assert "Regla: " in paso and "Queda: " in paso, paso
    # Sin solución no hay nada que sustituir; si no, el último paso comprueba (o descarta raíces extrañas)
    if not (tipo.startswith("Ecuación") and res.valor == S.EmptySet):
        assert titulos(res.texto)[-1].endswith("Comprobación.") or "raíces extrañas" in titulos(res.texto)[-1]
    assert "NO se cumple" not in res.texto.split("Comprobación.")[-1] or tipo.startswith("Inecuación")


# ---------------- Ecuaciones ----------------

def test_primer_grado_quita_parentesis_y_comprueba(core):
    texto = core.ecuacion("2*(x+1) - 3 = x/2 + 1").texto
    assert "Quitamos paréntesis (propiedad distributiva): 2*(x + 1) - 3 = 2*x + 2 - 3." in texto
    assert "Agrupamos términos semejantes: 2 - 3 = -1." in texto
    assert "Dividimos los dos lados entre 3/2: x = 2/(3/2) = 4/3." in texto
    assert "x = 4/3: lado izquierdo 2*((4/3) + 1) - 3 = 5/3; lado derecho (4/3)/2 + 1 = 5/3; 5/3 = 5/3 se cumple." in texto


def test_identidad_muestra_la_distributiva_antes_de_anularse(core):
    texto = core.ecuacion("2*(x+1) = 2*x + 2").texto
    assert "Quitamos paréntesis (propiedad distributiva): 2*(x + 1) - (2*x + 2) = 2*x - 2*x + 2 - 2." in texto
    assert "La incógnita x se anula: queda 0 = 0, que es cierto sea cual sea x." in texto


def test_cuadratica_discriminante_con_sus_cuentas_y_factorizacion(core):
    texto = core.ecuacion("x^2 - 5*x + 6 = 0").texto
    assert titulos(texto) == ["1. Calcular el discriminante.", "2. Factorizar y aplicar el producto nulo.",
                              "3. Comprobación."]
    assert "a = 1 (coeficiente de x^2), b = -5 (coeficiente de x) y c = 6 (término independiente)." in texto
    assert "Sustituimos: Δ = (-5)^2 - 4*1*6." in texto
    assert "(-5)^2 = 25 y 4*1*6 = 24." in texto
    assert "Δ = 25 - 24 = 1." in texto
    assert "Buscamos dos números que multiplicados den 6 y sumados den -5: -3 y -2." in texto
    assert "Queda x^2 - 5*x + 6 = (x - 2)*(x - 3)." in texto
    assert "x = 2: lado izquierdo 2^2 - 5*2 + 6 = 0; lado derecho 0; 0 = 0 se cumple." in texto


def test_cuadratica_formula_general_con_raices_irracionales(core):
    texto = core.ecuacion("2*x^2 - 4*x - 1 = 0").texto
    assert "Aplicar la fórmula general" in texto
    assert "Sustituimos: x = (-(-4) ± sqrt(24))/(2*2) = (4 ± sqrt(24))/4." in texto
    assert "24 = 2^2*6, así que sqrt(24) = 2*sqrt(6)." in texto
    assert "x1 = (4 + 2*sqrt(6))/4 = 4/4 + (2*sqrt(6))/4 = 1 + sqrt(6)/2." in texto
    assert "aproximadamente 2.224745" in texto.splitlines()[0]


def test_cuadratica_sin_soluciones_reales(core):
    texto = core.ecuacion("x^2 + x + 1 = 0").texto
    assert texto.startswith("RESULTADO: no tiene solución real")
    assert "Δ = -3 es negativo: no hay soluciones reales" in texto


def test_cuadratica_divide_entre_el_coeficiente_principal(core):
    texto = core.ecuacion("2*x^2 - 10*x + 12 = 0").texto
    assert "Dividir entre el coeficiente principal" in texto
    assert "Operamos: x^2 - 5*x + 6 = 0." in texto


def test_cuadratica_factor_comun_e_incompleta(core):
    texto = core.ecuacion("x^2 = 3*x").texto
    assert "Restamos 3*x en los dos lados para dejar 0 a la derecha: x^2 - 3*x = 0." in texto
    assert "Los dos términos tienen el factor x: x^2 - 3*x = x*(x - 3)." in texto
    assert "x = 0: ya está despejada." in texto
    texto = core.ecuacion("2*x^2 - 8 = 0").texto
    assert "Los números cuyo cuadrado es 4 son sqrt(4) y -sqrt(4)." in texto
    assert "sqrt(4) = 2, porque 2^2 = 4." in texto


def test_racional_restricciones_mcm_y_raiz_extrana(core):
    texto = core.ecuacion("x^2/(x-1) = 1/(x-1)").texto
    assert titulos(texto)[:2] == ["1. Restricciones del dominio.", "2. Multiplicar por el MCM de los denominadores."]
    assert "Queda: x ≠ 1" in texto
    assert "x^2/(x - 1) por (x - 1): se simplifica el denominador x - 1 y queda x^2." in texto
    assert ("x = 1 anula el denominador x - 1: no está en el dominio. Es una raíz extraña (apareció al "
            "multiplicar por el MCM) y se descarta.") in texto
    assert "x = -1 no anula ningún denominador: es válida." in texto
    assert texto.startswith("RESULTADO: x = -1\n")


def test_racional_factoriza_el_denominador_sin_repetir_restricciones(core):
    texto = core.ecuacion("x/(x^2-4) = 1/(x-2)").texto
    assert "Factorizamos el denominador: x^2 - 4 = (x - 2)*(x + 2)." in texto
    assert "x - 2 = 0 da x = 2, que ya está entre las restricciones." in texto
    assert "Queda: x ≠ -2, x ≠ 2" in texto


def test_racional_con_denominador_numerico_en_el_mcm(core):
    texto = core.ecuacion("x/2 + 1/x = 3/2").texto
    assert "MCM de los denominadores: 2*x." in texto


# ---------------- Inecuaciones ----------------

def test_inecuacion_lineal_invierte_el_sentido_al_dividir_entre_negativo(core):
    texto = core.ecuacion("3 - 2*x > 7").texto
    assert texto.startswith("RESULTADO: x < -2, es decir, (-∞, -2)")
    assert ("Dividimos los dos lados entre -2. Como -2 es negativo, el sentido de la desigualdad se invierte "
            "(> pasa a <): x < 4/(-2).") in texto
    assert "Operamos: 4/(-2) = -2." in texto
    assert "x = -3 (dentro de la solución): lado izquierdo 3 - 2*(-3) = 9; lado derecho 7; 9 > 7 se cumple." in texto
    assert "x = 0 (fuera de la solución)" in texto and "3 > 7 NO se cumple" in texto
    assert "x = -2 (extremo excluido)" in texto


def test_inecuacion_lineal_con_divisor_positivo_conserva_el_sentido(core):
    texto = core.ecuacion("2*x + 1 <= 7").texto
    assert "Como 2 es positivo, el sentido de la desigualdad no cambia: x <= 6/2." in texto
    assert "x = 3 (extremo incluido)" in texto


def test_inecuacion_cuadratica_tabla_de_signos_linea_a_linea(core):
    texto = core.ecuacion("x^2 - 4 <= 0").texto
    assert "Factorizamos con las raíces: x^2 - 4 = (x + 2)*(x - 2)." in texto
    assert "Los puntos críticos -2 y 2 dividen la recta en 3 intervalos: (-∞, -2), (-2, 2), (2, ∞)." in texto
    assert "Intervalo (-2, 2): probamos con x = 0." in texto
    assert "x + 2 = 0 + 2 = 2: positivo." in texto
    assert "Producto de signos: (+)*(-) = -. El polinomio es negativo: cumple x^2 - 4 <= 0." in texto
    assert "como la desigualdad es <=, se incluyen (0 <= 0 es cierto)." in texto
    assert texto.startswith("RESULTADO: -2 <= x <= 2, es decir, [-2, 2]")


def test_inecuacion_cuadratica_con_a_negativo(core):
    texto = core.ecuacion("-x^2 + 2*x + 3 < 0").texto
    assert "Como -1 es negativo, el sentido de la desigualdad se invierte (< pasa a >)." in texto
    assert "(-∞, -1) ∪ (3, ∞)" in texto.splitlines()[0]


def test_inecuacion_cuadratica_con_coeficiente_en_la_tabla(core):
    texto = core.ecuacion("2*x^2 + 3*x - 2 >= 0").texto
    assert "a = 2: positivo." in texto
    assert "Producto de signos: (+)*(-)*(-) = +." in texto


def test_inecuacion_sin_raices_tiene_el_signo_de_a(core):
    texto = core.ecuacion("x^2 + 1 > 0").texto
    assert "Signo del polinomio" in texto
    assert "x^2 + 1 es siempre positivo, así que x^2 + 1 > 0 se cumple para todo número real." in texto


def test_inecuacion_con_raiz_doble(core):
    texto = core.ecuacion("x^2 - 6*x + 9 > 0").texto
    assert "El punto crítico 3 divide la recta en 2 intervalos: (-∞, 3), (3, ∞)." in texto
    assert "El factor (x - 3)^2 aparece dos veces: su signo se repite." in texto


# ---------------- Sin pasos y errores ----------------

def test_otros_tipos_los_resuelve_sympy_con_una_nota(core):
    res = core.ecuacion("x^3 = x")
    assert not res.es_error
    assert res.texto.startswith("RESULTADO: x = -1 o x = 0 o x = 1")
    assert "NOTA: hay explicación paso a paso" in res.texto and "PASO A PASO" not in res.texto
    assert core.ecuacion("1/(x^2 - 1) < 0").texto.startswith("RESULTADO: -1 < x < 1")


@pytest.mark.parametrize("entrada, mensaje", [
    ("x^2 + 1", "Escriba una ecuación o inecuación"),
    ("x < 3 = 2", "Escriba un solo signo"),
    ("x + y = 1", "Hay varias variables (x, y)"),
    ("2 = 2", "No hay ninguna incógnita"),
    ("= 3", "Falta uno de los dos lados"),
    ("sin(x) = 0", "no se puede resolver esta ecuación"),
])
def test_errores(core, entrada, mensaje):
    res = core.ecuacion(entrada)
    assert res.es_error and mensaje in res.texto


def test_otras_formas_de_escribir_los_signos(core):
    assert core.ecuacion("2x + 1 ≤ 7").valor == core.ecuacion("2x + 1 =< 7").valor == sympy.Interval(-sympy.oo, 3)
    assert core.ecuacion("x ≥ 1").valor == sympy.Interval(1, sympy.oo)
    assert core.ecuacion("2x == 4").valor == sympy.FiniteSet(2)


# ---------------- Piezas ----------------

def test_despejar_desigualdad_invierte_con_coeficiente_menos_uno():
    lineas, valor = despejar(-x, 3, x, relacion="<")
    assert valor == -3
    assert lineas[-1] == ("Multiplicamos los dos lados por -1. Como -1 es negativo, el sentido de la desigualdad "
                          "se invierte (< pasa a >): x > -3.")


def test_invertir():
    assert [invertir(r) for r in ("<", "<=", ">", ">=", "=")] == [">", ">=", "<", "<=", "="]


def test_describir_conjunto():
    assert describir_conjunto(S.EmptySet, x) == "no tiene solución real"
    assert describir_conjunto(S.Reals, x) == "todos los números reales"
    assert describir_conjunto(sympy.FiniteSet(-1, 2), x) == "x = -1 o x = 2"
    assert describir_conjunto(sympy.Interval.Lopen(-2, 5), x) == "-2 < x <= 5, es decir, (-2, 5]"
    assert intervalo_texto(sympy.Interval(1, sympy.oo)) == "[1, ∞)"


def test_exportar_conjunto_solucion(core):
    res = core.ecuacion("x^2 - 4 <= 0")
    assert exportar.resultado_corto(res) == "-2 <= x <= 2, es decir, [-2, 2]"
    assert exportar.latex(res) == r"x^{2} - 4 \leq 0 \quad\Longrightarrow\quad x \in \left[-2, 2\right]"
    assert "<mo>&#x2208;</mo>" in exportar.mathml(res)


def test_mathml_de_desigualdad_estricta_es_xml_valido(core):
    import xml.dom.minidom
    for entrada in ("x^2 + 1 < 0", "3 - 2*x > 7"):
        xml.dom.minidom.parseString(exportar.mathml(core.ecuacion(entrada)))


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.ecuacion("x^2 - 4 <= 0").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert texto.startswith("RESULT: -2 <= x <= 2, that is, [-2, 2]")
    assert "TYPE: Quadratic inequality" in texto and "Sign chart" in texto
