"""
La interfaz decide si mostrar un diálogo de error mirando el prefijo del texto.
Estas pruebas aseguran que cada motor reporta sus fallos con un prefijo reconocido
(y que los resultados válidos no se confunden con errores). No abre ventanas.
"""
import pytest

from main import CalculadoraAccesible

PREFIJOS = CalculadoraAccesible.PREFIJOS_ERROR


def es_error(texto: str) -> bool:
    return texto.lstrip().lower().startswith(PREFIJOS)


@pytest.mark.parametrize("llamada", [
    lambda c: c.Evaluar("2+"),
    lambda c: c.Simplificar("(x+"),
    lambda c: c.Derivar("sin(x"),
    lambda c: c.calculo.RenderizarTexto(c.calculo.CalcularIntegral("5")),
    lambda c: c.CalcularLimite("sin(x", "x", "0"),
    lambda c: c.ResolverSistemaGauss(["x+y=1=2", "x-y=0"]),
    lambda c: c.ResolverSistemaEducativo(["x+y=1=2", "x-y=0"], "sustitucion"),
    lambda c: c.MatrizInversaCofactores("1 2\n2 4"),
], ids=["evaluar", "simplificar", "derivar", "integrar", "limite", "gauss", "clasico", "inversa"])
def test_errores_de_cada_motor_se_detectan(core, llamada):
    assert es_error(llamada(core))


@pytest.mark.parametrize("llamada", [
    lambda c: c.Evaluar("2+2"),
    lambda c: c.Derivar("x^2"),
    lambda c: c.CalcularLimite("abs(x)/x", "x", "0"),  # "No existe" es un resultado, no un error
    lambda c: c.ResolverSistemaGauss(["x+y=1", "x+y=2"]),  # sistema sin solución: también es un resultado
    lambda c: c.MatrizInversaCofactores("1 2\n3 4"),
], ids=["evaluar", "derivar", "limite-no-existe", "gauss-inconsistente", "inversa"])
def test_resultados_validos_no_son_errores(core, llamada):
    assert not es_error(llamada(core))
