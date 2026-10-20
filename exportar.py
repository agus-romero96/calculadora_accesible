"""
Copiar y exportar resultados en distintos formatos.

Formatos de archivo: texto plano, Markdown, LaTeX, HTML con MathML y JSON.
Para el portapapeles: el resultado en una línea, la explicación completa, LaTeX o MathML.

Todo parte de un ResultadoOperacion (puente.py): texto accesible, valor SymPy y
"planteamiento" (el problema sin evaluar: Derivative, Integral, Limit...), de modo
que LaTeX y MathML muestran "planteamiento = resultado" como en un libro.

El HTML incluye MathML y texto alternativo. La lectura y exploración efectivas
con NVDA, MathCAT o JAWS requieren validación manual en esos entornos.
"""
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, List, Optional

import sympy

from _version import __version__
from algebra.resolucion import describir_conjunto
from calculo import edo
from calculo.extremos import lineas_resultado
from calculo.rectas import ecuacion_recta
from calculo.taylor import nombre_polinomio, taylor_latex, taylor_texto, _coeficientes
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


def _cabecera(res: ResultadoOperacion) -> List[str]:
    lineas = []
    for linea in res.texto.strip().splitlines():
        if re.fullmatch(r"[=\-]{3,}", linea.strip()) or linea.strip() in ("PASO A PASO:", "STEP BY STEP:"):
            break
        lineas.append(linea.strip())
    return lineas


def _sin_encabezado(linea: str) -> str:
    # El idioma del registro puede ser distinto del idioma actual de la aplicación.
    return re.sub(r"^(?:(?:RESULTADO|RESULT):\s*)+", "", linea.strip(), flags=re.I)


def _resultado_textual(res: ResultadoOperacion) -> str:
    lineas = _cabecera(res)
    if not lineas:
        return ""
    primero = _sin_encabezado(lineas[0])
    return primero if primero else "; ".join(l for l in lineas[1:] if l)


def _condiciones(res: ResultadoOperacion) -> List[str]:
    """Conserva las salvedades del informe, también en historiales sin objetos SymPy.

    Los motores sitúan avisos y condiciones antes de la línea de separación;
    aritmética y cálculo usan además una sección de advertencias con viñetas.
    Solo se omiten notas conocidas sobre el procedimiento de explicación.
    """
    base = _resultado_base(res)
    cabecera = _cabecera(res)
    candidatos = cabecera[1:]
    if cabecera and not _sin_encabezado(cabecera[0]):
        # El resultado ocupa varias líneas antes de los avisos. No se deben
        # confundir esas filas con condiciones (ni sus aproximaciones decimales).
        if _son_rectas(res):
            candidatos = candidatos[2:]
        elif res.operacion == "extremos" and isinstance(res.valor, dict):
            candidatos = candidatos[len(lineas_resultado(res.valor, _variable(res))):]
        elif isinstance(res.valor, sympy.MatrixBase):
            candidatos = candidatos[res.valor.rows:]
    en_avisos = False
    for linea in res.texto.splitlines():
        limpia = linea.strip()
        if limpia in ("ADVERTENCIAS:", "WARNINGS:", "Advertencias:", "Warnings:", "[!] AVISOS:", "[!] WARNINGS:"):
            en_avisos = True
        elif en_avisos and limpia.startswith("- "):
            candidatos.append(limpia[2:])
        elif en_avisos and limpia:
            en_avisos = False
    restriccion = res.parametros.get("restricciones")
    if restriccion:
        candidatos.append(f"{tr('Restricciones del dominio')}: {restriccion}")
    informativas = ("Se verifican las derivadas bilaterales", "Two-sided derivatives are verified",
                    "Cociente incremental:", "Difference quotient:", "NOTA: hay explicación paso a paso",
                    "NOTE: there is a step-by-step explanation")
    return list(dict.fromkeys(l for l in candidatos if l and l.replace(" ", "") not in base.replace(" ", "")
                              and not l.startswith(informativas)))


