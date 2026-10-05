"""
Módulo especializado en Cálculo Diferencial e Integral.
Arquitectura: Deep Inspection V4.3 (Enterprise Rigor + Didactic Honesty + Pragmatic UX).

Cambios V4.3 (respecto a tu V4.2):
  - Cierre completo en Potencia General u(x)^v(x): y' = y * (v' ln u + v * u'/u).
  - Derivada enésima: simplificación controlada para evitar explosión de términos.
  - Integral: manejo de errores sin "except:" pelado (no oculta fallos reales).
  - Integración por sustitución (URule): pasos más honestos (sin fingir cambio de variable con Symbol('u')).
  - Render: "RESULTADO primero" opcional por accesibilidad (mantiene RenderizarTexto()).

Nota: Se mantiene la inyección de dependencias: self.parser.parsear(...) como en tu diseño. :contentReference[oaicite:2]{index=2}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import sympy
from sympy import Symbol, Dummy

# Reglas de integración manual (manualintegrate)
from sympy.integrals.manualintegrate import (
    integral_steps,
    ConstantTimesRule, AddRule, URule, PartsRule, TrigRule, ExpRule,
    ReciprocalRule, PowerRule, ConstantRule, DontKnowRule
)


# =============================================================
# CAPA DE DATOS (DTOs Inmutables)
# =============================================================

@dataclass(frozen=True)
class PasoCalculo:
    titulo: str
    descripcion: str
    expresion_matematica: str = ""


@dataclass(frozen=True)
class ResultadoCalculo:
    es_exitoso: bool
    tipo: str  # "DERIVADA", "INTEGRAL", "DERIVADA_ENECIMA"
    expresion_input: str
    expr_sympy: Optional[Any]
    variable: Optional[Symbol]
    resultado: Any

    estrategia_principal: str = ""
    estrategias_secundarias: List[str] = field(default_factory=list)
    diagnostico: str = ""
    pasos: List[PasoCalculo] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)
    mensaje_error: str = ""
    requiere_constante: bool = False


# =============================================================
# MOTOR LÓGICO
# =============================================================

class Calculo:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # ---------------------------------------------------------
    # 1) GESTIÓN DE VARIABLES (VALIDACIÓN ESTRICTA)
    # ---------------------------------------------------------

    def _resolver_variable(self, expr: Any, var_str: Optional[str], operacion: str) -> Tuple[Symbol, List[str]]:
        advertencias: List[str] = []

        # 1. Prioridad: usuario explícito
        if var_str and str(var_str).strip():
            return Symbol(str(var_str).strip()), advertencias

        # 2. Inferencia
        syms = sorted(list(expr.free_symbols), key=lambda s: s.name)

        if len(syms) == 1:
            return syms[0], advertencias

        # 3. Caso constante
        if len(syms) == 0:
            if operacion == "INTEGRAL":
                raise ValueError(
                    "Ambigüedad en Integral: está intentando integrar una constante sin especificar la variable. Indíquela."
                )
            advertencias.append("La expresión es constante. Se asume derivación respecto a 'x'.")
            return Symbol("x"), advertencias

        # 4. Caso multivariable: política (preferir x si existe)
        nombres = [s.name for s in syms]
        if "x" in nombres:
            x_sym = next(s for s in syms if s.name == "x")
            advertencias.append(
                f"Ambigüedad: se detectaron varias variables ({', '.join(nombres)}). Se asume derivación respecto a 'x'."
            )
            return x_sym, advertencias

        raise ValueError(
            f"Ambigüedad Matemática: la expresión tiene varias variables ({', '.join(nombres)}). "
            "Especifique respecto a cuál desea operar."
        )

    # ---------------------------------------------------------
    # 2) MOTOR DE DERIVADAS (RECURSIVIDAD PEDAGÓGICA)
    # ---------------------------------------------------------

    def CalcularDerivada(self, expresion: str, variable: str = None) -> ResultadoCalculo:
        try:
            expr = self.parser.parsear(expresion)
            var, avisos = self._resolver_variable(expr, variable, "DERIVADA")

            # Verdad matemática
            derivada_final = sympy.diff(expr, var)

            # Análisis estructural
            pasos, estrategia, diag, secundarias = self._analizar_estructura_derivada(expr, var, profundidad=0)

            # Deduplicado estable
            secundarias_limpias = list(dict.fromkeys(secundarias))

            # Aviso si SymPy no pudo “cerrar” (derivada formal)
            if derivada_final.has(sympy.Derivative):
                avisos.append("NOTA: el resultado contiene Derivative(...): SymPy lo dejó en forma simbólica (no elemental o no simplificado).")

            return ResultadoCalculo(
                es_exitoso=True,
                tipo="DERIVADA",
                expresion_input=expresion,
                expr_sympy=expr,
                variable=var,
                resultado=sympy.simplify(derivada_final),
                estrategia_principal=estrategia,
                estrategias_secundarias=secundarias_limpias,
                diagnostico=diag,
                pasos=pasos,
                advertencias=avisos
            )

        except Exception as e:
            return ResultadoCalculo(False, "DERIVADA", expresion, None, None, None, mensaje_error=str(e))

    def _analizar_estructura_derivada(
        self,
        expr: Any,
        var: Symbol,
        profundidad: int = 0
    ) -> Tuple[List[PasoCalculo], str, str, List[str]]:
        """
        Retorna: (Pasos, EstrategiaPrincipal, Diagnóstico, EstrategiasSecundarias)
        """
        pasos: List[PasoCalculo] = []
        secundarias: List[str] = []

        # A) Constante
        if not expr.has(var):
            return (
                [PasoCalculo("Derivada de Constante", "La expresión no varía respecto a la variable.", "Resultado = 0")],
                "Constante",
                "Función constante.",
                []
            )

        # B) Linealidad (Suma/Resta)
        if expr.is_Add:
            terminos = expr.args
            pasos.append(PasoCalculo("Regla de Linealidad", f"Suma de derivadas ({len(terminos)} términos).", "(u+v)'=u'+v'"))

            for i, t in enumerate(terminos, 1):
                _, strat_t, _, sec_t = self._analizar_estructura_derivada(t, var, profundidad + 1)
                d_t = sympy.diff(t, var)
                if strat_t not in ("Constante", "Directa"):
                    secundarias.append(strat_t)
                secundarias.extend(sec_t)

                pasos.append(PasoCalculo(f"Derivada Término {i}", f"Estrategia: {strat_t}", f"d({t}) = {d_t}"))

            return pasos, "Linealidad", "Suma algebraica.", secundarias

        # C) Cociente (y detección de potencia negativa)
        num, den = expr.as_numer_denom()
        es_potencia_negativa = (expr.is_Pow and getattr(expr, "exp", None) is not None and expr.exp.is_negative)

        if den != 1 and den.has(var):
            if es_potencia_negativa:
                secundarias.append("Regla del Cociente (alternativa)")
                base, exp = expr.as_base_exp()
                u = base
                n = exp
                du = sympy.diff(u, var)
                pasos.append(PasoCalculo("Regla de Potencia Negativa", "Expresión recíproca/inversa.", f"u={u}, n={n}"))
                pasos.append(PasoCalculo("Regla Generalizada", "n*u^(n-1)*u'", f"{n}*({u})^({n}-1)*({du})"))
                return pasos, "Potencia Negativa", "Potencia con exponente negativo.", secundarias

            u = num
            v = den
            du = sympy.diff(u, var)
            dv = sympy.diff(v, var)

            _, strat_u, _, sec_u = self._analizar_estructura_derivada(u, var, profundidad + 1)
            _, strat_v, _, sec_v = self._analizar_estructura_derivada(v, var, profundidad + 1)
            secundarias.extend([s for s in (strat_u, strat_v) if s not in ("Constante", "Directa")])
            secundarias.extend(sec_u + sec_v)

            pasos.append(PasoCalculo("Regla del Cociente", "Identificamos u y v.", f"u={u}\nv={v}"))
            pasos.append(PasoCalculo("Derivadas", f"u' ({strat_u}) y v' ({strat_v}).", f"u'={du}\nv'={dv}"))
            pasos.append(PasoCalculo("Aplicar Fórmula", "(u'v - uv')/v²", f"(({du})*({v}) - ({u})*({dv})) / ({v})^2"))
            return pasos, "Regla del Cociente", "Función racional.", secundarias

        # D) Producto (constantes simbólicas separadas)
        if expr.is_Mul:
            constantes = []
            variables = []
            for arg in expr.args:
                (variables if arg.has(var) else constantes).append(arg)

            if constantes:
                coeff = sympy.Mul(*constantes)
                if not variables:
                    return (
                        [PasoCalculo("Derivada de Constante", "Expresión simbólica constante.", "0")],
                        "Constante",
                        "Constante simbólica.",
                        []
                    )

                resto = sympy.Mul(*variables)
                sub_pasos, sub_strat, _, sub_sec = self._analizar_estructura_derivada(resto, var, profundidad + 1)

                pasos.append(PasoCalculo("Constante por Función", f"Extraemos coeficiente {coeff}.", f"{coeff} * d({resto})"))
                pasos.extend(sub_pasos)

                if sub_strat not in ("Constante", "Directa"):
                    secundarias.append(sub_strat)
                secundarias.extend(sub_sec)

                return pasos, "Multiplicación por Constante", "Coeficiente extraído.", secundarias

            # Producto real
            if len(variables) >= 2:
                u = variables[0]
                v = sympy.Mul(*variables[1:])

                du = sympy.diff(u, var)
                dv = sympy.diff(v, var)

                _, strat_u, _, sec_u = self._analizar_estructura_derivada(u, var, profundidad + 1)
                _, strat_v, _, sec_v = self._analizar_estructura_derivada(v, var, profundidad + 1)
                secundarias.extend([s for s in (strat_u, strat_v) if s not in ("Constante", "Directa")])
                secundarias.extend(sec_u + sec_v)

                pasos.append(PasoCalculo("Regla del Producto", "Identificamos u, v.", f"u={u}\nv={v}"))
                pasos.append(PasoCalculo("Derivadas", f"u' ({strat_u}) y v' ({strat_v}).", f"u'={du}\nv'={dv}"))
                pasos.append(PasoCalculo("Fórmula", "u'v + uv'", f"({du})*({v}) + ({u})*({dv})"))
                return pasos, "Regla del Producto", "Producto de funciones.", secundarias

        # E) Potencias
        if expr.is_Pow:
            base, exp = expr.as_base_exp()

            # Caso 1: a^u(x)
            if (not base.has(var)) and exp.has(var):
                _, strat_e, _, sec_e = self._analizar_estructura_derivada(exp, var, profundidad + 1)
                secundarias.extend(sec_e)
                if strat_e != "Directa":
                    secundarias.append(strat_e)

                a = base
                u = exp
                du = sympy.diff(u, var)

                pasos.append(PasoCalculo("Exponencial General", "Base constante a, exponente u(x).", f"y = {a}^{u}"))
                pasos.append(PasoCalculo("Regla", "d(a^u) = a^u ln(a) u'", f"{a}^{u} * ln({a}) * ({du})"))
                return pasos, "Exponencial", "Función exponencial.", secundarias

            # Caso 2: u(x)^v(x) — CIERRE COMPLETO (V4.3)
            if base.has(var) and exp.has(var):
                u = base
                v = exp
                du = sympy.diff(u, var)
                dv = sympy.diff(v, var)

                # Fórmula final: y' = u^v * (v' ln(u) + v * u'/u)
                formula = sympy.simplify((u**v) * (dv * sympy.log(u) + v * du / u))

                pasos.append(PasoCalculo("Potencia General", "Base y exponente dependen de x.", f"y = ({u})^({v})"))
                pasos.append(PasoCalculo("Logaritmación", "Aplicamos ln a ambos lados.", "ln(y) = v * ln(u)"))
                pasos.append(PasoCalculo("Derivada Implícita", "Derivamos ambos lados.", "y'/y = (v*ln(u))'"))
                pasos.append(PasoCalculo("Producto + Cadena", "Expandimos (v*ln(u))'.", "v'*ln(u) + v*(u'/u)"))
                pasos.append(PasoCalculo("Cierre", "Multiplicamos por y.", f"y' = y*(v'*ln(u) + v*u'/u) = {formula}"))

                secundarias.extend(["Regla del Producto", "Regla de la Cadena"])
                return pasos, "Potencia General (Logarítmica)", "Función elevado a función.", secundarias

            # Caso 3: u(x)^n
            if base.has(var) and (not exp.has(var)):
                n = exp
                u = base
                du = sympy.diff(u, var)

                if u == var:
                    return (
                        [PasoCalculo("Regla de la Potencia", "Polinomio simple.", f"{n}*x^({n}-1)")],
                        "Potencia",
                        "Polinomio.",
                        []
                    )

                _, strat_u, _, sec_u = self._analizar_estructura_derivada(u, var, profundidad + 1)
                secundarias.extend(sec_u)
                if strat_u != "Directa":
                    secundarias.append(strat_u)

                pasos.append(PasoCalculo("Cadena (Potencia)", "u(x)^n con n constante.", f"u={u}, n={n}"))
                pasos.append(PasoCalculo("Regla", "n*u^(n-1)*u'", f"{n}*({u})^({n}-1)*({du})"))
                return pasos, "Regla de la Cadena", "Potencia de función.", secundarias

        # F) Cadena para funciones generales f(g(x))
        if expr.is_Function:
            arg = expr.args[0] if expr.args else None
            if arg is not None and arg.has(var) and arg != var:
                u_dummy = Dummy("u")
                func_externa = expr.func(u_dummy)
                derivada_externa = sympy.diff(func_externa, u_dummy)
                derivada_interna = sympy.diff(arg, var)
                derivada_externa_visible = derivada_externa.subs(u_dummy, arg)

                msg_externa = str(derivada_externa_visible)
                if derivada_externa.has(sympy.Derivative):
                    msg_externa += " (Forma Simbólica)"

                _, strat_in, _, sec_in = self._analizar_estructura_derivada(arg, var, profundidad + 1)
                secundarias.extend(sec_in)
                if strat_in != "Directa":
                    secundarias.append(strat_in)

                pasos.append(PasoCalculo("Regla de la Cadena", "Composición f(g(x)).", f"Externa: {expr.func.__name__}, Interna u={arg}"))
                pasos.append(PasoCalculo("Derivar Externa", "Derivada de f respecto a u.", msg_externa))
                pasos.append(PasoCalculo("Derivar Interna", "Multiplicamos por u'.", f"* ({derivada_interna})"))
                return pasos, "Regla de la Cadena", "Composición.", secundarias

        # Fallback
        return (
            [PasoCalculo("Derivada Directa", "Regla estándar.", str(sympy.diff(expr, var)))],
            "Directa",
            "Elemental.",
            []
        )

    # ---------------------------------------------------------
    # 3) MOTOR DE INTEGRALES (RIGOR + HONESTIDAD DIDÁCTICA)
    # ---------------------------------------------------------

    def CalcularIntegral(self, expresion: str, variable: str = None) -> ResultadoCalculo:
        try:
            expr = self.parser.parsear(expresion)
            var, avisos = self._resolver_variable(expr, variable, "INTEGRAL")

            pasos_rule = None
            try:
                pasos_rule = integral_steps(expr, var)
            except Exception as ex:
                # No lo ocultes: informa, pero sigue con integrate()
                avisos.append(f"NOTA: no se pudieron generar pasos manuales (manualintegrate): {type(ex).__name__}.")

            integral = sympy.integrate(expr, var)

            estrategia = "Directa / Algorítmica"
            pasos_dto: List[PasoCalculo] = []

            if pasos_rule:
                estrategia = self._obtener_nombre_regla(pasos_rule)
                pasos_dto = self._regla_a_pasos(pasos_rule, var)
            else:
                pasos_dto = [PasoCalculo("Cálculo Avanzado", "Sin pasos manuales simples.", "Algoritmo / heurísticas de SymPy")]

            if integral.has(sympy.Integral):
                avisos.append("ADVERTENCIA: SymPy no encontró solución cerrada (resultado queda como Integral(...)).")

            # Detección segura de funciones especiales
            special_names = ["erf", "Ei", "Si", "Ci", "li", "fresnels", "fresnelc"]
            funciones_especiales = [getattr(sympy, name) for name in special_names if getattr(sympy, name, None)]
            if funciones_especiales and integral.has(*funciones_especiales):
                avisos.append("NOTA: el resultado contiene funciones especiales no elementales.")

            return ResultadoCalculo(
                es_exitoso=True,
                tipo="INTEGRAL",
                expresion_input=expresion,
                expr_sympy=expr,
                variable=var,
                resultado=integral,
                requiere_constante=True,
                estrategia_principal=estrategia,
                pasos=pasos_dto,
                advertencias=avisos
            )

        except Exception as e:
            return ResultadoCalculo(False, "INTEGRAL", expresion, None, None, None, mensaje_error=str(e))

    def _regla_a_pasos(self, rule: Any, var: Symbol, nivel: int = 0) -> List[PasoCalculo]:
        """
        Convierte el árbol de manualintegrate en pasos.
        Importante: en URule no fingimos el cambio de variable recalculando con Symbol('u'),
        porque eso puede ser pedagógicamente engañoso. Mostramos u y du, y describimos el subpaso.
        """
        pasos: List[PasoCalculo] = []

        if isinstance(rule, ConstantTimesRule):
            pasos.append(PasoCalculo("Extraer Constante", f"Sacamos {rule.constant} fuera de la integral.", "k∫f = ∫kf"))
            pasos.extend(self._regla_a_pasos(rule.substep, var, nivel + 1))
            return pasos

        if isinstance(rule, AddRule):
            pasos.append(PasoCalculo("Linealidad", "Separamos la integral en suma de integrales.", "∫(u+v)=∫u+∫v"))
            for sub in rule.substeps:
                pasos.extend(self._regla_a_pasos(sub, var, nivel + 1))
            return pasos

        if isinstance(rule, URule):
            u = rule.u_func
            du = sympy.diff(u, var)
            pasos.append(PasoCalculo("Sustitución (u)", f"Elegimos u = {u}", f"du = d({u}) = {du}"))
            # No cambiamos var a 'u' artificialmente: describimos el subpaso
            pasos.append(PasoCalculo("Integrar en función de u", "Reescribimos la integral en u y resolvemos.", f"Subpaso: {self._obtener_nombre_regla(rule.substep)}"))
            pasos.extend(self._regla_a_pasos(rule.substep, var, nivel + 1))
            pasos.append(PasoCalculo("Revertir Sustitución", "Volvemos a la variable original.", f"u → {u}"))
            return pasos

        if isinstance(rule, PartsRule):
            pasos.append(PasoCalculo("Integración por Partes", f"Elegimos u={rule.u} y dv={rule.dv}", "∫u dv = uv - ∫v du"))
            pasos.extend(self._regla_a_pasos(rule.second_step, var, nivel + 1))
            return pasos

        if isinstance(rule, (PowerRule, TrigRule, ExpRule, ReciprocalRule, ConstantRule)):
            pasos.append(PasoCalculo("Integral Inmediata", f"Aplicamos regla: {self._obtener_nombre_regla(rule)}.", "Tabla de integrales"))
            return pasos

        if isinstance(rule, DontKnowRule):
            pasos.append(PasoCalculo("Método Desconocido", "No hay regla manual clara para este caso.", "Se requiere técnica avanzada / CAS"))
            return pasos

        pasos.append(PasoCalculo("Paso Intermedio", f"Regla detectada: {type(rule).__name__}", ""))
        return pasos

    def _obtener_nombre_regla(self, rule: Any) -> str:
        return type(rule).__name__.replace("Rule", "")

    # ---------------------------------------------------------
    # 4) DERIVADAS SUCESIVAS (CONTROL DE EXPLOSIÓN)
    # ---------------------------------------------------------

    def DerivadaEnecima(self, expresion: str, variable: str, orden: int) -> ResultadoCalculo:
        try:
            n = int(orden)
            if n < 1:
                raise ValueError("El orden de derivación debe ser 1 o mayor.")

            expr = self.parser.parsear(expresion)
            var, avisos = self._resolver_variable(expr, variable, "DERIVADA")

            pasos: List[PasoCalculo] = []
            actual = expr
            pasos.append(PasoCalculo("Inicio", "Función original.", str(actual)))

            # Política: simplificar cada k pasos, no siempre (evita explosión de costo)
            simplificar_cada = 2 if n <= 6 else 3

            for i in range(1, n + 1):
                actual = sympy.diff(actual, var)

                if i % simplificar_cada == 0 or i == n:
                    actual = sympy.simplify(actual)

                pasos.append(PasoCalculo(f"Derivada {i}", "Resultado iterativo.", str(actual)))

            if actual.has(sympy.Derivative):
                avisos.append("NOTA: la derivada enésima contiene Derivative(...): quedó en forma simbólica.")

            return ResultadoCalculo(
                es_exitoso=True,
                tipo="DERIVADA_ENECIMA",
                expresion_input=expresion,
                expr_sympy=expr,
                variable=var,
                resultado=actual,
                estrategia_principal="Iteración",
                pasos=pasos,
                advertencias=avisos
            )

        except Exception as e:
            return ResultadoCalculo(False, "DERIVADA_ENECIMA", expresion, None, None, None, mensaje_error=str(e))

    # ---------------------------------------------------------
    # 5) RENDERIZADO ACCESIBLE (RESULTADO PRIMERO)
    # ---------------------------------------------------------

    def RenderizarTexto(self, res: ResultadoCalculo) -> str:
        if not res.es_exitoso:
            return f"Error Matemático:\n{res.mensaje_error}"

        txt: List[str] = []

        # Resultado primero (más NVDA-friendly)
        res_str = str(res.resultado)
        if res.requiere_constante:
            res_str += " + C"
        txt.append(f"RESULTADO: {res_str}")
        txt.append("=" * 30)

        txt.append(f"OPERACIÓN: {res.tipo}")
        txt.append(f"Expresión: {res.expresion_input}")
        if res.variable:
            txt.append(f"Variable: {res.variable}")

        if res.diagnostico or res.estrategia_principal:
            txt.append("\nANÁLISIS:")
            if res.estrategia_principal:
                txt.append(f"Estrategia Principal: {res.estrategia_principal}")
            if res.estrategias_secundarias:
                txt.append(f"Estrategias Secundarias: {', '.join(res.estrategias_secundarias)}")
            if res.diagnostico:
                txt.append(f"Diagnóstico: {res.diagnostico}")

        if res.pasos:
            txt.append("\nPASO A PASO:")
            for i, p in enumerate(res.pasos, 1):
                linea = f"{i}. {p.titulo}. {p.descripcion}"
                if p.expresion_matematica:
                    linea += f"\n   [Fórmula]: {p.expresion_matematica}"
                txt.append(linea)

        if res.advertencias:
            txt.append("\n[!] AVISOS:")
            for adv in res.advertencias:
                txt.append(f" - {adv}")

        return "\n".join(txt)

    # Facades (compatibilidad con tu estilo)
    def derivar(self, e: str) -> str:
        return self.RenderizarTexto(self.CalcularDerivada(e))

    def integrar(self, e: str) -> str:
        return self.RenderizarTexto(self.CalcularIntegral(e))

    def derivada_enecima(self, e: str, v: str, o: int) -> str:
        return self.RenderizarTexto(self.DerivadaEnecima(e, v, o))
