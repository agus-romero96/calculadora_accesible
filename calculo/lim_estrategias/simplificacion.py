from __future__ import annotations

from typing import Any, List, Optional

import sympy
from sympy import S

from ._base import (
    Estrategia,
    ResultadoEstrategia,
    ESTADO_FINITO,
    ESTADO_INFINITO,
    ESTADO_NO_CONCLUYENTE,
)


class SimplificacionCancelacion(Estrategia):
    """
    Estrategia: Simplificación / Cancelación (álgebra previa)

    Objetivo:
      - Resolver límites que se arreglan con álgebra básica:
        * fracciones anidadas
        * factores comunes que se cancelan
        * simplificación de una forma 0/0 que se vuelve evaluable

    Herramientas (suaves):
      - together(): pone todo en una sola fracción sin reescribir agresivo
      - cancel(): cancela factores comunes en fracciones racionales/simbólicas
      - factor(): opcional, ayuda a revelar factores (muy útil en (x^2-1)/(x-1))
    """

    def nombre(self) -> str:
        return "Simplificación y cancelación"

    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        # Es un agente “barato”: casi siempre puede intentar si la expr depende de var.
        try:
            return var in expr.free_symbols
        except Exception:
            return True

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        dir_ = kwargs.get("dir", None)
        pasos: List[str] = []
        pasos.append("Intentamos simplificación algebraica (together + cancel) antes de métodos especiales.")

        expr_trabajo = expr

        # 1) Agrupar fracciones (fracción de fracciones -> fracción simple)
        try:
            expr_t = sympy.together(expr_trabajo)
            if expr_t != expr_trabajo:
                pasos.append(f"Aplicamos together(): {expr_t}")
            expr_trabajo = expr_t
        except Exception as e:
            pasos.append(f"(Aviso) together() falló: {e}")

        # 2) Cancelación de factores comunes
        try:
            expr_c = sympy.cancel(expr_trabajo)
            if expr_c != expr_trabajo:
                pasos.append(f"Aplicamos cancel(): {expr_c}")
            expr_trabajo = expr_c
        except Exception as e:
            pasos.append(f"(Aviso) cancel() falló: {e}")

        # 3) Factorización ligera (solo si parece racional y ayuda a cancelar)
        #    Nota: factor() puede ser costoso, así que lo aplicamos con cuidado.
        try:
            num, den = expr_trabajo.as_numer_denom()
            # Si ambos “parecen” polinomiales en var, factor puede ayudar
            if num.is_polynomial(var) and den.is_polynomial(var):
                num_f = sympy.factor(num)
                den_f = sympy.factor(den)
                expr_f = sympy.cancel(num_f / den_f)
                if expr_f != expr_trabajo:
                    pasos.append(f"Factorizamos num/den y recancelamos: {expr_f}")
                    expr_trabajo = expr_f
        except Exception:
            # silencioso: factor es opcional
            pass

        # Si no cambió nada, no tiene sentido “ganar” este agente
        if sympy.srepr(expr_trabajo) == sympy.srepr(expr):
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion="No hubo simplificación/cancelación útil (la expresión quedó esencialmente igual).",
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr_trabajo,
            )

        # 4) Intentar evaluar límite
        val = self._limite_seguro(expr_trabajo, var, punto, dir_)

        if not self._es_limite_evaluable(val):
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion="Se simplificó la expresión, pero el límite aún no se pudo evaluar directamente.",
                pasos=pasos + [f"Límite tras simplificar quedó no evaluado: {val}"],
                expr_original=expr,
                expr_trabajo=expr_trabajo,
            )

        # 5) Estado coherente
        res_final = sympy.simplify(val)
        estado = ESTADO_FINITO
        if res_final in (S.Infinity, S.NegativeInfinity) or getattr(res_final, "is_infinite", False):
            estado = ESTADO_INFINITO

        pasos.append(f"Evaluamos el límite de la expresión simplificada: {res_final}")

        return ResultadoEstrategia(
            aplica=True,
            estado=estado,
            resultado=res_final,
            nombre_estrategia=self.nombre(),
            explicacion="Álgebra básica (simplificación/cancelación) dejó el límite evaluable.",
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr_trabajo,
        )

    # ---------------- helpers ----------------

    def _limite_seguro(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> Any:
        try:
            if dir_ in ("+", "-"):
                return sympy.limit(expr, var, punto, dir=dir_)
            return sympy.limit(expr, var, punto)
        except Exception:
            return sympy.Limit(expr, var, punto, dir=dir_) if dir_ in ("+", "-") else sympy.Limit(expr, var, punto)

    def _es_limite_evaluable(self, val: Any) -> bool:
        if val is None:
            return False
        if val is sympy.nan or val is sympy.zoo:
            return False
        if isinstance(val, sympy.Limit):
            return False
        return True