def resultado_corto(res: ResultadoOperacion) -> str:
    base = _resultado_base(res)
    return "; ".join([base] + _condiciones(res)) if not res.es_error else ""


def _resultado_base(res: ResultadoOperacion) -> str:
    """El resultado en una sola línea, para copiar o como texto alternativo."""
    valor = res.valor
    if res.es_error:
        return ""
    if valor is None:
        return _resultado_textual(res)
    if res.operacion == "limite":
        return humanizar_limite(valor)
    if res.operacion == "integral_definida":
        return humanizar_integral(valor)
    if _es_conjunto_solucion(res):
        return describir_conjunto(valor, _variable(res), aproximar=False)
    if res.operacion == "extremos" and isinstance(valor, dict):
        return "; ".join(lineas_resultado(valor, _variable(res), aproximar=False))
    if res.operacion == "taylor" and valor is not None:
        return _taylor_corto(res)
    if res.operacion == "implicita" and valor is not None:
        return f"{_derivada_implicita(res)} = {valor}"
    if res.operacion == "edo" and _es_lista(valor):
        return "; ".join(_solucion_edo(eq) for eq in valor)
    if _son_rectas(res):
        tangente, normal = (ecuacion_recta(eq, _variable(res)) for eq in valor)
        return tr("tangente: {t}; normal: {n}", t=tangente, n=normal)
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
    if res.operacion == "extremos" and isinstance(valor, dict):
        lineas = lineas_resultado(valor, _variable(res))
    elif _son_rectas(res):
        lineas = [tr("Recta tangente: {recta}", recta=ecuacion_recta(valor[0], _variable(res))),
                  tr("Recta normal: {recta}", recta=ecuacion_recta(valor[1], _variable(res)))]
    elif res.operacion == "edo" and _es_lista(valor):
        lineas = [_solucion_edo(eq) for eq in valor]
    elif _es_lista(valor):
        lineas = [f"{eq.lhs} = {eq.rhs}" for eq in valor]
    elif isinstance(valor, sympy.MatrixBase) and valor.rows > 1:
        lineas = ["[ " + ", ".join(str(e) for e in fila) + " ]" for fila in valor.tolist()]
    else:
        lineas = [_resultado_base(res)]
    texto = [tr("RESULTADO: {valor}", valor=lineas[0])] if len(lineas) == 1 else [tr("RESULTADO:")] + lineas
    texto.append(tr("Operación: {operacion}", operacion=nombre_operacion(res)))
    texto.append(f"{tr('Entrada')}: {res.entrada.strip().replace(chr(10), '; ')}")
    # El método de un sistema clásico ya lo dice el nombre de la operación (el de una ecuación diferencial, no)
    texto += _parametros_legibles(res, excluir={"metodo"} if res.operacion == "sistema_clasico" else ())
    texto += [l for l in _condiciones(res) if l not in texto]
    return "\n".join(texto)


def _es_conjunto_solucion(res: ResultadoOperacion) -> bool:
    """Ecuación o inecuación: el valor es el conjunto solución (se escribe 'x ∈ conjunto')."""
    return res.operacion == "ecuacion" and isinstance(res.valor, sympy.Set)


def _variable(res: ResultadoOperacion) -> sympy.Symbol:
    # Real, como las del parser: si no, no coincidiría con la variable de las rectas
    return sympy.Symbol(res.parametros.get("variable") or "x", real=True)


def _solucion_edo(eq: Any) -> str:
    """'y = x^2/2 + C': como en el paso a paso, con ^ y la constante al final."""
    return f"{edo.texto(eq.lhs)} = {edo.texto(eq.rhs)}"


def _derivada_implicita(res: ResultadoOperacion) -> str:
    """'dy/dx' con los nombres de las variables de la operación."""
    return f"d{res.parametros.get('dependiente', 'y')}/d{res.parametros.get('variable', 'x')}"


def _punto_taylor(res: ResultadoOperacion) -> Any:
    from parser_matematico import ParserMatematico
    return ParserMatematico().parsear(str(res.parametros.get("punto") or "0")).doit()


