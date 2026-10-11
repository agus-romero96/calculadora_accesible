"""
Ecuaciones e inecuaciones de una variable, explicadas paso a paso con el formato de
calculo/pasos.py (Regla, En este caso, las cuentas y Queda):

  - Ecuaciones de primer grado: despejar() de algebra/ecuaciones.py (quitar paréntesis,
    agrupar, pasar términos, dividir).
  - Ecuaciones de segundo grado: forma general, discriminante con sus cuentas y, según el
    caso, factor común, ecuación incompleta, factorización (dos números) o fórmula general,
    con la propiedad del producto nulo.
  - Ecuaciones racionales: restricciones del dominio, multiplicar por el MCM de los
    denominadores, resolver la ecuación que queda y descartar las raíces extrañas.
  - Inecuaciones de primer grado: como las ecuaciones, invirtiendo el sentido al multiplicar
    o dividir entre un número negativo.
  - Inecuaciones de segundo grado: puntos críticos y tabla de signos, intervalo a intervalo.

Al final se sustituye la solución en la ecuación original y se compara con solveset de
SymPy: si no coinciden, se da el resultado de SymPy sin pasos y con un aviso. Otros tipos
(grado 3 o más, funciones) se resuelven con SymPy, sin pasos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, List, Optional, Sequence, Tuple

import sympy
from sympy import S

from algebra.ecuaciones import _quitar_parentesis, despejar, invertir, sustituir
from calculo.pasos import PasoCalculo, entre_parentesis, suma_texto, texto, texto_paso
from i18n import N_, tr
from pasos_aritmetica import ExplicadorFactorizar, limpiar

# Relación escrita -> clase de SymPy
RELACIONES = {"=": sympy.Eq, "<": sympy.Lt, "<=": sympy.Le, ">": sympy.Gt, ">=": sympy.Ge}
# Otras formas de escribirlas (la de la izquierda es la que se muestra)
_SINONIMOS = (("≤", "<="), ("≥", ">="), ("=<", "<="), ("=>", ">="), ("==", "="))
_CUMPLE = {"=": lambda a, b: a == b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
           ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}

PRIMER_GRADO = N_("Ecuación de primer grado")
SEGUNDO_GRADO = N_("Ecuación de segundo grado")
RACIONAL = N_("Ecuación racional")
INECUACION_PRIMER_GRADO = N_("Inecuación de primer grado")
INECUACION_SEGUNDO_GRADO = N_("Inecuación de segundo grado")
OTRA_ECUACION = N_("Ecuación")
OTRA_INECUACION = N_("Inecuación")


class SinExplicacion(Exception):
    """El tipo no tiene explicación paso a paso: se resuelve solo con SymPy."""


@dataclass
class ResultadoEcuacion:
    texto: str
    conjunto: Any = None          # conjunto solución (FiniteSet, Interval, Union, EmptySet, Reals)
    es_error: bool = False
    variable: Any = None
    planteamiento: Any = None     # Eq / Lt / Le... sin evaluar, para exportar
    avisos: List[str] = field(default_factory=list)


# ---------------- Texto de conjuntos ----------------

def _numero(v: Any) -> str:
    return texto(v)


def _extremo(v: Any) -> str:
    if v == S.Infinity:
        return "∞"
    if v == S.NegativeInfinity:
        return "-∞"
    return _numero(v)


def intervalo_texto(intervalo: sympy.Interval) -> str:
    """Notación de intervalos: (-∞, 3], con corchete si el extremo se incluye."""
    abre = "(" if intervalo.left_open or intervalo.start.is_infinite else "["
    cierra = ")" if intervalo.right_open or intervalo.end.is_infinite else "]"
    return f"{abre}{_extremo(intervalo.start)}, {_extremo(intervalo.end)}{cierra}"


def _desigualdad_de(intervalo: sympy.Interval, variable: Any) -> str:
    """El intervalo como desigualdad: x < 3, x >= -1, -2 < x <= 2."""
    a, b = intervalo.start, intervalo.end
    menor_izq = "<" if intervalo.left_open else "<="
    menor_der = "<" if intervalo.right_open else "<="
    if a == S.NegativeInfinity:
        return f"{variable} {menor_der} {_numero(b)}"
    if b == S.Infinity:
        return f"{variable} {invertir(menor_izq)} {_numero(a)}"
    return f"{_numero(a)} {menor_izq} {variable} {menor_der} {_numero(b)}"


def _aproximado(v: Any) -> str:
    """'1 + sqrt(2) (aproximadamente 2.414214)' si el valor es irracional."""
    if v.is_Rational or not v.is_number:
        return _numero(v)
    decimal = f"{float(v):.6f}".rstrip("0").rstrip(".")
    return tr("{valor} (aproximadamente {decimal})", valor=_numero(v), decimal=decimal)


def _piezas(conjunto: Any) -> List[Any]:
    """Los intervalos y puntos de un conjunto, de izquierda a derecha."""
    piezas = list(conjunto.args) if isinstance(conjunto, sympy.Union) else [conjunto]
    salida = []
    for p in piezas:
        salida.extend(sympy.FiniteSet(e) for e in p.args) if isinstance(p, sympy.FiniteSet) else salida.append(p)
    return sorted(salida, key=lambda p: float(p.inf))


def describible(conjunto: Any) -> bool:
    """Si el conjunto es de los que se saben leer (no, por ejemplo, las soluciones periódicas de sin(x) = 0)."""
    if conjunto in (S.EmptySet, S.Reals):
        return True
    try:
        return all(isinstance(p, (sympy.Interval, sympy.FiniteSet)) and all(e.is_real for e in p.boundary)
                   for p in _piezas(conjunto))
    except Exception:
        return False


def describir_conjunto(conjunto: Any, variable: Any, aproximar: bool = True) -> str:
    """
    El conjunto solución para leer: 'x = -2 o x = 3', 'x < -2 o x > 2, es decir, (-∞, -2) ∪ (2, ∞)',
    'todos los números reales', 'no tiene solución real'.
    """
    if conjunto == S.EmptySet:
        return tr("no tiene solución real")
    if conjunto == S.Reals:
        return tr("todos los números reales")
    piezas = _piezas(conjunto)
    partes = []
    for p in piezas:
        if isinstance(p, sympy.FiniteSet):
            valor = p.args[0]
            partes.append(f"{variable} = {_aproximado(valor) if aproximar else _numero(valor)}")
        else:
            partes.append(_desigualdad_de(p, variable))
    lectura = tr(" o ").join(partes)
    if all(isinstance(p, sympy.FiniteSet) for p in piezas):
        return lectura
    notacion = " ∪ ".join(intervalo_texto(p) if isinstance(p, sympy.Interval) else "{" + _numero(p.args[0]) + "}"
                          for p in piezas)
    return tr("{desigualdades}, es decir, {intervalos}", desigualdades=lectura, intervalos=notacion)


def mismo_conjunto(a: Any, b: Any) -> bool:
    if a == b:
        return True
    try:
        if isinstance(a, sympy.FiniteSet) and isinstance(b, sympy.FiniteSet):
            return len(a) == len(b) and all(any(sympy.simplify(x - y) == 0 for y in b.args) for x in a.args)
        return sympy.Union(sympy.Complement(a, b), sympy.Complement(b, a)) == S.EmptySet
    except Exception:
        return False


# ---------------- Expresiones ----------------

def _terminos(expr: Any) -> List[Any]:
    return [t for t in sympy.Add.make_args(expr) if t != 0]


def _polinomio_texto(expr: Any, x: Any) -> str:
    """De mayor a menor grado: -x^2 + 4 (SymPy escribiría 4 - x^2)."""
    poli = sympy.Poly(sympy.expand(expr), x)
    terminos = [c * x ** k for (k,), c in poli.terms() if c != 0]
    return suma_texto(terminos) if terminos else "0"


def _preparar(lado: Any) -> Any:
    """
    El lado tal como se escribió (2*(x + 1) - 3 sigue con su paréntesis), con los productos de
    números hechos (-1*3 = -3) y los términos que no cambian al evaluarlos ya en su forma normal.
    """
    lado = limpiar(lado)
    terminos = []
    for t in sympy.Add.make_args(lado):
        normal = t.doit()
        terminos.append(normal if texto(normal) == texto(t) or not normal.free_symbols and normal.is_Number else t)
    return terminos[0] if len(terminos) == 1 else sympy.Add(*terminos, evaluate=False)


def _unir(intro: Sequence[str], regla: str) -> str:
    """La regla tras una frase de introducción, empezando con mayúscula."""
    if not intro:
        return regla
    return "".join(intro) + regla[:1].upper() + regla[1:]


def _signo_texto(v: Any) -> str:
    return tr("positivo") if v > 0 else tr("negativo")


def _cuenta(expr: Any, x: Any, valor: Any) -> Tuple[str, Any]:
    """('2*0 - 3 = -3', -3): la expresión con el valor sustituido y su resultado."""
    resultado = sympy.simplify(sympy.sympify(expr).doit().subs(x, valor))
    escrita = sustituir(expr, {x: valor})
    return (escrita if escrita == texto(resultado) else f"{escrita} = {texto(resultado)}"), resultado


# ---------------- Motor ----------------

class MotorEcuaciones:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # --- Lectura ---

    def _leer(self, entrada: str) -> Tuple[Any, Any, str, Any, str, str]:
        """(izquierda, derecha, relación, variable, izquierda escrita, derecha escrita)."""
        txt = " ".join(entrada.split())
        for otra, normal in _SINONIMOS:
            txt = txt.replace(otra, normal)
        partes = re.split(r"(<=|>=|<|>|=)", txt)
        if len(partes) != 3:
            if len(partes) == 1:
                raise ValueError(tr("Escriba una ecuación o inecuación con un signo =, <, >, <= o >= (ej: 2*x + 1 = 7)."))
            raise ValueError(tr("Escriba un solo signo de igualdad o desigualdad (=, <, >, <= o >=)."))
        izq_txt, relacion, der_txt = (p.strip() for p in partes)
        if not izq_txt or not der_txt:
            raise ValueError(tr("Falta uno de los dos lados de la {tipo}.",
                                tipo=tr("ecuación") if relacion == "=" else tr("inecuación")))
        izquierda = _preparar(self.parser.parsear(izq_txt))
        derecha = _preparar(self.parser.parsear(der_txt))
        variables = sorted((izquierda.doit() - derecha.doit()).free_symbols | izquierda.free_symbols
                           | derecha.free_symbols, key=lambda s: s.name)
        if not variables:
            raise ValueError(tr("No hay ninguna incógnita: escriba una ecuación con una variable (ej: x^2 = 4)."))
        if len(variables) > 1:
            raise ValueError(tr("Hay varias variables ({variables}): esta operación resuelve ecuaciones e inecuaciones "
                                "de una sola variable. Para varias ecuaciones con varias incógnitas, use Gauss-Jordan.",
                                variables=", ".join(v.name for v in variables)))
        return izquierda, derecha, relacion, variables[0], texto(izquierda), texto(derecha)

    # --- Fachada ---

    def resolver(self, entrada: str) -> ResultadoEcuacion:
        try:
            izquierda, derecha, relacion, x, izq_txt, der_txt = self._leer(entrada)
        except ValueError as e:
            return ResultadoEcuacion(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except Exception as e:
            return ResultadoEcuacion(tr("Error del Sistema: {error}", error=str(e)), es_error=True)

        izq_normal, der_normal = izquierda.doit(), derecha.doit()
        planteamiento = RELACIONES[relacion](izq_normal, der_normal, evaluate=False)
        enunciado = f"{izq_txt} {relacion} {der_txt}"
        try:
            verdad = sympy.solveset(RELACIONES[relacion](izq_normal, der_normal), x, domain=S.Reals)
        except Exception:
            verdad = None
        if verdad is None or not describible(verdad):
            return ResultadoEcuacion(tr("Error de Validación: {error}", error=tr(
                "no se puede resolver esta {tipo} con los métodos de la calculadora.",
                tipo=tr("ecuación") if relacion == "=" else tr("inecuación"))), es_error=True)

        avisos: List[str] = []
        try:
            tipo, pasos, conjunto = self._explicar(izquierda, derecha, relacion, x)
            if not mismo_conjunto(conjunto, verdad):
                avisos.append(tr("AVISO: la explicación no llegó al resultado de SymPy; se muestra el resultado "
                                 "sin pasos."))
                pasos = []
        except SinExplicacion:
            tipo, pasos = (OTRA_ECUACION if relacion == "=" else OTRA_INECUACION), []
            avisos.append(tr("NOTA: hay explicación paso a paso para ecuaciones de primer y segundo grado y racionales, "
                             "y para inecuaciones de primer y segundo grado. Esta la resuelve SymPy, sin pasos."))
        except Exception:
            tipo, pasos = (OTRA_ECUACION if relacion == "=" else OTRA_INECUACION), []
            avisos.append(tr("AVISO: no se pudo explicar paso a paso; el resultado es el que calcula SymPy."))

        lineas = [tr("RESULTADO: {valor}", valor=describir_conjunto(verdad, x))] + avisos + ["=" * 30]
        lineas += [tr("TIPO: {tipo}", tipo=tr(tipo)), tr("Incógnita: {variable}", variable=x),
                   tr("Planteamiento: {enunciado}", enunciado=enunciado)]
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoEcuacion("\n".join(lineas), conjunto=verdad, variable=x, planteamiento=planteamiento,
                                 avisos=avisos)

    # --- Clasificación ---

    def _explicar(self, izquierda: Any, derecha: Any, relacion: str, x: Any) -> Tuple[str, List[PasoCalculo], Any]:
        diferencia = sympy.together(izquierda.doit() - derecha.doit())
        if not diferencia.is_rational_function(x):
            raise SinExplicacion()
        _, denominador = sympy.fraction(diferencia)
        con_denominador = any(sympy.fraction(sympy.together(t))[1].has(x)
                              for lado in (izquierda, derecha) for t in sympy.Add.make_args(lado.doit()))
        if con_denominador or denominador.has(x):
            if relacion != "=":
                raise SinExplicacion()
            return RACIONAL, *self._racional(izquierda, derecha, x)
        grado = sympy.Poly(sympy.expand(izquierda.doit() - derecha.doit()), x).degree()
        if grado > 2:
            raise SinExplicacion()
        pasos: List[PasoCalculo] = []
        conjunto = self._polinomica(izquierda, derecha, relacion, x, pasos)
        if grado <= 1:
            tipo = PRIMER_GRADO if relacion == "=" else INECUACION_PRIMER_GRADO
        else:
            tipo = SEGUNDO_GRADO if relacion == "=" else INECUACION_SEGUNDO_GRADO
        if not (relacion == "=" and conjunto == S.EmptySet):  # sin solución no hay nada que sustituir
            pasos.append(self._paso_comprobar(izquierda, derecha, relacion, x, conjunto))
        return tipo, pasos, conjunto

    def _polinomica(self, izquierda: Any, derecha: Any, relacion: str, x: Any, pasos: List[PasoCalculo]) -> Any:
        """Resuelve una ecuación o inecuación polinómica de grado 0, 1 o 2; añade sus pasos y devuelve el conjunto."""
        diferencia = sympy.expand(izquierda.doit() - derecha.doit())
        grado = sympy.Poly(diferencia, x).degree() if diferencia.has(x) else 0
        if grado == 0:
            return self._sin_incognita(izquierda, derecha, relacion, x, pasos)
        if grado == 1:
            return self._primer_grado(izquierda, derecha, relacion, x, pasos)
        return self._segundo_grado(izquierda, derecha, relacion, x, pasos)

    # --- Grado 0: la incógnita se anula ---

    def _sin_incognita(self, izquierda: Any, derecha: Any, relacion: str, x: Any, pasos: List[PasoCalculo]) -> Any:
        lineas, forma = self._a_cero(izquierda, derecha, relacion, x)
        constante = sympy.expand(izquierda.doit() - derecha.doit())
        cierta = bool(_CUMPLE[relacion](constante, 0))
        lineas.append(tr("La incógnita {variable} se anula: queda {afirmacion}, que es {verdad} sea cual sea {variable}.",
                         variable=x, afirmacion=f"{texto(constante)} {relacion} 0",
                         verdad=tr("cierto") if cierta else tr("falso")))
        conjunto = S.Reals if cierta else S.EmptySet
        pasos.append(PasoCalculo(
            tr("Pasar todo a un lado"),
            regla=tr("si al pasar todos los términos a un lado la incógnita desaparece, queda una afirmación entre "
                     "números: si es cierta, vale cualquier número real; si es falsa, no hay solución."),
            partes=tr("la {tipo} es {enunciado}.", tipo=self._tipo(relacion), enunciado=self._enunciado(izquierda, derecha, relacion)),
            calculo=tuple(lineas),
            queda=describir_conjunto(conjunto, x)))
        return conjunto

    @staticmethod
    def _tipo(relacion: str) -> str:
        return tr("ecuación") if relacion == "=" else tr("inecuación")

    @staticmethod
    def _enunciado(izquierda: Any, derecha: Any, relacion: str) -> str:
        return f"{texto(izquierda)} {relacion} {texto(derecha)}"

    def _a_cero(self, izquierda: Any, derecha: Any, relacion: str, x: Any) -> Tuple[List[str], str]:
        """Líneas de pasar todo a la izquierda (desarrollar y agrupar) y la forma 'p(x) rel 0' que queda."""
        lineas: List[str] = []
        if sympy.expand(derecha.doit()) != 0:
            # Un solo término sin paréntesis dentro (3*x) se resta tal cual; una suma, entre paréntesis
            simple = not derecha.is_Add and not derecha.has(sympy.Add) and not derecha.could_extract_minus_sign()
            restado = texto(derecha) if simple else f"({texto(derecha)})"
            escrito = f"{texto(izquierda)} - {restado}"
            lineas.append(tr("Restamos {derecha} en los dos lados para dejar 0 a la derecha: {expresion} {relacion} 0.",
                             derecha=restado, expresion=escrito, relacion=relacion))
            junto = sympy.Add(*_terminos(izquierda),
                              *[-t if not t.has(sympy.Add) else sympy.Mul(-1, t, evaluate=False) for t in _terminos(derecha)],
                              evaluate=False)
            _quitar_parentesis(junto, lineas, escrito)
        else:
            _quitar_parentesis(izquierda, lineas)
        forma = f"{_polinomio_texto(izquierda.doit() - derecha.doit(), x)} {relacion} 0"
        return lineas, forma

    # --- Primer grado ---

    def _primer_grado(self, izquierda: Any, derecha: Any, relacion: str, x: Any, pasos: List[PasoCalculo]) -> Any:
        lineas, valor = despejar(izquierda, derecha, x, texto(izquierda), texto(derecha), relacion)
        coeficiente = sympy.expand(izquierda.doit() - derecha.doit()).coeff(x)
        final = invertir(relacion) if coeficiente.is_negative else relacion
        if relacion == "=":
            regla = tr("una ecuación de primer grado se resuelve quitando paréntesis, agrupando términos semejantes, "
                       "pasando los términos con la incógnita a un lado y los números al otro (cambiando de signo), "
                       "y dividiendo entre el coeficiente de la incógnita.")
            conjunto = sympy.FiniteSet(valor)
        else:
            regla = tr("una inecuación de primer grado se resuelve como una ecuación: sumar o restar lo mismo en los dos "
                       "lados no cambia el sentido de la desigualdad, ni multiplicar o dividir por un número positivo; "
                       "pero al multiplicar o dividir por un número negativo el sentido se invierte (< pasa a >).")
            conjunto = sympy.solveset(RELACIONES[final](x, valor), x, domain=S.Reals)
        queda = f"{x} {final} {texto(valor)}"
        if relacion != "=":
            queda = tr("{desigualdad}, es decir, el intervalo {intervalo}", desigualdad=queda,
                       intervalo=intervalo_texto(conjunto))
        pasos.append(PasoCalculo(
            tr("Despejar {variable}", variable=x),
            regla=regla,
            partes=tr("la {tipo} es {enunciado}, con una sola incógnita, {variable}.", tipo=self._tipo(relacion),
                      enunciado=self._enunciado(izquierda, derecha, relacion), variable=x),
            calculo=tuple(lineas),
            queda=queda))
        return conjunto

    # --- Segundo grado ---

    def _segundo_grado(self, izquierda: Any, derecha: Any, relacion: str, x: Any, pasos: List[PasoCalculo]) -> Any:
        lineas, forma = self._a_cero(izquierda, derecha, relacion, x)
        poli = sympy.Poly(sympy.expand(izquierda.doit() - derecha.doit()), x)
        if lineas:
            pasos.append(PasoCalculo(
                tr("Llevar a la forma general"),
                regla=tr("una {tipo} de segundo grado se escribe como a*x^2 + b*x + c {relacion} 0: se pasan todos los "
                         "términos a un lado (restar lo mismo en los dos lados no cambia la {tipo}), se quitan los "
                         "paréntesis y se agrupan los términos semejantes.", tipo=self._tipo(relacion), relacion=relacion),
                partes=tr("la {tipo} es {enunciado}.", tipo=self._tipo(relacion),
                          enunciado=self._enunciado(izquierda, derecha, relacion)),
                calculo=tuple(lineas),
                queda=forma))
        a, b, c = poli.all_coeffs()
        # Si todos los coeficientes son múltiplos de a, se divide entre a: queda x^2 + ...
        if a != 1 and a.is_Integer and (b / a).is_Integer and (c / a).is_Integer:
            nueva = invertir(relacion) if a < 0 else relacion
            p = poli.as_expr()
            terminos = [t for t in _terminos(p)]
            division = " + ".join(f"{entre_parentesis(t)}/{entre_parentesis(a)}" for t in
                                  sorted(terminos, key=lambda t: -sympy.degree(t, x)))
            a, b, c = sympy.Integer(1), b / a, c / a
            calculo = [tr("Dividimos cada término entre {a}: {division} {relacion} 0/{a2}.", a=texto(poli.LC()),
                          division=division, relacion=nueva, a2=entre_parentesis(poli.LC())),
                       tr("Operamos: {forma}.", forma=f"{_polinomio_texto(x ** 2 + b * x + c, x)} {nueva} 0")]
            if relacion != "=" and poli.LC() < 0:
                calculo.insert(0, tr("Como {a} es negativo, el sentido de la desigualdad se invierte ({antes} pasa a "
                                     "{despues}).", a=texto(poli.LC()), antes=relacion, despues=nueva))
            pasos.append(PasoCalculo(
                tr("Dividir entre el coeficiente principal"),
                regla=tr("dividir los dos lados entre el mismo número (distinto de 0) da una {tipo} equivalente; si el "
                         "número es negativo y es una inecuación, el sentido se invierte. Así el término x^2 queda con "
                         "coeficiente 1 y las cuentas son más sencillas.", tipo=self._tipo(relacion)),
                partes=tr("todos los coeficientes ({coeficientes}) son múltiplos de {a}.",
                          coeficientes=", ".join(texto(k) for k in poli.all_coeffs()), a=texto(poli.LC())),
                calculo=tuple(calculo),
                queda=f"{_polinomio_texto(x ** 2 + b * x + c, x)} {nueva} 0"))
            relacion = nueva
        raices = self._raices(a, b, c, x, relacion, pasos)
        if relacion == "=":
            return sympy.FiniteSet(*raices)
        return self._tabla_signos(a, b, c, x, raices, relacion, pasos)

    def _paso_coeficientes(self, a: Any, b: Any, c: Any, x: Any) -> str:
        return tr("a = {a} (coeficiente de {x}^2), b = {b} (coeficiente de {x}) y c = {c} (término independiente).",
                  a=texto(a), b=texto(b), c=texto(c), x=x)

    def _raices(self, a: Any, b: Any, c: Any, x: Any, relacion: str, pasos: List[PasoCalculo]) -> List[Any]:
        """Las raíces reales de a*x^2 + b*x + c = 0, de menor a mayor, con los pasos del método que corresponda."""
        polinomio = _polinomio_texto(a * x ** 2 + b * x + c, x)
        asociada = relacion != "="
        titulo = (tr("Puntos críticos: resolver {ecuacion}", ecuacion=f"{polinomio} = 0") if asociada else None)
        intro = ((tr("los puntos críticos son los valores donde el polinomio vale 0 (ahí puede cambiar de signo): se "
                     "resuelve la ecuación asociada. "),) if asociada else ())
        if c == 0:
            return self._factor_comun(a, b, x, polinomio, titulo, intro, pasos)
        if b == 0:
            return self._incompleta(a, c, x, polinomio, titulo, intro, pasos)

        # Discriminante
        delta = b ** 2 - 4 * a * c
        cuadrado, producto = b ** 2, 4 * a * c
        calculo = [tr("Sustituimos: Δ = {b}^2 - 4*{a}*{c}.", b=entre_parentesis(b), a=entre_parentesis(a),
                      c=entre_parentesis(c)),
                   tr("{b}^2 = {cuadrado} y 4*{a}*{c} = {producto}.", b=entre_parentesis(b), cuadrado=texto(cuadrado),
                      a=entre_parentesis(a), c=entre_parentesis(c), producto=texto(producto)),
                   tr("Δ = {cuadrado} - {producto} = {delta}.", cuadrado=texto(cuadrado),
                      producto=entre_parentesis(producto), delta=texto(delta))]
        if delta > 0:
            calculo.append(tr("Δ = {delta} es positivo: hay dos soluciones reales distintas.", delta=texto(delta)))
        elif delta == 0:
            calculo.append(tr("Δ = 0: hay una sola solución real (raíz doble)."))
        else:
            calculo.append(tr("Δ = {delta} es negativo: no hay soluciones reales, porque no existe la raíz cuadrada "
                              "real de un número negativo.", delta=texto(delta)))
        pasos.append(PasoCalculo(
            titulo or tr("Calcular el discriminante"),
            regla=_unir(intro, tr("el discriminante, Δ = b^2 - 4*a*c, dice cuántas soluciones reales tiene "
                                      "a*x^2 + b*x + c = 0: dos si es positivo, una (doble) si es 0 y ninguna si es negativo.")),
            partes=self._paso_coeficientes(a, b, c, x),
            calculo=tuple(calculo),
            queda=f"Δ = {texto(delta)}"))
        if delta < 0:
            return []

        par = ExplicadorFactorizar._dos_numeros(b, c) if a == 1 else None
        if par is not None and sympy.sqrt(delta).is_Integer:
            return self._por_factorizacion(b, c, x, par, polinomio, delta, pasos)
        return self._formula_general(a, b, c, x, delta, pasos)

    def _producto_nulo(self, factores: Sequence[Any], x: Any) -> Tuple[List[str], List[Any]]:
        """Cada factor igualado a 0 y despejado: 'x - 2 = 0, así que x = 2'."""
        lineas, raices = [], []
        for factor in factores:
            if factor == x:
                lineas.append(tr("{variable} = 0: ya está despejada.", variable=x))
                raices.append(S.Zero)
                continue
            cuentas, valor = despejar(factor, S.Zero, x)
            final = f"{x} = {texto(valor)}."
            if not cuentas or not cuentas[-1].endswith(final):
                cuentas.append(final)
            lineas.append(tr("{factor} = 0: {cuentas}", factor=texto(factor), cuentas=" ".join(cuentas)))
            raices.append(valor)
        return lineas, raices

    def _factor_comun(self, a, b, x, polinomio, titulo, intro, pasos) -> List[Any]:
        otro = a * x + b
        lineas = [tr("Los dos términos tienen el factor {variable}: {polinomio} = {variable}*({otro}).", variable=x,
                     polinomio=polinomio, otro=_polinomio_texto(otro, x)),
                  tr("Comprobamos multiplicando: {variable}*({otro}) = {polinomio}.", variable=x,
                     otro=_polinomio_texto(otro, x), polinomio=_polinomio_texto(x * otro, x))]
        cuentas, raices = self._producto_nulo([x, otro], x)
        pasos.append(PasoCalculo(
            titulo or tr("Factor común y producto nulo"),
            regla=_unir(intro, tr("si falta el término independiente (c = 0), se saca {variable} factor común. "
                                      "Propiedad del producto nulo: si un producto vale 0, alguno de sus factores vale 0.",
                                      variable=x)),
            partes=tr("c = 0 en {polinomio} = 0.", polinomio=polinomio),
            calculo=tuple(lineas + cuentas),
            queda=tr(" o ").join(f"{x} = {texto(r)}" for r in sorted(raices))))
        return sorted(raices)

    def _incompleta(self, a, c, x, polinomio, titulo, intro, pasos) -> List[Any]:
        cuadrado = sympy.Symbol(f"{x.name}^2", real=True)  # x^2 como incógnita: se despeja igual que x
        lineas, k = despejar(a * cuadrado + c, S.Zero, cuadrado)
        if k < 0:
            lineas.append(tr("Un cuadrado nunca es negativo: no hay ningún número real cuyo cuadrado sea {k}.", k=texto(k)))
            raices = []
            queda = tr("no tiene solución real")
        else:
            raiz = sympy.sqrt(k)
            lineas.append(tr("Los números cuyo cuadrado es {k} son sqrt({k}) y -sqrt({k}).", k=texto(k)))
            lineas += self._raiz_texto(k)
            raices = sorted({-raiz, raiz})
            queda = tr(" o ").join(f"{x} = {texto(r)}" for r in raices)
        pasos.append(PasoCalculo(
            titulo or tr("Despejar {variable}^2", variable=x),
            regla=_unir(intro, tr("si falta el término en {variable} (b = 0), se despeja {variable}^2 como en una "
                                      "ecuación de primer grado y se sacan las dos raíces cuadradas: si {variable}^2 = k "
                                      "con k positivo, {variable} = sqrt(k) o {variable} = -sqrt(k).", variable=x)),
            partes=tr("b = 0 en {polinomio} = 0.", polinomio=polinomio),
            calculo=tuple(lineas),
            queda=queda))
        return raices

    @staticmethod
    def _raiz_texto(k: Any) -> List[str]:
        """Cómo se calcula sqrt(k): exacta (sqrt(9) = 3) o sacando factores (sqrt(8) = 2*sqrt(2))."""
        raiz = sympy.sqrt(k)
        escrito = f"sqrt({texto(k)})"
        if raiz.is_Rational:
            if texto(raiz) == escrito or k in (0, 1):
                return []
            return [tr("{f} = {r}, porque {r}^2 = {v}.", f=escrito, r=texto(raiz), v=texto(k))]
        coef, resto = raiz.as_coeff_Mul()
        if coef != 1 and k.is_Integer and resto.is_Pow:
            return [tr("{v} = {c}^2*{k}, así que {f} = {r}.", v=texto(k), c=entre_parentesis(coef), k=texto(resto.base),
                       f=escrito, r=texto(raiz))]
        if texto(raiz) != escrito:
            return [f"{escrito} = {texto(raiz)}."]
        return [tr("{f} no es exacta: se deja indicada.", f=escrito)]

    def _por_factorizacion(self, b, c, x, par, polinomio, delta, pasos) -> List[Any]:
        m, n = par
        f1, f2 = x + max(m, n), x + min(m, n)  # las raíces, de menor a mayor
        lineas = [tr("Como Δ = {delta} es un cuadrado perfecto, las soluciones son racionales y el trinomio se "
                     "factoriza.", delta=texto(delta)),
                  tr("Buscamos dos números que multiplicados den {c} y sumados den {b}: {m} y {n}.", c=texto(c),
                     b=texto(b), m=texto(m), n=texto(n)),
                  tr("Comprobación: {m}*{n} = {c} y {m} + {n} = {b}.", m=entre_parentesis(m), n=entre_parentesis(n),
                     c=texto(c), b=texto(b))]
        if f1 == f2:
            lineas.append(tr("Queda {polinomio} = ({factor})^2.", polinomio=polinomio, factor=texto(f1)))
            cuentas, raices = self._producto_nulo([f1], x)
            lineas += cuentas
            lineas.append(tr("Los dos factores son iguales: es una raíz doble."))
        else:
            lineas.append(tr("Queda {polinomio} = ({f1})*({f2}).", polinomio=polinomio, f1=texto(f1), f2=texto(f2)))
            cuentas, raices = self._producto_nulo([f1, f2], x)
            lineas += cuentas
        raices = sorted(set(raices))
        pasos.append(PasoCalculo(
            tr("Factorizar y aplicar el producto nulo"),
            regla=tr("{x}^2 + b*{x} + c = ({x} + m)*({x} + n) cuando m + n = b y m*n = c: se buscan dos números "
                     "que multiplicados den c y sumados den b.", x=x) + " " +
                  tr("Propiedad del producto nulo: si un producto vale 0, alguno de sus factores vale 0."),
            partes=tr("b = {b} y c = {c}.", b=texto(b), c=texto(c)),
            calculo=tuple(lineas),
            queda=tr(" o ").join(f"{x} = {texto(r)}" for r in raices)))
        return raices

    def _formula_general(self, a, b, c, x, delta, pasos) -> List[Any]:
        raiz = sympy.sqrt(delta)
        dos_a = 2 * a
        lineas = [tr("Sustituimos: {variable} = (-{b} ± sqrt({delta}))/(2*{a}) = ({nb} ± sqrt({delta}))/{dos_a}.",
                     variable=x, b=entre_parentesis(b), delta=texto(delta), a=entre_parentesis(a), nb=texto(-b),
                     dos_a=entre_parentesis(dos_a))]
        lineas += self._raiz_texto(delta)
        raices = []
        signos = ("+", "-") if delta != 0 else ("+",)
        for i, signo in enumerate(signos, 1):
            numerador = -b + raiz if signo == "+" else -b - raiz
            valor = sympy.radsimp(numerador / dos_a)
            nombre = f"{x}{i}" if delta != 0 else f"{x}"
            escrito = (f"({texto(-b)} {signo} {texto(raiz)})/{entre_parentesis(dos_a)}" if raiz != 0
                       else f"{entre_parentesis(-b)}/{entre_parentesis(dos_a)}")
            cuentas = [escrito]
            if raiz.is_Rational:
                if raiz != 0:
                    cuentas.append(f"{entre_parentesis(numerador)}/{entre_parentesis(dos_a)}")
            elif -b != 0:
                cuentas.append(f"{entre_parentesis(-b)}/{entre_parentesis(dos_a)} {signo} "
                               f"{texto(raiz) if raiz.is_Pow else entre_parentesis(raiz)}/{entre_parentesis(dos_a)}")
            if texto(valor) not in cuentas:
                cuentas.append(texto(valor))
            lineas.append(f"{nombre} = " + " = ".join(cuentas) + ".")
            raices.append(valor)
        if delta == 0:
            lineas.append(tr("Con Δ = 0, sumar o restar sqrt(0) da lo mismo: es una raíz doble."))
        raices = sorted(set(raices), key=lambda r: float(r))
        pasos.append(PasoCalculo(
            tr("Aplicar la fórmula general"),
            regla=tr("las soluciones de a*x^2 + b*x + c = 0 son x = (-b ± sqrt(Δ))/(2*a): una con + y otra con -."),
            partes=self._paso_coeficientes(a, b, c, x) + " " + tr("Δ = {delta}.", delta=texto(delta)),
            calculo=tuple(lineas),
            queda=tr(" o ").join(f"{x} = {texto(r)}" for r in raices)))
        return raices

    # --- Tabla de signos ---

    @staticmethod
    def _punto_de_prueba(inicio: Any, fin: Any) -> Any:
        """Un número cómodo dentro del intervalo abierto (inicio, fin): 0 si está dentro, si no un entero."""
        if (inicio == S.NegativeInfinity or inicio < 0) and (fin == S.Infinity or fin > 0):
            return S.Zero
        if inicio == S.NegativeInfinity:
            return sympy.floor(fin) - 1 if fin.is_Integer else sympy.floor(fin)
        if fin == S.Infinity:
            return sympy.ceiling(inicio) + 1 if inicio.is_Integer else sympy.ceiling(inicio)
        entero = sympy.floor(inicio) + 1
        return entero if entero < fin else (inicio + fin) / 2

    def _tabla_signos(self, a, b, c, x, raices, relacion, pasos) -> Any:
        polinomio = _polinomio_texto(a * x ** 2 + b * x + c, x)
        expresion = f"{polinomio} {relacion} 0"
        if not raices:
            # Δ < 0: el polinomio no cambia de signo
            linea, valor = _cuenta(a * x ** 2 + b * x + c, x, S.Zero)
            signo = sympy.sign(a)
            cumple = bool(_CUMPLE[relacion](signo, 0))
            conjunto = S.Reals if cumple else S.EmptySet
            pasos.append(PasoCalculo(
                tr("Signo del polinomio"),
                regla=tr("si el polinomio no tiene raíces reales, nunca vale 0 y no cambia de signo: tiene siempre el "
                         "signo de a."),
                partes=tr("a = {a}, que es {signo}.", a=texto(a), signo=_signo_texto(a)),
                calculo=(tr("Lo comprobamos con {variable} = 0: {cuenta}, {signo}.", variable=x, cuenta=linea,
                            signo=_signo_texto(valor)),
                         tr("{polinomio} es siempre {signo}, así que {expresion} {veredicto}.", polinomio=polinomio,
                            signo=_signo_texto(a), expresion=expresion,
                            veredicto=tr("se cumple para todo número real") if cumple else tr("no se cumple nunca"))),
                queda=describir_conjunto(conjunto, x)))
            return conjunto

        # Factores: a*(x - r1)*(x - r2) o a*(x - r)^2
        factores = [x - r for r in raices] if len(raices) == 2 else [x - raices[0], x - raices[0]]
        if len(raices) == 2:
            factorizado = f"{entre_parentesis(a) + '*' if a != 1 else ''}({texto(factores[0])})*({texto(factores[1])})"
        else:
            factorizado = f"{entre_parentesis(a) + '*' if a != 1 else ''}({texto(factores[0])})^2"
        puntos = sorted(raices, key=float)
        bordes = [S.NegativeInfinity] + puntos + [S.Infinity]
        intervalos = [sympy.Interval.open(i, f) for i, f in zip(bordes, bordes[1:])]
        lineas = [tr("Factorizamos con las raíces: {polinomio} = {factorizado}.", polinomio=polinomio, factorizado=factorizado),
                  (tr("Los puntos críticos {puntos} dividen la recta en {n} intervalos: {intervalos}.",
                      puntos=tr(" y ").join(texto(p) for p in puntos), n=len(intervalos),
                      intervalos=", ".join(intervalo_texto(i) for i in intervalos)) if len(puntos) > 1 else
                   tr("El punto crítico {punto} divide la recta en 2 intervalos: {intervalos}.", punto=texto(puntos[0]),
                      intervalos=", ".join(intervalo_texto(i) for i in intervalos)))]
        elegidos = []
        for intervalo in intervalos:
            punto = self._punto_de_prueba(intervalo.start, intervalo.end)
            lineas.append(tr("Intervalo {intervalo}: probamos con {variable} = {punto}.",
                             intervalo=intervalo_texto(intervalo), variable=x, punto=texto(punto)))
            signos = []
            if a != 1:
                lineas.append(tr("   a = {a}: {signo}.", a=texto(a), signo=_signo_texto(a)))
                signos.append("+" if a > 0 else "-")
            vistos = []
            for factor in factores:
                if factor in vistos:
                    signos.append(signos[-1])
                    continue
                vistos.append(factor)
                cuenta, valor = _cuenta(factor, x, punto)
                lineas.append(tr("   {factor} = {cuenta}: {signo}.", factor=texto(factor), cuenta=cuenta,
                                 signo=_signo_texto(valor)))
                signos.append("+" if valor > 0 else "-")
            if len(raices) == 1:
                lineas.append(tr("   El factor ({factor})^2 aparece dos veces: su signo se repite.",
                                 factor=texto(factores[0])))
            negativos = signos.count("-")
            resultado = "+" if negativos % 2 == 0 else "-"
            cumple = bool(_CUMPLE[relacion](1 if resultado == "+" else -1, 0))
            lineas.append(tr("   Producto de signos: {signos} = {resultado}. El polinomio es {signo}: {veredicto} {expresion}.",
                             signos="*".join(f"({s})" for s in signos), resultado=resultado,
                             signo=tr("positivo") if resultado == "+" else tr("negativo"),
                             veredicto=tr("cumple") if cumple else tr("no cumple"), expresion=expresion))
            if cumple:
                elegidos.append(intervalo)
        estricta = relacion in ("<", ">")
        lineas.append(tr("En los puntos críticos el polinomio vale 0: como la desigualdad es {relacion}, {decision}.",
                         relacion=relacion, decision=tr("no se incluyen (0 no es {cmp} 0)", cmp=relacion) if estricta
                         else tr("se incluyen (0 {cmp} 0 es cierto)", cmp=relacion)))
        conjunto = sympy.Union(*elegidos) if elegidos else S.EmptySet
        if not estricta:
            conjunto = sympy.Union(conjunto, sympy.FiniteSet(*puntos))
        pasos.append(PasoCalculo(
            tr("Tabla de signos"),
            regla=tr("un producto es positivo si tiene un número par de factores negativos, y negativo si es impar. "
                     "Entre dos puntos críticos seguidos el polinomio no cambia de signo, así que basta probar un "
                     "número de cada intervalo."),
            partes=(tr("{expresion}, con puntos críticos {puntos}.", expresion=expresion,
                       puntos=tr(" y ").join(texto(p) for p in puntos)) if len(puntos) > 1 else
                    tr("{expresion}, con un solo punto crítico: {punto}.", expresion=expresion, punto=texto(puntos[0]))),
            calculo=tuple(lineas),
            queda=describir_conjunto(conjunto, x)))
        return conjunto

    # --- Racionales ---

    def _racional(self, izquierda: Any, derecha: Any, x: Any) -> Tuple[List[PasoCalculo], Any]:
        pasos: List[PasoCalculo] = []
        terminos = [(lado, t) for lado, expr in (("izq", izquierda), ("der", derecha)) for t in _terminos(expr)]
        denominadores = []
        for _, t in terminos:
            d = sympy.fraction(sympy.together(t.doit()))[1]
            if d.has(x) and all(sympy.simplify(d - e) != 0 for e in denominadores):
                denominadores.append(d)

        # 1. Restricciones del dominio
        prohibidos: List[Any] = []
        lineas = []
        # Primero los de grado 1: los factores de los demás que ya se vieron no se repiten
        for d in sorted(denominadores, key=lambda d: sympy.degree(d, x)):
            ceros = sorted(set(sympy.solveset(d, x, domain=S.Reals)), key=float)
            factorizado = sympy.factor(d)
            texto_d = texto(d) if texto(factorizado) == texto(d) else f"{texto(d)} = {texto(factorizado)}"
            if not ceros:
                lineas.append(tr("El denominador {denominador} no se anula para ningún número real.", denominador=texto_d))
            elif sympy.degree(d, x) == 1:
                lineas += self._producto_nulo([d], x)[0]
            elif all(sympy.degree(f, x) <= 1 for f in sympy.Mul.make_args(factorizado)):
                # (x - 2)*(x + 2): cada factor con x igualado a 0
                lineas.append(tr("Factorizamos el denominador: {denominador}. Se anula si alguno de sus factores vale 0.",
                                 denominador=texto_d))
                for f in (f for f in sympy.Mul.make_args(factorizado) if f.has(x)):
                    cero = sympy.solve(f, x)[0]
                    if cero in prohibidos:
                        lineas.append(tr("{factor} = 0 da {variable} = {valor}, que ya está entre las restricciones.",
                                         factor=texto(f), variable=x, valor=texto(cero)))
                    else:
                        lineas += self._producto_nulo([f], x)[0]
            else:
                lineas.append(tr("{denominador}: se anula en {valores}.", denominador=texto_d,
                                 valores=tr(" y ").join(f"{x} = {texto(c)}" for c in ceros)))
            prohibidos += [c for c in ceros if c not in prohibidos]
        prohibidos.sort(key=float)
        restriccion = ", ".join(f"{x} ≠ {texto(p)}" for p in prohibidos) or tr("ninguna")
        pasos.append(PasoCalculo(
            tr("Restricciones del dominio"),
            regla=tr("una fracción no está definida si su denominador vale 0: esos valores de {variable} quedan fuera "
                     "del dominio y no pueden ser solución, aunque aparezcan al resolver.", variable=x),
            partes=tr("los denominadores con {variable} son {denominadores}.", variable=x,
                      denominadores="; ".join(texto(d) for d in denominadores)),
            calculo=tuple(lineas),
            queda=restriccion))

        # 2. Multiplicar por el MCM de los denominadores (también los numéricos)
        todos = [sympy.fraction(sympy.together(t.doit()))[1] for _, t in terminos]
        mcm = sympy.factor(reduce(sympy.lcm, todos, S.One))
        lineas = [tr("MCM de los denominadores: {mcm}.", mcm=texto(mcm))]
        nuevos = {"izq": [], "der": []}
        for lado, t in terminos:
            num, den = sympy.fraction(sympy.together(t.doit()))
            cociente = sympy.factor(sympy.cancel(mcm / den))
            if cociente == 1:
                nuevo = num
            elif num == 1:
                nuevo = cociente
            else:
                nuevo = sympy.Mul(num, cociente, evaluate=False)
            nuevo = _preparar(nuevo) if not isinstance(nuevo, sympy.Mul) else nuevo
            nuevos[lado].append(nuevo)
            if den == 1:
                lineas.append(tr("{termino} por {mcm} = {resultado}.", termino=entre_parentesis(t), mcm=entre_parentesis(mcm),
                                 resultado=texto(nuevo)))
            else:
                lineas.append(tr("{termino} por {mcm}: se simplifica el denominador {den} y queda {resultado}.",
                                 termino=texto(t.doit()), mcm=entre_parentesis(mcm), den=texto(den), resultado=texto(nuevo)))
        nueva_izq = (sympy.Add(*nuevos["izq"], evaluate=False) if len(nuevos["izq"]) > 1 else nuevos["izq"][0])
        nueva_der = (sympy.Add(*nuevos["der"], evaluate=False) if len(nuevos["der"]) > 1 else nuevos["der"][0])
        pasos.append(PasoCalculo(
            tr("Multiplicar por el MCM de los denominadores"),
            regla=tr("multiplicar los dos lados por el mínimo común múltiplo de los denominadores (que no vale 0 dentro "
                     "del dominio) da una ecuación sin fracciones: cada término se multiplica por el MCM y se simplifica "
                     "su denominador."),
            partes=tr("la ecuación es {enunciado}; los denominadores son {denominadores}.",
                      enunciado=self._enunciado(izquierda, derecha, "="),
                      denominadores="; ".join(texto(d) for d in todos if d != 1) or "1"),
            calculo=tuple(lineas),
            queda=f"{texto(nueva_izq)} = {texto(nueva_der)}"))

        # 3. La ecuación polinómica que queda
        diferencia = sympy.expand(nueva_izq.doit() - nueva_der.doit())
        if diferencia.has(x) and sympy.Poly(diferencia, x).degree() > 2:
            raise SinExplicacion()
        candidatos = self._polinomica(nueva_izq, nueva_der, "=", x, pasos)

        # 4. Descartar las raíces extrañas
        lineas = []
        if candidatos == S.Reals:
            conjunto = sympy.Complement(S.Reals, sympy.FiniteSet(*prohibidos)) if prohibidos else S.Reals
            lineas.append(tr("La ecuación sin fracciones se cumple siempre, pero los valores prohibidos ({restriccion}) "
                             "no están en el dominio.", restriccion=restriccion))
        else:
            validas = []
            for r in sorted(candidatos, key=float):
                if any(sympy.simplify(r - p) == 0 for p in prohibidos):
                    anulados = [texto(d) for d in denominadores if sympy.simplify(d.subs(x, r)) == 0]
                    lineas.append(tr("{variable} = {valor} anula el denominador {denominador}: no está en el dominio. Es "
                                     "una raíz extraña (apareció al multiplicar por el MCM) y se descarta.", variable=x,
                                     valor=texto(r), denominador=tr(" y ").join(anulados)))
                else:
                    lineas.append(tr("{variable} = {valor} no anula ningún denominador: es válida.", variable=x,
                                     valor=texto(r)))
                    validas.append(r)
            conjunto = sympy.FiniteSet(*validas)
            if not candidatos:
                lineas.append(tr("La ecuación sin fracciones no tiene solución: la original tampoco."))
        pasos.append(PasoCalculo(
            tr("Descartar las raíces extrañas"),
            regla=tr("multiplicar por una expresión con la incógnita puede añadir soluciones falsas: los valores que "
                     "anulan un denominador se descartan."),
            partes=tr("soluciones de la ecuación sin fracciones: {candidatos}; restricciones: {restriccion}.",
                      candidatos=describir_conjunto(candidatos, x, aproximar=False), restriccion=restriccion),
            calculo=tuple(lineas),
            queda=describir_conjunto(conjunto, x, aproximar=False)))
        if isinstance(conjunto, sympy.FiniteSet) and conjunto:
            pasos.append(self._paso_comprobar(izquierda, derecha, "=", x, conjunto))
        return pasos, conjunto

    # --- Comprobación ---

    def _linea_comprobar(self, izquierda, derecha, relacion, x, valor, como: str = "") -> Tuple[str, bool]:
        cuenta_izq, v_izq = _cuenta(izquierda, x, valor)
        cuenta_der, v_der = _cuenta(derecha, x, valor)
        if relacion == "=":
            cumple = sympy.simplify(v_izq - v_der) == 0
            afirmacion = f"{texto(v_izq)} = {texto(v_der)}"
        else:
            cumple = bool(_CUMPLE[relacion](sympy.N(v_izq - v_der), 0))
            afirmacion = f"{texto(v_izq)} {relacion} {texto(v_der)}"
        return tr("{variable} = {valor}{como}: lado izquierdo {izquierda}; lado derecho {derecha}; {afirmacion} "
                  "{veredicto}.", variable=x, valor=texto(valor), como=como, izquierda=cuenta_izq, derecha=cuenta_der,
                  afirmacion=afirmacion, veredicto=tr("se cumple") if cumple else tr("NO se cumple")), cumple

    def _paso_comprobar(self, izquierda, derecha, relacion, x, conjunto) -> PasoCalculo:
        lineas = []
        if relacion == "=":
            if isinstance(conjunto, sympy.FiniteSet) and conjunto:
                for r in sorted(conjunto, key=float):
                    lineas.append(self._linea_comprobar(izquierda, derecha, relacion, x, r)[0])
            else:
                punto = S.Zero
                lineas.append(self._linea_comprobar(izquierda, derecha, relacion, x, punto,
                                                    tr(" (un valor cualquiera)"))[0])
            regla = tr("se sustituye cada solución en la ecuación original: los dos lados deben valer lo mismo.")
        else:
            # Un punto de cada intervalo (dentro y fuera de la solución) y los extremos
            bordes = sorted({e for p in _piezas(conjunto) for e in p.boundary if e.is_finite} if conjunto not in
                            (S.EmptySet, S.Reals) else set(), key=float)
            limites = [S.NegativeInfinity] + bordes + [S.Infinity]
            for i, f in zip(limites, limites[1:]):
                punto = self._punto_de_prueba(i, f)
                dentro = conjunto.contains(punto) == S.true
                lineas.append(self._linea_comprobar(izquierda, derecha, relacion, x, punto,
                                                    tr(" (dentro de la solución)") if dentro else
                                                    tr(" (fuera de la solución)"))[0])
            for e in bordes:
                dentro = conjunto.contains(e) == S.true
                lineas.append(self._linea_comprobar(izquierda, derecha, relacion, x, e,
                                                    tr(" (extremo incluido)") if dentro else tr(" (extremo excluido)"))[0])
            regla = tr("se sustituye en la inecuación original un número de cada intervalo y los extremos: debe "
                       "cumplirse exactamente en los que forman la solución.")
        return PasoCalculo(
            tr("Comprobación"),
            regla=regla,
            partes=tr("la {tipo} original es {enunciado}.", tipo=self._tipo(relacion),
                      enunciado=self._enunciado(izquierda, derecha, relacion)),
            calculo=tuple(lineas),
            queda=describir_conjunto(conjunto, x))
