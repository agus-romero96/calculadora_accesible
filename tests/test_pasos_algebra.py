"""
Paso a paso de Álgebra (sistemas clásicos, Gauss-Jordan e inversa): formato estándar
(Regla, En este caso, cuentas, Queda), resultado primero, sin saltos y con comprobación.
"""
import re

import pytest
import sympy

from algebra.ecuaciones import comprobar, despejar, sustituir

x, y = sympy.symbols("x y", real=True)

SISTEMAS = [
    (["2*x + 3*y = 12", "x - y = 1"], {"x": "3", "y": "2"}),
    (["3*x - 2*y = 4", "5*x + 4*y = 14"], {"x": "2", "y": "1"}),
    (["x/2 + y = 3", "2*(x - 1) = y + 1"], {"x": "12/5", "y": "9/5"}),
    (["y = 2*x - 1", "3*x + y = 9"], {"x": "2", "y": "3"}),
    (["x + y = 10", "x - y = 2"], {"x": "6", "y": "4"}),
    (["4*x + 6*y = 2", "6*x - 4*y = 16"], {"x": "2", "y": "-1"}),
]
METODOS = ["sustitucion", "igualacion", "reduccion"]


def pasos(salida):
    """Los pasos numerados, cada uno con sus líneas."""
    texto = salida.split("PASO A PASO:")[1]
    return re.split(r"\n(?=\d+\. )", texto.strip())


# ---------------- Ecuaciones de primer grado ----------------

def test_despejar_con_parentesis_y_terminos_semejantes():
    lineas, valor = despejar(2 * sympy.UnevaluatedExpr(y + 1) + 3 * y, 12, y, "2*(y + 1) + 3*y")
    assert valor == 2
    assert lineas == [
        "Quitamos paréntesis (propiedad distributiva): 2*(y + 1) + 3*y = 2*y + 3*y + 2.",
        "Agrupamos términos semejantes: 2*y + 3*y = 5*y.",
        "Pasamos 2 a la derecha cambiando de signo (es restar 2 en los dos lados).",
        "Queda 5*y = 12 - 2.",
        "Operamos cada lado: 5*y = 10.",
        "Dividimos los dos lados entre 5: y = 10/5 = 2.",
    ]


def test_despejar_con_la_incognita_en_los_dos_lados():
    lineas, valor = despejar(6 - 3 * y / 2, y + 1, y)
    assert valor == 2
    assert "Pasamos y a la izquierda cambiando de signo (es restar y en los dos lados)." in lineas
    assert "Queda -3*y/2 - y = 1 - 6." in lineas
    assert "Operamos cada lado: -5*y/2 = -5." in lineas


def test_pasar_un_termino_negativo_es_sumar():
    lineas, valor = despejar(x - y, 1, x)
    assert valor == y + 1
    assert lineas[0] == "Pasamos -y a la derecha cambiando de signo (es sumar y en los dos lados)."


def test_sustituir_conserva_el_orden_escrito():
    assert sustituir(2 * x + 3 * y, {x: 3, y: 2}) == "2*3 + 3*2"
    assert sustituir(x - y, {x: 3, y: -2}) == "3 - (-2)"
    assert sustituir(2 * x + 3 * y, {x: y + 1}) == "2*(y + 1) + 3*y"
    assert comprobar([(x - y, 1)], {x: 3, y: 2}) == ["Ecuación 1: 3 - 2 = 1, y el lado derecho es 1: se cumple."]


# ---------------- Métodos clásicos ----------------

@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("ecuaciones, solucion", SISTEMAS)
def test_metodo_clasico_completo(core, ecuaciones, solucion, metodo):
    salida = core.ResolverSistemaEducativo(ecuaciones, metodo)
    assert salida.splitlines()[:3] == ["RESULTADO:", f"x = {solucion['x']}", f"y = {solucion['y']}"]
    lista = pasos(salida)
    assert lista[-1].startswith(f"{len(lista)}. Comprobación.")
    assert lista[-1].count(": se cumple.") == 2
    for paso in lista:
        assert "Regla: " in paso and "En este caso: " in paso and "Queda: " in paso, paso


def test_sustitucion_muestra_la_ecuacion_sustituida(core):
    salida = core.ResolverSistemaEducativo(["2*x + 3*y = 12", "x - y = 1"], "sustitucion")
    assert "elegimos la ecuación 2, x - y = 1, y despejamos x, porque su coeficiente es 1" in salida
    assert "Cambiamos x por (y + 1): 2*(y + 1) + 3*y = 12." in salida
    assert "Quitamos paréntesis (propiedad distributiva): 2*(y + 1) + 3*y = 2*y + 3*y + 2." in salida
    assert "Sustituimos y = 2: x = 2 + 1 = 3." in salida


def test_reduccion_multiplica_y_suma_termino_a_termino(core):
    salida = core.ResolverSistemaEducativo(["2*x + 3*y = 12", "x - y = 1"], "reduccion")
    assert "Multiplicamos la ecuación 1 por 1 y la ecuación 2 por (-2): 2*1 = 2 y 1*(-2) = -2, que son opuestos." in salida
    assert "Ecuación 2 por (-2): (-2)*(x - y) = (-2)*1, es decir -2*x + 2*y = -2." in salida
    assert "Términos en x: 2*x + (-2)*x = 0." in salida
    assert "Lado derecho: 12 + (-2) = 10." in salida


