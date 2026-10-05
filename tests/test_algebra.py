import sympy as sp
import pytest


# ---------------- Gauss-Jordan ----------------

def test_gauss_solucion_unica(core):
    salida = core.ResolverSistemaGauss(["x + y = 10", "x - y = 2"])
    assert "CONCLUSIÓN: UNICA" in salida
    assert "x = 6" in salida and "y = 4" in salida


def test_gauss_3x3(core):
    salida = core.ResolverSistemaGauss(["x + y + z = 6", "2x - y + z = 3", "x + 2y - z = 2"])
    assert "CONCLUSIÓN: UNICA" in salida
    assert "x = 1" in salida and "y = 2" in salida and "z = 3" in salida


def test_gauss_entrada_matricial(core):
    salida = core.ResolverSistemaGauss(["[[1,1,10],[1,-1,2]]"])
    assert "x = 6" in salida and "y = 4" in salida


def test_gauss_infinitas_soluciones(core):
    salida = core.ResolverSistemaGauss(["x + y = 1", "2x + 2y = 2"])
    assert "CONCLUSIÓN: INFINITA" in salida
    assert "Grados de libertad: 1" in salida


def test_gauss_sin_solucion(core):
    salida = core.ResolverSistemaGauss(["x + y = 1", "x + y = 2"])
    assert "CONCLUSIÓN: INCONSISTENTE" in salida


def test_gauss_rechaza_doble_igual(core):
    # Regresión: antes descartaba en silencio todo lo que había después del segundo '='
    salida = core.ResolverSistemaGauss(["x+y=1=2", "x-y=0"])
    assert salida.startswith("Error")
    assert "exactamente un signo '='" in salida


# ---------------- Métodos clásicos 2x2 ----------------

@pytest.mark.parametrize("metodo, nombre", [("sustitucion", "Sustitución"), ("igualacion", "Igualación"), ("reduccion", "Reducción")])
def test_sistemas_clasicos(core, metodo, nombre):
    salida = core.ResolverSistemaEducativo(["x + y = 10", "x - y = 2"], metodo)
    assert f"RESOLUCIÓN POR {nombre.upper()}" in salida
    assert salida.rstrip().endswith("x = 6\ny = 4")


def test_sistema_clasico_incompatible(core):
    salida = core.ResolverSistemaEducativo(["x + y = 1", "x + y = 2"], "sustitucion")
    assert "INCOMPATIBLE" in salida


def test_sistema_clasico_rechaza_doble_igual(core):
    salida = core.ResolverSistemaEducativo(["x+y=1=2", "x-y=0"], "sustitucion")
    assert salida.startswith("Error")


# ---------------- Inversa por cofactores ----------------

@pytest.mark.parametrize("entrada", ["1 2\n3 4", "1, 2\n3, 4", "[[1,2],[3,4]]"])
def test_inversa_formatos_de_entrada(core, entrada):
    res = core.matrices.CalcularInversaCofactores(entrada)
    assert res.es_posible
    assert res.matriz_inversa == sp.Matrix([[-2, 1], [sp.Rational(3, 2), sp.Rational(-1, 2)]])


def test_inversa_3x3_es_inversa(core):
    res = core.matrices.CalcularInversaCofactores("2 0 1\n1 3 2\n1 1 2")  # det = 6
    assert res.es_posible
    assert res.matriz_original * res.matriz_inversa == sp.eye(3)


@pytest.mark.parametrize("entrada, motivo", [
    ("1 2\n2 4", "singular"),
    ("1 2 3\n4 5 6", "no es cuadrada"),
    ("1 0 0 0 0\n0 1 0 0 0\n0 0 1 0 0\n0 0 0 1 0\n0 0 0 0 1", "Gauss-Jordan"),
])
def test_inversa_casos_no_validos(core, entrada, motivo):
    res = core.matrices.CalcularInversaCofactores(entrada)
    assert not res.es_posible
    assert motivo in res.mensaje_error
