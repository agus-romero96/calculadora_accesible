"""Restricciones de denominadores recogidas antes de evaluar el árbol original.

Una cancelación conserva los valores en el dominio, pero no los puntos excluidos.
Se recorren también los denominadores anidados y los términos multiplicados por 0.
No se infiere aquí el dominio de funciones ni de potencias de exponente simbólico.
"""
from typing import Any, Tuple

import sympy
from sympy import S

from calculo.pasos import texto
from i18n import tr


def decimales_exactos(expr: Any) -> Any:
    """Interpreta los decimales escritos como racionales sin cancelar el árbol."""
    reemplazos = {f: sympy.Rational(str(f)) for f in expr.atoms(sympy.Float)}
    with sympy.evaluate(False):
        return expr.xreplace(reemplazos)


def denominadores_originales(*expresiones: Any) -> Tuple[Any, ...]:
    denominadores = []
    for expr in expresiones:
        for nodo in sympy.preorder_traversal(expr):
            if nodo.is_Pow and nodo.exp.is_negative:
                if nodo.base not in denominadores:
                    denominadores.append(nodo.base)
    return tuple(denominadores)


def restricciones_denominadores(*expresiones: Any) -> Tuple[Any, ...]:
    """Condiciones simbólicas, también con parámetros; False significa dominio vacío."""
    condiciones = []
    for den in denominadores_originales(*expresiones):
        # Las restricciones de la fracción dentro de den ya se recogieron al recorrerla.
        num = sympy.fraction(sympy.together(decimales_exactos(den).doit()))[0]
        for factor in sympy.Mul.make_args(sympy.factor(num)):
            base, exponente = factor.as_base_exp()
            if exponente.is_Integer and exponente.is_positive:
                factor = base
            condicion = sympy.Ne(factor, 0)
            if condicion is S.false:
                return (S.false,)
            if condicion is not S.true and condicion not in condiciones:
                condiciones.append(condicion)
    return tuple(condiciones)


def dominio_real(restricciones: Tuple[Any, ...], variable: Any) -> Any:
    """Dominio real permitido por los denominadores de una expresión univariada."""
    dominio = S.Reals
    for condicion in restricciones:
        if condicion is S.false:
            return S.EmptySet
        ceros = sympy.solveset(condicion.lhs - condicion.rhs, variable, domain=S.Reals)
        dominio = dominio - ceros
    return dominio


def textos_restricciones(restricciones: Tuple[Any, ...]) -> list:
    if S.false in restricciones:
        return ["0 ≠ 0"]
    return [f"{texto(c.lhs)} ≠ {texto(c.rhs)}" for c in restricciones if c not in (S.true, S.false)]


def aviso_restricciones(restricciones: Tuple[Any, ...]) -> str:
    if S.false in restricciones:
        return tr("Un denominador de la expresión original vale 0: no hay valores admitidos.")
    return tr("Restricciones de los denominadores originales: {restricciones}. Se mantienen aunque la expresión se simplifique.",
              restricciones="; ".join(textos_restricciones(restricciones)))


def comprobar_candidato(izquierda: Any, derecha: Any, variable: Any, valor: Any) -> Any:
    """True, False o None: sustituye antes de evaluar, sin aceptar aproximaciones."""
    izq = izquierda.subs(variable, valor).doit()
    der = derecha.subs(variable, valor).doit()
    if any(lado.has(S.ComplexInfinity, S.NaN, S.Infinity, S.NegativeInfinity) for lado in (izq, der)):
        return False
    diferencia = sympy.simplify(izq - der)
    return True if diferencia == 0 else diferencia.equals(0)