def _taylor_corto(res: ResultadoOperacion) -> str:
    """'P_3(x) = 1 + x + x^2/2 + x^3/6', en potencias de (x - x0) como en el paso a paso."""
    x = _variable(res)
    try:
        return f"{nombre_polinomio(int(res.parametros.get('orden')), x)} = {taylor_texto(res.valor, x, _punto_taylor(res))}"
    except Exception:
        return str(res.valor)


def _son_rectas(res: ResultadoOperacion) -> bool:
    """Recta tangente y normal: el valor es [tangente, normal], cada una con su nombre."""
    return res.operacion == "tangente" and _es_lista(res.valor) and len(res.valor) == 2


def _nombres_rectas() -> tuple:
    return tr("Tangente"), tr("Normal")


def _signo_igual(res: ResultadoOperacion) -> tuple:
    """(LaTeX, MathML) del signo entre planteamiento y resultado: = o ≈ si es decimal; ⟹ si es un conjunto solución."""
    if _es_conjunto_solucion(res):
        return r"\quad\Longrightarrow\quad", "<mo>&#x27F9;</mo>"
    if isinstance(res.valor, sympy.Float) and res.planteamiento is not None and not res.planteamiento.is_Float:
        return r"\approx", "<mo>&#x2248;</mo>"
    return "=", "<mo>=</mo>"


def _valor_simbolico(res: ResultadoOperacion) -> Optional[Any]:
    """Valor apto para LaTeX/MathML (None si es un 'no existe' o similar)."""
    v = res.valor
    if res.es_error or v is None or v is sympy.nan or v is sympy.zoo:
        return None
    if res.operacion == "extremos":
        return None  # varios datos (puntos, extremos, intervalos): se escriben como texto
    return v


def _latex_extremos(res: ResultadoOperacion) -> str:
    """El estudio de extremos en LaTeX: una línea por dato, con fórmulas (\\infty, \\cup) y no texto plano."""
    v, x = res.valor, _variable(res)

    def texto_latex(t):
        return r"\text{" + _escapar_latex(t) + "}"

    def intervalos(conjunto):
        return texto_latex(tr("ningún intervalo")) if conjunto == sympy.S.EmptySet else sympy.latex(conjunto)

    criticos = sorted(v["criticos"], key=float)
    lineas = [texto_latex(tr("Puntos críticos") + ": ") +
              (", ".join(f"{sympy.latex(x)} = {sympy.latex(c)}" for c in criticos) if criticos
               else texto_latex(tr("ninguno")))]
    for nombre, lista in ((tr("Máximo local"), v["maximos"]), (tr("Mínimo local"), v["minimos"])):
        for c, fc in lista:
            lineas.append(texto_latex(nombre + ": ") + f"f\\left({sympy.latex(c)}\\right) = {sympy.latex(fc)}")
    if not v["maximos"] and not v["minimos"]:
        lineas.append(texto_latex(tr("Sin extremos locales interiores") if v.get("solo_interiores") else tr("Sin extremos locales")))
    lineas.append(texto_latex(tr("Creciente en") + " ") + intervalos(v["crece"]))
    lineas.append(texto_latex(tr("Decreciente en") + " ") + intervalos(v["decrece"]))
    return r"\begin{aligned} " + r" \\ ".join(lineas) + r" \end{aligned}"


def latex(res: ResultadoOperacion) -> str:
    formula = _latex_formula(res)
    condiciones = _condiciones(res) if not res.es_error else []
    if not condiciones:
        return formula
    return (r"\begin{gathered} " + formula + r" \\ " + r" \\ ".join(
        r"\text{" + _escapar_latex(c) + "}" for c in condiciones) + r" \end{gathered}")


