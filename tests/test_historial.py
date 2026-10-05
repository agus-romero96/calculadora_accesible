import json

import pytest

import exportar
import i18n
from historial import Historial, describir


@pytest.fixture
def historial(core):
    h = Historial()
    h.agregar(core.derivar("x^2*sin(x)"))
    h.agregar(core.evaluar("2+"))  # los errores no se guardan
    h.agregar(core.sistema_gauss(["x + y = 10", "x - y = 2"]))
    h.agregar(core.integrar("x*exp(x)"))
    return h


# ---------------- Modelo ----------------

def test_guarda_solo_resultados_correctos_en_orden(historial):
    assert len(historial) == 3
    assert [r.operacion for r in historial.entradas()] == ["derivar", "gauss", "integrar"]


def test_numeracion_cronologica(historial):
    assert [historial.numero(r) for r in historial.entradas()] == [1, 2, 3]


def test_eliminar_y_renumerar(historial):
    gauss = historial.entradas()[1]
    historial.eliminar(gauss)
    assert len(historial) == 2
    assert [historial.numero(r) for r in historial.entradas()] == [1, 2]


def test_vaciar(historial):
    historial.vaciar()
    assert len(historial) == 0


def test_limite_descarta_las_mas_antiguas(core):
    h = Historial()
    h.MAXIMO = 3
    for n in range(5):
        h.agregar(core.evaluar(f"{n}+1"))
    assert [r.entrada for r in h.entradas()] == ["2+1", "3+1", "4+1"]


def test_entradas_es_una_copia(historial):
    historial.entradas().clear()
    assert len(historial) == 3


def test_describir(historial):
    gauss = historial.entradas()[1]
    assert describir(gauss, 2) == "2. Sistema de ecuaciones (Gauss-Jordan): x + y = 10; x - y = 2 → x = 6, y = 4"


def test_describir_acorta_resultados_largos(core):
    res = core.derivada_enecima("exp(x)*sin(x)*cos(x)*tan(x)*log(x)", "x", 3)
    assert describir(res, 1).endswith("…")


def test_describir_en_ingles(historial):
    i18n.establecer_idioma("en")
    try:
        assert describir(historial.entradas()[0], 1).startswith("1. Derivative: x^2*sin(x) → ")
    finally:
        i18n.establecer_idioma("es")


# ---------------- Exportar el historial ----------------

@pytest.mark.parametrize("formato", sorted(exportar.FORMATOS))
def test_exportar_historial_incluye_todas_las_operaciones(historial, formato):
    contenido = exportar.exportar_historial(historial.entradas(), formato)
    for r in historial.entradas():
        assert r.texto.splitlines()[0] in contenido or formato == "json"


def test_historial_json(historial):
    datos = json.loads(exportar.exportar_historial(historial.entradas(), "json"))
    assert [e["operation"] for e in datos["entries"]] == ["derivar", "gauss", "integrar"]
    assert datos["entries"][1]["result"]["text"] == "x = 6, y = 4"


def test_historial_markdown_numerado(historial):
    md = exportar.exportar_historial(historial.entradas(), "md")
    assert md.startswith("# Historial de operaciones")
    assert "## 1. Derivada" in md and "## 2. Sistema de ecuaciones (Gauss-Jordan)" in md
    assert "### Explicación paso a paso" in md


def test_historial_html_secciones_y_mathml(historial):
    pagina = exportar.exportar_historial(historial.entradas(), "html")
    assert pagina.count("<section") == 3
    assert pagina.count("<math ") == 3
    assert "<h2>3. Integral indefinida</h2>" in pagina


def test_historial_html_marca_el_idioma_de_cada_operacion(core):
    h = Historial()
    h.agregar(core.derivar("x^3"))
    i18n.establecer_idioma("en")
    try:
        h.agregar(core.derivar("x^4"))
        pagina = exportar.exportar_historial(h.entradas(), "html")
    finally:
        i18n.establecer_idioma("es")
    assert '<html lang="en">' in pagina
    assert '<section lang="es">' in pagina  # la primera se calculó en español


def test_historial_latex(historial):
    tex = exportar.exportar_historial(historial.entradas(), "tex")
    assert r"\section*{Historial de operaciones}" in tex
    assert tex.count(r"\subsection*{") == 3
    assert tex.count(r"\begin{document}") == 1


def test_historial_texto(historial):
    txt = exportar.exportar_historial(historial.entradas(), "txt")
    assert txt.startswith("HISTORIAL DE OPERACIONES")
    assert "3. Integral indefinida" in txt


def test_guardar_historial(historial, tmp_path):
    ruta = tmp_path / "historial.html"
    exportar.guardar_historial(historial.entradas(), "html", str(ruta))
    assert ruta.read_text(encoding="utf-8") == exportar.exportar_historial(historial.entradas(), "html")
