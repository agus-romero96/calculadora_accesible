"""
Copiar y exportar resultados en distintos formatos.

Formatos de archivo: texto plano, Markdown, LaTeX, HTML con MathML y JSON.
Para el portapapeles: el resultado en una línea, la explicación completa, LaTeX o MathML.

Todo parte de un ResultadoOperacion (puente.py): texto accesible, valor SymPy y
"planteamiento" (el problema sin evaluar: Derivative, Integral, Limit...), de modo
que LaTeX y MathML muestran "planteamiento = resultado" como en un libro.

El HTML con MathML es el formato más accesible: NVDA (con MathCAT) y JAWS pueden
leer y explorar las fórmulas, y cualquier navegador lo abre.
"""
import html
import json
import re
from datetime import datetime
from typing import Any, List, Optional

import sympy

from _version import __version__
from calculo.calculo import humanizar_integral
from calculo.router import humanizar_limite
from i18n import N_, idioma_actual, tr
from puente import OPERACIONES, ResultadoOperacion

# clave -> (nombre visible, extensión)
FORMATOS = {
    "html": (N_("HTML con fórmulas MathML (accesible)"), "html"),
    "txt": (N_("Texto plano"), "txt"),
    "md": (N_("Markdown"), "md"),
    "tex": (N_("Documento LaTeX"), "tex"),
    "json": (N_("JSON (datos estructurados)"), "json"),
}


# ---------------------------------------------------------
# Piezas comunes
# ---------------------------------------------------------

def nombre_operacion(res: ResultadoOperacion) -> str:
    return tr(OPERACIONES.get(res.operacion, res.operacion))


def _es_lista(valor: Any) -> bool:
    return isinstance(valor, (list, tuple))


def resultado_corto(res: ResultadoOperacion) -> str:
    """El resultado en una sola línea, para copiar o como texto alternativo."""
    valor = res.valor
    if res.es_error:
        return ""
    if res.operacion == "limite":
        return humanizar_limite(valor)
    if res.operacion == "integral_definida":
        return humanizar_integral(valor)
    if valor is None:
        # Sin valor (p. ej. sistema indeterminado): primera línea del informe
        return res.texto.strip().splitlines()[0] if res.texto.strip() else ""
    if _es_lista(valor):
        return ", ".join(f"{eq.lhs} = {eq.rhs}" for eq in valor)
    if valor == sympy.EmptySet:
        return tr("Sin solución")
    if isinstance(valor, sympy.MatrixBase):
        return "; ".join("[" + ", ".join(str(e) for e in fila) + "]" for fila in valor.tolist())
    return f"{valor} + C" if res.mas_constante else str(valor)


def resumen(res: ResultadoOperacion) -> str:
    """
    El resultado sin el paso a paso (opción "Solo el resultado"): el resultado primero,
    como en la explicación completa, y luego la operación y los datos, para saber a qué
    corresponde al revisarlo en el historial. Las soluciones de un sistema y las filas
    de una matriz van una por línea, para leerlas con las flechas.
    """
    if res.es_error:
        return res.texto
    valor = res.valor
    if _es_lista(valor):
        lineas = [f"{eq.lhs} = {eq.rhs}" for eq in valor]
    elif isinstance(valor, sympy.MatrixBase) and valor.rows > 1:
        lineas = ["[ " + ", ".join(str(e) for e in fila) + " ]" for fila in valor.tolist()]
    else:
        lineas = [resultado_corto(res)]
    texto = [tr("RESULTADO: {valor}", valor=lineas[0])] if len(lineas) == 1 else [tr("RESULTADO:")] + lineas
    texto.append(tr("Operación: {operacion}", operacion=nombre_operacion(res)))
    texto.append(f"{tr('Entrada')}: {res.entrada.strip().replace(chr(10), '; ')}")
    # El método de un sistema clásico ya lo dice el nombre de la operación
    texto += _parametros_legibles(res, excluir={"metodo"})
    return "\n".join(texto)


