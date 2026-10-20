"""Certificación local mediante dominio original y cocientes incrementales reales."""
import sympy as sp

from dominios import dominio_funciones_originales, dominio_real, restricciones_denominadores
from calculo.router import RouterMatematico
from calculo.pasos import texto
from i18n import tr


def avisar_potencias(original, avisos):
    for nodo in sp.preorder_traversal(original):
        if nodo.is_Pow:
            exponente = nodo.exp.doit()
            if exponente.is_Rational and exponente.q > 1 and exponente.q % 2:
                avisos.append(tr("Las potencias fraccionarias usan la rama compleja principal: una base negativa no representa una raíz impar real. El estudio se restringe al dominio real de esa expresión."))
                break


def dominio_original(original, x):
    try:
        return dominio_funciones_originales(x, original).intersect(
            dominio_real(restricciones_denominadores(original), x))
    except Exception as exc:
        raise ValueError(tr("No concluyente: no se puede certificar el dominio real original.")) from exc


def cocientes(original, expr, x, a, valor=None):
    """Laterales del cociente, nunca valores aislados de la derivada simbólica."""
    dominio = dominio_original(original, x)
    if dominio.contains(a) is not sp.S.true:
        raise ValueError(tr("La función no está definida en el punto solicitado dentro de su dominio real original."))
    valor = sp.simplify(expr.subs(x, a)) if valor is None else valor
    if valor.is_real is not True or valor.is_finite is not True:
        raise ValueError(tr("La función no tiene un valor real finito en el punto solicitado."))
    laterales = {}
    for lado in ("-", "+"):
        estado = RouterMatematico._lado_real(original, x, a, lado)
        if estado is None:
            raise ValueError(tr("No concluyente: no se puede certificar un entorno real lateral."))
        if estado:
            h = sp.Dummy("h", positive=True)
            desplazamiento = h if lado == "+" else -h
            q = (expr.subs(x, a + desplazamiento) - valor) / desplazamiento
            try:
                continuo = sp.limit(expr.subs(x, a + desplazamiento), h, 0, dir="+")
                if sp.simplify(continuo - valor) != 0:
                    raise ValueError(tr("La función no es continua por todos los lados reales disponibles; no se justifica una tangente."))
                laterales[lado] = sp.limit(q, h, 0, dir="+")
                if laterales[lado].has(sp.AccumBounds, sp.Limit):
                    raise ValueError(tr("No concluyente: no se pudo calcular el cociente incremental."))
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError(tr("No concluyente: no se pudo calcular el cociente incremental.")) from exc
    return laterales


def derivada_bilateral(original, expr, x, a, valor=None):
    lados = cocientes(original, expr, x, a, valor)
    if len(lados) != 2:
        raise ValueError(tr("No hay derivada bilateral: el punto es un extremo unilateral del dominio."))
    izq, der = lados["-"], lados["+"]
    if izq.is_real is not True or izq.is_finite is not True or sp.simplify(izq - der) != 0:
        raise ValueError(tr("No existe la derivada bilateral: cociente incremental izquierdo {izquierda}; derecho {derecha}.",
                            izquierda=texto(izq), derecha=texto(der)))
    return izq
