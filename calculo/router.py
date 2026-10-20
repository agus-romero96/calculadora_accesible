from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, List
import sympy as sp
from sympy import Symbol, S

from calculo.pasos import PasoCalculo, texto_paso
from i18n import tr
from .lim_estrategias.trigonometria import LimitesTrigNotables
from .lim_estrategias.racionalizacion import RacionalizacionRaices
from .lim_estrategias.infinito import LimiteRacionalInfinito
from .lim_estrategias.continuidad import ContinuidadComposicion
from .lim_estrategias.simplificacion import SimplificacionCancelacion
from .lim_estrategias._base import ESTADO_NO_CONCLUYENTE, ResultadoEstrategia, limite_seguro
from .lim_estrategias.general import LimiteGeneral


def humanizar_limite(val: Any) -> str:
    """Traduce el valor de limite_seguro() a texto claro para lector de pantalla."""
    if val is None:
        return tr("No concluyente")
    if isinstance(val, sp.Basic) and val.has(sp.AccumBounds):
        return tr("No existe (comportamiento oscilatorio)")
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
    def __init__(self, parser_compartido):
        self.parser = parser_compartido
        self.general = LimiteGeneral()

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
            # El parser no evalúa (evaluate=False): doit() quita formas como sqrt(x + 1) - 1*1
            expr = self.parser.parsear(expresion).doit()
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

        return self._modo_general(expresion, expr, var, punto, dir_)

    # -------------------------
    # Modo general: lo que no resuelve ninguna estrategia
    # -------------------------
    def _modo_general(self, expr_str: str, expr: Any, var: Any, punto: Any, dir_: Optional[str]) -> ResultadoRouter:
        """
        El valor lo da SymPy; la explicación, LimiteGeneral (sustitución, laterales, L'Hôpital,
        forma exponencial...). Si no llega a ese valor, se da el resultado sin pasos y con un aviso.
        """
        valor = limite_seguro(expr, var, punto, dir_)
        explicacion = self.general.explicar(expr, var, punto, dir_, valor) if valor is not None else None
        if explicacion is not None:
            pasos, tecnica = explicacion
            res = ResultadoEstrategia(aplica=True, resultado=valor, pasos=pasos,
                                      nombre_estrategia=tr("Modo General ({tecnica})", tecnica=tr(tecnica)))
        else:
            res = ResultadoEstrategia(aplica=True, resultado=valor,
                                      nombre_estrategia=tr("Modo General ({tecnica})", tecnica="SymPy"),
                                      avisos=[tr("No se pudo explicar este límite paso a paso; el resultado es el que "
                                                 "calcula SymPy.")])
        return ResultadoRouter(self._render_estrategia(expr_str, var, punto, dir_, res), valor)

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

        return self.parser.parsear(raw).doit(), d

    def _render_estrategia(self, expr_in, var, punto, dir_, res):
        s = dir_ if dir_ else ""
        txt = [tr("RESULTADO: {valor}", valor=humanizar_limite(res.resultado)), "=" * 30]
        txt.append(tr("Límite de {expresion} cuando {variable} -> {punto}", expresion=expr_in, variable=var, punto=f"{punto}{s}"))
        txt.append("\n" + tr("MÉTODO: {metodo}", metodo=tr(res.nombre_estrategia)))
        if res.explicacion:
            txt.append(tr(res.explicacion))
        if res.pasos:
            txt.append("\n" + tr("PASO A PASO:"))
            for i, p in enumerate(res.pasos, 1):
                txt.append(texto_paso(i, p) if isinstance(p, PasoCalculo) else f"• {p}")
        if res.avisos:
            txt.append("\n" + tr("[!] AVISOS:"))
            txt.extend(f" - {a}" for a in res.avisos)
        return "\n".join(txt)
