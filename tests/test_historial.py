import json
import os

import pytest
import sympy

import configuracion
import exportar
import i18n
from historial import Historial, cargar, describir, guardar, ruta_historial
from parser_matematico import ParserMatematico
from test_exportar import RESULTADOS


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


def test_guardar_historial(historial, tmp_path, monkeypatch):
    # Hora fija: el pie lleva la hora al segundo, y las dos exportaciones podían caer
    # a ambos lados de un cambio de segundo
    monkeypatch.setattr(exportar, "_ahora", lambda: "2026-10-10T12:00:00")
    ruta = tmp_path / "historial.html"
    exportar.guardar_historial(historial.entradas(), "html", str(ruta))
    assert ruta.read_text(encoding="utf-8") == exportar.exportar_historial(historial.entradas(), "html")


# ---------------- Guardar entre sesiones ----------------

# Además de los tipos de resultado de test_exportar, entradas que el parser deja sin evaluar
RESULTADOS_PERSISTENCIA = {
    **RESULTADOS,
    "evaluar_sin_evaluar": lambda c: c.evaluar("sin(pi)+1/2"),
    "derivada_n_seno": lambda c: c.derivada_enecima("sin(2*x)", "x", 4),
    "limite_infinito": lambda c: c.limite("(3x^2+1)/(x^2-2)", "x", "oo"),
    "integral_abs": lambda c: c.integrar("abs(x)"),
    "integral_definida_pi": lambda c: c.integral_definida("1/(1+x^2)", None, "-oo", "oo"),
    "integral_definida_parametro": lambda c: c.integral_definida("x", None, "0", "k"),
    # Rectas tangente y normal (lista de Eq, una vertical)
    "tangente": lambda c: c.recta_tangente("x^3 - 2*x", None, "1"),
    "tangente_horizontal": lambda c: c.recta_tangente("x^2", None, "0"),
    # Estudio de extremos (un dict con puntos, extremos e intervalos)
    "extremos": lambda c: c.extremos("x^3 - 3*x"),
    "extremos_cociente": lambda c: c.extremos("x^2/(x-1)"),
    # Conjuntos solución y relaciones sin evaluar (Eq, Le, Gt...)
    "ecuacion_racional": lambda c: c.ecuacion("x^2/(x-1) = 1/(x-1)"),
    "ecuacion_irracional": lambda c: c.ecuacion("2*x^2 - 4*x - 1 = 0"),
    "inecuacion_union": lambda c: c.ecuacion("-x^2 + 2*x + 3 < 0"),
    "inecuacion_intervalo": lambda c: c.ecuacion("x^2 - 4 <= 0"),
    "inecuacion_sin_solucion": lambda c: c.ecuacion("x^2 + 1 < 0"),
}


def _ida_y_vuelta(res, tmp_path):
    ruta = str(tmp_path / "historial.json")
    guardar([res], ruta)
    (recuperado,) = cargar(ruta)
    return recuperado


@pytest.mark.parametrize("nombre", sorted(RESULTADOS_PERSISTENCIA))
def test_guardar_y_cargar_conserva_la_operacion_exacta(core, tmp_path, nombre):
    res = RESULTADOS_PERSISTENCIA[nombre](core)
    assert not res.es_error
    recuperado = _ida_y_vuelta(res, tmp_path)
    for campo in ("operacion", "entrada", "texto", "parametros", "mas_constante", "idioma", "fecha"):
        assert getattr(recuperado, campo) == getattr(res, campo), campo
    # Los objetos SymPy, con la misma estructura (el planteamiento sigue sin evaluar)
    for campo in ("valor", "expresion", "planteamiento"):
        assert sympy.srepr(getattr(recuperado, campo)) == sympy.srepr(getattr(res, campo)), campo
    assert exportar.latex(recuperado) == exportar.latex(res)
    assert exportar.mathml(recuperado) == exportar.mathml(res)
    assert exportar.resultado_corto(recuperado) == exportar.resultado_corto(res)