def _latex_formula(res: ResultadoOperacion) -> str:
    """'planteamiento = resultado' en LaTeX (sin delimitadores $)."""
    if res.operacion == "extremos" and isinstance(res.valor, dict) and not res.es_error:
        return _latex_extremos(res)
    if res.operacion == "implicita" and res.valor is not None and not res.es_error:
        y = sympy.latex(sympy.Symbol(res.parametros.get("dependiente", "y")))
        x = sympy.latex(_variable(res))
        return rf"\frac{{d{y}}}{{d{x}}} = " + sympy.latex(res.valor)
    if res.operacion == "taylor" and res.valor is not None and not res.es_error:
        try:
            return taylor_latex(res.valor, _variable(res), _punto_taylor(res), int(res.parametros.get("orden")))
        except Exception:
            pass
    valor = _valor_simbolico(res)
    texto_valor = sympy.latex(valor) if valor is not None and not _es_lista(valor) else None
    if texto_valor is not None and _es_conjunto_solucion(res):
        texto_valor = sympy.latex(_variable(res)) + r" \in " + texto_valor
    if texto_valor is not None and res.mas_constante:
        texto_valor += " + C"
    if _son_rectas(res):
        texto_valor = r",\quad ".join(r"\text{" + _escapar_latex(nombre) + r": } " + sympy.latex(eq)
                                       for nombre, eq in zip(_nombres_rectas(), valor))
    elif _es_lista(valor):
        texto_valor = r",\quad ".join(sympy.latex(eq) for eq in valor)
    if texto_valor is None:
        texto_valor = r"\text{" + _escapar_latex(_resultado_base(res)) + "}"

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
    raiz = ET.fromstring(_entidades_numericas(mathml))

    def transformar(nodo):
        for hijo in list(nodo):
            transformar(hijo)
        if nodo.tag.rsplit("}", 1)[-1] != "mfenced":
            return
        prefijo = nodo.tag[:-len("mfenced")]
        abre = nodo.attrib.pop("open", "(")
        cierra = nodo.attrib.pop("close", ")")
        separadores = "".join(nodo.attrib.pop("separators", ",").split())
        hijos = list(nodo)
        nodo[:] = []
        nodo.tag = prefijo + "mrow"

        def operador(padre, cadena, atributo):
            if cadena:
                ET.SubElement(padre, prefijo + "mo", {atributo: "true"}).text = cadena

        # Expansión de MathML 3, sección 3.3.8: el grupo interior conserva
        # los argumentos y el papel de los operadores como separadores.
        operador(nodo, abre, "fence")
        grupo = ET.SubElement(nodo, prefijo + "mrow") if len(hijos) > 1 else nodo
        for i, hijo in enumerate(hijos):
            if i and separadores:
                operador(grupo, separadores[min(i - 1, len(separadores) - 1)], "separator")
            grupo.append(hijo)
        operador(nodo, cierra, "fence")

    transformar(raiz)
    return ET.tostring(raiz, encoding="unicode")


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


def _mathml_taylor(res: ResultadoOperacion) -> str:
    x, x0 = _variable(res), _punto_taylor(res)
    n = int(res.parametros["orden"])
    variable = _mathml_de(x)
    if x0 == 0:
        base = variable
    else:
        signo, centro = ("+", -x0) if x0.could_extract_minus_sign() else ("-", x0)
        base = f"<mrow><mo>(</mo>{variable}<mo>{signo}</mo>{_mathml_de(centro)}<mo>)</mo></mrow>"
    terminos = []
    for k, c in _coeficientes(res.valor, x, x0):
        negativo = c.could_extract_minus_sign()
        a = -c if negativo else c
        if terminos or negativo:
            terminos.append("<mo>-</mo>" if negativo else "<mo>+</mo>")
        if k == 0:
            cuerpo = _mathml_de(a)
        else:
            potencia = base if k == 1 else f"<msup>{base}<mn>{k}</mn></msup>"
            cuerpo = potencia if a == 1 else f"<mrow>{_mathml_de(a)}<mo>&#x2062;</mo>{potencia}</mrow>"
        terminos.append(cuerpo)
    nombre = f"<msub><mi>P</mi><mn>{n}</mn></msub><mo>(</mo>{variable}<mo>)</mo>"
    return f"<mrow>{nombre}<mo>=</mo>{''.join(terminos) or '<mn>0</mn>'}</mrow>"


