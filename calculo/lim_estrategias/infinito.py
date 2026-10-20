from __future__ import annotations

from typing import Any, Optional, Tuple, List

import sympy
from sympy import S

from calculo.pasos import PasoCalculo, entre_parentesis, texto
from i18n import N_, tr
from ._pasos import paso_sustitucion
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

        if not d.has(var):
            return False

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
            pasos = self._pasos(expr, n, d, var, punto, sympy.Integer(0))
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
            pasos = self._pasos(expr, n, d, var, punto, res)
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
            pasos = self._pasos(expr, n, d, var, punto, inf)
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

    # ---------------- Pasos ----------------

    def _pasos(self, expr: Any, n: Any, d: Any, var: sympy.Symbol, punto: Any, valor: Any) -> List[PasoCalculo]:
        """Sustitución (∞/∞) y comparación de los términos principales."""
        paso_inicial, _ = paso_sustitucion(expr, var, punto)
        deg_n, deg_d = (int(g) for g in self._safe_degree_pair(n, d, var))
        lc_n, lc_d = self._safe_lc_pair(n, d, var)
        principal_n, principal_d = lc_n * var ** deg_n, lc_d * var ** deg_d
        cociente = sympy.simplify(principal_n / principal_d)
        calculo = [tr("Cociente de los términos principales: {num}/{den} = {cociente}.",
                      num=entre_parentesis(principal_n), den=entre_parentesis(principal_d), cociente=texto(cociente))]
        if deg_n == deg_d:
            calculo.append(tr("Los grados son iguales ({n} = {d}): las potencias de {x} se cancelan y queda el cociente "
                              "de los coeficientes principales, {cociente}.", n=deg_n, d=deg_d, x=var,
                              cociente=f"{entre_parentesis(lc_n)}/{entre_parentesis(lc_d)} = {texto(valor)}"
                              if f"{entre_parentesis(lc_n)}/{entre_parentesis(lc_d)}" != texto(valor) else texto(valor)))
        elif deg_n < deg_d:
            calculo.append(tr("El grado del denominador es mayor ({n} < {d}): queda un número entre una potencia de {x}, "
                              "que crece sin límite, así que el cociente tiende a 0.", n=deg_n, d=deg_d, x=var))
        else:
            k = deg_n - deg_d
            ratio = sympy.simplify(lc_n / lc_d)
            calculo.append(tr("El grado del numerador es mayor ({n} > {d}): queda {ratio}*{x}^{k}, con k = {n} - {d} = {k}, "
                              "que crece sin límite.", n=deg_n, d=deg_d, ratio=entre_parentesis(ratio), x=var, k=k))
            if k % 2 == 0:
                calculo.append(tr("{x}^{k} tiene exponente par: es positivo tanto si {x} → oo como si {x} → -oo.", x=var, k=k))
            elif punto == S.Infinity:
                calculo.append(tr("{x}^{k} tiene exponente impar: cuando {x} → oo es positivo.", x=var, k=k))
            else:
                calculo.append(tr("{x}^{k} tiene exponente impar: cuando {x} → -oo es negativo.", x=var, k=k))
            calculo.append(tr("El coeficiente {ratio} es {signo}, así que el límite es {valor}.", ratio=texto(ratio),
                              signo=tr("positivo") if ratio.is_positive else tr("negativo"), valor=texto(valor)))
        paso = PasoCalculo(
            tr("Comparar los grados"),
            regla=tr("cuando {x} → ±∞, en cada polinomio manda el término de mayor grado, porque los demás crecen más "
                     "despacio: el cociente se comporta como el cociente de los términos principales.", x=var),
            partes=tr("el numerador tiene grado {n} y su término principal es {principal_n}; el denominador tiene "
                      "grado {d} y su término principal es {principal_d}.", n=deg_n, principal_n=texto(principal_n),
                      d=deg_d, principal_d=texto(principal_d)),
            calculo=tuple(calculo),
            queda=texto(valor))
        return [p for p in (paso_inicial, paso) if p]

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
