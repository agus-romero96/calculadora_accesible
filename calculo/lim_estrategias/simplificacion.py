from __future__ import annotations

from typing import Any, List, Optional

import sympy

from i18n import N_, tr
from ._base import (
    Estrategia,
    ResultadoEstrategia,
    ESTADO_FINITO,
    ESTADO_NO_CONCLUYENTE,
    es_punto_finito,
)


class SimplificacionCancelacion(Estrategia):
    """
    Estrategia: Simplificación / Cancelación (álgebra previa)

    Objetivo:
      - Resolver límites 0/0 en un punto finito que se arreglan con álgebra básica:
        * fracciones anidadas
        * factores comunes que se cancelan (ej: (x^2-1)/(x-1) en x=1)

    Solo "gana" si la cancelación realmente elimina la indeterminación:
      1) la sustitución directa en la forma original da 0/0, y
      2) tras simplificar, la sustitución directa da un valor finito.
    Si no se cumple, devuelve NO_CONCLUYENTE y el router prueba otra estrategia
    (así no se atribuye a "simplificación" un límite que en realidad resolvió SymPy).

    Herramientas (suaves):
      - together(): pone todo en una sola fracción sin reescribir agresivo
      - cancel(): cancela factores comunes en fracciones racionales/simbólicas
      - factor(): opcional, ayuda a revelar factores
    """

    def nombre(self) -> str:
        return N_("Simplificación y cancelación")

    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        try:
            return es_punto_finito(punto) and var in expr.free_symbols
        except Exception:
            return False

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        pasos: List[str] = []
        pasos.append(tr("Intentamos simplificación algebraica (together + cancel) antes de métodos especiales."))

        # 0) ¿Hay realmente una indeterminación 0/0 que cancelar?
        try:
            num0, den0 = sympy.together(expr).as_numer_denom()
            n0 = sympy.simplify(num0.subs(var, punto))
            d0 = sympy.simplify(den0.subs(var, punto))
        except Exception:
            return self._no_concluyente(expr, expr, pasos, tr("No se pudo evaluar la sustitución directa."))

        if not (n0 == 0 and d0 == 0):
            return self._no_concluyente(expr, expr, pasos, tr("La sustitución directa no produce 0/0: no hay factor que cancelar."))

        pasos.append(tr("Sustitución directa x = {punto}: numerador → 0 y denominador → 0 (forma 0/0).", punto=punto))

        expr_trabajo = expr

        # 1) Agrupar fracciones (fracción de fracciones -> fracción simple)
        try:
            expr_t = sympy.together(expr_trabajo)
            if expr_t != expr_trabajo:
                pasos.append(tr("Aplicamos together(): {expr_t}", expr_t=expr_t))
            expr_trabajo = expr_t
        except Exception as e:
            pasos.append(tr("(Aviso) together() falló: {e}", e=e))

        # 2) Cancelación de factores comunes
        try:
            expr_c = sympy.cancel(expr_trabajo)
            if expr_c != expr_trabajo:
                pasos.append(tr("Aplicamos cancel(): {expr_c}", expr_c=expr_c))
            expr_trabajo = expr_c
        except Exception as e:
            pasos.append(tr("(Aviso) cancel() falló: {e}", e=e))

        # 3) Factorización ligera (solo si num/den son polinomios en var)
        try:
            num, den = expr_trabajo.as_numer_denom()
            if num.is_polynomial(var) and den.is_polynomial(var):
                expr_f = sympy.cancel(sympy.factor(num) / sympy.factor(den))
                if expr_f != expr_trabajo:
                    pasos.append(tr("Factorizamos num/den y recancelamos: {expr_f}", expr_f=expr_f))
                    expr_trabajo = expr_f
        except Exception:
            # silencioso: factor es opcional
            pass

        # 4) Tras simplificar, ¿la sustitución directa ya es un valor finito?
        try:
            val = sympy.simplify(expr_trabajo.subs(var, punto))
        except Exception:
            val = None

        if val is None or val.is_finite is not True:
            return self._no_concluyente(
                expr, expr_trabajo,
                pasos + [tr("Tras simplificar, la sustitución sigue sin dar un valor finito: {val}", val=val)],
                tr("La simplificación no eliminó la indeterminación."),
            )

        pasos.append(tr("La expresión simplificada es continua en x = {punto}; sustituimos: {val}", punto=punto, val=val))

        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_FINITO,
            resultado=val,
            nombre_estrategia=self.nombre(),
            explicacion=N_("Cancelar el factor común eliminó la indeterminación 0/0."),
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr_trabajo,
        )

    def _no_concluyente(self, expr: Any, expr_trabajo: Any, pasos: List[str], explicacion: str) -> ResultadoEstrategia:
        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_NO_CONCLUYENTE,
            resultado=None,
            nombre_estrategia=self.nombre(),
            explicacion=explicacion,
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr_trabajo,
        )
