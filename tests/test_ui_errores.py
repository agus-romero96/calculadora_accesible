"""
La interfaz muestra un diálogo de error cuando el resultado trae es_error=True.
Estas pruebas aseguran que cada motor marca sus fallos (en cualquier idioma) y que
los resultados válidos no se confunden con errores. No abre ventanas.
"""
import pytest

import i18n

ERRORES = [
    lambda c: c.evaluar("2+"),
    lambda c: c.simplificar("(x+"),
    lambda c: c.derivar("sin(x"),
    lambda c: c.integrar("5"),
    lambda c: c.integral_definida("x^2", None, "0", ""),
    lambda c: c.limite("sin(x", "x", "0"),
    lambda c: c.sistema_gauss(["x+y=1=2", "x-y=0"]),
    lambda c: c.sistema_clasico(["x+y=1=2", "x-y=0"], "sustitucion"),
    lambda c: c.inversa("1 2\n2 4"),
]
IDS_ERRORES = ["evaluar", "simplificar", "derivar", "integrar", "integral-definida", "limite", "gauss", "clasico", "inversa"]

VALIDOS = [
    lambda c: c.evaluar("2+2"),
    lambda c: c.derivar("x^2"),
    lambda c: c.limite("abs(x)/x", "x", "0"),  # "No existe" es un resultado, no un error
    lambda c: c.integral_definida("1/x^2", None, "-1", "1"),  # diverge: también es un resultado
    lambda c: c.sistema_gauss(["x+y=1", "x+y=2"]),  # sistema sin solución: también es un resultado
    lambda c: c.inversa("1 2\n3 4"),
]
IDS_VALIDOS = ["evaluar", "derivar", "limite-no-existe", "integral-diverge", "gauss-inconsistente", "inversa"]


@pytest.fixture(params=["es", "en"])
def idioma(request):
    i18n.establecer_idioma(request.param)
    yield request.param
    i18n.establecer_idioma("es")


@pytest.mark.parametrize("llamada", ERRORES, ids=IDS_ERRORES)
def test_errores_de_cada_motor_se_detectan(core, idioma, llamada):
    res = llamada(core)
    assert res.es_error
    assert res.texto.strip()  # el diálogo debe tener un mensaje


@pytest.mark.parametrize("llamada", VALIDOS, ids=IDS_VALIDOS)
def test_resultados_validos_no_son_errores(core, idioma, llamada):
    assert not llamada(core).es_error