def _signo_igual(res: ResultadoOperacion) -> tuple:
    """(LaTeX, MathML) del signo entre planteamiento y resultado: = o ≈ si es decimal."""
    if isinstance(res.valor, sympy.Float) and res.planteamiento is not None and not res.planteamiento.is_Float:
        return r"\approx", "<mo>&#x2248;</mo>"
    return "=", "<mo>=</mo>"


def _valor_simbolico(res: ResultadoOperacion) -> Optional[Any]:
    """Valor apto para LaTeX/MathML (None si es un 'no existe' o similar)."""
    v = res.valor
    if res.es_error or v is None or v is sympy.nan or v is sympy.zoo:
        return None
    return v


def latex(res: ResultadoOperacion) -> str:
    """'planteamiento = resultado' en LaTeX (sin delimitadores $)."""
    valor = _valor_simbolico(res)
    texto_valor = sympy.latex(valor) if valor is not None and not _es_lista(valor) else None
    if texto_valor is not None and res.mas_constante:
        texto_valor += " + C"
    if _es_lista(valor):
        texto_valor = r",\quad ".join(sympy.latex(eq) for eq in valor)
    if texto_valor is None:
        texto_valor = r"\text{" + _escapar_latex(resultado_corto(res)) + "}"

    p = res.planteamiento
    if p is None or (not _es_lista(p) and p == valor):
        return texto_valor
    if _es_lista(p):
        sistema = r"\begin{cases} " + r" \\ ".join(sympy.latex(eq) for eq in p) + r" \end{cases}"
        return sistema + r"\quad\Longrightarrow\quad " + texto_valor
    return sympy.latex(p) + f" {_signo_igual(res)[0]} " + texto_valor


def _sin_mfenced(mathml: str) -> str:
    """
    Sustituye <mfenced> (que los navegadores actuales ya no dibujan) por
    <mrow><mo>(</mo>...<mo>)</mo></mrow>, la forma de MathML Core.
    """
    pila: List[str] = []

    def reemplazar(m):
        if m.group(0).startswith("</"):
            return f"<mo>{pila.pop()}</mo></mrow>"
        attrs = m.group(1) or ""
        abre = re.search(r'open="([^"]*)"', attrs)
        cierra = re.search(r'close="([^"]*)"', attrs)
        pila.append(html.escape(cierra.group(1) if cierra else ")"))
        return f"<mrow><mo>{html.escape(abre.group(1) if abre else '(')}</mo>"

    return re.sub(r"<mfenced([^>]*)>|</mfenced>", reemplazar, mathml)


def _entidades_numericas(marcado: str) -> str:
    """
    SymPy usa entidades con nombre de HTML (&pi;, &InvisibleTimes;) que no existen en
    XML: un MathML pegado en otro programa podría fallar. Se pasan a numéricas (&#x3C0;).
    """
    def convertir(m):
        caracteres = html.unescape(m.group(0))
        if caracteres == m.group(0):  # entidad desconocida: se deja como está
            return m.group(0)
        return "".join(f"&#x{ord(c):X};" for c in caracteres)

    return re.sub(r"&(?!#)[A-Za-z][A-Za-z0-9]*;", convertir, marcado)


def _mathml_de(expr: Any) -> str:
    marcado = sympy.mathml(expr, printer="presentation")
    # SymPy escribe < y > de las desigualdades estrictas sin escapar: no sería XML válido
    marcado = marcado.replace("<mo><</mo>", "<mo>&lt;</mo>").replace("<mo>></mo>", "<mo>&gt;</mo>")
    return _entidades_numericas(_sin_mfenced(marcado))


