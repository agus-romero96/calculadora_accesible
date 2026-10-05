from __future__ import annotations

from typing import Any, List, Optional, Tuple

import sympy
from sympy import S
from sympy.assumptions import Q, ask

from .trigonometria import LimitesTrigNotables
from i18n import N_, tr
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

    def __init__(self):
        # Reutiliza los núcleos trigonométricos para calcular el límite interno
        self._trig = LimitesTrigNotables()

    def nombre(self) -> str:
        return N_("Continuidad por composición")

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
        pasos.append(tr("Buscamos una forma compuesta f(g(x)) y aplicamos continuidad si corresponde."))

        outer, inner = self._extraer_compuesta(expr)
        if outer is None or inner is None:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion=N_("No se pudo identificar una composición directa f(g(x))."),
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr,
            )

        pasos.append(tr("Identificamos función externa: f(·) = {outer}", outer=self._repr_outer(outer)))
        pasos.append(tr("Identificamos función interna: g(x) = {inner}", inner=inner))

        # 1) Calcular L = lim g(x) con ayuda V1.5
        L = self._limite_interno_mejorado(inner, var, punto, dir_, pasos)
        pasos.append(tr("Resultado para L = lim g(x): {L}", L=L))

        if not self._es_limite_evaluable(L):
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion=N_("No se pudo evaluar el límite de la función interna g(x)."),
                pasos=pasos + [tr("El límite interno quedó no evaluado (Limit) o falló.")],
                expr_original=expr,
                expr_trabajo=expr,
            )

        # 2) Verificar continuidad / dominio de f en L (guardrails)
        ok_cont, motivo = self._verificar_continuidad_y_dominio(outer, L)
        pasos.append(tr("Chequeo de continuidad/dominio en L: {motivo}", motivo=motivo))

        if not ok_cont:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion=N_("No podemos garantizar continuidad (o el dominio) de f en el valor L."),
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
                explicacion=N_("Falló la evaluación f(L) por una excepción."),
                pasos=pasos + [tr("Error evaluando f(L): {e}", e=e)],
                expr_original=expr,
                expr_trabajo=expr,
            )

        pasos.append(tr("Aplicamos el teorema: si g(x)->L y f es continua en L, entonces lim f(g(x)) = f(L)."))
        pasos.append(tr("Evaluamos f(L) = {resultado}", resultado=resultado))

        # 4) Estado coherente
        estado = ESTADO_FINITO
        if resultado in (S.Infinity, S.NegativeInfinity) or getattr(resultado, "is_infinite", False):
            estado = ESTADO_INFINITO

        return ResultadoEstrategia(
            aplica=True,
            estado=estado,
            resultado=sympy.simplify(resultado),
            nombre_estrategia=self.nombre(),
            explicacion=N_("Se evaluó el límite usando continuidad por composición."),
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
                pasos.append(tr("(Inner) Normalizamos con together+cancel: {c}", c=c))
            inner2 = c
        except Exception as e:
            pasos.append(tr("(Inner) Aviso: together/cancel falló: {e}", e=e))

        # 2) Intento trig notable local si hay trig
        try:
            if inner2.has(sympy.sin) or inner2.has(sympy.cos) or inner2.has(sympy.tan):
                L_trig = self._limite_trig_notable_local(inner2, var, punto, dir_, pasos)
                if self._es_limite_evaluable(L_trig):
                    pasos.append(tr("(Inner) Se resolvió por trig notable local."))
                    return L_trig
        except Exception as e:
            pasos.append(tr("(Inner) Aviso: intento trig local falló: {e}", e=e))

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
        Intento local con los núcleos de LimitesTrigNotables (sin duplicar su lógica):
          - sin(u)/u -> 1
          - tan(u)/u -> 1
          - (1-cos(u))/u^2 -> 1/2

        Si encuentra núcleo y el resto es evaluable, devuelve el límite; si no, None.
        """
        if pasos is None:
            pasos = []

        nucleos = (
            ("sin(u)/u", self._trig._match_sin, 1),
            ("tan(u)/u", self._trig._match_tan, 1),
            ("(1-cos(u))/u^2", self._trig._match_one_minus_cos, sympy.Rational(1, 2)),
        )
        for nombre, match, factor in nucleos:
            ok, u, resto, lim_resto = match(expr, var, punto, dir_)
            if ok:
                pasos.append(tr("(Inner) Núcleo trig local: {nombre} con u={u}", nombre=nombre, u=u))
                pasos.append(tr("(Inner) Resto R = {resto}, lim R = {lim_resto}", resto=resto, lim_resto=lim_resto))
                return sympy.simplify(factor * lim_resto)

        return None

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
                return True, tr("Potencia con exponente entero ({c}): continua para todo L real.", c=c)

            if c.is_Rational:
                q = int(c.q)
                if q % 2 == 0:
                    if self._es_no_negativo(L):
                        return True, tr("Potencia racional ({c}) con denominador par: dominio real requiere L>=0, verificado.", c=c)
                    return False, tr("Potencia racional ({c}) con denominador par: no podemos garantizar L>=0.", c=c)
                return True, tr("Potencia racional ({c}) con denominador impar: continua para L real.", c=c)

            return False, tr("Potencia con exponente {c}: no podemos garantizar continuidad/dominio.", c=c)

        # 2) exp
        if outer == sympy.exp:
            return True, tr("exp es continua para todo L real.")

        # 3) sin/cos/sinh/cosh/tanh/atan
        if outer in (sympy.sin, sympy.cos, sympy.sinh, sympy.cosh, sympy.tanh, sympy.atan):
            return True, tr("{funcion} es continua para todo L real.", funcion=outer.__name__)

        # 4) tan: cos(L) != 0
        if outer == sympy.tan:
            try:
                c = sympy.cos(L)
                if sympy.simplify(c) == 0:
                    return False, tr("tan NO es continua cuando cos(L)=0 (asíntota vertical).")
            except Exception:
                pass
            return True, tr("tan es continua donde cos(L)≠0; no detectamos cos(L)=0.")

        # 5) log: L > 0
        if outer == sympy.log:
            if self._es_positivo(L):
                return True, tr("log es continua en su dominio real; se verificó L>0.")
            return False, tr("log requiere L>0 para continuidad real; no podemos garantizarlo.")

        # 6) sqrt: L >= 0
        if outer == sympy.sqrt:
            if self._es_no_negativo(L):
                return True, tr("sqrt es continua en su dominio real; se verificó L>=0.")
            return False, tr("sqrt requiere L>=0 para continuidad real; no podemos garantizarlo.")

        # 7) Abs
        if outer == sympy.Abs:
            return True, tr("abs es continua para todo L real.")

        # 8) asin/acos: L en [-1,1]
        if outer in (sympy.asin, sympy.acos):
            if self._en_intervalo_menos1_1(L):
                return True, tr("{funcion} es continua en [-1,1]; se verificó L en el intervalo.", funcion=outer.__name__)
            return False, tr("{funcion} requiere L∈[-1,1] en reales; no podemos garantizarlo.", funcion=outer.__name__)

        return False, tr("Función externa no soportada para chequeo de continuidad.")

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
