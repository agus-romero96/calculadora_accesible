"""Restricciones de denominadores recogidas antes de evaluar el árbol original.

Una cancelación conserva los valores en el dominio, pero no los puntos excluidos.
Se recorren también los denominadores anidados y los términos multiplicados por 0.
Las restricciones de denominadores no bastan para validar funciones reales;
dominio_funciones_originales realiza una comprobación conservadora adicional.
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


def dominio_funciones_originales(variable: Any, *expresiones: Any) -> Any:
    """Interseca dominios continuos de cada nodo, antes de cualquier cancelación.

    Es conservador: las funciones que continuous_domain no soporta se rechazan,
    en vez de interpretar la falta de restricciones como dominio real completo.
    Recorrer los hijos evita perder restricciones en 0*f(x), f(x)/f(x) o f(x)^0.
    """
    from sympy.calculus.util import continuous_domain

    dominio = S.Reals
    for expr in expresiones:
        for nodo in sympy.preorder_traversal(expr):
            if not nodo.free_symbols:
                valor = nodo.doit()
                if valor.is_real is not True or valor.is_finite is not True:
                    return S.EmptySet
            elif nodo.is_Function or nodo.is_Pow:
                evaluado = nodo.doit()
                if nodo.is_Pow:
                    # Solo se normaliza una copia del exponente. El recorrido sigue
                    # usando el árbol original, incluidas sus divisiones y funciones.
                    exponente = decimales_exactos(nodo.exp).doit()
                    if (exponente.is_Rational is not True
                            and not (nodo.base.is_positive is True and exponente.is_real is True)):
                        raise NotImplementedError("Potencia sin dominio real validado")
                    evaluado = sympy.Pow(nodo.base.doit(), exponente)
                    if exponente.is_Rational and exponente.q != 1:
                        # Pow usa la rama compleja principal, no real_root:
                        # incluso con denominador impar, las bases negativas
                        # no tienen potencia real para un racional no entero.
                        condicion = (sympy.Gt(nodo.base.doit(), 0) if exponente < 0
                                     else sympy.Ge(nodo.base.doit(), 0))
                        dominio = dominio.intersect(sympy.solveset(condicion, variable, domain=S.Reals))
                permitido = continuous_domain(evaluado, variable, S.Reals)
                if permitido.has(sympy.ConditionSet):
                    raise NotImplementedError("Dominio sin determinar")
                dominio = dominio.intersect(permitido)
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
