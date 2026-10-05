from __future__ import annotations

from typing import Any, Tuple, List, Optional

import sympy
from sympy import S

from ._base import (
    Estrategia,
    ResultadoEstrategia,
    ESTADO_FINITO,
    ESTADO_INFINITO,
    ESTADO_NO_CONCLUYENTE,
)


class LimitesTrigNotables(Estrategia):
    """
    Estrategia robusta para límites trigonométricos notables mediante
    “Extracción de Núcleo”.

    Núcleos:
      A) sin(u)/u -> 1
      B) tan(u)/u -> 1
      C) (1 - cos(u))/u^2 -> 1/2

    Aplica cuando (para el punto pedido):
      - u(x) -> 0
      - el límite del “resto” existe y se evalúa (no queda como Limit)
    """

    def nombre(self) -> str:
        return "Límites trigonométricos notables"

    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        if not (expr.has(sympy.sin) or expr.has(sympy.cos) or expr.has(sympy.tan)):
            return False

        dir_ = kwargs.get("dir", None)

        ok, *_ = self._match_sin(expr, var, punto, dir_)
        if ok:
            return True
        ok, *_ = self._match_tan(expr, var, punto, dir_)
        if ok:
            return True
        ok, *_ = self._match_one_minus_cos(expr, var, punto, dir_)
        return ok

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        dir_ = kwargs.get("dir", None)

        pasos: List[str] = []
        pasos.append("Buscamos un núcleo trigonométrico notable (sin series).")

        ok, u, resto, lim_resto = self._match_sin(expr, var, punto, dir_)
        if ok:
            pasos.append("Detectamos un candidato tipo sin(u).")
            pasos.append(f"  • u = {u}")
            pasos.append("Construimos el núcleo K = sin(u)/u, cuyo límite es 1 si u→0.")
            pasos.append("Separamos: expr = K * R, donde R = expr / K.")
            pasos.append(f"  • R = {resto}")
            pasos.append(f"Calculamos lim R = {lim_resto}")
            pasos.append("Aplicamos: lim sin(u)/u = 1.")
            res = sympy.simplify(lim_resto)
            pasos.append(f"Resultado final: 1 * {lim_resto} = {res}")
            return self._ok(expr, pasos, res, f"Extracción de núcleo sin(u)/u con u={u}")

        ok, u, resto, lim_resto = self._match_tan(expr, var, punto, dir_)
        if ok:
            pasos.append("Detectamos un candidato tipo tan(u).")
            pasos.append(f"  • u = {u}")
            pasos.append("Construimos el núcleo K = tan(u)/u, cuyo límite es 1 si u→0.")
            pasos.append(f"R = expr / K = {resto}")
            pasos.append(f"Calculamos lim R = {lim_resto}")
            pasos.append("Aplicamos: lim tan(u)/u = 1.")
            res = sympy.simplify(lim_resto)
            pasos.append(f"Resultado final: {res}")
            return self._ok(expr, pasos, res, f"Extracción de núcleo tan(u)/u con u={u}")

        ok, u, resto, lim_resto = self._match_one_minus_cos(expr, var, punto, dir_)
        if ok:
            pasos.append("Detectamos un candidato tipo (1 - cos(u)).")
            pasos.append(f"  • u = {u}")
            pasos.append("Construimos el núcleo K = (1 - cos(u))/u^2, cuyo límite es 1/2 si u→0.")
            pasos.append(f"R = expr / K = {resto}")
            pasos.append(f"Calculamos lim R = {lim_resto}")
            pasos.append("Aplicamos: lim (1-cos(u))/u^2 = 1/2.")
            res = sympy.simplify(sympy.Rational(1, 2) * lim_resto)
            pasos.append(f"Resultado final: 1/2 * {lim_resto} = {res}")
            return self._ok(expr, pasos, res, f"Extracción de núcleo (1-cos(u))/u^2 con u={u}")

        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_NO_CONCLUYENTE,
            resultado=None,
            nombre_estrategia=self.nombre(),
            pasos=["Parecía trigonométrico, pero no se pudo aislar un núcleo notable con un resto evaluable."],
            avisos=["Requiere identidad adicional, encaje u otro método."],
            expr_original=expr,
            expr_trabajo=expr,
        )

    # ---------------- helpers ----------------

    def _ok(self, expr: Any, pasos: List[str], res: Any, explicacion: str) -> ResultadoEstrategia:
        # ✅ FIX: estado coherente con el valor del resultado
        estado = ESTADO_FINITO
        if res in (S.Infinity, S.NegativeInfinity) or getattr(res, "is_infinite", False):
            estado = ESTADO_INFINITO

        return ResultadoEstrategia(
            aplica=True,
            estado=estado,
            resultado=res,
            nombre_estrategia=self.nombre(),
            explicacion=explicacion,
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr,
        )

    def _prep(self, expr: Any) -> Any:
        try:
            # ✅ FIX: normalización liviana, sin simplify() para no romper patrones
            return sympy.together(sympy.cancel(expr))
        except Exception:
            return expr

    def _u_tiende_a_0(self, u: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> bool:
        lu = self._limite_seguro(u, var, punto, dir_)
        if not self._es_limite_evaluable(lu):
            return False
        try:
            return sympy.simplify(lu) == 0
        except Exception:
            return False

    # ---------------- matching núcleo ----------------

    def _match_sin(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> Tuple[bool, Any, Any, Any]:
        return self._match_generic(expr, var, punto, dir_, sympy.sin)

    def _match_tan(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> Tuple[bool, Any, Any, Any]:
        return self._match_generic(expr, var, punto, dir_, sympy.tan)

    def _match_generic(
        self,
        expr: Any,
        var: sympy.Symbol,
        punto: Any,
        dir_: Optional[str],
        func_type,
    ) -> Tuple[bool, Any, Any, Any]:
        """
        Intenta escribir:
          expr = (func(u)/u) * R
        => R = expr * (u/func(u))

        Requisitos:
          - u(x) -> 0 cuando x -> punto (mismo dir)
          - lim R existe y se evalúa
        """
        expr_s = self._prep(expr)
        num, _ = expr_s.as_numer_denom()

        # ✅ FIX: en SymPy NO se usa isinstance(t, sympy.sin). Se usa t.func == sympy.sin / tan
        candidates = [t for t in sympy.preorder_traversal(num) if getattr(t, "func", None) == func_type]

        for term in candidates:
            u = term.args[0]

            # Chequeo correcto: u(x) -> 0 en el punto pedido
            if not self._u_tiende_a_0(u, var, punto, dir_):
                continue

            # Construimos resto: R = expr * u / func(u)
            try:
                resto_expr = sympy.simplify(expr_s * (u / term))
            except Exception:
                continue

            lim_resto = self._limite_seguro(resto_expr, var, punto, dir_)
            if not self._es_limite_evaluable(lim_resto):
                continue

            return True, u, resto_expr, sympy.simplify(lim_resto)

        return False, None, None, None

    def _match_one_minus_cos(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> Tuple[bool, Any, Any, Any]:
        """
        Intenta escribir:
          expr = ((1 - cos(u))/u^2) * R
        => R = expr * u^2 / (1 - cos(u))
        """
        expr_s = self._prep(expr)

        # Buscamos cos(u) en toda la expresión (no solo numerador, aquí da igual)
        candidates = [t for t in sympy.preorder_traversal(expr_s) if getattr(t, "func", None) == sympy.cos]

        for cos_u in candidates:
            u = cos_u.args[0]

            if not self._u_tiende_a_0(u, var, punto, dir_):
                continue

            denom = (1 - cos_u)
            # Si aparece cos(u)-1, esto lo maneja el signo en el resto automáticamente
            try:
                resto_expr = sympy.simplify(expr_s * (u**2) / denom)
            except Exception:
                continue

            lim_resto = self._limite_seguro(resto_expr, var, punto, dir_)
            if not self._es_limite_evaluable(lim_resto):
                continue

            return True, u, resto_expr, sympy.simplify(lim_resto)

        return False, None, None, None
