"""
Determinante por cofactores (algebra/determinante.py): el valor es el de SymPy y el paso a
paso sigue el estándar: desarrollo por la fila o columna con más ceros, cada menor (los 3x3
de una 4x4 en sus propios pasos, con otra notación), cada cofactor con su signo y la suma.
"""
import re

import pytest
import sympy

import exportar
from algebra.determinante import MotorDeterminante


def pasos(salida):
    texto = salida.split("PASO A PASO:")[1]
    return re.split(r"\n(?=\d+\. )", texto.strip())


def titulos(salida):
    return [p.splitlines()[0].split(". ", 1)[1] for p in pasos(salida)]


CASOS = [
    ("7", 7),
    ("1 2\n3 4", -2),
    ("2 0 1\n1 3 2\n1 0 4", 21),
    ("1 2 3\n4 5 6\n7 8 9", 0),
    ("1 2 3\n0 0 0\n7 8 9", 0),
    ("2 -1 3\n0 4 5\n1 0 -2", -33),
    ("1/2 1\n3 4", -1),
    ("1 2 0 1\n0 1 3 0\n2 0 1 1\n1 1 0 2", 16),
    ("1 2 3 4\n5 6 7 8\n2 6 4 8\n3 1 1 2", 72),
    ("[[1,2],[3,4]]", -2),
]


@pytest.mark.parametrize("entrada, valor", CASOS, ids=[c[0].replace("\n", "; ") for c in CASOS])
def test_valor_y_estructura(core, entrada, valor):
    res = core.determinante(entrada)
    assert not res.es_error, res.texto
    assert res.operacion == "determinante"
    assert res.valor == valor == sympy.simplify(res.expresion.det())
    assert res.texto.splitlines()[0] == f"RESULTADO: det(A) = {valor}"
    assert "AVISO" not in res.texto and "NOTA" not in res.texto
    for paso in pasos(res.texto):
        assert "Regla: " in paso and "Queda: " in paso, paso
    assert pasos(res.texto)[-1].splitlines()[-1] == f"   Queda: det(A) = {valor}"


def test_elige_la_linea_con_mas_ceros(core):
    texto = core.determinante("2 0 1\n1 3 2\n1 0 4").texto
    assert "la columna 2 es [ 0, 3, 0 ]: tiene 2 ceros, y ninguna otra tiene más (se desarrolla por ella)." in texto
    assert "a12 = 0: su término vale 0 y no hace falta su menor." in texto
    assert "Queda: det(A) = a22*C22" in texto
    assert ("a22 = 3: quitamos la fila 2 y la columna 2, queda [ 2, 1 ]; [ 1, 4 ], así que M22 = 2*4 - 1*1 = 8 - 1 = 7. "
            "Signo: (-1)^(2+2) = 1, así que C22 = 1*7 = 7.") in texto


def test_sin_ceros_usa_la_fila_1(core):
    texto = core.determinante("1 2 3\n4 5 6\n7 8 9").texto
    assert "ninguna fila ni columna tiene ceros: se desarrolla por la fila 1, [ 1, 2, 3 ]." in texto
    assert "det(A) = a11*C11 + a12*C12 + a13*C13 = 1*(-3) + 2*6 + 3*(-3) = -3 + 12 + (-9) = 0." in texto


def test_linea_de_ceros(core):
    texto = core.determinante("1 2 3\n0 0 0\n7 8 9").texto
    assert "Línea de ceros." in titulos(texto)


def test_cuatro_por_cuatro_desarrolla_cada_menor(core):
    texto = core.determinante("1 2 0 1\n0 1 3 0\n2 0 1 1\n1 1 0 2").texto
    assert titulos(texto) == ["Desarrollo por cofactores de A.", "Desarrollo por cofactores de M22.",
                              "Cofactores y suma de M22.", "Desarrollo por cofactores de M23.",
                              "Cofactores y suma de M23.", "Cofactores y suma de A."]
    # Dentro de un menor, otra notación: no se confunde con la de A
    assert "en M23 los elementos se llaman b_ij, sus menores N_ij y sus cofactores D_ij." in texto
    assert "b21 = 2: quitamos la fila 2 y la columna 1" in texto and "D21 = -1*3 = -3." in texto
    assert "y M23 = -5 (calculado en los pasos anteriores)" in texto


def test_letras(core):
    res = core.determinante("a b\nc d")
    assert res.texto.splitlines()[0] == "RESULTADO: det(A) = a*d - b*c"
    assert "det(A) = a*d - b*c." in res.texto  # sin la cuenta intermedia que repetiría lo mismo


def test_cinco_por_cinco_sin_pasos(core):
    res = core.determinante("\n".join(" ".join("1" if i == j else "0" for j in range(5)) for i in range(5)))
    assert not res.es_error and res.valor == 1
    assert "NOTA: el desarrollo por cofactores se explica hasta matrices 4x4" in res.texto
    assert "PASO A PASO" not in res.texto


@pytest.mark.parametrize("entrada, mensaje", [
    ("1 2 3\n4 5 6", "La matriz no es cuadrada (2x3)"),
    ("", "La expresión está vacía"),
])
def test_errores(core, entrada, mensaje):
    res = core.determinante(entrada)
    assert res.es_error and mensaje in res.texto, res.texto


def test_exportar(core):
    res = core.determinante("1 2\n3 4")
    assert exportar.resultado_corto(res) == "-2"
    assert exportar.latex(res) == r"\left|{\begin{matrix}1 & 2\\3 & 4\end{matrix}}\right| = -2"
    import xml.dom.minidom
    xml.dom.minidom.parseString(exportar.mathml(res))


def test_la_inversa_sigue_igual(core):
    """El determinante de la inversa sigue desarrollándose por la fila 1, como antes."""
    texto = core.inversa("2 0 1\n1 3 2\n1 0 4").texto
    assert "la primera fila es [ 2, 0, 1 ]." in texto


def test_en_ingles(core):
    import i18n
    anterior = i18n.idioma_actual()
    try:
        i18n.establecer_idioma("en")
        texto = core.determinante("2 0 1\n1 3 2\n1 0 4").texto
    finally:
        i18n.establecer_idioma(anterior)
    assert texto.splitlines()[0] == "RESULT: det(A) = 21"
    assert "column 2 is [ 0, 3, 0 ]: it has 2 zeros, and no other has more (we expand along it)." in texto
