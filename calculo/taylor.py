"""
Polinomio de Taylor de orden n de f(x) alrededor de x = x0, explicado con el formato de
calculo/pasos.py (Regla, En este caso, las cuentas y Queda):

  1. La fórmula: P_n(x) = suma de f^(k)(x0)/k! * (x - x0)^k para k = 0, ..., n.
  2. Las derivadas f', f'', ..., f^(n), cada una a partir de la anterior con el paso a paso de
     Derivar (como Derivada de orden N: si se hace demasiado larga, solo los resultados).
  3. Un paso por término: f^(k)(x0) con sus cuentas, k! desarrollado, el coeficiente
     f^(k)(x0)/k! y el término. Si f^(k)(x0) = 0, el término no aparece.
  4. La suma de los términos, en potencias de (x - x0), tras verificar derivadas bilaterales.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import sympy
from sympy import S

from calculo.calculo import MAX_PASOS_DERIVADA, MAX_PASOS_ENESIMA, Calculo
from calculo.derivadas import ExplicadorDerivada
from calculo.derivabilidad import dominio_original, derivada_bilateral, avisar_potencias
from calculo.pasos import PasoCalculo, entre_parentesis, texto, texto_paso
from calculo.rectas import cuentas_sustitucion
from i18n import tr

# Más allá de este orden, las derivadas (y la explicación) crecen demasiado
ORDEN_MAXIMO = 15


@dataclass
class ResultadoTaylor:
    texto: str
    es_error: bool = False
    polinomio: Any = None
    variable: Any = None
    expresion: Any = None
    orden: Optional[int] = None
    punto: Any = None
    avisos: List[str] = field(default_factory=list)


def _potencia(x: Any, x0: Any, k: int) -> Any:
    """(x - x0)^k, o x^k si x0 = 0."""
    return (x - x0) ** k


def potencia_texto(x: Any, x0: Any, k: int) -> str:
    """'x', '(x - 1)^2': la potencia de (x - x0) sin desarrollar (SymPy escribiría x/4 - 1 en lugar de (x - 4)/4)."""
    base = texto(x) if x0 == 0 else f"({texto(x - x0)})"
    return base if k == 1 else f"{base}^{k}"


def termino_texto(coeficiente: Any, x: Any, x0: Any, k: int) -> str:
    """Un término c*(x - x0)^k como se escribe a mano: (x - 4)/4, -(x - 1)^2/2, 3*(x - 1)^2, sqrt(2)*x/2."""
    if k == 0:
        return texto(coeficiente)
    potencia = potencia_texto(x, x0, k)
    c = sympy.sympify(coeficiente)
    if c.is_Rational:
        signo = "-" if c < 0 else ""
        p, q = abs(c.p), c.q
        numerador = potencia if p == 1 else f"{p}*{potencia}"
        return signo + (numerador if q == 1 else f"{numerador}/{q}")
    if c.could_extract_minus_sign():
        return f"-{entre_parentesis(-c)}*{potencia}"
    return f"{entre_parentesis(c)}*{potencia}"


def suma_terminos(textos: List[str]) -> str:
    """Los términos sumados, con los negativos restando: 1 + x - x^3/6."""
    if not textos:
        return "0"
    partes = [textos[0]]
    for t in textos[1:]:
        partes.append(f"- {t[1:]}" if t.startswith("-") else f"+ {t}")
    return " ".join(partes)


def _coeficientes(polinomio: Any, x: Any, x0: Any) -> List[tuple]:
    """[(k, c)] de polinomio = suma de c*(x - x0)^k, de menor a mayor k (sin los nulos)."""
    t = sympy.Dummy("t")
    poli = sympy.Poly(sympy.expand(sympy.sympify(polinomio).subs(x, t + x0)), t)
    return [(k, sympy.simplify(c)) for (k,), c in sorted(poli.terms(), key=lambda e: e[0][0]) if c != 0]


def taylor_latex(polinomio: Any, x: Any, x0: Any, n: int) -> str:
    """P_{n}(x) = 2 + \\frac{\\left(x - 4\\right)}{4} - ...: en potencias de (x - x0) sin desarrollar."""
    base = sympy.latex(x) if x0 == 0 else r"\left(" + sympy.latex(x - x0) + r"\right)"
    partes = []
    for k, c in _coeficientes(polinomio, x, x0):
        potencia = "" if k == 0 else (base if k == 1 else f"{base}^{{{k}}}")
        negativo = c.could_extract_minus_sign()
        a = -c if negativo else c
        if k == 0:
            cuerpo = sympy.latex(a)
        elif a.is_Rational:
            numerador = potencia if a.p == 1 else f"{a.p} {potencia}"
            cuerpo = numerador if a.q == 1 else rf"\frac{{{numerador}}}{{{a.q}}}"
        else:
            cuerpo = (rf"\left({sympy.latex(a)}\right) " if a.is_Add else f"{sympy.latex(a)} ") + potencia
        partes.append(("- " if negativo else "+ ") + cuerpo)
    suma = " ".join(partes) if partes else "+ 0"
    suma = ("-" + suma[2:]) if suma.startswith("- ") else suma[2:]
    return f"P_{{{n}}}\\left({sympy.latex(x)}\\right) = {suma}"


def taylor_texto(polinomio: Any, x: Any, x0: Any) -> str:
    """El polinomio en potencias de (x - x0), de menor a mayor grado: 1 + (x - 1)/2 - (x - 1)^2/8."""
    return suma_terminos([termino_texto(c, x, x0, k) for k, c in _coeficientes(polinomio, x, x0)])


def nombre_polinomio(n: int, x: Any) -> str:
    return f"P_{n}({x})"


def _factorial_texto(k: int) -> str:
    """'3! = 1*2*3 = 6'; 0! y 1! valen 1."""
    if k == 0:
        return tr("0! = 1 (por definición).")
    if k == 1:
        return "1! = 1."
    return f"{k}! = {'*'.join(str(i) for i in range(1, k + 1))} = {sympy.factorial(k)}."


class MotorTaylor:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido
        self.calculo = Calculo(parser_compartido)

    def resolver(self, expresion: str, variable: Optional[str], orden: Any, punto: str) -> ResultadoTaylor:
        try:
            original = self.parser.parsear(expresion)
            expr = original.doit()
            x, avisos = self.calculo._resolver_variable(expr, variable, "DERIVADA")
            avisar_potencias(original, avisos)
            try:
                n = int(orden)
            except (TypeError, ValueError):
                raise ValueError(tr("El orden debe ser un número entero."))
            if n < 0 or n > ORDEN_MAXIMO:
                raise ValueError(tr("El orden debe estar entre 0 y {maximo}.", maximo=ORDEN_MAXIMO))
            if not str(punto or "").strip():
                raise ValueError(tr("Falta el punto x0 alrededor del que se desarrolla."))
            x0 = self.parser.parsear(punto).doit()
            if x0.free_symbols or not x0.is_real or not x0.is_finite:
                raise ValueError(tr("El punto debe ser un número real (ej: 1, -2, pi/4)."))
            dominio = dominio_original(original, x)
            if dominio.contains(x0) is not S.true:
                raise ValueError(tr("f({variable}) no está definida en {variable} = {valor} dentro del dominio real original.", variable=x, valor=texto(x0)))
            anterior = expr
            valor = sympy.simplify(expr.subs(x, x0))
            for k in range(1, n + 1):
                valor = derivada_bilateral(original if k == 1 else anterior, anterior, x, x0, valor)
                anterior = sympy.diff(anterior, x)
                simbolico = sympy.simplify(anterior.subs(x, x0))
                if sympy.simplify(simbolico - valor) != 0:
                    raise ValueError(tr("No concluyente: la expresión simbólica no representa la derivada en el punto."))
            avisos.append(tr("Se verifican las derivadas bilaterales hasta el orden solicitado. Esto no demuestra la convergencia de una serie de Taylor."))
            return self._explicar(expr, x, n, x0, avisos)
        except ValueError as e:
            return ResultadoTaylor(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except Exception as e:
            return ResultadoTaylor(tr("Error del Sistema: {error}", error=str(e)), es_error=True)

    def _explicar(self, expr: Any, x: Any, n: int, x0: Any, avisos: List[str]) -> ResultadoTaylor:
        nombres = [Calculo._nombre_derivada(k, x) for k in range(n + 1)]
        nombre_x0 = f"{x}0"
        maclaurin = x0 == 0
        pasos = [PasoCalculo(
            tr("Fórmula de Taylor"),
            regla=tr("el polinomio de Taylor de orden n de f alrededor de {x0} es P_n({variable}) = f({x0}) + "
                     "f'({x0})*({variable} - {x0}) + f''({x0})/2!*({variable} - {x0})^2 + ... + "
                     "f^(n)({x0})/n!*({variable} - {x0})^n: cada término usa una derivada evaluada en {x0}, dividida "
                     "entre el factorial de su orden.", x0=nombre_x0, variable=x)
                  + (" " + tr("Alrededor de 0 se llama polinomio de Maclaurin.") if maclaurin else ""),
            partes=tr("f({variable}) = {funcion}, n = {n} y {x0} = {valor}.", variable=x, funcion=texto(expr), n=n,
                      x0=nombre_x0, valor=texto(x0)),
            calculo=(tr("Hacen falta las derivadas hasta la de orden {n} ({lista}), evaluadas en {valor}.", n=n,
                        lista=", ".join(nombres[1:]) or "-", valor=texto(x0)),) if n else
                    (tr("Con n = 0, el polinomio es solo el primer término, f({x0}).", x0=nombre_x0),),
            queda=f"{nombre_polinomio(n, x)} = " + " + ".join(
                [f"f({texto(x0)})"] + [f"{nombres[k].replace(f'({x})', f'({texto(x0)})')}/{k}!*"
                                       f"{entre_parentesis(_potencia(x, x0, k)) if k > 1 else entre_parentesis(x - x0)}"
                                       for k in range(1, n + 1)]))]

        # Las derivadas, como en Derivada de orden N
        derivadas = [expr]
        explicar = True
        simplificar_cada = 2 if n <= 6 else 3
        for k in range(1, n + 1):
            anterior = derivadas[-1]
            actual = sympy.diff(anterior, x)
            if k % simplificar_cada == 0 or k == n:
                actual = sympy.simplify(actual)
            derivadas.append(actual)
            if explicar:
                sub_pasos = Calculo._explicar_derivada(ExplicadorDerivada(x), anterior, actual, avisos)
                explicar = bool(sub_pasos) and len(sub_pasos) <= MAX_PASOS_DERIVADA and len(pasos) <= MAX_PASOS_ENESIMA
                if explicar:
                    pasos.append(Calculo._paso_orden(k, nombres, anterior))
                    pasos.extend(sub_pasos)
                    continue
                if sub_pasos:
                    avisos.append(tr("Desde la derivada {i} se muestra solo el resultado de cada derivada: "
                                     "la explicación completa sería demasiado larga.", i=k))
            pasos.append(Calculo._paso_orden(k, nombres, anterior, actual))

        # Un término por derivada
        terminos = []
        for k, derivada in enumerate(derivadas):
            valor = sympy.simplify(derivada.subs(x, x0))
            if not valor.is_finite or valor.has(sympy.I) or valor is S.NaN:
                raise ValueError(tr("{nombre} no está definida en {variable} = {valor}: no hay polinomio de Taylor "
                                    "alrededor de ese punto.", nombre=nombres[k], variable=x, valor=texto(x0)))
            factorial = sympy.factorial(k)
            coeficiente = sympy.simplify(valor / factorial)
            evaluada = nombres[k].replace(f"({x})", f"({texto(x0)})")
            lineas = [tr("{nombre} en {variable} = {valor}:", nombre=nombres[k], variable=x, valor=texto(x0))]
            lineas += ["   " + l for l in cuentas_sustitucion(derivada, x, x0, valor)]
            lineas.append(_factorial_texto(k))
            potencia = _potencia(x, x0, k)
            if valor == 0:
                lineas.append(tr("{evaluada} = 0: el término vale 0 y no aparece en el polinomio.", evaluada=evaluada))
                queda = tr("término {k}: 0", k=k)
            else:
                division = f"{entre_parentesis(valor)}/{factorial}"
                lineas.append(tr("Coeficiente: {evaluada}/{k}! = {division} = {coeficiente}.", evaluada=evaluada, k=k,
                                 division=division, coeficiente=texto(coeficiente))
                              if division != texto(coeficiente) else
                              tr("Coeficiente: {evaluada}/{k}! = {coeficiente}.", evaluada=evaluada, k=k,
                                 coeficiente=texto(coeficiente)))
                termino = termino_texto(coeficiente, x, x0, k)
                if k > 0:
                    producto = f"{entre_parentesis(coeficiente)}*{potencia_texto(x, x0, k)}"
                    lineas.append(tr("Término: {coeficiente}*{potencia} = {termino}.", coeficiente=entre_parentesis(coeficiente),
                                     potencia=potencia_texto(x, x0, k), termino=termino) if producto != termino else
                                  tr("Término: {termino}.", termino=termino))
                terminos.append((coeficiente * potencia, termino))
                queda = tr("término {k}: {termino}", k=k, termino=termino)
            pasos.append(PasoCalculo(
                tr("Término {k} (orden {k})", k=k),
                regla=(tr("el término de orden 0 es f({x0}): el valor de la función en el punto.", x0=nombre_x0) if k == 0
                       else tr("el término de orden {k} es {nombre}({x0})/{k}! * ({variable} - {x0})^{k}.", k=k,
                               nombre=nombres[k].replace(f"({x})", ""), x0=nombre_x0, variable=x)),
                partes=f"{nombres[k]} = {texto(derivada)}.",
                calculo=tuple(lineas),
                queda=queda))

        polinomio = sympy.Add(*[valor for valor, _ in terminos]) if terminos else S.Zero
        resultado_txt = suma_terminos([t for _, t in terminos])
        pasos.append(PasoCalculo(
            tr("Sumar los términos"),
            regla=tr("el polinomio de Taylor es la suma de todos los términos, de menor a mayor orden."),
            partes=tr("términos distintos de 0: {terminos}.", terminos="; ".join(t for _, t in terminos)
                      or tr("ninguno")),
            calculo=(f"{nombre_polinomio(n, x)} = {resultado_txt}.",),
            queda=f"{nombre_polinomio(n, x)} = {resultado_txt}"))

        lineas = [tr("RESULTADO: {valor}", valor=f"{nombre_polinomio(n, x)} = {resultado_txt}")] + avisos + [
            "=" * 30,
            tr("Función: f({variable}) = {funcion}", variable=x, funcion=texto(expr)),
            tr("Orden: {n}; punto: {x0} = {valor}", n=n, x0=nombre_x0, valor=texto(x0))]
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoTaylor("\n".join(lineas), polinomio=polinomio, variable=x, expresion=expr, orden=n, punto=x0,
                               avisos=avisos)
