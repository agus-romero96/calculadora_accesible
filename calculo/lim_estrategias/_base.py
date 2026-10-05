from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional


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


class Estrategia(ABC):
    @abstractmethod
    def nombre(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        raise NotImplementedError
