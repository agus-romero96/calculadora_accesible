"""
Módulo especializado en Límites.
Arquitectura: Deep Inspection V2.3 (Didactic Solver + Pragmatic UX).

Cambios V2.3:
  - Normalización previa real (together -> cancel -> simplify) antes del diagnóstico.
  - Cancelación se intenta también en escenarios tipo k/0 (porque puede ser cancelable).
  - L'Hôpital validado por iteración (solo si la forma sigue siendo 0/0 o ∞/∞).
  - Triple-Check de cero en Den' (Performance + Rigor + Aviso si equals no decide).
  - _limite_seguro con fallback a sympy.Limit (no rompe el flujo).
  - Humanización de sympy.zoo simplificada para estudiantes (cálculo real).
  - Renderizado "Resumen Primero" (Accesibilidad NVDA).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sympy
from sympy import Symbol, S

from calculo.lim_estrategias._base import limite_seguro
from i18n import tr


# =============================================================
# 1) DTO (Inmutable y Transparente)
# =============================================================

@dataclass(frozen=True)
class ResultadoLimite:
    es_exitoso: bool

    expresion_input: str
    expr_sympy: Optional[Any]

    variable_input: Optional[str]
    variable: Optional[Symbol]

    tendencia_input: str
    punto: Optional[Any]

    limite_global: Optional[Any]
    laterales: Dict[str, Optional[Any]] = field(default_factory=lambda: {"izq": None, "der": None})

    indeterminacion_inicial: Optional[str] = None
    tipo_comportamiento: str = ""

    estrategia_resolucion: str = ""
    pasos_resolucion: List[str] = field(default_factory=list)

    pasos: List[str] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)
    mensaje_error: str = ""


# =============================================================
# 2) MOTOR LÓGICO
# =============================================================

class GestorLimites:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # ---------------- API PÚBLICA ----------------

    def calcular_limite(self, expresion: str, variable: Optional[str] = None, tendencia: str = "0") -> str:
        dto = self.calcular_limite_dto(expresion, variable=variable, tendencia=tendencia)
        return self.renderizar(dto)

    def calcular_limite_dto(
        self,
        expresion: str,
        variable: Optional[str] = None,
        tendencia: str = "0"
    ) -> ResultadoLimite:
        try:
            # 1) Parsing y preparación
            expr_original = self.parser.parsear(expresion)
            var_sym, avisos_var = self._resolver_variable(expr_original, variable)
            advertencias = list(avisos_var)

            punto = self._parsear_tendencia(tendencia)

            pasos_grales: List[str] = []
            pasos_res: List[str] = []
            estrategia_res = tr("Directa")

            # 2) Normalización previa (forma equivalente) ANTES de diagnosticar
            expr_norm, notas_norm = self._normalizar_para_diagnostico(expr_original)
            pasos_grales.extend(notas_norm)

            # 3) Diagnóstico inicial (sobre forma normalizada)
            indet, nota = self._diagnostico_por_sustitucion(expr_norm, var_sym, punto)
            if nota:
                pasos_grales.append(nota)

            # 4) Resolución didáctica por prioridad (si aplica)
            if indet in ("0/0", "inf/inf", "k/0"):
                estrategia_res, pasos_res = self._resolver_con_prioridad(
                    expr_original=expr_original,
                    expr_norm=expr_norm,
                    var=var_sym,
                    punto=punto,
                    tipo=indet
                )

            # 5) Verdad matemática: límite global SIEMPRE sobre la expresión original
            lim_global = self._limite_seguro(expr_original, var_sym, punto, dir=None)

            # 6) Laterales solo si el punto es finito con certeza
            laterales = {"izq": None, "der": None}
            if self._es_punto_finito(punto):
                laterales["izq"] = self._limite_seguro(expr_original, var_sym, punto, dir="-")
                laterales["der"] = self._limite_seguro(expr_original, var_sym, punto, dir="+")

            # 7) Clasificación final
            tipo_comp = self._diagnosticar_comportamiento(expr_original, var_sym, punto, lim_global, laterales)

            return ResultadoLimite(
                es_exitoso=True,
                expresion_input=expresion,
                expr_sympy=expr_original,
                variable_input=variable,
                variable=var_sym,
                tendencia_input=tendencia,
                punto=punto,
                limite_global=lim_global,
                laterales=laterales,
                indeterminacion_inicial=indet,
                tipo_comportamiento=tipo_comp,
                estrategia_resolucion=estrategia_res,
                pasos_resolucion=pasos_res,
                pasos=pasos_grales,
                advertencias=advertencias,
            )

        except Exception as e:
            return ResultadoLimite(
                es_exitoso=False,
                expresion_input=expresion,
                expr_sympy=None,
                variable_input=variable,
                variable=None,
                tendencia_input=tendencia,
                punto=None,
                limite_global=None,
                tipo_comportamiento=tr("Error Crítico"),
                mensaje_error=str(e),
            )

    # =============================================================
    # 3) Resolución (Prioridad Algebraica > L'Hôpital)
    # =============================================================

    def _resolver_con_prioridad(
        self,
        expr_original: Any,
        expr_norm: Any,
        var: Symbol,
        punto: Any,
        tipo: str
    ) -> Tuple[str, List[str]]:
        pasos: List[str] = []

        # A) Intento 1: Cancelación (aplica también si el diagnóstico fue k/0)
        # Porque "k" puede volverse 0 tras simplificar/cancelar correctamente.
        try:
            expr_cancel = sympy.cancel(expr_norm)
        except Exception:
            expr_cancel = expr_norm

        if expr_cancel != expr_norm:
            pasos.append(tr("Estrategia: Cancelación / simplificación de factores comunes."))
            pasos.append(tr("1) Forma normalizada: {expr_norm}", expr_norm=expr_norm))
            pasos.append(tr("2) cancel(forma): {expr_cancel}", expr_cancel=expr_cancel))

            ind2, nota2 = self._diagnostico_por_sustitucion(expr_cancel, var, punto)
            if nota2:
                pasos.append(tr("   Diagnóstico tras cancelación: {nota2}", nota2=nota2))

            if ind2 not in ("0/0", "inf/inf"):
                lim2 = self._limite_seguro(expr_cancel, var, punto, dir=None)
                pasos.append(tr("3) La indeterminación se eliminó algebraicamente."))
                pasos.append(tr("   Nuevo límite evaluable = {lim2}", lim2=lim2))
                return tr("Cancelación"), pasos

        expr_for_lhop = expr_cancel  # mejor que usar expr_norm si hubo mejoras

        # B) Intento 2: L'Hôpital (solo si sigue siendo 0/0 o inf/inf)
        ind_lhop, nota_lhop = self._diagnostico_por_sustitucion(expr_for_lhop, var, punto)
        if ind_lhop in ("0/0", "inf/inf"):
            pasos_lhop = []
            if nota_lhop:
                pasos_lhop.append(tr("Verificación: {nota_lhop}", nota_lhop=nota_lhop))
            est, pasos_det = self._resolver_lhopital_validado(expr_for_lhop, var, punto, ind_lhop)
            return est, pasos + pasos_lhop + pasos_det

        # Si no aplica L'Hôpital, nos quedamos con normalización/cancelación
        pasos.append(tr("No se aplicó L'Hôpital (la forma ya no es 0/0 ni ∞/∞ tras simplificar)."))
        return tr("Normalización"), pasos

    def _resolver_lhopital_validado(self, expr: Any, var: Symbol, punto: Any, tipo: str) -> Tuple[str, List[str]]:
        pasos: List[str] = []
        pasos.append(tr("Estrategia: Regla de L'Hôpital (solo para 0/0 o ∞/∞). Forma detectada: {tipo}.", tipo=tipo))
        pasos.append(tr("Nota didáctica: L'Hôpital requiere derivabilidad en un entorno del punto (aquí se usa como herramienta CAS)."))

        current = expr
        max_iter = 3

        for k in range(1, max_iter + 1):
            num, den = current.as_numer_denom()
            if den == 1:
                pasos.append(tr("La expresión dejó de ser un cociente; L'Hôpital ya no corresponde."))
                break

            # Validación por iteración: ¿sigue siendo 0/0 o inf/inf?
            ind_step, nota_step = self._diagnostico_por_sustitucion(current, var, punto)
            if ind_step not in ("0/0", "inf/inf"):
                lim_now = self._limite_seguro(current, var, punto, dir=None)
                pasos.append(tr("Cierre: ya no es 0/0 ni ∞/∞, evaluamos sin L'Hôpital."))
                if nota_step:
                    pasos.append(tr("   Diagnóstico: {nota_step}", nota_step=nota_step))
                pasos.append(tr("   lim = {lim_now}", lim_now=lim_now))
                return tr("Evaluación (tras L'Hôpital parcial)"), pasos

            # Derivación
            dnum = sympy.diff(num, var)
            dden = sympy.diff(den, var)

            dnum_s = sympy.simplify(dnum)
            dden_s = sympy.simplify(dden)

            pasos.append(tr("Paso {k}: derivamos numerador y denominador.", k=k))
            pasos.append(tr("   Num = {num}", num=num))
            pasos.append(tr("   Den = {den}", den=den))
            pasos.append(tr("   Num' = {dnum_s}", dnum_s=dnum_s))
            pasos.append(tr("   Den' = {dden_s}", dden_s=dden_s))

            # TRIPLE-CHECK de cero en Den'
            es_cero, aviso_cero = self._triple_check_cero(dden_s)
            if aviso_cero:
                pasos.append(tr("   Aviso: {aviso_cero}", aviso_cero=aviso_cero))

            if es_cero:
                pasos.append(tr("   [!] Den' = 0: L'Hôpital no progresa. Se requiere otro método (series/transformaciones)."))
                return tr("L'Hôpital (no progresa)"), pasos

            current = sympy.simplify(dnum_s / dden_s)
            pasos.append(tr("   Nuevo cociente: {current}", current=current))

        pasos.append(tr("Tras varias iteraciones, no se obtuvo un cierre concluyente con L'Hôpital limitado."))
        return tr("L'Hôpital (iteración limitada)"), pasos

    def _triple_check_cero(self, expr: Any) -> Tuple[bool, str]:
        """
        Devuelve (es_cero, aviso).
        - check rápido: expr == 0
        - check profundo: expr.equals(0)
        - si equals no decide (None), no se asume cero, pero se avisa.
        """
        try:
            if expr == 0:
                return True, ""
        except Exception:
            pass

        try:
            r = expr.equals(0)
            if r is True:
                return True, ""
            if r is None:
                return False, tr("No se pudo decidir simbólicamente si Den' es 0 (equals devolvió None); se continúa con cautela.")
            return False, ""
        except Exception:
            return False, tr("equals(0) falló; se continúa con el mejor esfuerzo.")

    # =============================================================
    # 4) Normalización previa (forma equivalente)
    # =============================================================

    def _normalizar_para_diagnostico(self, expr: Any) -> Tuple[Any, List[str]]:
        notas: List[str] = []
        try:
            expr0 = sympy.together(expr)
            if expr0 != expr:
                notas.append(tr("Normalización: together(expr) → {expr0}", expr0=expr0))
            else:
                notas.append(tr("Normalización: together(expr) no cambió la forma."))

            expr1 = sympy.cancel(expr0)
            if expr1 != expr0:
                notas.append(tr("Normalización: cancel(forma) → {expr1}", expr1=expr1))

            expr2 = sympy.simplify(expr1)
            if expr2 != expr1:
                notas.append(tr("Normalización: simplify(forma) → {expr2}", expr2=expr2))

            return expr2, notas
        except Exception:
            notas.append(tr("Normalización: no concluyente (se mantiene la expresión original para diagnóstico)."))
            return expr, notas

    # =============================================================
    # 5) Utilidades / Parsing
    # =============================================================

    def _resolver_variable(self, expr: Any, var_str: Optional[str]) -> Tuple[Symbol, List[str]]:
        avisos: List[str] = []

        if var_str and str(var_str).strip():
            return self.parser.simbolo(var_str), avisos

        syms = sorted(list(expr.free_symbols), key=lambda s: s.name)
        if len(syms) == 1:
            return syms[0], avisos
        if len(syms) == 0:
            raise ValueError(tr("La expresión no contiene variables. Especifique una variable para calcular el límite."))
        raise ValueError(tr("La expresión tiene varias variables ({variables}). Especifique la variable.",
                            variables=", ".join(s.name for s in syms)))

    def _parsear_tendencia(self, t: str) -> Any:
        s = str(t).strip().lower()
        if s in {"oo", "inf", "+inf", "infinito", "+infinito", "∞", "+∞"}:
            return S.Infinity
        if s in {"-oo", "-inf", "-infinito", "-∞"}:
            return S.NegativeInfinity
        return self.parser.parsear(t)

    def _es_punto_finito(self, punto: Any) -> bool:
        try:
            return punto is not None and (punto.is_finite is True)
        except Exception:
            return False

    # =============================================================
    # 6) Diagnóstico por sustitución (robusto)
    # =============================================================

    def _diagnostico_por_sustitucion(self, expr: Any, var: Symbol, punto: Any) -> Tuple[Optional[str], str]:
        try:
            if punto in (S.Infinity, S.NegativeInfinity):
                return None, tr("Punto en infinito: la sustitución directa no es concluyente; se analiza asintóticamente.")

            num, den = expr.as_numer_denom()

            # No es fracción
            if den == 1:
                v = sympy.simplify(expr.subs(var, punto))
                if (v is sympy.nan) or (v is sympy.zoo):
                    return None, tr("Sustitución directa produce NaN/zoo (posible indeterminación o divergencia).")
                if getattr(v, "is_finite", None) is True:
                    return None, tr("Sustitución directa: f({punto}) = {v}.", punto=punto, v=v)
                return None, tr("Sustitución directa no concluyente.")

            # Es fracción
            n0 = sympy.simplify(num.subs(var, punto))
            d0 = sympy.simplify(den.subs(var, punto))

            if n0 == 0 and d0 == 0:
                return "0/0", tr("Sustitución directa en numerador/denominador: 0/0.")
            if d0 == 0 and n0 != 0:
                return "k/0", tr("Sustitución directa sugiere k/0 (podría ser asíntota vertical o cancelable tras simplificar).")
            if (n0 in (S.Infinity, S.NegativeInfinity)) and (d0 in (S.Infinity, S.NegativeInfinity)):
                return "inf/inf", tr("Sustitución directa sugiere ∞/∞.")
            return None, tr("Sustitución directa no concluyente.")

        except Exception:
            return None, tr("Sustitución directa no concluyente.")

    # =============================================================
    # 7) Límite seguro (con fallback formal)
    # =============================================================

    def _limite_seguro(self, expr: Any, var: Symbol, punto: Any, dir: Optional[str]) -> Any:
        # Bilateral real en puntos finitos (sympy.limit sin dir es solo el lateral derecho)
        return limite_seguro(expr, var, punto, dir)

    # =============================================================
    # 8) Diagnóstico de comportamiento (robusto)
    # =============================================================

    def _diagnosticar_comportamiento(self, expr: Any, var: Symbol, punto: Any, lim: Any, laterales: Dict[str, Any]) -> str:
        izq = laterales.get("izq")
        der = laterales.get("der")

        # Infinito: asíntota horizontal vs divergencia
        if punto in (S.Infinity, S.NegativeInfinity):
            if self._es_finito(lim):
                return tr("Converge (Asíntota Horizontal)")
            if self._es_infinito(lim) or (lim is sympy.zoo):
                return tr("Diverge (Infinito)")
            return tr("Comportamiento complejo en infinito")

        # Finito: continuidad vs hueco
        if self._es_finito(lim):
            try:
                val = sympy.simplify(expr.subs(var, punto))
                if val is sympy.nan or val is sympy.zoo:
                    return tr("Discontinuidad evitable (hueco)")
                if sympy.simplify(val - lim) == 0:
                    return tr("Función continua")
                return tr("Discontinuidad evitable (hueco)")
            except Exception:
                return tr("Discontinuidad evitable (hueco)")

        # Asíntota vertical
        if self._es_infinito(lim) or (lim is sympy.zoo):
            if izq is not None and der is not None:
                if self._es_infinito(izq) and self._es_infinito(der):
                    if izq == der:
                        return tr("Asíntota vertical (misma dirección)")
                    return tr("Asíntota vertical (signos opuestos)")
                return tr("Asíntota vertical (divergencia lateral)")
            return tr("Asíntota vertical")

        # Si global no existe, mirar laterales
        if izq is not None and der is not None:
            if self._es_finito(izq) and self._es_finito(der) and sympy.simplify(izq - der) != 0:
                try:
                    salto = sympy.simplify(sympy.Abs(der - izq))
                    return tr("Discontinuidad de salto (salto = {salto})", salto=salto)
                except Exception:
                    return tr("Discontinuidad de salto")
            if izq == der:
                return tr("Límite existe (según laterales) pero no fue determinado globalmente")
            return tr("Límite no existe (laterales no coinciden)")

        return tr("No concluyente / comportamiento complejo")

    def _es_finito(self, val: Any) -> bool:
        if val is None:
            return False
        if val is sympy.nan or val is sympy.zoo:
            return False
        try:
            return val.is_finite is True
        except Exception:
            return False

    def _es_infinito(self, val: Any) -> bool:
        if val is None:
            return False
        if val in (S.Infinity, S.NegativeInfinity):
            return True
        try:
            return val.is_infinite is True
        except Exception:
            return False

    # =============================================================
    # 9) Renderizado accesible (Resumen primero)
    # =============================================================

    def renderizar(self, res: ResultadoLimite) -> str:
        if not res.es_exitoso:
            return tr("ERROR DE CÁLCULO:\n{mensaje_error}", mensaje_error=res.mensaje_error)

        txt: List[str] = []

        # 0) RESULTADO (primero, NVDA-friendly)
        txt.append(tr("RESULTADO: {limite_global}", limite_global=self._humanizar(res.limite_global)))
        txt.append("=" * 34)

        # 1) CONTEXTO
        txt.append(tr("Límite de: {expresion_input}", expresion_input=res.expresion_input))
        txt.append(tr("Cuando {variable} tiende a {punto}", variable=res.variable, punto=res.punto))

        # 2) DIAGNÓSTICO
        txt.append(tr("\n1. DIAGNÓSTICO"))
        if res.indeterminacion_inicial:
            txt.append(tr("   • Forma inicial: [{indeterminacion_inicial}]", indeterminacion_inicial=res.indeterminacion_inicial))
        else:
            txt.append(tr("   • Sustitución directa no mostró una indeterminación clásica inmediata."))
        txt.append(tr("   • Clasificación: {tipo_comportamiento}", tipo_comportamiento=res.tipo_comportamiento))

        # 3) NOTAS / NORMALIZACIÓN
        if res.pasos:
            txt.append(tr("\n2. NOTAS / NORMALIZACIÓN"))
            for p in res.pasos:
                txt.append(f"   • {p}")

        # 4) PROCEDIMIENTO
        if res.pasos_resolucion:
            txt.append(tr("\n3. PROCEDIMIENTO ({estrategia_resolucion})", estrategia_resolucion=res.estrategia_resolucion))
            for p in res.pasos_resolucion:
                txt.append(f"   • {p}")

        # 5) LATERALES
        if self._es_punto_finito(res.punto):
            txt.append(tr("\n4. ANÁLISIS LATERAL"))
            txt.append(tr("   • Izquierda (-): {izq}", izq=self._humanizar(res.laterales.get('izq'))))
            txt.append(tr("   • Derecha   (+): {der}", der=self._humanizar(res.laterales.get('der'))))

        # 6) AVISOS
        if res.advertencias:
            txt.append(tr("\n[!] AVISOS:"))
            for a in res.advertencias:
                txt.append(f"   - {a}")

        return "\n".join(txt)

    def _humanizar(self, val: Any) -> str:
        """Traductor didáctico de símbolos SymPy (cálculo real)."""
        if val is None:
            return tr("Indeterminado / No concluyente")
        if val == S.Infinity:
            return tr("+Infinito")
        if val == S.NegativeInfinity:
            return tr("-Infinito")
        if val is sympy.zoo:
            return tr("No existe (diverge a infinitos de distinto signo)")
        if val is sympy.nan:
            return tr("No existe (los límites laterales no coinciden)")
        return str(val)
