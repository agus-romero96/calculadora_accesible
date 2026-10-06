"""
Registro de operaciones (puente.REGISTRO): cada entrada debe poder calcularse, tener
menú y datos válidos, y sus atajos no deben chocar con los de otras opciones.
"""
import os
import re
import string

import pytest

from conftest import RAIZ
from puente import OPERACION, OPERACIONES, REGISTRO, CoreMatematico

# Argumentos de ejemplo de cada operación, en el orden en que la interfaz los pasa al
# método (la variante del submenú va al final). Una operación nueva debe añadirse aquí.
EJEMPLOS = {
    "evaluar": ("1/3+1/6",),
    "simplificar": ("x + x",),
    "factorizar": ("x^2-9",),
    "derivar": ("x^2", None),
    "derivada_n": ("x^5", "x", 3),
    "integrar": ("x", None),
    "limite": ("sin(x)/x", "x", "0"),
    "gauss": (["x + y = 10", "x - y = 2"],),
    "sistema_clasico": (["x + y = 10", "x - y = 2"],),
    "inversa": ("1 2\n3 4",),
}

# Marcadores que rellena cada tipo de datos en la descripción ("Calculando ...")
MARCADORES_DE_DATOS = {"variable_orden": {"orden"}}


def marcadores(texto):
    return {campo for _, campo, _, _ in string.Formatter().parse(texto) if campo}


def test_claves_unicas_y_operaciones_derivadas():
    claves = [op.clave for op in REGISTRO]
    assert len(claves) == len(set(claves))
    assert OPERACIONES == {op.clave: op.nombre for op in REGISTRO}
    assert set(OPERACION) == set(claves)


def test_cada_operacion_tiene_ejemplo():
    assert set(EJEMPLOS) == set(OPERACION)


@pytest.mark.parametrize("op", REGISTRO, ids=lambda op: op.clave)
def test_metodo_devuelve_resultado_con_su_clave(core, op):
    """El método calcula y el resultado lleva la clave del registro (historial y exportación)."""
    metodo = getattr(CoreMatematico, op.metodo, None)
    assert callable(metodo), f"CoreMatematico no tiene el método {op.metodo!r}"
    variantes = list(op.variantes) or [None]
    for variante in variantes:
        args = EJEMPLOS[op.clave] + ((variante,) if variante else ())
        res = getattr(core, op.metodo)(*args)
        assert not res.es_error, res.texto
        assert res.operacion == op.clave


@pytest.mark.parametrize("op", REGISTRO, ids=lambda op: op.clave)
def test_menu_y_descripcion(op):
    if op.menu is not None:
        assert op.etiqueta, "una operación con menú necesita etiqueta"
    if op.datos == "expresion_variable":
        assert op.verbo, "hace falta el verbo para preguntar la variable"
    disponibles = MARCADORES_DE_DATOS.get(op.datos, set()) | ({"metodo"} if op.variantes else set())
    assert marcadores(op.descripcion) <= disponibles


def test_datos_y_menus_existen_en_la_interfaz():
    wx = pytest.importorskip("wx")  # noqa: F841
    import main
    for op in REGISTRO:
        assert op.datos in main.CalculadoraAccesible.PEDIR_DATOS, op.clave
        assert op.menu is None or op.menu in main.CalculadoraAccesible.MENUS, op.clave


def test_atajos_sin_repetir():
    """Los atajos del registro y los fijos de main.py (Resultado, Historial, F1...) son distintos."""
    fuente = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    fijos = re.findall(r'"\\?t?((?:Ctrl|Alt)\+[^"]+|F\d+)"', fuente)
    atajos = [op.atajo.lower() for op in REGISTRO if op.atajo] + [a.lower() for a in fijos]
    repetidos = {a for a in atajos if atajos.count(a) > 1}
    assert not repetidos, repetidos
    assert len(fijos) >= 8  # si baja, la búsqueda en main.py dejó de funcionar