def mathml(res: ResultadoOperacion) -> str:
    """'planteamiento = resultado' como un elemento <math> (MathML de presentación)."""
    valor = _valor_simbolico(res)
    if valor is None:
        derecha = f"<mtext>{html.escape(resultado_corto(res))}</mtext>"
    elif _es_lista(valor):
        derecha = "<mo>,</mo>".join(_mathml_de(eq) for eq in valor)
    else:
        derecha = _mathml_de(valor)
        if res.mas_constante:
            derecha = f"<mrow>{derecha}<mo>+</mo><mi>C</mi></mrow>"

    p = res.planteamiento
    if p is None or (not _es_lista(p) and p == valor):
        cuerpo = derecha
    elif _es_lista(p):
        sistema = "".join(f"<mtr><mtd>{_mathml_de(eq)}</mtd></mtr>" for eq in p)
        cuerpo = (f"<mrow><mo>{{</mo><mtable>{sistema}</mtable></mrow>"
                  f"<mo>&#x27F9;</mo>{derecha}")
    else:
        cuerpo = f"{_mathml_de(p)}{_signo_igual(res)[1]}{derecha}"
    alt = html.escape(f"{res.entrada}: {resultado_corto(res)}", quote=True)
    return (f'<math xmlns="http://www.w3.org/1998/Math/MathML" display="block" alttext="{alt}">'
            f"<mrow>{cuerpo}</mrow></math>")


def _escapar_latex(texto: str) -> str:
    reemplazos = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
                  "#": r"\#", "_": r"\_", "%": r"\%", "^": r"\^{}", "~": r"\~{}"}
    return "".join(reemplazos.get(c, c) for c in texto)


def _parametros_legibles(res: ResultadoOperacion, excluir=()) -> List[str]:
    etiquetas = {"variable": tr("Variable"), "tendencia": tr("Tendencia"),
                 "orden": tr("Orden"), "metodo": tr("Método"),
                 "inferior": tr("Límite inferior"), "superior": tr("Límite superior")}
    return [f"{etiquetas.get(k, k)}: {v}" for k, v in res.parametros.items()
            if v not in (None, "") and k not in excluir]


# ---------------------------------------------------------
# Formatos de archivo
# ---------------------------------------------------------

def _titulo(res: ResultadoOperacion, numero: Optional[int]) -> str:
    """Título de una operación: su nombre, numerado si forma parte del historial."""
    nombre = nombre_operacion(res)
    return f"{numero}. {nombre}" if numero is not None else nombre


def _pie(fecha: str) -> str:
    return f"{tr('Generado por Calculadora Accesible {version}', version=__version__)} — {fecha}"


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _titulo_historial() -> str:
    return tr("Historial de operaciones")


# --- Texto plano ---

def _texto_bloque(res: ResultadoOperacion, numero: Optional[int] = None) -> str:
    if numero is None:
        return res.texto.rstrip()
    titulo = _titulo(res, numero)
    entrada = res.entrada.replace("\n", "; ")
    return "\n".join([titulo, "-" * len(titulo), f"{tr('Entrada')}: {entrada}", "", res.texto.rstrip()])


def a_texto(res: ResultadoOperacion) -> str:
    return _texto_bloque(res) + "\n"


def historial_a_texto(lista: List[ResultadoOperacion]) -> str:
    titulo = _titulo_historial().upper()
    bloques = [_texto_bloque(r, i) for i, r in enumerate(lista, 1)]
    separador = "\n\n" + "=" * 40 + "\n\n"
    return "\n".join([titulo, "=" * len(titulo), ""]) + separador.join(bloques) + "\n\n" + _pie(_ahora()) + "\n"


# --- Markdown ---

def _markdown_bloque(res: ResultadoOperacion, titulo: str, nivel: int) -> List[str]:
    h, h2 = "#" * nivel, "#" * (nivel + 1)
    lineas = [f"{h} {titulo}", "", f"**{tr('Entrada')}:**", "", "```text", res.entrada, "```", ""]
    for p in _parametros_legibles(res):
        lineas.append(f"- {p}")
    if res.parametros:
        lineas.append("")
    if not res.es_error:
        lineas += [f"**{tr('Resultado')}:** `{resultado_corto(res)}`", "", "$$", latex(res), "$$", ""]
    lineas += [f"{h2} {tr('Explicación paso a paso')}", "", "```text", res.texto.rstrip(), "```", ""]
    return lineas


