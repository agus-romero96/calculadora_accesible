"""
Pasos comunes de las explicaciones de límites, con el formato de calculo/pasos.py
(Regla, En este caso, cuentas, Queda):

  - paso_sustitucion: lo primero, sustituir. Dice qué sale (un valor, o la forma
    indeterminada 0/0, ∞/∞, k/0...) y por qué hace falta otro método.
  - paso_evaluacion: el final, el límite de una expresión ya transformada, con la
    sustitución y sus cuentas o con la regla del cociente que corresponda (k/∞ = 0...).
"""
from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

import sympy
from sympy import S, Symbol

from calculo.pasos import PasoCalculo, entre_parentesis, texto
from i18n import N_, tr

from ._base import es_punto_finito, limite_seguro

# Formas del cociente al sustituir
FORMA_CERO_CERO = "0/0"
FORMA_INF_INF = "∞/∞"
FORMA_K_CERO = "k/0"
FORMA_INF_MENOS_INF = "∞ - ∞"
FORMA_VALOR = "valor"


def tendencia(var: Any, punto: Any, dir_: Optional[str] = None) -> str:
    """'x → 2', 'x → 0+' o 'x → oo'."""
    return f"{var} → {punto}{dir_ or ''}"


def sustituir_texto(expr: Any, var: Symbol, punto: Any) -> str:
    """La expresión con el punto escrito en lugar de la variable, sin calcular: '1^2 - 1'."""
    nombre = texto(punto)
    if not (punto.is_Symbol or (punto.is_Integer and punto >= 0)):
        nombre = f"({nombre})"
    escrita = texto(expr.subs(var, Symbol(nombre)))
    return re.sub(r"\(\(([^()]+)\)\)", r"(\1)", escrita)


def valor_texto(valor: Any) -> str:
    if valor is None:
        return tr("no se puede calcular")
    if valor is sympy.nan or isinstance(valor, sympy.AccumBounds):
        return tr("no existe")
    if valor is sympy.zoo:
        return tr("infinito, con signo distinto a cada lado")
    return texto(valor)


def es_infinito(valor: Any) -> bool:
    return valor in (S.Infinity, S.NegativeInfinity)


def cuenta(expr: Any, var: Symbol, punto: Any) -> Optional[str]:
    """'1^2 - 1 = 0' si el punto es finito y la sustitución da un número; si no, None."""
    if not es_punto_finito(punto):
        return None
    try:
        valor = sympy.simplify(expr.subs(var, punto))
    except Exception:
        return None
    if valor.has(sympy.nan, sympy.zoo, S.Infinity, S.NegativeInfinity) or valor.is_finite is not True:
        return None
    escrita = sustituir_texto(expr, var, punto)
    if escrita == texto(valor):
        return escrita
    num, den = expr.as_numer_denom()
    if den.has(var):
        # (2^2 + 2*2 + 4)/(2 + 2) = 12/4 = 3: primero numerador y denominador
        num_valor, den_valor = sympy.simplify(num.subs(var, punto)), sympy.simplify(den.subs(var, punto))
        intermedio = f"{entre_parentesis(num_valor)}/{entre_parentesis(den_valor)}"
        if intermedio not in (escrita, texto(valor)):
            return f"{escrita} = {intermedio} = {texto(valor)}"
    return f"{escrita} = {texto(valor)}"


def _tiende(expr: Any, var: Symbol, punto: Any, dir_: Optional[str]) -> Tuple[Any, str]:
    """(límite, texto de cómo se obtiene): la cuenta si se puede sustituir, si no 'tiende a'."""
    texto_cuenta = cuenta(expr, var, punto)
    if texto_cuenta is not None:
        return sympy.simplify(expr.subs(var, punto)), texto_cuenta
    valor = limite_seguro(expr, var, punto, dir_)
    return valor, tr("{expresion} tiende a {valor}", expresion=texto(expr), valor=valor_texto(valor))


def forma_del_cociente(num_lim: Any, den_lim: Any) -> str:
    if num_lim == 0 and den_lim == 0:
        return FORMA_CERO_CERO
    if es_infinito(num_lim) and es_infinito(den_lim):
        return FORMA_INF_INF
    if den_lim == 0 and num_lim is not None and num_lim != 0:
        return FORMA_K_CERO
    return FORMA_VALOR


REGLA_SUSTITUCION = N_("lo primero es sustituir: si la función es continua en el punto, el límite es su valor ahí. "
                       "Si sale una forma indeterminada (0/0, ∞/∞, ∞ - ∞, 0*∞, 1^∞), sustituir no basta y hay que "
                       "transformar la expresión.")


