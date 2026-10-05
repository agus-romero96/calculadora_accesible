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

from i18n import N_, tr

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
    tipo: str  # "DERIVADA", "INTEGRAL", "DERIVADA DE ORDEN N"
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
            return self.parser.simbolo(var_str), advertencias

        # 2. Inferencia
        syms = sorted(list(expr.free_symbols), key=lambda s: s.name)

        if len(syms) == 1:
            return syms[0], advertencias

        # 3. Caso constante
        if len(syms) == 0:
            if operacion == "INTEGRAL":
                raise ValueError(
                    tr("Ambigüedad en Integral: está intentando integrar una constante sin especificar la variable. Indíquela.")
                )
            advertencias.append(tr("La expresión es constante. Se asume derivación respecto a 'x'."))
            return self.parser.simbolo("x"), advertencias

        # 4. Caso multivariable: política (preferir x si existe)
        nombres = [s.name for s in syms]
        if "x" in nombres:
            x_sym = next(s for s in syms if s.name == "x")
            advertencias.append(
                tr("Ambigüedad: se detectaron varias variables ({variables}). Se asume derivación respecto a 'x'.",
                   variables=", ".join(nombres))
            )
            return x_sym, advertencias

        raise ValueError(
            tr("Ambigüedad Matemática: la expresión tiene varias variables ({variables}). "
               "Especifique respecto a cuál desea operar.", variables=", ".join(nombres))
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
                avisos.append(tr("NOTA: el resultado contiene Derivative(...): SymPy lo dejó en forma simbólica (no elemental o no simplificado)."))

            return ResultadoCalculo(
                es_exitoso=True,
                tipo=N_("DERIVADA"),
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
                [PasoCalculo(tr("Derivada de Constante"), tr("La expresión no varía respecto a la variable."), tr("Resultado = 0"))],
                N_("Constante"),
                N_("Función constante."),
                []
            )

        # B) Linealidad (Suma/Resta)
        if expr.is_Add:
            terminos = expr.args
            pasos.append(PasoCalculo(tr("Regla de Linealidad"), tr("Suma de derivadas ({n} términos).", n=len(terminos)), "(u+v)'=u'+v'"))

            for i, t in enumerate(terminos, 1):
                _, strat_t, _, sec_t = self._analizar_estructura_derivada(t, var, profundidad + 1)
                d_t = sympy.diff(t, var)
                if strat_t not in ("Constante", "Directa"):
                    secundarias.append(strat_t)
                secundarias.extend(sec_t)

                pasos.append(PasoCalculo(tr("Derivada Término {i}", i=i), tr("Estrategia: {estrategia}", estrategia=tr(strat_t)), f"d({t}) = {d_t}"))

            return pasos, N_("Linealidad"), N_("Suma algebraica."), secundarias

        # C) Cociente (y detección de potencia negativa)
        num, den = expr.as_numer_denom()
        es_potencia_negativa = (expr.is_Pow and getattr(expr, "exp", None) is not None and expr.exp.is_negative)

        if den != 1 and den.has(var):
            if es_potencia_negativa:
                secundarias.append(N_("Regla del Cociente (alternativa)"))
                base, exp = expr.as_base_exp()
                u = base
                n = exp
                du = sympy.diff(u, var)
                pasos.append(PasoCalculo(tr("Regla de Potencia Negativa"), tr("Expresión recíproca/inversa."), f"u={u}, n={n}"))
                pasos.append(PasoCalculo(tr("Regla Generalizada"), tr("n*u^(n-1)*u'"), f"{n}*({u})^({n}-1)*({du})"))
                return pasos, N_("Potencia Negativa"), N_("Potencia con exponente negativo."), secundarias

            u = num
            v = den
            du = sympy.diff(u, var)
            dv = sympy.diff(v, var)

            _, strat_u, _, sec_u = self._analizar_estructura_derivada(u, var, profundidad + 1)
            _, strat_v, _, sec_v = self._analizar_estructura_derivada(v, var, profundidad + 1)
            secundarias.extend([s for s in (strat_u, strat_v) if s not in ("Constante", "Directa")])
            secundarias.extend(sec_u + sec_v)

            pasos.append(PasoCalculo(tr("Regla del Cociente"), tr("Identificamos u y v."), f"u={u}\nv={v}"))
            pasos.append(PasoCalculo(tr("Derivadas"), tr("u' ({estrategia_u}) y v' ({estrategia_v}).", estrategia_u=tr(strat_u), estrategia_v=tr(strat_v)), f"u'={du}\nv'={dv}"))
            pasos.append(PasoCalculo(tr("Aplicar Fórmula"), tr("(u'v - uv')/v²"), f"(({du})*({v}) - ({u})*({dv})) / ({v})^2"))
            return pasos, N_("Regla del Cociente"), N_("Función racional."), secundarias

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
                        [PasoCalculo(tr("Derivada de Constante"), tr("Expresión simbólica constante."), "0")],
                        N_("Constante"),
                        N_("Constante simbólica."),
                        []
                    )

                resto = sympy.Mul(*variables)
                sub_pasos, sub_strat, _, sub_sec = self._analizar_estructura_derivada(resto, var, profundidad + 1)

                pasos.append(PasoCalculo(tr("Constante por Función"), tr("Extraemos coeficiente {coeficiente}.", coeficiente=coeff), f"{coeff} * d({resto})"))
                pasos.extend(sub_pasos)

                if sub_strat not in ("Constante", "Directa"):
                    secundarias.append(sub_strat)
                secundarias.extend(sub_sec)

                return pasos, N_("Multiplicación por Constante"), N_("Coeficiente extraído."), secundarias

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

                pasos.append(PasoCalculo(tr("Regla del Producto"), tr("Identificamos u, v."), f"u={u}\nv={v}"))
                pasos.append(PasoCalculo(tr("Derivadas"), tr("u' ({estrategia_u}) y v' ({estrategia_v}).", estrategia_u=tr(strat_u), estrategia_v=tr(strat_v)), f"u'={du}\nv'={dv}"))
                pasos.append(PasoCalculo(tr("Fórmula"), tr("u'v + uv'"), f"({du})*({v}) + ({u})*({dv})"))
                return pasos, N_("Regla del Producto"), N_("Producto de funciones."), secundarias

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

                pasos.append(PasoCalculo(tr("Exponencial General"), tr("Base constante a, exponente u(x)."), f"y = {a}^{u}"))
                pasos.append(PasoCalculo(tr("Regla"), tr("d(a^u) = a^u ln(a) u'"), f"{a}^{u} * ln({a}) * ({du})"))
                return pasos, N_("Exponencial"), N_("Función exponencial."), secundarias

            # Caso 2: u(x)^v(x) — CIERRE COMPLETO (V4.3)
            if base.has(var) and exp.has(var):
                u = base
                v = exp
                du = sympy.diff(u, var)
                dv = sympy.diff(v, var)

                # Fórmula final: y' = u^v * (v' ln(u) + v * u'/u)
                formula = sympy.simplify((u**v) * (dv * sympy.log(u) + v * du / u))

                pasos.append(PasoCalculo(tr("Potencia General"), tr("Base y exponente dependen de x."), f"y = ({u})^({v})"))
                pasos.append(PasoCalculo(tr("Logaritmación"), tr("Aplicamos ln a ambos lados."), "ln(y) = v * ln(u)"))
                pasos.append(PasoCalculo(tr("Derivada Implícita"), tr("Derivamos ambos lados."), "y'/y = (v*ln(u))'"))
                pasos.append(PasoCalculo(tr("Producto + Cadena"), tr("Expandimos (v*ln(u))'."), "v'*ln(u) + v*(u'/u)"))
                pasos.append(PasoCalculo(tr("Cierre"), tr("Multiplicamos por y."), f"y' = y*(v'*ln(u) + v*u'/u) = {formula}"))

                secundarias.extend([N_("Regla del Producto"), N_("Regla de la Cadena")])
                return pasos, N_("Potencia General (Logarítmica)"), N_("Función elevado a función."), secundarias

            # Caso 3: u(x)^n
            if base.has(var) and (not exp.has(var)):
                n = exp
                u = base
                du = sympy.diff(u, var)

                if u == var:
                    return (
                        [PasoCalculo(tr("Regla de la Potencia"), tr("Polinomio simple."), f"{n}*{var}^({n}-1)")],
                        N_("Potencia"),
                        N_("Polinomio."),
                        []
                    )

                _, strat_u, _, sec_u = self._analizar_estructura_derivada(u, var, profundidad + 1)
                secundarias.extend(sec_u)
                if strat_u != "Directa":
                    secundarias.append(strat_u)

                pasos.append(PasoCalculo(tr("Cadena (Potencia)"), tr("u(x)^n con n constante."), f"u={u}, n={n}"))
                pasos.append(PasoCalculo(tr("Regla"), tr("n*u^(n-1)*u'"), f"{n}*({u})^({n}-1)*({du})"))
                return pasos, N_("Regla de la Cadena"), N_("Potencia de función."), secundarias

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
                    msg_externa += " " + tr("(Forma Simbólica)")

                _, strat_in, _, sec_in = self._analizar_estructura_derivada(arg, var, profundidad + 1)
                secundarias.extend(sec_in)
                if strat_in != "Directa":
                    secundarias.append(strat_in)

                pasos.append(PasoCalculo(tr("Regla de la Cadena"), tr("Composición f(g(x))."), tr("Externa: {externa}, Interna u={interna}", externa=expr.func.__name__, interna=arg)))
                pasos.append(PasoCalculo(tr("Derivar Externa"), tr("Derivada de f respecto a u."), msg_externa))
                pasos.append(PasoCalculo(tr("Derivar Interna"), tr("Multiplicamos por u'."), f"* ({derivada_interna})"))
                return pasos, N_("Regla de la Cadena"), N_("Composición."), secundarias

        # Fallback
        return (
            [PasoCalculo(tr("Derivada Directa"), tr("Regla estándar."), str(sympy.diff(expr, var)))],
            N_("Directa"),
            N_("Elemental."),
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
                avisos.append(tr("NOTA: no se pudieron generar pasos manuales (manualintegrate): {error}.", error=type(ex).__name__))

            integral = sympy.integrate(expr, var)

            estrategia = N_("Directa / Algorítmica")
            pasos_dto: List[PasoCalculo] = []

            if pasos_rule:
                estrategia = self._obtener_nombre_regla(pasos_rule)
                pasos_dto = self._regla_a_pasos(pasos_rule, var)
            else:
                pasos_dto = [PasoCalculo(tr("Cálculo Avanzado"), tr("Sin pasos manuales simples."), tr("Algoritmo / heurísticas de SymPy"))]

            if integral.has(sympy.Integral):
                avisos.append(tr("ADVERTENCIA: SymPy no encontró solución cerrada (resultado queda como Integral(...))."))

            # Detección segura de funciones especiales
            special_names = ["erf", "Ei", "Si", "Ci", "li", "fresnels", "fresnelc"]
            funciones_especiales = [getattr(sympy, name) for name in special_names if getattr(sympy, name, None)]
            if funciones_especiales and integral.has(*funciones_especiales):
                avisos.append(tr("NOTA: el resultado contiene funciones especiales no elementales."))

            return ResultadoCalculo(
                es_exitoso=True,
                tipo=N_("INTEGRAL"),
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
            pasos.append(PasoCalculo(tr("Extraer Constante"), tr("Sacamos {constante} fuera de la integral.", constante=rule.constant), "k∫f = ∫kf"))
            pasos.extend(self._regla_a_pasos(rule.substep, var, nivel + 1))
            return pasos

        if isinstance(rule, AddRule):
            pasos.append(PasoCalculo(tr("Linealidad"), tr("Separamos la integral en suma de integrales."), "∫(u+v)=∫u+∫v"))
            for sub in rule.substeps:
                pasos.extend(self._regla_a_pasos(sub, var, nivel + 1))
            return pasos

        if isinstance(rule, URule):
            u = rule.u_func
            du = sympy.diff(u, var)
            pasos.append(PasoCalculo(tr("Sustitución (u)"), tr("Elegimos u = {u}", u=u), f"du = d({u}) = {du}"))
            # No cambiamos var a 'u' artificialmente: describimos el subpaso
            pasos.append(PasoCalculo(tr("Integrar en función de u"), tr("Reescribimos la integral en u y resolvemos."), tr("Subpaso: {regla}", regla=tr(self._obtener_nombre_regla(rule.substep)))))
            pasos.extend(self._regla_a_pasos(rule.substep, var, nivel + 1))
            pasos.append(PasoCalculo(tr("Revertir Sustitución"), tr("Volvemos a la variable original."), f"u → {u}"))
            return pasos

        if isinstance(rule, PartsRule):
            pasos.append(PasoCalculo(tr("Integración por Partes"), tr("Elegimos u={u} y dv={dv}", u=rule.u, dv=rule.dv), "∫u dv = uv - ∫v du"))
            pasos.extend(self._regla_a_pasos(rule.second_step, var, nivel + 1))
            return pasos

        if isinstance(rule, (PowerRule, TrigRule, ExpRule, ReciprocalRule, ConstantRule)):
            pasos.append(PasoCalculo(tr("Integral Inmediata"), tr("Aplicamos regla: {regla}.", regla=tr(self._obtener_nombre_regla(rule))), tr("Tabla de integrales")))
            return pasos

        if isinstance(rule, DontKnowRule):
            pasos.append(PasoCalculo(tr("Método Desconocido"), tr("No hay regla manual clara para este caso."), tr("Se requiere técnica avanzada / CAS")))
            return pasos

        pasos.append(PasoCalculo(tr("Paso Intermedio"), tr("Regla detectada: {regla}", regla=type(rule).__name__), ""))
        return pasos

    # Nombres de las reglas de manualintegrate (clase sin "Rule") en lenguaje de clase.
    NOMBRES_REGLAS = {
        "ConstantTimes": N_("Constante por función"),
        "Add": N_("Linealidad"),
        "U": N_("Sustitución"),
        "Parts": N_("Integración por partes"),
        "Power": N_("Regla de la potencia"),
        "Trig": N_("Integral trigonométrica inmediata"),
        "Exp": N_("Integral exponencial inmediata"),
        "Reciprocal": N_("Integral de 1/x"),
        "Constant": N_("Integral de una constante"),
        "DontKnow": N_("Sin regla conocida"),
    }

    def _obtener_nombre_regla(self, rule: Any) -> str:
        nombre = type(rule).__name__.replace("Rule", "")
        return self.NOMBRES_REGLAS.get(nombre, nombre)

    # ---------------------------------------------------------
    # 4) DERIVADAS SUCESIVAS (CONTROL DE EXPLOSIÓN)
    # ---------------------------------------------------------

    def DerivadaEnecima(self, expresion: str, variable: str, orden: int) -> ResultadoCalculo:
        try:
            n = int(orden)
            if n < 1:
                raise ValueError(tr("El orden de derivación debe ser 1 o mayor."))

            expr = self.parser.parsear(expresion)
            var, avisos = self._resolver_variable(expr, variable, "DERIVADA")

            pasos: List[PasoCalculo] = []
            actual = expr
            pasos.append(PasoCalculo(tr("Inicio"), tr("Función original."), str(actual)))

            # Política: simplificar cada k pasos, no siempre (evita explosión de costo)
            simplificar_cada = 2 if n <= 6 else 3

            for i in range(1, n + 1):
                actual = sympy.diff(actual, var)

                if i % simplificar_cada == 0 or i == n:
                    actual = sympy.simplify(actual)

                pasos.append(PasoCalculo(tr("Derivada {i}", i=i), tr("Resultado iterativo."), str(actual)))

            if actual.has(sympy.Derivative):
                avisos.append(tr("NOTA: la derivada enésima contiene Derivative(...): quedó en forma simbólica."))

            return ResultadoCalculo(
                es_exitoso=True,
                tipo=N_("DERIVADA DE ORDEN N"),
                expresion_input=expresion,
                expr_sympy=expr,
                variable=var,
                resultado=actual,
                estrategia_principal=N_("Iteración"),
                pasos=pasos,
                advertencias=avisos
            )

        except Exception as e:
            return ResultadoCalculo(False, "DERIVADA DE ORDEN N", expresion, None, None, None, mensaje_error=str(e))

    # ---------------------------------------------------------
    # 5) RENDERIZADO ACCESIBLE (RESULTADO PRIMERO)
    # ---------------------------------------------------------

    def RenderizarTexto(self, res: ResultadoCalculo) -> str:
        if not res.es_exitoso:
            return tr("Error Matemático:") + f"\n{res.mensaje_error}"

        txt: List[str] = []

        # Resultado primero (más NVDA-friendly)
        res_str = str(res.resultado)
        if res.requiere_constante:
            res_str += " + C"
        txt.append(tr("RESULTADO: {valor}", valor=res_str))
        txt.append("=" * 30)

        txt.append(tr("OPERACIÓN: {operacion}", operacion=tr(res.tipo)))
        txt.append(tr("Expresión: {expresion}", expresion=res.expresion_input))
        if res.variable:
            txt.append(tr("Variable: {variable}", variable=res.variable))

        if res.diagnostico or res.estrategia_principal:
            txt.append("\n" + tr("ANÁLISIS:"))
            if res.estrategia_principal:
                txt.append(tr("Estrategia Principal: {estrategia}", estrategia=tr(res.estrategia_principal)))
            if res.estrategias_secundarias:
                txt.append(tr("Estrategias Secundarias: {estrategias}", estrategias=", ".join(tr(e) for e in res.estrategias_secundarias)))
            if res.diagnostico:
                txt.append(tr("Diagnóstico: {diagnostico}", diagnostico=tr(res.diagnostico)))

        if res.pasos:
            txt.append("\n" + tr("PASO A PASO:"))
            for i, p in enumerate(res.pasos, 1):
                linea = f"{i}. {tr(p.titulo)}. {tr(p.descripcion)}"
                if p.expresion_matematica:
                    linea += "\n   " + tr("[Fórmula]: {formula}", formula=p.expresion_matematica)
                txt.append(linea)

        if res.advertencias:
            txt.append("\n" + tr("[!] AVISOS:"))
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
