from __future__ import annotations

from typing import Any, Optional, Tuple, List

import sympy
from sympy import S

from i18n import N_, tr
from ._base import (
    Estrategia,
    ResultadoEstrategia,
    ESTADO_FINITO,
    ESTADO_INFINITO,
    ESTADO_NO_CONCLUYENTE,
)


class LimiteRacionalInfinito(Estrategia):
    """
    Estrategia clásica: límites de cocientes de polinomios cuando x -> ±∞.

    Método “profesor” (sin series):
      - Si deg(n) < deg(d) => 0
      - Si deg(n) = deg(d) => cociente de coeficientes líderes
      - Si deg(n) > deg(d) => diverge como (LC(n)/LC(d)) * x^(deg(n)-deg(d))
        * con signo determinado por:
            - signo(LC(n)/LC(d))
            - paridad del exponente k
            - dirección (+∞ o -∞) si k es impar
    """

    def nombre(self) -> str:
        return N_("Comparación de grados (racionales en infinito)")

    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        if punto not in (S.Infinity, S.NegativeInfinity):
            return False

        n, d = expr.as_numer_denom()

        # Guardas: deben ser polinomios en var y degree debe ser computable
        if not (n.is_polynomial(var) and d.is_polynomial(var)):
            return False

        deg_n, deg_d = self._safe_degree_pair(n, d, var)
        if deg_n is None or deg_d is None:
            return False

        # degree no debería dar -oo si es polinomio, pero por seguridad:
        if deg_n in (S.NegativeInfinity, -sympy.oo) or deg_d in (S.NegativeInfinity, -sympy.oo):
            return False

        return True

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        n, d = expr.as_numer_denom()

        pasos: List[str] = []
        pasos.append(tr("Identificamos un cociente de polinomios en infinito."))

        deg_n, deg_d = self._safe_degree_pair(n, d, var)
        if deg_n is None or deg_d is None:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion=N_("No se pudieron determinar grados de forma segura."),
                pasos=pasos + [tr("No se pudo calcular degree() para numerador/denominador.")],
                avisos=[tr("Se requiere fallback CAS u otra estrategia.")],
                expr_original=expr,
                expr_trabajo=expr,
            )

        pasos.append(tr("Grado del numerador: {deg_n}", deg_n=deg_n))
        pasos.append(tr("Grado del denominador: {deg_d}", deg_d=deg_d))

        # Caso 1: deg(n) < deg(d) -> 0
        if deg_n < deg_d:
            pasos.append(tr("Como el grado del denominador es mayor, el cociente tiende a 0."))
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_FINITO,
                resultado=sympy.Integer(0),
                nombre_estrategia=self.nombre(),
                explicacion=N_("En infinito domina el término de mayor grado del denominador."),
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr,
            )

        # Coeficientes líderes (con guardas)
        lc_n, lc_d = self._safe_lc_pair(n, d, var)
        if lc_n is None or lc_d is None:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion=N_("No se pudieron determinar coeficientes líderes de forma segura."),
                pasos=pasos + [tr("No se pudo calcular LC() para numerador/denominador.")],
                avisos=[tr("Se requiere fallback CAS u otra estrategia.")],
                expr_original=expr,
                expr_trabajo=expr,
            )

        pasos.append(tr("Coeficiente líder numerador: {lc_n}", lc_n=lc_n))
        pasos.append(tr("Coeficiente líder denominador: {lc_d}", lc_d=lc_d))

        # Caso 2: deg(n) == deg(d) -> cociente de líderes
        if deg_n == deg_d:
            res = sympy.simplify(lc_n / lc_d)
            pasos.append(tr("Grados iguales: el límite es la razón de coeficientes principales."))
            pasos.append(tr("Límite = {lc_n}/{lc_d} = {res}", lc_n=lc_n, lc_d=lc_d, res=res))
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_FINITO,
                resultado=res,
                nombre_estrategia=self.nombre(),
                explicacion=N_("Grados iguales → razón de coeficientes líderes."),
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr,
            )

        # Caso 3: deg(n) > deg(d) -> diverge con signo (o condicional)
        k = int(deg_n - deg_d)
        ratio = sympy.simplify(lc_n / lc_d)

        pasos.append(tr("El numerador tiene mayor grado. Diferencia k = {k}.", k=k))
        pasos.append(tr("En infinito, domina el término principal: (LC(n)/LC(d)) * x^k."))
        pasos.append(tr("Ratio dominante = {ratio}", ratio=ratio))

        # 3A) Intento: decidir signo totalmente
        inf = self._infinito_con_signo(ratio, k, punto)
        if inf is not None:
            pasos.append(tr("Como el signo se puede decidir, el límite diverge hacia {inf}.", inf=inf))
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_INFINITO,
                resultado=inf,
                nombre_estrategia=self.nombre(),
                explicacion=N_("Grado arriba mayor → divergencia tipo ratio*x^k (signo según paridad y tendencia)."),
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr,
            )

        # 3B) Si no se puede decidir el signo, intentamos diagnóstico condicional
        cond = self._diagnostico_condicional(ratio, k, punto)
        if cond:
            pasos.append(tr("El signo depende de parámetros y no se puede fijar sin hipótesis."))
            pasos.extend([f"• {linea}" for linea in cond])
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion=N_("Diverge en magnitud, pero el signo depende de parámetros."),
                pasos=pasos,
                avisos=[tr("Se requiere suponer el signo del coeficiente dominante para decidir +∞ o −∞.")],
                expr_original=expr,
                expr_trabajo=expr,
            )

        # 3C) Último: no concluyente
        pasos.append(tr("Conclusión: el límite diverge en magnitud (|f|→∞), pero no se pudo determinar el signo."))
        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_NO_CONCLUYENTE,
            resultado=None,
            nombre_estrategia=self.nombre(),
            explicacion=N_("Diverge (grado mayor arriba), pero el signo no pudo determinarse."),
            pasos=pasos,
            avisos=[tr("No se pudo decidir el signo de LC(n)/LC(d).")],
            expr_original=expr,
            expr_trabajo=expr,
        )

    # ---------------- Helpers robustos ----------------

    def _safe_degree_pair(self, n: Any, d: Any, var: sympy.Symbol) -> Tuple[Optional[Any], Optional[Any]]:
        try:
            deg_n = sympy.degree(n, var)
            deg_d = sympy.degree(d, var)
            return deg_n, deg_d
        except Exception:
            return None, None

    def _safe_lc_pair(self, n: Any, d: Any, var: sympy.Symbol) -> Tuple[Optional[Any], Optional[Any]]:
        try:
            lc_n = sympy.LC(n, var)
            lc_d = sympy.LC(d, var)
            return lc_n, lc_d
        except Exception:
            return None, None

    def _infinito_con_signo(self, ratio: Any, k: int, punto: Any) -> Optional[Any]:
        """
        Decide +∞ / -∞ si se puede decidir el signo de ratio.
        Retorna None si el signo no es decidible o ratio es patológico.
        """
        sign = self._signo_seguro(ratio)
        if sign is None:
            return None

        # ratio == 0 es patológico: indica que “no era el líder real” o que hay cancelación simbólica rara.
        if sign == 0:
            return None

        # k par: x^k >= 0 para ±∞
        if k % 2 == 0:
            return S.Infinity if sign > 0 else S.NegativeInfinity

        # k impar: x^k sigue el signo de x
        if punto == S.Infinity:
            return S.Infinity if sign > 0 else S.NegativeInfinity
        if punto == S.NegativeInfinity:
            return S.NegativeInfinity if sign > 0 else S.Infinity

        return None

    def _signo_seguro(self, expr: Any) -> Optional[int]:
        """
        Devuelve +1, -1, 0 o None si no se puede decidir.
        """
        try:
            expr_s = sympy.simplify(expr)

            # Decisiones rápidas
            if expr_s.is_positive is True:
                return 1
            if expr_s.is_negative is True:
                return -1

            # sign() puede devolver 0, ±1 o algo simbólico
            s = sympy.sign(expr_s)
            if s == 1:
                return 1
            if s == -1:
                return -1
            if s == 0:
                return 0

            # equals(0) como último intento
            r0 = expr_s.equals(0)
            if r0 is True:
                return 0

            return None
        except Exception:
            return None

    def _diagnostico_condicional(self, ratio: Any, k: int, punto: Any) -> List[str]:
        """
        Construye un diagnóstico condicional simple:
          - si ratio > 0 / ratio < 0
          - y considerando paridad de k y ±∞
        No intenta resolver inequaciones complejas; solo da un esquema útil.
        """
        ratio_s = sympy.simplify(ratio)

        # Si SymPy no puede ni siquiera tratarlo como real, no damos condiciones.
        # (Evita decir tonterías con complejos.)
        try:
            if ratio_s.is_real is False:
                return []
        except Exception:
            pass

        # Condiciones “de libro”
        if k % 2 == 0:
            return [
                tr("Si {ratio_s} > 0 entonces el límite → +∞", ratio_s=ratio_s),
                tr("Si {ratio_s} < 0 entonces el límite → −∞", ratio_s=ratio_s),
            ]

        # k impar: depende del lado del infinito
        if punto == S.Infinity:
            return [
                tr("Si {ratio_s} > 0 entonces el límite → +∞", ratio_s=ratio_s),
                tr("Si {ratio_s} < 0 entonces el límite → −∞", ratio_s=ratio_s),
            ]
        if punto == S.NegativeInfinity:
            return [
                tr("Si {ratio_s} > 0 entonces el límite → −∞", ratio_s=ratio_s),
                tr("Si {ratio_s} < 0 entonces el límite → +∞", ratio_s=ratio_s),
            ]

        return []