def _mathml_extremos(res: ResultadoOperacion) -> str:
    v, x = res.valor, _variable(res)
    filas = []

    def fila(etiqueta, formula):
        filas.append(f"<mtr><mtd><mtext>{html.escape(etiqueta)}: </mtext>{formula}</mtd></mtr>")

    fila(tr("Puntos críticos"), _mathml_de(sympy.FiniteSet(*v["criticos"])))
    for etiqueta, lista in ((tr("Máximo local"), v["maximos"]), (tr("Mínimo local"), v["minimos"])):
        for c, fc in lista:
            fila(etiqueta, f"{_mathml_de(x)}<mo>=</mo>{_mathml_de(c)}<mo>;</mo>"
                 f"<mi>f</mi><mo>(</mo>{_mathml_de(c)}<mo>)</mo><mo>=</mo>{_mathml_de(fc)}")
    if not v["maximos"] and not v["minimos"]:
        fila(tr("Sin extremos locales interiores") if v.get("solo_interiores") else tr("Sin extremos locales"), "")
    fila(tr("Creciente en"), _mathml_de(v["crece"]))
    fila(tr("Decreciente en"), _mathml_de(v["decrece"]))
    return "<mtable>" + "".join(filas) + "</mtable>"


def mathml(res: ResultadoOperacion) -> str:
    """'planteamiento = resultado' como un elemento <math> (MathML de presentación)."""
    valor = _valor_simbolico(res)
    if res.operacion == "taylor" and valor is not None:
        derecha = _mathml_taylor(res)
    elif res.operacion == "implicita" and valor is not None:
        dependiente = html.escape(str(res.parametros.get("dependiente", "y")))
        derecha = (f"<mfrac><mrow><mi>d</mi><mi>{dependiente}</mi></mrow>"
                   f"<mrow><mi>d</mi>{_mathml_de(_variable(res))}</mrow></mfrac><mo>=</mo>{_mathml_de(valor)}")
    elif res.operacion == "extremos" and isinstance(res.valor, dict) and not res.es_error:
        derecha = _mathml_extremos(res)
    elif valor is None:
        derecha = f"<mtext>{html.escape(_resultado_base(res))}</mtext>"
    elif _son_rectas(res):
        derecha = "<mo>,</mo>".join(f"<mrow><mtext>{html.escape(nombre)}: </mtext>{_mathml_de(eq)}</mrow>"
                                    for nombre, eq in zip(_nombres_rectas(), valor))
    elif _es_lista(valor):
        derecha = "<mo>,</mo>".join(_mathml_de(eq) for eq in valor)
    else:
        derecha = _mathml_de(valor)
        if _es_conjunto_solucion(res):
            derecha = f"<mrow>{_mathml_de(_variable(res))}<mo>&#x2208;</mo>{derecha}</mrow>"
        if res.mas_constante:
            derecha = f"<mrow>{derecha}<mo>+</mo><mi>C</mi></mrow>"

    p = None if res.es_error else res.planteamiento
    if p is None or (not _es_lista(p) and p == valor):
        cuerpo = derecha
    elif _es_lista(p):
        sistema = "".join(f"<mtr><mtd>{_mathml_de(eq)}</mtd></mtr>" for eq in p)
        cuerpo = (f"<mrow><mo>{{</mo><mtable>{sistema}</mtable></mrow>"
                  f"<mo>&#x27F9;</mo>{derecha}")
    else:
        cuerpo = f"{_mathml_de(p)}{_signo_igual(res)[1]}{derecha}"
    condiciones = _condiciones(res) if not res.es_error else []
    if condiciones:
        filas = [f"<mtr><mtd><mrow>{cuerpo}</mrow></mtd></mtr>"]
        filas += [f"<mtr><mtd><mtext>{html.escape(c)}</mtext></mtd></mtr>" for c in condiciones]
        cuerpo = "<mtable>" + "".join(filas) + "</mtable>"
    entrada_lineal = res.entrada.replace("\n", "; ")
    alt = html.escape(f"{entrada_lineal}: {resultado_corto(res)}", quote=True)
    return (f'<math xmlns="http://www.w3.org/1998/Math/MathML" display="block" alttext="{alt}">'
            f"<mrow>{cuerpo}</mrow></math>")