def a_markdown(res: ResultadoOperacion) -> str:
    return "\n".join(_markdown_bloque(res, _titulo(res, None), 1) + [f"_{_pie(res.fecha)}_", ""])


def historial_a_markdown(lista: List[ResultadoOperacion]) -> str:
    lineas = [f"# {_titulo_historial()}", ""]
    for i, r in enumerate(lista, 1):
        lineas += _markdown_bloque(r, _titulo(r, i), 2)
    return "\n".join(lineas + [f"_{_pie(_ahora())}_", ""])


# --- LaTeX ---

def _latex_bloque(res: ResultadoOperacion, titulo: str, seccion: str, subseccion: str) -> List[str]:
    lineas = [
        "\\" + seccion + "*{" + _escapar_latex(titulo) + "}",
        r"\textbf{" + _escapar_latex(tr("Entrada")) + r":} \verb|" + res.entrada.replace("|", "/").replace("\n", "; ") + "|",
        "",
    ]
    for p in _parametros_legibles(res):
        lineas.append(_escapar_latex(p) + r"\\")
    if not res.es_error:
        lineas += ["\\" + subseccion + "*{" + _escapar_latex(tr("Resultado")) + "}",
                   r"\begin{equation*}", latex(res), r"\end{equation*}"]
    lineas += ["\\" + subseccion + "*{" + _escapar_latex(tr("Explicación paso a paso")) + "}",
               r"\begin{verbatim}", res.texto.rstrip(), r"\end{verbatim}"]
    return lineas


def _latex_documento(cuerpo: List[str]) -> str:
    return "\n".join([
        "% " + tr("Generado por Calculadora Accesible {version}", version=__version__),
        "% " + tr("Compile con XeLaTeX o LuaLaTeX: la explicación contiene caracteres Unicode."),
        r"\documentclass{article}",
        r"\usepackage{amsmath}",
        r"\usepackage{fontspec}",
        r"\begin{document}",
    ] + cuerpo + [r"\end{document}", ""])


def a_latex(res: ResultadoOperacion) -> str:
    return _latex_documento(_latex_bloque(res, _titulo(res, None), "section", "subsection"))


def historial_a_latex(lista: List[ResultadoOperacion]) -> str:
    cuerpo = [r"\section*{" + _escapar_latex(_titulo_historial()) + "}"]
    for i, r in enumerate(lista, 1):
        cuerpo += _latex_bloque(r, _titulo(r, i), "subsection", "subsubsection") + [""]
    return _latex_documento(cuerpo)


# --- HTML con MathML ---

def _html_bloque(res: ResultadoOperacion, titulo: str, nivel: int) -> List[str]:
    e = html.escape
    h, h2 = f"h{nivel}", f"h{nivel + 1}"
    partes = [f"<{h}>{e(titulo)}</{h}>",
              f"<{h2}>{e(tr('Entrada'))}</{h2}>",
              f"<pre>{e(res.entrada)}</pre>"]
    params = _parametros_legibles(res)
    if params:
        partes.append("<ul>" + "".join(f"<li>{e(p)}</li>" for p in params) + "</ul>")
    if not res.es_error:
        partes += [f"<{h2}>{e(tr('Resultado'))}</{h2}>",
                   f"<p>{e(resultado_corto(res))}</p>",
                   mathml(res)]
    partes += [f"<{h2}>{e(tr('Explicación paso a paso'))}</{h2}>",
               f"<pre>{e(res.texto.rstrip())}</pre>"]
    return partes


