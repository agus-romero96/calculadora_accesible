from __future__ import annotations

from typing import Any, Tuple, List, Optional

import sympy
from sympy import S

from calculo.pasos import PasoCalculo, entre_parentesis, texto
from i18n import N_, tr
from ._pasos import cuenta, paso_sustitucion, valor_texto
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
        return N_("Límites trigonométricos notables")

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

    # Núcleos: (función que lo detecta, cómo se escribe con u, su límite, enunciado)
    NUCLEOS = (
        ("_match_sin", "sin({u})/{up}", 1,
         N_("cuando u → 0, sin(u)/u → 1 (límite notable). Si la expresión se escribe como (sin(u)/u)*R, "
            "su límite es 1 por el límite de R.")),
        ("_match_tan", "tan({u})/{up}", 1,
         N_("cuando u → 0, tan(u)/u → 1 (límite notable, porque tan(u) = sin(u)/cos(u) y cos(0) = 1). "
            "Si la expresión se escribe como (tan(u)/u)*R, su límite es 1 por el límite de R.")),
        ("_match_one_minus_cos", "(1 - cos({u}))/{up}^2", sympy.Rational(1, 2),
         N_("cuando u → 0, (1 - cos(u))/u^2 → 1/2 (límite notable). Si la expresión se escribe como "
            "((1 - cos(u))/u^2)*R, su límite es 1/2 por el límite de R.")),
    )

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        dir_ = kwargs.get("dir", None)

        for metodo, plantilla, factor, enunciado in self.NUCLEOS:
            ok, u, resto, lim_resto = getattr(self, metodo)(expr, var, punto, dir_)
            if not ok:
                continue
            res = sympy.simplify(factor * lim_resto)
            nucleo = plantilla.format(u=texto(u), up=texto(u) if u.is_Symbol else entre_parentesis(u))
            paso_inicial, _ = paso_sustitucion(expr, var, punto, dir_)

            cuenta_u = cuenta(u, var, punto)
            if u == var or cuenta_u is None:
                tiende_u = tr("u → 0 cuando {variable} → {punto}", variable=var, punto=punto)
            else:
                tiende_u = tr("u → 0: {cuenta}", cuenta=cuenta_u)
            calculo = [tr("Escribimos la expresión como el núcleo por un resto: {expresion} = ({nucleo})*R.",
                          expresion=texto(expr), nucleo=nucleo),
                       tr("R es la expresión dividida entre el núcleo: R = ({expresion})/({nucleo}) = {resto}.",
                          expresion=texto(expr), nucleo=nucleo, resto=texto(resto))]
            calculo += self._explicar_resto(resto, var, punto, dir_, lim_resto)
            calculo.append(tr("Multiplicamos los dos límites: {factor} * {resto} = {resultado}.", factor=texto(factor),
                              resto=entre_parentesis(lim_resto), resultado=valor_texto(res)))
            paso = PasoCalculo(
                tr("Límite trigonométrico notable"),
                regla=tr(enunciado),
                partes=tr("el núcleo es {nucleo} con u = {u} ({tiende}).", nucleo=nucleo, u=texto(u), tiende=tiende_u),
                calculo=tuple(calculo),
                queda=valor_texto(res))
            return self._ok(expr, [p for p in (paso_inicial, paso) if p], res,
                            tr("Extracción de núcleo {nucleo} con u={u}", nucleo=plantilla.format(u="u", up="u"), u=u))

        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_NO_CONCLUYENTE,
            resultado=None,
            nombre_estrategia=self.nombre(),
            pasos=[],
            avisos=[tr("Requiere identidad adicional, encaje u otro método.")],
            expr_original=expr,
            expr_trabajo=expr,
        )

    def _explicar_resto(self, resto: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str],
                        lim_resto: Any) -> List[str]:
        """Cómo se obtiene el límite del resto: sustituyendo, o con el núcleo invertido v/sin(v) → 1."""
        texto_cuenta = cuenta(resto, var, punto)
        if texto_cuenta is not None:
            return [tr("Límite del resto, sustituyendo: R = {cuenta}.", cuenta=texto_cuenta)]
        # sin(2x)/sin(3x): R = 2*x/sin(3*x) = (3*x/sin(3*x)) * (2*x/(3*x)), y 3*x/sin(3*x) → 1
        _, den = resto.as_numer_denom()
        for f in sympy.Mul.make_args(den):
            if getattr(f, "func", None) in (sympy.sin, sympy.tan) and self._u_tiende_a_0(f.args[0], var, punto, dir_):
                v = f.args[0]
                otro = sympy.simplify(resto * f / v)
                cuenta_otro = cuenta(otro, var, punto)
                if cuenta_otro is None:
                    break
                return [tr("El resto tiene {funcion}(v) en el denominador, con v = {v} → 0: R = ({v}/{funcion}({v}))*{otro}, "
                           "y {v}/{funcion}({v}) → 1 porque es el inverso del límite notable.",
                           funcion=f.func.__name__, v=texto(v), otro=entre_parentesis(otro)),
                        tr("El otro factor, sustituyendo: {cuenta}.", cuenta=cuenta_otro),
                        tr("Límite del resto: 1 * {valor} = {valor}.", valor=valor_texto(lim_resto))]
        return [tr("Límite del resto: R tiende a {valor}.", valor=valor_texto(lim_resto))]


    # ---------------- helpers ----------------

    def _ok(self, expr: Any, pasos: List[Any], res: Any, explicacion: str) -> ResultadoEstrategia:
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

    def _factores(self, num: Any) -> List[Any]:
        """
        Factores multiplicativos del numerador (sin exponentes enteros positivos).
        El núcleo solo se puede extraer si es uno de ellos: un sin(u) dentro de
        exp(...) o de una suma no permite escribir expr = K * R.
        """
        try:
            num = sympy.factor_terms(num)
        except Exception:
            pass
        factores = []
        for f in sympy.Mul.make_args(num):
            if f.is_Pow and f.exp.is_Integer and f.exp > 0:
                f = f.base
            factores.append(f)
        return factores

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
        candidates = [t for t in self._factores(num) if getattr(t, "func", None) == func_type]

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
        num, _ = expr_s.as_numer_denom()

        # El núcleo exige que (1 - cos(u)) o (cos(u) - 1) sea un factor del numerador:
        # un cos(u) suelto, como en cos(1/x), no forma el núcleo
        candidates = []
        for f in self._factores(num):
            for cos_u in f.atoms(sympy.cos):
                if sympy.expand(f - (1 - cos_u)) == 0 or sympy.expand(f - (cos_u - 1)) == 0:
                    candidates.append(cos_u)

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
