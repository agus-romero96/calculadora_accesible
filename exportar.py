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
from typing import Any, List, Optional

import sympy

from _version import __version__
from calculo.router import humanizar_limite
from i18n import N_, tr
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
    return _entidades_numericas(_sin_mfenced(sympy.mathml(expr, printer="presentation")))


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


def _parametros_legibles(res: ResultadoOperacion) -> List[str]:
    etiquetas = {"variable": tr("Variable"), "tendencia": tr("Tendencia"),
                 "orden": tr("Orden"), "metodo": tr("Método")}
    return [f"{etiquetas.get(k, k)}: {v}" for k, v in res.parametros.items() if v not in (None, "")]


# ---------------------------------------------------------
# Formatos de archivo
# ---------------------------------------------------------

def a_texto(res: ResultadoOperacion) -> str:
    return res.texto.rstrip() + "\n"


def a_markdown(res: ResultadoOperacion) -> str:
    lineas = [f"# {nombre_operacion(res)}", "",
              f"**{tr('Entrada')}:**", "", "```text", res.entrada, "```", ""]
    for p in _parametros_legibles(res):
        lineas.append(f"- {p}")
    if res.parametros:
        lineas.append("")
    if not res.es_error:
        lineas += [f"**{tr('Resultado')}:** `{resultado_corto(res)}`", "", "$$", latex(res), "$$", ""]
    lineas += [f"## {tr('Explicación paso a paso')}", "", "```text", res.texto.rstrip(), "```", "",
               f"_{tr('Generado por Calculadora Accesible {version}', version=__version__)} — {res.fecha}_", ""]
    return "\n".join(lineas)


def a_latex(res: ResultadoOperacion) -> str:
    lineas = [
        "% " + tr("Generado por Calculadora Accesible {version}", version=__version__),
        "% " + tr("Compile con XeLaTeX o LuaLaTeX: la explicación contiene caracteres Unicode."),
        r"\documentclass{article}",
        r"\usepackage{amsmath}",
        r"\usepackage{fontspec}",
        r"\begin{document}",
        r"\section*{" + _escapar_latex(nombre_operacion(res)) + "}",
        r"\textbf{" + _escapar_latex(tr("Entrada")) + r":} \verb|" + res.entrada.replace("|", "/").replace("\n", "; ") + "|",
        "",
    ]
    for p in _parametros_legibles(res):
        lineas.append(_escapar_latex(p) + r"\\")
    if not res.es_error:
        lineas += [r"\subsection*{" + _escapar_latex(tr("Resultado")) + "}",
                   r"\begin{equation*}", latex(res), r"\end{equation*}"]
    lineas += [r"\subsection*{" + _escapar_latex(tr("Explicación paso a paso")) + "}",
               r"\begin{verbatim}", res.texto.rstrip(), r"\end{verbatim}", r"\end{document}", ""]
    return "\n".join(lineas)


def a_html(res: ResultadoOperacion) -> str:
    e = html.escape
    titulo = nombre_operacion(res)
    partes = [
        "<!DOCTYPE html>",
        f'<html lang="{e(res.idioma)}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(titulo)}</title>",
        "<style>body{font-family:sans-serif;max-width:50rem;margin:1rem auto;padding:0 1rem;line-height:1.5}"
        "pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem}math{font-size:1.3em}</style>",
        "</head>",
        "<body>",
        "<main>",
        f"<h1>{e(titulo)}</h1>",
        f"<h2>{e(tr('Entrada'))}</h2>",
        f"<pre>{e(res.entrada)}</pre>",
    ]
    params = _parametros_legibles(res)
    if params:
        partes.append("<ul>" + "".join(f"<li>{e(p)}</li>" for p in params) + "</ul>")
    if not res.es_error:
        partes += [f"<h2>{e(tr('Resultado'))}</h2>",
                   f"<p>{e(resultado_corto(res))}</p>",
                   mathml(res)]
    partes += [
        f"<h2>{e(tr('Explicación paso a paso'))}</h2>",
        f"<pre>{e(res.texto.rstrip())}</pre>",
        "</main>",
        f"<footer><p>{e(tr('Generado por Calculadora Accesible {version}', version=__version__))} — {e(res.fecha)}</p></footer>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(partes)


def a_json(res: ResultadoOperacion) -> str:
    """Claves en inglés: es un formato de intercambio, igual en todos los idiomas."""
    valor = _valor_simbolico(res)
    datos = {
        "application": "Calculadora Accesible",
        "version": __version__,
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
    return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"


CONVERSORES = {"txt": a_texto, "md": a_markdown, "tex": a_latex, "html": a_html, "json": a_json}


def exportar(res: ResultadoOperacion, formato: str) -> str:
    return CONVERSORES[formato](res)


def guardar(res: ResultadoOperacion, formato: str, ruta: str) -> None:
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(exportar(res, formato))
