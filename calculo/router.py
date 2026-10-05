from __future__ import annotations
from typing import Optional, Any, List
import sympy as sp
from sympy import Symbol, S

from .lim_estrategias.trigonometria import LimitesTrigNotables
from .lim_estrategias.racionalizacion import RacionalizacionRaices
from .lim_estrategias.infinito import LimiteRacionalInfinito
from .lim_estrategias.continuidad import ContinuidadComposicion
from .lim_estrategias.simplificacion import SimplificacionCancelacion
from .lim_estrategias._base import ESTADO_NO_CONCLUYENTE



class RouterMatematico:
    def __init__(self, parser_compartido, motor_limites_viejo):
        self.parser = parser_compartido
        self.motor_limites = motor_limites_viejo

        self.estrategias = [
            SimplificacionCancelacion(),
            LimitesTrigNotables(),
            RacionalizacionRaices(),
            ContinuidadComposicion(),
            LimiteRacionalInfinito(),
        ]

    def CalcularLimite(self, expresion: str, variable: Optional[str] = None, tendencia: str = "0") -> str:
        try:
            expr = self.parser.parsear(expresion)
            var = self._resolver_var(expr, variable)
            punto, dir_ = self._parsear_tendencia(tendencia)
        except Exception as e:
            return f"Error en los datos del límite:\n{e}"

        for est in self.estrategias:
            try:
                if not est.puede_resolver(expr, var, punto, dir=dir_):
                    continue
                res = est.resolver(expr, var, punto, dir=dir_)
            except Exception:
                # Una estrategia que falla no debe impedir probar las siguientes ni el fallback
                continue
            if res.aplica and res.estado != ESTADO_NO_CONCLUYENTE:
                return self._render_estrategia(expresion, var, punto, dir_, res)

        return self._fallback(expresion, variable, tendencia, expr, var, punto, dir_)

    # -------------------------
    # PASO 1: Fallback robusto
    # -------------------------
    def _fallback(self, expr_str: str, var_str: Optional[str], tend_str: str,
                  expr_parsed: Any, var_sym: Any, punto: Any, dir_: Optional[str]) -> str:
        """
        Regla de oro para tu auditor:
        - SIEMPRE devolver una línea 'RESULTADO: ...'
        - SIEMPRE devolver una línea 'MÉTODO: ...'
        """

        # 1) Si es lateral explícito, intentamos SymPy directo (es lo más fiel al dir)
        if dir_ in {"+", "-"}:
            try:
                val = sp.limit(expr_parsed, var_sym, punto, dir=dir_)
                return "\n".join([
                    f"RESULTADO: {val}",
                    "=" * 30,
                    f"MÉTODO: Límite lateral directo (SymPy, dir='{dir_}')",
                    f"Límite de {expr_str} cuando {var_sym} -> {punto}{dir_}",
                ])
            except Exception as e:
                # Si falla, igual devolvemos RESULTADO parseable
                base = self._motor_viejo(expr_str, var_str, tend_str)
                return "\n".join([
                    "RESULTADO: No concluyente",
                    "=" * 30,
                    f"MÉTODO: Modo General (Motor Viejo) + Error en lateral directo",
                    f"Error (lateral dir='{dir_}'): {e}",
                    "",
                    base,
                ])

        # 2) Bilateral / infinito: intentamos SymPy primero para sacar RESULTADO parseable
        sympy_val_ok = False
        sympy_val = None
        try:
            sympy_val = sp.limit(expr_parsed, var_sym, punto)
            sympy_val_ok = True
        except Exception:
            sympy_val_ok = False

        # 3) Ejecutamos motor viejo para explicación/pasos (aunque SymPy haya funcionado)
        base = self._motor_viejo(expr_str, var_str, tend_str)

        if sympy_val_ok:
            return "\n".join([
                f"RESULTADO: {sympy_val}",
                "=" * 30,
                "MÉTODO: Modo General (Motor Viejo) + Verificación SymPy",
                f"Límite de {expr_str} cuando {var_sym} -> {punto}",
                "",
                base,
            ])

        # 4) Si SymPy no pudo, igual devolvemos un RESULTADO parseable
        return "\n".join([
            "RESULTADO: No concluyente",
            "=" * 30,
            "MÉTODO: Modo General (Motor Viejo)",
            f"Límite de {expr_str} cuando {var_sym} -> {punto}",
            "",
            base,
        ])

    def _motor_viejo(self, expr_str: str, var_str: Optional[str], tend_str: str) -> str:
        # El motor viejo espera strings; si var_str es None, pasamos "x" como default
        v = var_str if var_str else "x"
        try:
            return self.motor_limites.calcular_limite(expr_str, v, tend_str)
        except Exception as e:
            return f"(Motor viejo falló) Error: {e}"

    # -------------------------
    # Helpers existentes
    # -------------------------
    def _resolver_var(self, expr, v_str):
        if v_str:
            return Symbol(v_str)
        s = list(expr.free_symbols)
        if not s:
            return Symbol("x")
        if Symbol("x") in s:
            return Symbol("x")
        return s[0]

    def _parsear_tendencia(self, t_str):
        raw = t_str.lower().strip().replace("∞", "oo").replace("infinito", "oo")
        if not raw:
            raise ValueError("La tendencia está vacía. Escriba un número, oo o -oo.")
        d = None
        if raw.endswith("+") and raw not in {"+oo", "+inf"}:
            d = "+"
            raw = raw[:-1]
        elif raw.endswith("-") and raw not in {"-oo", "-inf"}:
            d = "-"
            raw = raw[:-1]

        if raw in ["oo", "inf", "+inf", "+oo"]:
            return S.Infinity, None
        if raw in ["-oo", "-inf"]:
            return S.NegativeInfinity, None

        return self.parser.parsear(raw), d

    def _render_estrategia(self, expr_in, var, punto, dir_, res):
        s = dir_ if dir_ else ""
        txt = [f"RESULTADO: {res.resultado}", "=" * 30]
        txt.append(f"Límite de {expr_in} cuando {var} -> {punto}{s}")
        txt.append(f"\nMÉTODO: {res.nombre_estrategia}")
        if res.explicacion:
            txt.append(f"• {res.explicacion}")
        if res.pasos:
            txt.append("\nPASOS:")
            for p in res.pasos:
                txt.append(f"• {p}")
        return "\n".join(txt)
