from __future__ import annotations

from typing import Any, List, Optional, Tuple

import sympy
from sympy import S
from sympy.assumptions import Q, ask

from ._base import (
    Estrategia,
    ResultadoEstrategia,
    ESTADO_FINITO,
    ESTADO_INFINITO,
    ESTADO_NO_CONCLUYENTE,
)


class ContinuidadComposicion(Estrategia):
    """
    Estrategia: Continuidad por composición (f(g(x))).

    Teorema:
      Si g(x)->L y f es continua en L, entonces lim f(g(x)) = f(L).

    V1.5 (sin router interno):
      - Para calcular L, hacemos ayuda ligera:
        1) together/cancel del inner
        2) intento local de trig notable (sin(u)/u, tan(u)/u, (1-cos(u))/u^2)
        3) sympy.limit
    """

    def nombre(self) -> str:
        return "Continuidad por composición"

    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        # Solo si depende de var
        try:
            if var not in expr.free_symbols:
                return False
        except Exception:
            pass

        outer, inner = self._extraer_compuesta(expr)
        return outer is not None and inner is not None and self._es_funcion_externa_conocida(outer)

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        dir_ = kwargs.get("dir", None)

        pasos: List[str] = []
        pasos.append("Buscamos una forma compuesta f(g(x)) y aplicamos continuidad si corresponde.")

        outer, inner = self._extraer_compuesta(expr)
        if outer is None or inner is None:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion="No se pudo identificar una composición directa f(g(x)).",
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr,
            )

        pasos.append(f"Identificamos función externa: f(·) = {self._repr_outer(outer)}")
        pasos.append(f"Identificamos función interna: g(x) = {inner}")

        # 1) Calcular L = lim g(x) con ayuda V1.5
        L = self._limite_interno_mejorado(inner, var, punto, dir_, pasos)
        pasos.append(f"Resultado para L = lim g(x): {L}")

        if not self._es_limite_evaluable(L):
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion="No se pudo evaluar el límite de la función interna g(x).",
                pasos=pasos + ["El límite interno quedó no evaluado (Limit) o falló."],
                expr_original=expr,
                expr_trabajo=expr,
            )

        # 2) Verificar continuidad / dominio de f en L (guardrails)
        ok_cont, motivo = self._verificar_continuidad_y_dominio(outer, L)
        pasos.append(f"Chequeo de continuidad/dominio en L: {motivo}")

        if not ok_cont:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion="No podemos garantizar continuidad (o el dominio) de f en el valor L.",
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr,
            )

        # 3) Aplicar continuidad: lim f(g(x)) = f(L)
        try:
            resultado = self._evaluar_externa(outer, L)
        except Exception as e:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion="Falló la evaluación f(L) por una excepción.",
                pasos=pasos + [f"Error evaluando f(L): {e}"],
                expr_original=expr,
                expr_trabajo=expr,
            )

        pasos.append("Aplicamos el teorema: si g(x)->L y f es continua en L, entonces lim f(g(x)) = f(L).")
        pasos.append(f"Evaluamos f(L) = {resultado}")

        # 4) Estado coherente
        estado = ESTADO_FINITO
        if resultado in (S.Infinity, S.NegativeInfinity) or getattr(resultado, "is_infinite", False):
            estado = ESTADO_INFINITO

        return ResultadoEstrategia(
            aplica=True,
            estado=estado,
            resultado=sympy.simplify(resultado),
            nombre_estrategia=self.nombre(),
            explicacion="Se evaluó el límite usando continuidad por composición.",
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr,
        )

    # --------------------------
    # V1.5: límite interno mejorado
    # --------------------------

    def _limite_interno_mejorado(
        self,
        inner: Any,
        var: sympy.Symbol,
        punto: Any,
        dir_: Optional[str],
        pasos: Optional[List[str]] = None,
    ) -> Any:
        """
        Resolver L = lim inner con ayuda ligera (sin router).

        Orden:
          1) together/cancel del inner
          2) intento local de núcleos trigonométricos notables
          3) sympy.limit normal
        """
        if pasos is None:
            pasos = []

        inner2 = inner

        # 1) Normalización suave
        try:
            t = sympy.together(inner2)
            c = sympy.cancel(t)
            if sympy.srepr(c) != sympy.srepr(inner2):
                pasos.append(f"(Inner) Normalizamos con together+cancel: {c}")
            inner2 = c
        except Exception as e:
            pasos.append(f"(Inner) Aviso: together/cancel falló: {e}")

        # 2) Intento trig notable local si hay trig
        try:
            if inner2.has(sympy.sin) or inner2.has(sympy.cos) or inner2.has(sympy.tan):
                L_trig = self._limite_trig_notable_local(inner2, var, punto, dir_, pasos)
                if self._es_limite_evaluable(L_trig):
                    pasos.append("(Inner) Se resolvió por trig notable local.")
                    return L_trig
        except Exception as e:
            pasos.append(f"(Inner) Aviso: intento trig local falló: {e}")

        # 3) Límite directo con SymPy
        L = self._limite_seguro(inner2, var, punto, dir_)
        return L

    def _limite_trig_notable_local(
        self,
        expr: Any,
        var: sympy.Symbol,
        punto: Any,
        dir_: Optional[str],
        pasos: Optional[List[str]] = None,
    ) -> Any:
        """
        Intento local:
          - sin(u)/u -> 1
          - tan(u)/u -> 1
          - (1-cos(u))/u^2 -> 1/2

        Si encuentra núcleo y el resto es evaluable, devuelve el límite.
        Si no, devuelve Limit(...) (no evaluado).
        """
        if pasos is None:
            pasos = []

        expr_s = self._prep_interno(expr)

        # A) sin(u)/u
        ok, u, resto, lim_resto = self._match_generic_local(expr_s, var, punto, dir_, sympy.sin)
        if ok:
            pasos.append(f"(Inner) Núcleo trig local: sin(u)/u con u={u}")
            pasos.append(f"(Inner) Resto R = {resto}, lim R = {lim_resto}")
            return sympy.simplify(lim_resto)

        # B) tan(u)/u
        ok, u, resto, lim_resto = self._match_generic_local(expr_s, var, punto, dir_, sympy.tan)
        if ok:
            pasos.append(f"(Inner) Núcleo trig local: tan(u)/u con u={u}")
            pasos.append(f"(Inner) Resto R = {resto}, lim R = {lim_resto}")
            return sympy.simplify(lim_resto)

        # C) (1-cos(u))/u^2
        ok, u, resto, lim_resto = self._match_one_minus_cos_local(expr_s, var, punto, dir_)
        if ok:
            pasos.append(f"(Inner) Núcleo trig local: (1-cos(u))/u^2 con u={u}")
            pasos.append(f"(Inner) Resto R = {resto}, lim R = {lim_resto}")
            return sympy.simplify(sympy.Rational(1, 2) * lim_resto)

        return sympy.Limit(expr_s, var, punto, dir=dir_) if dir_ in ("+", "-") else sympy.Limit(expr_s, var, punto)

    def _prep_interno(self, expr: Any) -> Any:
        """Prep suave para inner: no simplify()."""
        try:
            return sympy.together(sympy.cancel(expr))
        except Exception:
            return expr

    def _match_generic_local(
        self,
        expr: Any,
        var: sympy.Symbol,
        punto: Any,
        dir_: Optional[str],
        func_type,
    ) -> Tuple[bool, Any, Any, Any]:
        """
        Escribe expr = (func(u)/u) * R  =>  R = expr * (u/func(u))

        Requisitos:
          - u -> 0 (mismo dir)
          - lim R evaluable
        """
        num, _ = expr.as_numer_denom()
        candidates = [t for t in sympy.preorder_traversal(num) if getattr(t, "func", None) == func_type]

        for term in candidates:
            u = term.args[0]
            if not self._u_tiende_a_0_local(u, var, punto, dir_):
                continue

            try:
                resto_expr = sympy.simplify(expr * (u / term))
            except Exception:
                continue

            lim_resto = self._limite_seguro(resto_expr, var, punto, dir_)
            if self._es_limite_evaluable(lim_resto):
                return True, u, resto_expr, sympy.simplify(lim_resto)

        return False, None, None, None

    def _match_one_minus_cos_local(
        self,
        expr: Any,
        var: sympy.Symbol,
        punto: Any,
        dir_: Optional[str],
    ) -> Tuple[bool, Any, Any, Any]:
        candidates = [t for t in sympy.preorder_traversal(expr) if getattr(t, "func", None) == sympy.cos]

        for cos_u in candidates:
            u = cos_u.args[0]
            if not self._u_tiende_a_0_local(u, var, punto, dir_):
                continue

            denom = (1 - cos_u)
            try:
                resto_expr = sympy.simplify(expr * (u**2) / denom)
            except Exception:
                continue

            lim_resto = self._limite_seguro(resto_expr, var, punto, dir_)
            if self._es_limite_evaluable(lim_resto):
                return True, u, resto_expr, sympy.simplify(lim_resto)

        return False, None, None, None

    def _u_tiende_a_0_local(self, u: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> bool:
        lu = self._limite_seguro(u, var, punto, dir_)
        if isinstance(lu, sympy.Limit):
            return False
        try:
            return sympy.simplify(lu) == 0
        except Exception:
            return False

    # --------------------------
    # Extracción de composición
    # --------------------------

    def _extraer_compuesta(self, expr: Any) -> Tuple[Optional[Any], Optional[Any]]:
        """
        Detecta 'expr = f(inner)' donde f sea:
          - función unaria conocida: exp, log, sin, cos, tan, sqrt, Abs...
          - o potencia inner**c (c constante)
        Retorna:
          outer: sympy.func o ("pow", c)
          inner: g(x)
        """
        # Caso 1: función unaria: sin(u), exp(u), log(u), sqrt(u), Abs(u)...
        if hasattr(expr, "func") and hasattr(expr, "args") and len(expr.args) == 1:
            f = expr.func
            u = expr.args[0]
            if self._es_funcion_externa_conocida(f):
                return f, u

        # Caso 2: potencia: u**c con c constante
        if isinstance(expr, sympy.Pow):
            base, exp = expr.args
            if self._es_constante(exp):
                return ("pow", exp), base

        return None, None

    def _repr_outer(self, outer: Any) -> str:
        if isinstance(outer, tuple) and outer and outer[0] == "pow":
            return f"(·)**({outer[1]})"
        try:
            return outer.__name__
        except Exception:
            return str(outer)

    def _es_funcion_externa_conocida(self, f: Any) -> bool:
        return f in {
            sympy.exp,
            sympy.log,
            sympy.sin,
            sympy.cos,
            sympy.tan,
            sympy.asin,
            sympy.acos,
            sympy.atan,
            sympy.sinh,
            sympy.cosh,
            sympy.tanh,
            sympy.sqrt,
            sympy.Abs,
        }

    def _es_constante(self, x: Any) -> bool:
        try:
            return len(x.free_symbols) == 0
        except Exception:
            return False

    # --------------------------
    # Continuidad / dominio
    # --------------------------

    def _verificar_continuidad_y_dominio(self, outer: Any, L: Any) -> Tuple[bool, str]:
        """
        Retorna (ok, mensaje). Conservador.
        """
        # 1) Potencias
        if isinstance(outer, tuple) and outer and outer[0] == "pow":
            c = outer[1]

            if c.is_integer is True:
                return True, f"Potencia con exponente entero ({c}): continua para todo L real."

            if c.is_Rational:
                q = int(c.q)
                if q % 2 == 0:
                    if self._es_no_negativo(L):
                        return True, f"Potencia racional ({c}) con denominador par: dominio real requiere L>=0, verificado."
                    return False, f"Potencia racional ({c}) con denominador par: no podemos garantizar L>=0."
                return True, f"Potencia racional ({c}) con denominador impar: continua para L real."

            return False, f"Potencia con exponente {c}: no podemos garantizar continuidad/dominio."

        # 2) exp
        if outer == sympy.exp:
            return True, "exp es continua para todo L real."

        # 3) sin/cos/sinh/cosh/tanh/atan
        if outer in (sympy.sin, sympy.cos, sympy.sinh, sympy.cosh, sympy.tanh, sympy.atan):
            return True, f"{outer.__name__} es continua para todo L real."

        # 4) tan: cos(L) != 0
        if outer == sympy.tan:
            try:
                c = sympy.cos(L)
                if sympy.simplify(c) == 0:
                    return False, "tan NO es continua cuando cos(L)=0 (asíntota vertical)."
            except Exception:
                pass
            return True, "tan es continua donde cos(L)≠0; no detectamos cos(L)=0."

        # 5) log: L > 0
        if outer == sympy.log:
            if self._es_positivo(L):
                return True, "log es continua en su dominio real; se verificó L>0."
            return False, "log requiere L>0 para continuidad real; no podemos garantizarlo."

        # 6) sqrt: L >= 0
        if outer == sympy.sqrt:
            if self._es_no_negativo(L):
                return True, "sqrt es continua en su dominio real; se verificó L>=0."
            return False, "sqrt requiere L>=0 para continuidad real; no podemos garantizarlo."

        # 7) Abs
        if outer == sympy.Abs:
            return True, "abs es continua para todo L real."

        # 8) asin/acos: L en [-1,1]
        if outer in (sympy.asin, sympy.acos):
            if self._en_intervalo_menos1_1(L):
                return True, f"{outer.__name__} es continua en [-1,1]; se verificó L en el intervalo."
            return False, f"{outer.__name__} requiere L∈[-1,1] en reales; no podemos garantizarlo."

        return False, "Función externa no soportada para chequeo de continuidad."

    def _es_positivo(self, x: Any) -> bool:
        try:
            q = ask(Q.positive(x))
            if q is True:
                return True
            if q is False:
                return False
        except Exception:
            pass
        try:
            sx = sympy.simplify(x)
            if sx.is_positive is True:
                return True
            if sx.is_positive is False:
                return False
        except Exception:
            pass
        return False

    def _es_no_negativo(self, x: Any) -> bool:
        try:
            q = ask(Q.nonnegative(x))
            if q is True:
                return True
            if q is False:
                return False
        except Exception:
            pass
        try:
            sx = sympy.simplify(x)
            if sx.is_nonnegative is True:
                return True
            if sx.is_nonnegative is False:
                return False
        except Exception:
            pass
        return False

    def _en_intervalo_menos1_1(self, x: Any) -> bool:
        try:
            sx = sympy.simplify(x)
            if sx.is_number:
                try:
                    return bool(sx >= -1 and sx <= 1)
                except Exception:
                    return False
        except Exception:
            pass
        return False  # conservador

    # --------------------------
    # Evaluación f(L)
    # --------------------------

    def _evaluar_externa(self, outer: Any, L: Any) -> Any:
        if isinstance(outer, tuple) and outer[0] == "pow":
            c = outer[1]
            return sympy.simplify(L ** c)
        return sympy.simplify(outer(L))

    # --------------------------
    # Límite seguro + evaluable
    # --------------------------

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
