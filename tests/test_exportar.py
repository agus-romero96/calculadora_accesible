import json
import xml.etree.ElementTree as ET

import pytest

import exportar
import i18n

RESULTADOS = {
    "integral": lambda c: c.integrar("x*exp(x)"),
    "derivada": lambda c: c.derivar("x^2*sin(x)"),
    "derivada_n": lambda c: c.derivada_enecima("x^5", "x", 3),
    "limite": lambda c: c.limite("sin(x)/x", "x", "0"),
    "limite_no_existe": lambda c: c.limite("abs(x)/x", "x", "0"),
    "limite_lateral": lambda c: c.limite("1/x", "x", "0+"),
    "gauss": lambda c: c.sistema_gauss(["x + y = 10", "x - y = 2"]),
    "gauss_sin_solucion": lambda c: c.sistema_gauss(["x + y = 1", "x + y = 2"]),
    "gauss_infinitas": lambda c: c.sistema_gauss(["x + y = 1", "2x + 2y = 2"]),
    "clasico": lambda c: c.sistema_clasico(["x + y = 10", "x - y = 2"], "reduccion"),
    "inversa": lambda c: c.inversa("1 2\n3 4"),
    "evaluar": lambda c: c.evaluar("1/3+1/6"),
    "evaluar_decimal": lambda c: c.evaluar("2*pi"),
    "factorizar": lambda c: c.factorizar("x^2-9"),
}


@pytest.fixture(params=sorted(RESULTADOS))
def resultado(request, core):
    return RESULTADOS[request.param](core)


@pytest.mark.parametrize("formato", sorted(exportar.FORMATOS))
def test_todos_los_formatos_se_generan(resultado, formato):
    contenido = exportar.exportar(resultado, formato)
    assert contenido.strip()


def test_json_valido_y_completo(resultado):
    datos = json.loads(exportar.a_json(resultado))
    assert datos["operation"] == resultado.operacion
    assert datos["input"] == resultado.entrada
    assert datos["result"]["text"] == exportar.resultado_corto(resultado)
    assert datos["explanation"] == resultado.texto.rstrip().splitlines()


def test_mathml_es_xml_valido_y_sin_mfenced(resultado):
    # XML estricto: sin entidades con nombre de HTML (&pi;), que fallarían al pegar en otro programa
    marcado = exportar.mathml(resultado)
    raiz = ET.fromstring(marcado)
    assert raiz.tag.endswith("math")
    assert "mfenced" not in marcado  # los navegadores actuales no lo dibujan


def test_html_accesible(resultado):
    pagina = exportar.a_html(resultado)
    assert f'<html lang="{resultado.idioma}">' in pagina
    assert "<math " in pagina and "alttext=" in pagina
    assert "<h1>" in pagina and "<main>" in pagina


@pytest.mark.parametrize("nombre, esperado", [
    ("integral", r"\int x e^{x}\, dx = \left(x - 1\right) e^{x} + C"),
    ("limite", r"\lim_{x \to 0}\left(\frac{\sin{\left(x \right)}}{x}\right) = 1"),
    ("limite_lateral", r"\lim_{x \to 0^+} \frac{1}{x} = \infty"),
    ("evaluar", r"\frac{1}{6} + \frac{1}{3} = \frac{1}{2}"),
    ("factorizar", r"x^{2} - 9 = \left(x - 3\right) \left(x + 3\right)"),
    ("derivada_n", r"\frac{d^{3}}{d x^{3}} x^{5} = 60 x^{2}"),
])
def test_latex_planteamiento_igual_resultado(core, nombre, esperado):
    assert exportar.latex(RESULTADOS[nombre](core)) == esperado


def test_latex_decimal_usa_aproximado(core):
    assert r"2 \pi \approx 6.28" in exportar.latex(core.evaluar("2*pi"))


def test_latex_sistema(core):
    texto = exportar.latex(core.sistema_gauss(["x + y = 10", "x - y = 2"]))
    assert texto.startswith(r"\begin{cases} x + y = 10 \\ x - y = 2 \end{cases}")
    assert texto.endswith(r"x = 6,\quad y = 4")


