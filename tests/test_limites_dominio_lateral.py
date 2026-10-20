"""El límite lateral real requiere dominio original por el lado solicitado."""
import pytest
import sympy as sp


INVALIDOS = [
    ("sqrt(x)", "0-"), ("log(x)", "0-"),
    ("sqrt(-x)", "0+"), ("asin(1+x)", "0+"),
    ("sqrt(x-2)", "2-"), ("acos(1+x)", "0+"),
    ("log(-x)", "0+"), ("sqrt(x)/sqrt(x)", "0-"),
    ("0*log(x)", "0-"), ("sqrt(x)^0", "0-"),
    ("exp(log(x))", "0-"), ("sqrt(x-a)", "a-"),
    ("sqrt(x)-sqrt(x)", "0-"),
]


@pytest.mark.parametrize("expr,tend", INVALIDOS)
def test_rechaza_lado_fuera_del_dominio_original(core, expr, tend):
    res = core.limite(expr, "x", tend)
    assert res.valor is None
    assert res.texto.startswith("RESULTADO: No existe el límite lateral real\n")
    assert "La función original no está definida en un entorno real por el lado solicitado." in res.texto
    assert "cuando x -> " + tend in res.texto
    assert "PASO A PASO:" not in res.texto
    assert "SymPy" not in res.texto


@pytest.mark.parametrize("expr,tend,valor", [
    ("sqrt(x)", "0+", sp.S.Zero), ("log(x)", "0+", -sp.oo),
    ("sqrt(-x)", "0-", sp.S.Zero), ("asin(1+x)", "0-", sp.pi/2),
    ("sqrt(x-2)", "2+", sp.S.Zero), ("acos(1+x)", "0-", sp.S.Zero),
    ("log(-x)", "0-", -sp.oo), ("sqrt(x)/sqrt(x)", "0+", sp.S.One),
    ("0*log(x)", "0+", sp.S.Zero), ("sqrt(x)^0", "0+", sp.S.One),
    ("exp(log(x))", "0+", sp.S.Zero), ("sqrt(x-a)", "a+", sp.S.Zero),
    ("1/x", "0+", sp.oo), ("1/x", "0-", -sp.oo),
    ("sqrt(x+1)", "0-", sp.S.One), ("x^x", "0+", sp.S.One),
    ("sqrt(x)-sqrt(x)", "0+", sp.S.Zero),
])
def test_acepta_lado_con_entorno_real(core, expr, tend, valor):
    res = core.limite(expr, "x", tend)
    assert not res.es_error
    assert res.valor == valor
    assert "No concluyente" not in res.texto
    assert "No existe el límite lateral real" not in res.texto


@pytest.mark.parametrize("indeterminado", [False, True])
def test_validacion_precede_todas_las_estrategias_y_el_respaldo(core, monkeypatch, indeterminado):
    import calculo.router as modulo

    llamadas = []
    def registrar(*args, **kwargs):
        llamadas.append(True)
        return False

    for estrategia in core.router.estrategias:
        monkeypatch.setattr(estrategia, "puede_resolver", registrar)
    monkeypatch.setattr(modulo, "limite_seguro", registrar)
    if indeterminado:
        def sin_dominio(*args):
            raise NotImplementedError("Dominio no soportado")
        monkeypatch.setattr(modulo, "dominio_funciones_originales", sin_dominio)
    res = core.limite("sqrt(x)", "x", "0-")
    assert not llamadas
    assert res.valor is None
    if indeterminado:
        assert res.texto.startswith("RESULTADO: No concluyente\n")
        assert "No se puede verificar" in res.texto
        assert "No existe el límite lateral real" not in res.texto


def test_dominio_sin_entorno_certificado_no_se_declara_valido(core):
    res = core.limite("tan(1/x)", "x", "0+")
    assert res.valor is None
    assert res.texto.startswith("RESULTADO: No concluyente\n")
    assert "No se puede verificar" in res.texto