def paso_sustitucion(expr: Any, var: Symbol, punto: Any,
                     dir_: Optional[str] = None) -> Tuple[Optional[PasoCalculo], str]:
    """
    Paso de la sustitución directa en un cociente (o en la expresión): (paso, forma).
    En el infinito no se puede sustituir: se dice a qué tienden numerador y denominador.
    Sin paso (None) si no hay nada que mostrar (un polinomio en el infinito: lo explica su método).
    """
    num, den = sympy.together(expr).as_numer_denom()
    calculo: List[str] = []
    if den.has(var):
        num_lim, num_texto = _tiende(num, var, punto, dir_)
        den_lim, den_texto = _tiende(den, var, punto, dir_)
        calculo.append(tr("Numerador: {cuenta}.", cuenta=num_texto))
        calculo.append(tr("Denominador: {cuenta}.", cuenta=den_texto))
        forma = forma_del_cociente(num_lim, den_lim)
        if forma == FORMA_CERO_CERO:
            calculo.append(tr("Sale 0/0, una forma indeterminada: el límite puede valer cualquier cosa, "
                              "así que hay que transformar la expresión."))
        elif forma == FORMA_INF_INF:
            calculo.append(tr("Sale ∞/∞, una forma indeterminada: hay que comparar a qué velocidad crecen "
                              "numerador y denominador."))
        elif forma == FORMA_K_CERO:
            calculo.append(tr("Sale un número distinto de 0 entre 0: el cociente se hace tan grande como se quiera; "
                              "falta ver el signo a cada lado."))
    else:
        forma = FORMA_VALOR
        texto_cuenta = cuenta(expr, var, punto)
        if texto_cuenta is not None:
            calculo.append(tr("Sustituimos: {cuenta}.", cuenta=texto_cuenta))
        elif expr.is_Add:
            # sqrt(x + 1) - sqrt(x) en oo: cada término por separado
            limites = []
            for termino in expr.as_ordered_terms():
                valor, texto_termino = _tiende(termino, var, punto, dir_)
                limites.append(valor)
                calculo.append(tr("Término {termino}: {cuenta}.", termino=texto(termino), cuenta=texto_termino))
            if S.Infinity in limites and S.NegativeInfinity in limites:
                forma = FORMA_INF_MENOS_INF
                calculo.append(tr("Sale ∞ - ∞, una forma indeterminada: los dos términos crecen y no se sabe "
                                  "cuál gana, así que hay que transformar la expresión."))
    if not calculo:
        return None, forma
    paso = PasoCalculo(
        tr("Sustitución directa"),
        regla=tr(REGLA_SUSTITUCION),
        partes=tr("buscamos el límite de {expresion} cuando {tendencia}.", expresion=texto(expr),
                  tendencia=tendencia(var, punto, dir_)),
        calculo=tuple(calculo))
    return paso, forma


def paso_evaluacion(expr: Any, var: Symbol, punto: Any, dir_: Optional[str], valor: Any,
                    titulo: str = N_("Calcular el límite")) -> PasoCalculo:
    """El límite de una expresión ya sin indeterminación: sustituyendo, o por la regla del cociente."""
    texto_cuenta = cuenta(expr, var, punto)
    if texto_cuenta is not None:
        return PasoCalculo(
            tr(titulo),
            regla=tr("esta expresión es continua en el punto: el límite es su valor ahí."),
            partes=tr("sustituimos {variable} = {punto}.", variable=var, punto=punto),
            calculo=(tr("Sustituimos: {cuenta}.", cuenta=texto_cuenta),),
            queda=valor_texto(valor))

    num, den = sympy.together(expr).as_numer_denom()
    calculo: List[str] = []
    regla = tr("se calcula a qué tiende cada parte y se combinan.")
    if den.has(var):
        num_lim, num_texto = _tiende(num, var, punto, dir_)
        den_lim, den_texto = _tiende(den, var, punto, dir_)
        calculo += [tr("Numerador: {cuenta}.", cuenta=num_texto), tr("Denominador: {cuenta}.", cuenta=den_texto)]
        if es_infinito(den_lim) and num_lim is not None and num_lim.is_finite:
            regla = tr("un número fijo dividido entre algo que crece sin límite tiende a 0.")
        elif es_infinito(num_lim) and den_lim is not None and den_lim.is_finite and den_lim != 0:
            regla = tr("algo que crece sin límite dividido entre un número fijo distinto de 0 crece sin límite, "
                       "con el signo del cociente.")
        elif den_lim == 0 and num_lim is not None and num_lim != 0:
            regla = tr("un número distinto de 0 dividido entre algo que tiende a 0 crece sin límite; "
                       "el signo depende de los signos de numerador y denominador.")
    else:
        calculo.append(tr("{expresion} tiende a {valor} cuando {tendencia}.", expresion=texto(expr),
                          valor=valor_texto(valor), tendencia=tendencia(var, punto, dir_)))
    return PasoCalculo(
        tr(titulo),
        regla=regla,
        partes=tr("buscamos el límite de {expresion} cuando {tendencia}.", expresion=texto(expr),
                  tendencia=tendencia(var, punto, dir_)),
        calculo=tuple(calculo),
        queda=valor_texto(valor))
