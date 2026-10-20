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


@pytest.mark.parametrize("expr,lado_ausente", [
    ("sqrt(x)", "-"), ("log(x)", "-"), ("sqrt(-x)", "+"),
    ("asin(1+x)", "+"), ("sqrt(x)/sqrt(x)", "-"), ("0*log(x)", "-"),
])
def test_bilateral_exige_dominio_original_por_ambos_lados(core, expr, lado_ausente):
    res = core.limite(expr, "x", "0")
    assert res.valor is None
    assert res.texto.startswith("RESULTADO: No existe el límite bilateral real\n")
    assert "se calcula el límite bilateral real: se requieren ambos lados" in res.texto
    assert "La función original no está definida en un entorno real" in res.texto
    assert "(x -> 0" + lado_ausente + ")" in res.texto
    assert "PASO A PASO:" not in res.texto


@pytest.mark.parametrize("expr,valor", [
    ("sqrt(x^2)", sp.S.Zero), ("1/x^2", sp.oo),
    ("sqrt(1+x)", sp.S.One), ("sin(x)/x", sp.S.One),
])
def test_bilateral_con_dominio_en_ambos_lados_se_conserva(core, expr, valor):
    res = core.limite(expr, "x", "0")
    assert res.valor == valor
    assert "se calcula el límite bilateral real: se requieren ambos lados" in res.texto


def test_bilateral_con_dominio_no_certificado_es_inconcluyente(core):
    res = core.limite("tan(1/x)", "x", "0")
    assert res.valor is None
    assert res.texto.startswith("RESULTADO: No concluyente\n")
    assert "No se puede verificar" in res.texto
    assert "La función original no está definida" not in res.texto
    assert "se calcula el límite bilateral real: se requieren ambos lados" in res.texto


@pytest.mark.parametrize("estados,resultado", [
    ((None, True), "No concluyente"), ((True, None), "No concluyente"),
    ((None, False), "No existe el límite bilateral real"),
    ((False, None), "No existe el límite bilateral real"),
])
def test_bilateral_distingue_ausencia_de_incertidumbre_y_no_consulta_motor(core, monkeypatch, estados, resultado):
    import calculo.router as modulo

    consultados = []
    def validar(original, var, punto, lado):
        consultados.append(lado)
        return estados[0 if lado == "-" else 1]

    llamadas_motor = []
    def registrar(*args, **kwargs):
        llamadas_motor.append(True)
        return False

    monkeypatch.setattr(core.router, "_lado_real", validar)
    for estrategia in core.router.estrategias:
        monkeypatch.setattr(estrategia, "puede_resolver", registrar)
    monkeypatch.setattr(modulo, "limite_seguro", registrar)
    res = core.limite("x", "x", "0")
    assert consultados == ["-", "+"]
    assert not llamadas_motor
    assert res.valor is None
    assert res.texto.startswith("RESULTADO: " + resultado + "\n")
    assert "No se puede verificar" in res.texto
    assert ("La función original no está definida" in res.texto) == (False in estados)