def test_reduccion_ordena_las_ecuaciones(core):
    salida = core.ResolverSistemaEducativo(["y = 2*x - 1", "3*x + y = 9"], "reduccion")
    assert "Ecuación 1: y = 2*x - 1 queda -2*x + y = -1." in salida
    assert "Operamos: 2*2 - 1 = 3." in salida


@pytest.mark.parametrize("ecuaciones, resultado, motivo", [
    (["x + y = 1", "x + y = 2"], "RESULTADO: Sin solución: SISTEMA INCOMPATIBLE", "se contradicen"),
    (["x + y = 1", "2*x + 2*y = 2"], "RESULTADO: Infinitas soluciones: SISTEMA INDETERMINADO", "dicen lo mismo"),
])
def test_clasico_sin_solucion_unica_se_explica(core, ecuaciones, resultado, motivo):
    salida = core.ResolverSistemaEducativo(ecuaciones, "sustitucion")
    assert salida.startswith(resultado)
    assert "Determinante de los coeficientes: 1*" in salida and motivo in salida


# ---------------- Gauss-Jordan ----------------

def test_gauss_cuenta_cada_elemento(core):
    salida = core.ResolverSistemaGauss(["2*x + y - z = 8", "-3*x - y + 2*z = -11", "-2*x + y + 2*z = -3"])
    assert salida.splitlines()[:4] == ["RESULTADO:", "x = 2", "y = 3", "z = -1"]
    assert "Ecuación 1: 2*x + y - z = 8 → fila [ 2, 1, -1 | 8 ]." in salida
    assert "F1 → F1/2: [2/2, 1/2, (-1)/2 | 8/2] = [ 1, 1/2, -1/2 | 4 ]." in salida
    assert ("F2 → F2 - (-3)*F1: [-3 - (-3)*1, -1 - (-3)*(1/2), 2 - (-3)*(-1/2) | -11 - (-3)*4] "
            "= [ 0, 1/2, 1/2 | 1 ].") in salida
    assert "F3 → (-1)*F3: [(-1)*0, (-1)*0, (-1)*(-1) | (-1)*1] = [ 0, 0, 1 | -1 ]." in salida
    assert "Fila 3: [ 0, 0, 1 | -1 ] significa z = -1." in salida
    assert pasos(salida)[-1].count(": se cumple.") == 3


def test_gauss_intercambia_para_un_pivote_comodo(core):
    salida = core.ResolverSistemaGauss(["2*x + y = 5", "x - y = 1"])
    assert "Intercambiar las filas 1 y 2" in salida
    assert "un pivote más cómodo que 2: con 1 o -1 no aparecen fracciones" in salida


def test_gauss_infinitas_explica_la_variable_libre(core):
    salida = core.ResolverSistemaGauss(["x + y + z = 2", "x - z = 1"])
    assert "Fila 1: x - z = 1, así que x = z + 1." in salida
    assert "z no tiene pivote: es libre, puede valer cualquier número." in salida


def test_gauss_cada_paso_tiene_regla_y_partes(core):
    for paso in pasos(core.ResolverSistemaGauss(["x + 2*y = 5", "3*x + 4*y = 6"])):
        assert "Regla: " in paso and "En este caso: " in paso and "Queda: " in paso, paso


# ---------------- Matriz inversa ----------------

def test_inversa_2x2_completa(core):
    salida = core.MatrizInversaCofactores("1 2\n3 4")
    assert salida.splitlines()[:3] == ["RESULTADO:", "[ -2, 1 ]", "[ 3/2, -1/2 ]"]
    assert "det(A) = 1*4 - 2*3 = 4 - 6 = -2." in salida
    # Todos los cofactores, no solo uno de ejemplo
    for c in ("C11", "C12", "C21", "C22"):
        assert f"{c}: quitamos la fila" in salida
    assert "Fila 2: (-3)/(-2) = 3/2; 1/(-2) = -1/2." in salida
    assert "Fila 1 por columna 1: 1*(-2) + 2*(3/2) = -2 + 3 = 1." in salida
    assert "A por A^(-1) es la identidad: la inversa es correcta." in salida


def test_inversa_3x3_desarrolla_el_determinante(core):
    salida = core.MatrizInversaCofactores("2 0 1\n1 1 0\n0 3 1")
    assert "det(A) = a11*C11 + a12*C12 + ... = 2*1 + 0*(-1) + 1*3 = 2 + 0 + 3 = 5." in salida
    assert salida.count(": quitamos la fila") == 3 + 9  # 3 en el determinante y 9 cofactores
    assert "M21 = 0*1 - 1*3 = 0 - 3 = -3" in salida


def test_inversa_de_matriz_singular_explica_el_determinante(core):
    salida = core.MatrizInversaCofactores("1 2\n2 4")
    assert salida.startswith("RESULTADO: No tiene inversa (determinante 0)")
    assert "det(A) = 1*4 - 2*2 = 4 - 4 = 0." in salida
    assert "habría que dividir entre 0" in salida