def _escapar_latex(texto: str) -> str:
    reemplazos = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
                  "#": r"\#", "_": r"\_", "%": r"\%", "^": r"\^{}", "~": r"\~{}"}
    return "".join(reemplazos.get(c, c) for c in texto)


def _parametros_legibles(res: ResultadoOperacion, excluir=()) -> List[str]:
    etiquetas = {"variable": tr("Variable"), "dependiente": tr("Variable dependiente"), "tendencia": tr("Tendencia"), "punto": tr("Punto"),
                 "orden": tr("Orden"), "metodo": tr("Método"), "restricciones": tr("Restricciones del dominio"),
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
        return "\n".join([tr("Operación: {operacion}", operacion=nombre_operacion(res)),
                          f"{tr('Entrada')}: {res.entrada}", *_parametros_legibles(res), "", res.texto.rstrip()])
    titulo = _titulo(res, numero)
    entrada = res.entrada.replace("\n", "; ")
    return "\n".join([titulo, "-" * len(titulo), f"{tr('Entrada')}: {entrada}",
                      *_parametros_legibles(res), "", res.texto.rstrip()])


def a_texto(res: ResultadoOperacion) -> str:
    return _texto_bloque(res) + "\n"


def historial_a_texto(lista: List[ResultadoOperacion]) -> str:
    titulo = _titulo_historial().upper()
    bloques = [_texto_bloque(r, i) for i, r in enumerate(lista, 1)]
    separador = "\n\n" + "=" * 40 + "\n\n"
    return "\n".join([titulo, "=" * len(titulo), ""]) + separador.join(bloques) + "\n\n" + _pie(_ahora()) + "\n"


# --- Markdown ---

def _codigo_markdown(texto: str, bloque: bool = False) -> str:
    longitud = max((len(s) for s in re.findall(r"`+", texto)), default=0) + 1
    cerca = "`" * max(3 if bloque else 1, longitud)
    return f"{cerca}text\n{texto}\n{cerca}" if bloque else f"{cerca} {texto} {cerca}"


def _markdown_bloque(res: ResultadoOperacion, titulo: str, nivel: int) -> List[str]:
    h, h2 = "#" * nivel, "#" * (nivel + 1)
    lineas = [f"{h} {titulo}", "", f"**{tr('Entrada')}:**", "", _codigo_markdown(res.entrada, True), ""]
    for p in _parametros_legibles(res):
        lineas.append(f"- {_codigo_markdown(p)}")
    if res.parametros:
        lineas.append("")
    if not res.es_error:
        lineas += [f"**{tr('Resultado')}:** {_codigo_markdown(resultado_corto(res))}", "", "$$", latex(res), "$$", ""]
    lineas += [f"{h2} {tr('Explicación paso a paso')}", "", _codigo_markdown(res.texto.rstrip(), True), ""]
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
        r"\textbf{" + _escapar_latex(tr("Entrada")) + r":} \texttt{" + _escapar_latex(res.entrada.replace("\n", "; ")) + "}",
        "",
    ]
    for p in _parametros_legibles(res):
        lineas.append(_escapar_latex(p) + r"\\")
    if not res.es_error:
        lineas += ["\\" + subseccion + "*{" + _escapar_latex(tr("Resultado")) + "}",
                   r"\begin{equation*}", latex(res), r"\end{equation*}"]
    lineas += ["\\" + subseccion + "*{" + _escapar_latex(tr("Explicación paso a paso")) + "}",
               r"\begin{flushleft}\ttfamily"]
    # Un párrafo por línea evita que un '[' de la siguiente fila se interprete
    # como el argumento opcional de un salto de línea LaTeX.
    lineas += [r"\strut " + _escapar_latex(l) + r"\par" for l in res.texto.rstrip().splitlines()]
    lineas.append(r"\end{flushleft}")
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