@pytest.mark.parametrize("nombre, esperado", [
    ("integral", "(x - 1)*exp(x) + C"),
    ("gauss", "x = 6, y = 4"),
    ("gauss_sin_solucion", "Sin solución"),
    ("inversa", "[-2, 1]; [3/2, -1/2]"),
    ("limite_no_existe", "No existe (los límites laterales no coinciden)"),
])
def test_resultado_corto(core, nombre, esperado):
    assert exportar.resultado_corto(RESULTADOS[nombre](core)) == esperado


def test_error_no_tiene_resultado(core):
    res = core.evaluar("2+")
    assert res.es_error
    assert exportar.resultado_corto(res) == ""
    assert json.loads(exportar.a_json(res))["result"] is None


def test_exportacion_en_ingles(core):
    i18n.establecer_idioma("en")
    try:
        res = core.integrar("x*exp(x)")
        md = exportar.a_markdown(res)
        assert md.startswith("# Indefinite integral")
        assert "## Step-by-step explanation" in md
        assert '<html lang="en">' in exportar.a_html(res)
        assert json.loads(exportar.a_json(res))["language"] == "en"
    finally:
        i18n.establecer_idioma("es")


def test_guardar_archivo(core, tmp_path):
    res = core.derivar("x^3")
    for formato, (_, extension) in exportar.FORMATOS.items():
        ruta = tmp_path / f"resultado.{extension}"
        exportar.guardar(res, formato, str(ruta))
        assert ruta.read_text(encoding="utf-8") == exportar.exportar(res, formato)


# ---------------- Solo el resultado (sin paso a paso) ----------------

def test_resumen_de_cada_resultado(resultado):
    texto = exportar.resumen(resultado)
    lineas = texto.splitlines()
    assert lineas[0].startswith("RESULTADO:")
    assert f"Operación: {exportar.nombre_operacion(resultado)}" in lineas
    assert any(linea.startswith("Entrada: ") for linea in lineas)
    assert len(texto) < len(resultado.texto) or resultado.operacion == "evaluar"


@pytest.mark.parametrize("operacion, esperado", [
    (lambda c: c.derivar("x^2*sin(x)"),
     ["RESULTADO: x*(x*cos(x) + 2*sin(x))", "Operación: Derivada", "Entrada: x^2*sin(x)", "Variable: x"]),
    (lambda c: c.integrar("x*exp(x)"),
     ["RESULTADO: (x - 1)*exp(x) + C", "Operación: Integral indefinida", "Entrada: x*exp(x)", "Variable: x"]),
    (lambda c: c.limite("abs(x)/x", "x", "0"),
     ["RESULTADO: No existe (los límites laterales no coinciden)", "Operación: Límite", "Entrada: abs(x)/x",
      "Variable: x", "Tendencia: 0"]),
    # Soluciones y filas, una por línea
    (lambda c: c.sistema_gauss(["x + y = 10", "x - y = 2"]),
     ["RESULTADO:", "x = 6", "y = 4", "Operación: Sistema de ecuaciones (Gauss-Jordan)",
      "Entrada: x + y = 10; x - y = 2"]),
    (lambda c: c.inversa("1 2\n3 4"),
     ["RESULTADO:", "[ -2, 1 ]", "[ 3/2, -1/2 ]", "Operación: Matriz inversa (cofactores)", "Entrada: 1 2; 3 4"]),
    # El método ya está en el nombre de la operación: no se repite su código interno
    (lambda c: c.sistema_clasico(["x + y = 1", "x + y = 2"], "reduccion"),
     ["RESULTADO: Sin solución", "Operación: Sistema 2x2 (método clásico)", "Entrada: x + y = 1; x + y = 2"]),
])
def test_resumen(core, operacion, esperado):
    assert exportar.resumen(operacion(core)).splitlines() == esperado


def test_resumen_de_un_error_es_el_mensaje(core):
    res = core.derivar("sin(x")
    assert res.es_error and exportar.resumen(res) == res.texto


def test_resumen_en_ingles(core):
    i18n.establecer_idioma("en")
    try:
        texto = exportar.resumen(core.sistema_gauss(["x + y = 10", "x - y = 2"]))
    finally:
        i18n.establecer_idioma("es")
    assert texto.splitlines()[:3] == ["RESULT:", "x = 6", "y = 4"]
    assert "Operation: System of equations (Gauss-Jordan)" in texto
