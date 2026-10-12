"""
Serialización de objetos SymPy sin evaluarlos.

La usan el historial (para guardarlo en disco) y el proceso de cálculo (para traer
el resultado desde el otro proceso). Con el pickle normal de SymPy, cada nodo se
reconstruye con su constructor, que evalúa: el planteamiento "1/6 + 1/3" volvería
como 1/2 y la ecuación y = y de un sistema con infinitas soluciones como True.
"""
import io
import pickle

from sympy import Atom, Basic, Function, Set
from sympy.concrete.expr_with_limits import ExprWithLimits
from sympy.core.function import AppliedUndef
from sympy.core.parameters import evaluate


def _sin_evaluar(cls, args):
    with evaluate(False):
        return cls(*args)


def _funcion(nombre, real, args):
    """y(x) de una ecuación diferencial: su clase se crea al vuelo y pickle no la encuentra por nombre."""
    return Function(nombre, real=real)(*args)


class _Pickler(pickle.Pickler):
    def reducer_override(self, obj):
        if isinstance(obj, AppliedUndef):
            return _funcion, (obj.func.__name__, bool(obj.is_real), obj.args)
        # Cada nodo se reconstruye sin evaluar, salvo las integrales (y sumas), cuyo
        # constructor no calcula nada pero sin evaluar añadiría un "1*" al integrando, y los
        # conjuntos solución de una ecuación: ya están en forma canónica, y Union sin evaluar
        # falla (necesita comparar los extremos de los intervalos).
        if isinstance(obj, Basic) and not isinstance(obj, (Atom, ExprWithLimits, Set)):
            return _sin_evaluar, (type(obj), obj.args)
        return NotImplemented


def a_bytes(objeto) -> bytes:
    buffer = io.BytesIO()
    _Pickler(buffer, protocol=4).dump(objeto)
    return buffer.getvalue()


def de_bytes(datos: bytes):
    return pickle.loads(datos)
