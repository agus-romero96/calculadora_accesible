from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

import sympy


# Estados matemáticos explícitos (evita mezclar "None", "zoo", etc. sin control)
ESTADO_FINITO = "FINITO"
ESTADO_INFINITO = "INFINITO"
ESTADO_NO_EXISTE = "NO_EXISTE"
ESTADO_NO_CONCLUYENTE = "NO_CONCLUYENTE"


@dataclass(frozen=True)
class ResultadoEstrategia:
    aplica: bool
    estado: str = ESTADO_NO_CONCLUYENTE
    resultado: Optional[Any] = None

    nombre_estrategia: str = ""
    explicacion: str = ""
    pasos: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)

    # Para trazabilidad / debug didáctico
    expr_original: Optional[Any] = None
    expr_trabajo: Optional[Any] = None

    # Para fallback uniforme
    fue_fallback: bool = False


def es_punto_finito(punto: Any) -> bool:
    try:
        return punto is not None and punto.is_finite is True
    except Exception:
        return False


def limite_seguro(expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str] = None) -> Any:
    """
    Límite con la semántica de un curso de cálculo:
      - dir_ "+" o "-": límite lateral.
      - Sin dir_ y punto finito: límite BILATERAL (dir="+-").
        Ojo: sympy.limit() sin dir calcula solo el lateral derecho.
      - Sin dir_ y punto ±oo: límite normal.

    Devuelve:
      - el valor (puede ser oo, -oo o zoo si diverge sin signo definido),
      - sympy.nan si los laterales existen pero no coinciden (el límite no existe),
      - None si SymPy no pudo calcularlo.
    """
    try:
        if dir_ in ("+", "-"):
            return sympy.limit(expr, var, punto, dir=dir_)
        if es_punto_finito(punto):
            return sympy.limit(expr, var, punto, dir="+-")
        return sympy.limit(expr, var, punto)
    except ValueError as e:
        # SymPy lanza ValueError cuando los laterales difieren con dir="+-"
        if "does not exist" in str(e):
            return sympy.nan
        return None
    except Exception:
        return None


def es_limite_evaluable(val: Any) -> bool:
    """True si val es un valor concreto (finito o ±oo): no None, nan, zoo ni Limit sin evaluar."""
    if val is None or val is sympy.nan or val is sympy.zoo:
        return False
    return (not isinstance(val, (sympy.Limit, sympy.AccumBounds))
            and not val.has(sympy.Limit, sympy.AccumBounds)
            and (val.is_finite is True or val in (sympy.oo, -sympy.oo)))


class Estrategia(ABC):
    def _limite_seguro(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> Any:
        return limite_seguro(expr, var, punto, dir_)

    def _es_limite_evaluable(self, val: Any) -> bool:
        return es_limite_evaluable(val)

    @abstractmethod
    def nombre(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        raise NotImplementedError