def _html_documento(titulo: str, idioma: str, cuerpo: List[str], fecha: str) -> str:
    e = html.escape
    return "\n".join([
        "<!DOCTYPE html>",
        f'<html lang="{e(idioma)}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(titulo)}</title>",
        "<style>body{font-family:sans-serif;max-width:50rem;margin:1rem auto;padding:0 1rem;line-height:1.5}"
        "pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem}math{font-size:1.3em}"
        "section{border-top:1px solid #ccc;margin-top:2rem}</style>",
        "</head>",
        "<body>",
        "<main>",
    ] + cuerpo + [
        "</main>",
        f"<footer><p>{e(_pie(fecha))}</p></footer>",
        "</body>",
        "</html>",
        "",
    ])


def a_html(res: ResultadoOperacion) -> str:
    titulo = _titulo(res, None)
    return _html_documento(titulo, res.idioma, _html_bloque(res, titulo, 1), res.fecha)


def historial_a_html(lista: List[ResultadoOperacion]) -> str:
    idioma = idioma_actual()
    cuerpo = [f"<h1>{html.escape(_titulo_historial())}</h1>"]
    for i, r in enumerate(lista, 1):
        # Cada operación conserva el idioma en que se calculó (el lector de pantalla cambia de voz)
        lang = f' lang="{html.escape(r.idioma)}"' if r.idioma != idioma else ""
        cuerpo += [f"<section{lang}>"] + _html_bloque(r, _titulo(r, i), 2) + ["</section>"]
    return _html_documento(_titulo_historial(), idioma, cuerpo, _ahora())


# --- JSON ---

def _json_datos(res: ResultadoOperacion) -> dict:
    """Claves en inglés: es un formato de intercambio, igual en todos los idiomas."""
    valor = _valor_simbolico(res)
    return {
        "date": res.fecha,
        "language": res.idioma,
        "operation": res.operacion,
        "operation_name": nombre_operacion(res),
        "input": res.entrada,
        "parameters": {k: (str(v) if v is not None else None) for k, v in res.parametros.items()},
        "is_error": res.es_error,
        "result": None if res.es_error else {
            "text": resultado_corto(res),
            "sympy": None if valor is None else (
                [str(eq) for eq in valor] if _es_lista(valor) else str(valor)),
            "latex": latex(res),
        },
        "explanation": res.texto.rstrip().splitlines(),
    }


def _json_cabecera() -> dict:
    return {"application": "Calculadora Accesible", "version": __version__}


def a_json(res: ResultadoOperacion) -> str:
    return json.dumps({**_json_cabecera(), **_json_datos(res)}, ensure_ascii=False, indent=2) + "\n"


def historial_a_json(lista: List[ResultadoOperacion]) -> str:
    datos = {**_json_cabecera(), "date": _ahora(), "language": idioma_actual(),
             "entries": [_json_datos(r) for r in lista]}
    return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------
# Puntos de entrada
# ---------------------------------------------------------

CONVERSORES = {"txt": a_texto, "md": a_markdown, "tex": a_latex, "html": a_html, "json": a_json}
CONVERSORES_HISTORIAL = {"txt": historial_a_texto, "md": historial_a_markdown, "tex": historial_a_latex,
                         "html": historial_a_html, "json": historial_a_json}


def exportar(res: ResultadoOperacion, formato: str) -> str:
    return CONVERSORES[formato](res)


def exportar_historial(lista: List[ResultadoOperacion], formato: str) -> str:
    """Todas las operaciones del historial en un solo documento (de la más antigua a la más reciente)."""
    return CONVERSORES_HISTORIAL[formato](lista)


def _escribir(ruta: str, contenido: str) -> None:
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenido)


def guardar(res: ResultadoOperacion, formato: str, ruta: str) -> None:
    _escribir(ruta, exportar(res, formato))


def guardar_historial(lista: List[ResultadoOperacion], formato: str, ruta: str) -> None:
    _escribir(ruta, exportar_historial(lista, formato))
