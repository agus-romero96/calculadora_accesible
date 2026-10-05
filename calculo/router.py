from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, List
import sympy as sp
from sympy import Symbol, S

from i18n import tr
from .lim_estrategias.trigonometria import LimitesTrigNotables
from .lim_estrategias.racionalizacion import RacionalizacionRaices
from .lim_estrategias.infinito import LimiteRacionalInfinito
from .lim_estrategias.continuidad import ContinuidadComposicion
from .lim_estrategias.simplificacion import SimplificacionCancelacion
from .lim_estrategias._base import ESTADO_NO_CONCLUYENTE, limite_seguro


def humanizar_limite(val: Any) -> str:
    """Traduce el valor de limite_seguro() a texto claro para lector de pantalla."""
    if val is None:
        return tr("No concluyente")
    if val == S.Infinity:
        return tr("+Infinito")
    if val == S.NegativeInfinity:
        return tr("-Infinito")
    if val is sp.zoo:
        return tr("No existe (diverge a infinitos de distinto signo)")
    if val is sp.nan:
        return tr("No existe (los límites laterales no coinciden)")
    return str(val)


@dataclass(frozen=True)
class ResultadoRouter:
    texto: str              # informe accesible (idioma actual)
    valor: Any = None       # valor SymPy del límite (oo, zoo, nan...) o None si no se pudo
    es_error: bool = False  # error en los datos (sintaxis, tendencia vacía...)


class RouterMatematico:
    def __init__(self, parser_compartido, motor_limites_viejo):
        self.parser = parser_compartido
        self.motor_limites = motor_limites_viejo

        # Orden: de la estrategia más específica a la más general.
        # La primera que llega a una conclusión gana, así que las técnicas didácticas
        # concretas (trig, racionalización, grados) van antes que la cancelación genérica.
        self.estrategias = [
            LimitesTrigNotables(),
            RacionalizacionRaices(),
            LimiteRacionalInfinito(),
            ContinuidadComposicion(),
            SimplificacionCancelacion(),
        ]

    def CalcularLimite(self, expresion: str, variable: Optional[str] = None, tendencia: str = "0") -> str:
        return self.calcular(expresion, variable, tendencia).texto

    def calcular(self, expresion: str, variable: Optional[str] = None, tendencia: str = "0") -> ResultadoRouter:
        try:
            expr = self.parser.parsear(expresion)
            var = self._resolver_var(expr, variable)
            punto, dir_ = self._parsear_tendencia(tendencia)
        except Exception as e:
            return ResultadoRouter(tr("Error en los datos del límite:") + f"\n{e}", es_error=True)

        for est in self.estrategias:
            try:
                if not est.puede_resolver(expr, var, punto, dir=dir_):
                    continue
                res = est.resolver(expr, var, punto, dir=dir_)
            except Exception:
                # Una estrategia que falla no debe impedir probar las siguientes ni el fallback
                continue
            if res.aplica and res.estado != ESTADO_NO_CONCLUYENTE:
                return ResultadoRouter(self._render_estrategia(expresion, var, punto, dir_, res), res.resultado)

        return self._fallback(expresion, variable, tendencia, expr, var, punto, dir_)

    # -------------------------
    # PASO 1: Fallback robusto
    # -------------------------
    def _fallback(self, expr_str: str, var_str: Optional[str], tend_str: str,
                  expr_parsed: Any, var_sym: Any, punto: Any, dir_: Optional[str]) -> ResultadoRouter:
        """
        Regla de oro para tu auditor:
        - SIEMPRE devolver una línea 'RESULTADO: ...'
        - SIEMPRE devolver una línea 'MÉTODO: ...'
        """

        # 1) Si es lateral explícito, intentamos SymPy directo (es lo más fiel al dir)
        if dir_ in {"+", "-"}:
            val = limite_seguro(expr_parsed, var_sym, punto, dir_)
            if val is not None:
                return ResultadoRouter("\n".join([
                    tr("RESULTADO: {valor}", valor=humanizar_limite(val)),
                    "=" * 30,
                    tr("MÉTODO: {metodo}", metodo=tr("Modo General (límite lateral calculado con SymPy, dir='{dir}')", dir=dir_)),
                    tr("Límite de {expresion} cuando {variable} -> {punto}", expresion=expr_str, variable=var_sym, punto=f"{punto}{dir_}"),
                ]), val)
            # Si falla, igual devolvemos RESULTADO parseable
            return ResultadoRouter("\n".join([
                tr("RESULTADO: {valor}", valor=tr("No concluyente")),
                "=" * 30,
                tr("MÉTODO: {metodo}", metodo=tr("Modo General (Motor Viejo) + Error en lateral directo")),
                "",
                self._motor_viejo(expr_str, var_str, tend_str),
            ]))

        # 2) Bilateral / infinito: SymPy da el RESULTADO; el motor viejo, la explicación
        sympy_val = limite_seguro(expr_parsed, var_sym, punto)
        base = self._motor_viejo(expr_str, var_str, tend_str)

        metodo = tr("Modo General (Motor Viejo)")
        if sympy_val is not None:
            metodo += " + " + tr("Verificación SymPy")

        return ResultadoRouter("\n".join([
            tr("RESULTADO: {valor}", valor=humanizar_limite(sympy_val)),
            "=" * 30,
            tr("MÉTODO: {metodo}", metodo=metodo),
            tr("Límite de {expresion} cuando {variable} -> {punto}", expresion=expr_str, variable=var_sym, punto=punto),
            "",
            base,
        ]), sympy_val)

    def _motor_viejo(self, expr_str: str, var_str: Optional[str], tend_str: str) -> str:
        # El motor viejo espera strings; si var_str es None, pasamos "x" como default
        v = var_str if var_str else "x"
        try:
            return self.motor_limites.calcular_limite(expr_str, v, tend_str)
        except Exception as e:
            return tr("(Motor viejo falló) Error: {error}", error=e)

    # -------------------------
    # Helpers existentes
    # -------------------------
    def _resolver_var(self, expr, v_str):
        # parser.simbolo() crea la misma variable real que el parser
        if v_str and v_str.strip():
            return self.parser.simbolo(v_str)
        x = self.parser.simbolo("x")
        s = list(expr.free_symbols)
        if not s or x in s:
            return x
        return s[0]

    def _parsear_tendencia(self, t_str):
        raw = (t_str.lower().strip()
               .replace("∞", "oo").replace("infinity", "oo").replace("infinito", "oo"))
        if not raw:
            raise ValueError(tr("La tendencia está vacía. Escriba un número, oo o -oo."))
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
        txt = [tr("RESULTADO: {valor}", valor=humanizar_limite(res.resultado)), "=" * 30]
        txt.append(tr("Límite de {expresion} cuando {variable} -> {punto}", expresion=expr_in, variable=var, punto=f"{punto}{s}"))
        txt.append("\n" + tr("MÉTODO: {metodo}", metodo=tr(res.nombre_estrategia)))
        if res.explicacion:
            txt.append(f"• {tr(res.explicacion)}")
        if res.pasos:
            txt.append("\n" + tr("PASOS:"))
            for p in res.pasos:
                txt.append(f"• {p}")
        return "\n".join(txt)