def test_las_variables_siguen_siendo_reales(core, tmp_path):
    recuperado = _ida_y_vuelta(core.derivar("x^3"), tmp_path)
    assert ParserMatematico.simbolo("x") in recuperado.valor.free_symbols


def test_historial_con_ruta_se_conserva(core, tmp_path):
    ruta = str(tmp_path / "carpeta" / "historial.json")  # la carpeta se crea al guardar
    h = Historial(ruta)
    h.agregar(core.derivar("x^2"))
    h.agregar(core.evaluar("2+"))  # los errores no se guardan
    h.agregar(core.factorizar("x^2-9"))
    h.agregar(core.evaluar("1/3+1/6"))
    assert [r.entrada for r in Historial(ruta).entradas()] == ["x^2", "x^2-9", "1/3+1/6"]

    h.eliminar(h.entradas()[1])
    assert [r.entrada for r in Historial(ruta).entradas()] == ["x^2", "1/3+1/6"]

    h.vaciar()
    assert len(Historial(ruta)) == 0


def test_al_cargar_se_respeta_el_maximo(core, tmp_path, monkeypatch):
    ruta = str(tmp_path / "historial.json")
    guardar([core.evaluar(f"{n}+1") for n in range(5)], ruta)
    monkeypatch.setattr(Historial, "MAXIMO", 3)
    assert [r.entrada for r in Historial(ruta).entradas()] == ["2+1", "3+1", "4+1"]


@pytest.mark.parametrize("contenido", ["", "no es json", "[]", '{"version": 99, "entradas": []}',
                                       '{"version": 1}'])
def test_archivo_ilegible_da_historial_vacio(tmp_path, contenido):
    ruta = tmp_path / "historial.json"
    ruta.write_text(contenido, encoding="utf-8")
    assert len(Historial(str(ruta))) == 0


def test_sin_archivo_da_historial_vacio(tmp_path):
    assert len(Historial(str(tmp_path / "no_existe.json"))) == 0


def test_entrada_danada_se_descarta(core, tmp_path):
    ruta = tmp_path / "historial.json"
    guardar([core.derivar("x^2"), core.derivar("x^3")], str(ruta))
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    del datos["entradas"][0]["texto"]
    datos["entradas"].append({"operacion": "operacion_desconocida"})
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert [r.entrada for r in cargar(str(ruta))] == ["x^3"]


@pytest.mark.parametrize("formato", sorted(exportar.FORMATOS))
def test_sin_objetos_sympy_se_conserva_el_texto(core, tmp_path, formato):
    # Por ejemplo, un historial guardado con otra versión de SymPy que ya no se puede leer
    res = core.integrar("x*exp(x)")
    ruta = tmp_path / "historial.json"
    guardar([res], str(ruta))
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["entradas"][0]["sympy"] = "no es pickle"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    (recuperado,) = cargar(str(ruta))
    assert recuperado.texto == res.texto and recuperado.valor is None
    assert describir(recuperado, 1).startswith("1. Integral indefinida: x*exp(x)")
    assert exportar.exportar(recuperado, formato).strip()


def test_no_poder_guardar_no_es_un_error(core, tmp_path):
    archivo = tmp_path / "archivo"
    archivo.write_text("", encoding="utf-8")
    h = Historial(str(archivo / "historial.json"))  # la "carpeta" es un archivo
    h.agregar(core.derivar("x^2"))
    assert len(h) == 1


def test_ruta_junto_a_la_configuracion():
    assert os.path.dirname(ruta_historial()) == os.path.dirname(configuracion.ruta_configuracion())
    assert os.path.basename(ruta_historial()) == "historial.json"


def test_historiales_anteriores_siguen_legibles():
    # Los historiales guardados antes de crear serializacion.py nombran la función de
    # reconstrucción como "historial._sin_evaluar" dentro del pickle
    import io
    import pickle

    import serializacion
    lector = pickle.Unpickler(io.BytesIO(b""))
    assert lector.find_class("historial", "_sin_evaluar") is serializacion._sin_evaluar
