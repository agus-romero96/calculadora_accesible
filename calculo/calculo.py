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
from sympy import Symbol
from sympy.calculus.util import continuous_domain

from calculo.derivadas import ExplicadorDerivada, texto
from calculo.pasos import PasoCalculo, texto_paso
from i18n import N_, tr

# Reglas de integración manual (manualintegrate)
from sympy.integrals.manualintegrate import (
    integral_steps,
    ConstantTimesRule, AddRule, URule, PartsRule, TrigRule, ExpRule,
    ReciprocalRule, PowerRule, NestedPowRule, ConstantRule, DontKnowRule, AlternativeRule
)


# =============================================================
# CAPA DE DATOS (DTOs Inmutables)
# =============================================================

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
    # Integral definida: (inferior, superior) tal como se escribieron, y el resultado en
    # texto ("+Infinito (la integral diverge)", "pi/4 (≈ 0.785398)")
    limites: Optional[Tuple[Any, Any]] = None
    texto_resultado: str = ""


def humanizar_integral(valor: Any) -> str:
    """Valor de una integral definida para el lector de pantalla: si diverge, lo dice."""
    if valor == sympy.oo:
        return tr("+Infinito (la integral diverge)")
    if valor == -sympy.oo:
        return tr("-Infinito (la integral diverge)")
    if valor is sympy.nan or valor is sympy.zoo or isinstance(valor, sympy.AccumBounds):
        return tr("No existe (la integral diverge)")
    aproximado = _aproximacion(valor)
    return f"{valor} (≈ {aproximado})" if aproximado else str(valor)


def _aproximacion(valor: Any) -> Optional[str]:
    """Decimal de un número exacto que no es racional (pi/4 -> 0.785398); None si no aporta."""
    try:
        if not valor.is_number or valor.is_Rational or valor.is_Float:
            return None
        real, imaginaria = sympy.N(valor, 15).as_real_imag()
        if abs(imaginaria) > 1e-12:
            return None
        return str(sympy.Float(real, 6))
    except Exception:
        return None


# Derivada de orden N: pasos como máximo por cada derivada y en total para seguir explicando
MAX_PASOS_DERIVADA = 30
MAX_PASOS_ENESIMA = 120


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
            resultado = sympy.simplify(derivada_final)

            # Explicación: cada regla, con sus partes y sus cuentas
            explicador = ExplicadorDerivada(var)
            pasos = self._explicar_derivada(explicador, expr, resultado, avisos)

            # Aviso si SymPy no pudo “cerrar” (derivada formal)
            if derivada_final.has(sympy.Derivative):
                avisos.append(tr("NOTA: el resultado contiene Derivative(...): SymPy lo dejó en forma simbólica (no elemental o no simplificado)."))

            return ResultadoCalculo(
                es_exitoso=True,
                tipo=N_("DERIVADA"),
                expresion_input=expresion,
                expr_sympy=expr,
                variable=var,
                resultado=resultado,
                estrategia_principal=explicador.principal.estrategia,
                estrategias_secundarias=explicador.secundarias,
                diagnostico=explicador.principal.diagnostico,
                pasos=pasos,
                advertencias=avisos
            )

        except Exception as e:
            return ResultadoCalculo(False, "DERIVADA", expresion, None, None, None, mensaje_error=str(e))

    @staticmethod
    def _explicar_derivada(explicador: ExplicadorDerivada, expr: Any, resultado: Any,
                           avisos: List[str]) -> List[PasoCalculo]:
        """Pasos de la derivada de expr, que debe valer resultado (el de SymPy, simplificado)."""
        try:
            # El parser no evalúa (evaluate=False): doit() da la forma de SymPy, sin "-1*7"
            explicada = explicador.derivar(expr.doit())
            coincide = explicada == resultado or sympy.simplify(explicada - resultado) == 0
        except Exception:  # una forma que las reglas no prevén: mejor el resultado sin pasos que un error
            explicada, coincide = None, False
        if not coincide:
            # Nunca una explicación que llegue a otro resultado
            avisos.append(tr("No se pudo explicar esta derivada paso a paso; el resultado es el que calcula SymPy."))
            return []

        pasos = list(explicador.pasos)
        if texto(explicada) != texto(resultado):
            pasos.append(PasoCalculo(
                tr("Simplificación"),
                regla=tr("se reescribe la expresión de forma más compacta (factor común, términos semejantes, fracciones, identidades trigonométricas) sin cambiar su valor."),
                calculo=(f"{texto(explicada)} = {texto(resultado)}",),
                queda=texto(resultado)))
        return pasos

    # ---------------------------------------------------------
    # 3) MOTOR DE INTEGRALES (RIGOR + HONESTIDAD DIDÁCTICA)
    # ---------------------------------------------------------

    def _primitiva(self, expr: Any, var: Symbol) -> Tuple[Any, str, List[PasoCalculo], List[str]]:
        """Primitiva con SymPy y sus pasos (manualintegrate): (primitiva, estrategia, pasos, avisos)."""
        avisos: List[str] = []
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

        return integral, estrategia, pasos_dto, avisos

    def CalcularIntegral(self, expresion: str, variable: str = None) -> ResultadoCalculo:
        try:
            expr = self.parser.parsear(expresion)
            var, avisos = self._resolver_variable(expr, variable, "INTEGRAL")

            integral, estrategia, pasos_dto, avisos_primitiva = self._primitiva(expr, var)
            avisos.extend(avisos_primitiva)

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

        if isinstance(rule, AlternativeRule):
            # Varios caminos posibles (p. ej. dos sustituciones): se explica el primero
            return self._regla_a_pasos(rule.alternatives[0], var, nivel)

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

        if isinstance(rule, (PowerRule, NestedPowRule, TrigRule, ExpRule, ReciprocalRule, ConstantRule)):
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
        "NestedPow": N_("Regla de la potencia"),
        "Trig": N_("Integral trigonométrica inmediata"),
        "Exp": N_("Integral exponencial inmediata"),
        "Reciprocal": N_("Integral de 1/x"),
        "Constant": N_("Integral de una constante"),
        "DontKnow": N_("Sin regla conocida"),
    }

    def _obtener_nombre_regla(self, rule: Any) -> str:
        if isinstance(rule, AlternativeRule):
            return self._obtener_nombre_regla(rule.alternatives[0])
        nombre = type(rule).__name__.replace("Rule", "")
        return self.NOMBRES_REGLAS.get(nombre, nombre)

    # ---------------------------------------------------------
    # 3b) INTEGRAL DEFINIDA (REGLA DE BARROW E INTEGRALES IMPROPIAS)
    # ---------------------------------------------------------
    # El valor lo da SymPy (integrate con límites). La explicación es la de clase:
    #   - función continua en [a, b] acotado: regla de Barrow, F(b) − F(a);
    #   - extremo infinito o discontinuidad: integral impropia. Se divide el intervalo en
    #     tramos donde la función es continua y en cada extremo impropio se toma el límite
    #     de la primitiva. Si un tramo diverge, la integral diverge.
    # Aplicar Barrow sin mirar la continuidad da valores falsos (∫ de 1/x² entre −1 y 1
    # "daría" −2, pero diverge), así que los pasos solo se muestran si coinciden con SymPy.

    def CalcularIntegralDefinida(self, expresion: str, variable: Optional[str],
                                 inferior: str, superior: str) -> ResultadoCalculo:
        tipo = N_("INTEGRAL DEFINIDA")
        try:
            expr = self.parser.parsear(expresion)
            a = self._parsear_limite_integracion(inferior)
            b = self._parsear_limite_integracion(superior)
            var, avisos = self._resolver_variable(expr, variable, "INTEGRAL")
            if var in a.free_symbols | b.free_symbols:
                raise ValueError(tr("Los límites de integración no pueden contener la variable de integración ({variable}).",
                                    variable=var))

            primitiva, estrategia, pasos, avisos_primitiva = self._primitiva(expr, var)
            avisos.extend(avisos_primitiva)

            valor_sympy = sympy.integrate(expr, (var, a, b))
            barrow = None
            try:
                barrow = self._evaluar_barrow(expr, var, a, b, primitiva)
            except Exception:
                barrow = None  # sin explicación paso a paso, pero con el valor de SymPy

            if barrow is not None and self._coinciden(barrow[0], valor_sympy):
                valor_barrow, pasos_barrow, metodo = barrow
                pasos = pasos + pasos_barrow
                estrategia = metodo
                # Si SymPy no dio una forma cerrada, vale la de Barrow (también es de SymPy)
                valor = valor_barrow if valor_sympy.has(sympy.Integral) else valor_sympy
            else:
                if barrow is not None:
                    avisos.append(tr("NOTA: la evaluación con la primitiva no coincide con el cálculo directo; "
                                     "se muestra el valor calculado por SymPy."))
                valor = valor_sympy
                if valor.has(sympy.Integral):
                    aproximado = sympy.Integral(expr, (var, a, b)).evalf(15)
                    if aproximado.is_Float:
                        valor = aproximado
                        avisos.append(tr("NOTA: no hay una primitiva elemental; el valor es una aproximación numérica."))

            if isinstance(valor, sympy.AccumBounds):
                valor = sympy.nan  # oscila sin tender a nada (∫ de sin(x) hasta oo): no existe
            if valor.is_number and valor.has(sympy.I, sympy.exp_polar):
                # Forma exacta real pero escrita con complejos (∫ de exp(x³)): se da el decimal
                real, imaginaria = valor.evalf(15).as_real_imag()
                if abs(imaginaria) < 1e-12:
                    valor = sympy.Float(real, 10)
                    avisos.append(tr("NOTA: la forma exacta de SymPy usa números complejos; se muestra el valor aproximado."))

            if valor in (sympy.oo, -sympy.oo, sympy.nan, sympy.zoo):
                diagnostico = N_("La integral diverge.")
            elif barrow is not None and estrategia == N_("Integral impropia"):
                diagnostico = N_("La integral impropia converge.")
            else:
                diagnostico = ""

            return ResultadoCalculo(
                es_exitoso=True,
                tipo=tipo,
                expresion_input=expresion,
                expr_sympy=expr,
                variable=var,
                resultado=valor,
                estrategia_principal=estrategia,
                diagnostico=diagnostico,
                pasos=pasos,
                advertencias=avisos,
                limites=(a, b),
                texto_resultado=humanizar_integral(valor),
            )

        except Exception as e:
            return ResultadoCalculo(False, tipo, expresion, None, None, None, mensaje_error=str(e))

    def _parsear_limite_integracion(self, texto: str) -> Any:
        texto = (texto or "").strip().replace("∞", "oo")
        if not texto:
            raise ValueError(tr("Falta un límite de integración. Escriba un número, una expresión (pi/2) u oo / -oo."))
        punto = self.parser.parsear(texto).doit()
        if punto.has(sympy.nan, sympy.zoo) or (punto.is_number and punto.is_extended_real is False):
            raise ValueError(tr("El límite de integración debe ser un número real, oo o -oo: {limite}", limite=texto))
        return punto

    def _discontinuidades(self, expr: Any, var: Symbol, lo: Any, hi: Any) -> Optional[List[Any]]:
        """Puntos de [lo, hi] donde la función no es continua (ordenados), o None si no se sabe."""
        intervalo = sympy.Interval(lo, hi)
        try:
            dominio = continuous_domain(expr, var, intervalo)
        except Exception:
            return None
        faltan = sympy.Complement(intervalo, dominio)
        if faltan is sympy.S.EmptySet:
            return []
        if isinstance(faltan, sympy.FiniteSet) and all(p.is_number for p in faltan):
            return sorted(faltan, key=lambda p: float(p))
        return None

    def _evaluar_barrow(self, expr: Any, var: Symbol, a: Any, b: Any,
                        primitiva: Any) -> Optional[Tuple[Any, List[PasoCalculo], str]]:
        """
        (valor, pasos, método) evaluando la primitiva en los extremos (con límites en los
        impropios), o None si no se puede explicar así (sin primitiva cerrada, o no se
        sabe dónde es discontinua la función).
        """
        if primitiva.has(sympy.Integral, sympy.I, sympy.exp_polar):
            return None  # sin primitiva cerrada, o escrita con complejos: no ayuda a explicar
        if a == b:
            return sympy.S.Zero, [PasoCalculo(tr("Límites iguales"),
                                              tr("Si los dos límites son iguales, la integral vale 0."), "")], N_("Límites iguales")

        pasos: List[PasoCalculo] = []
        lo, hi, signo = a, b, 1
        if (a > b) == sympy.true:
            lo, hi, signo = b, a, -1
            paso_invertir = (PasoCalculo(tr("Invertir los límites"),
                                     tr("El límite inferior es mayor que el superior: se intercambian y el resultado cambia de signo."),
                                     tr("∫ de {a} a {b} = −∫ de {b} a {a}", a=a, b=b)),)
        else:
            paso_invertir = ()

        if lo.is_number and hi.is_number:
            puntos = self._discontinuidades(expr, var, lo, hi)
            if puntos is None:
                return None
        else:
            # Límites con parámetros (∫ de 0 a k): no se puede estudiar la continuidad
            puntos = []
            pasos.append(PasoCalculo(tr("Suposición"),
                                     tr("Los límites tienen parámetros: se supone que la función es continua entre ellos."), ""))

        impropios = set(puntos) | {sympy.oo, -sympy.oo}
        cortes = [lo] + [p for p in puntos if (lo < p) == sympy.true and (p < hi) == sympy.true] + [hi]
        if lo == -sympy.oo and hi == sympy.oo and len(cortes) == 2:
            cortes = [lo, sympy.S.Zero, hi]  # ∫ de −∞ a ∞ = ∫ de −∞ a 0 + ∫ de 0 a ∞
        tramos = list(zip(cortes, cortes[1:]))
        es_impropia = any(p in impropios for p in cortes)

        # ln|u| en lugar de ln(u): SymPy da log(x) como primitiva de 1/x, y en x < 0 los
        # pasos mostrarían logaritmos de negativos (iπ) aunque el resultado sea real
        candidatas = [primitiva]
        if primitiva.has(sympy.log):
            candidatas.append(primitiva.replace(sympy.log, lambda u: sympy.log(sympy.Abs(u))))
        for F in candidatas:
            evaluados = [self._evaluar_tramo(F, var, l, r, impropios) for l, r in tramos]
            if not any(v.has(sympy.I) for tramo in evaluados for v in tramo):
                break

        pasos.insert(0, PasoCalculo(tr("Primitiva"), tr("Una primitiva es F({variable}) = {primitiva}.", variable=var, primitiva=F), ""))
        pasos[1:1] = paso_invertir

        piezas = [vr - vl for vl, vr in evaluados]
        piezas = [p if p in (sympy.nan, sympy.zoo) else sympy.simplify(p) for p in piezas]
        diverge = [not self._es_finito(p) for p in piezas]

        if not es_impropia:
            vl, vr = evaluados[0]
            pasos.append(PasoCalculo(tr("Regla de Barrow"),
                                     tr("La función es continua en el intervalo: la integral es F({superior}) − F({inferior}).",
                                        superior=hi, inferior=lo),
                                     f"F({hi}) − F({lo}) = {self._texto_valor(vr)} − {self._restando(vl)} = {piezas[0]}"))
            metodo = N_("Regla de Barrow")
        else:
            motivos = []
            if lo.is_infinite or hi.is_infinite:
                motivos.append(tr("el intervalo llega a infinito"))
            discontinuos = [p for p in puntos if p in cortes]
            if discontinuos:
                motivos.append(tr("la función no es continua en {variable} = {puntos}",
                                  variable=var, puntos=", ".join(str(p) for p in discontinuos)))
            pasos.append(PasoCalculo(tr("Integral impropia"),
                                     tr("No se puede aplicar Barrow directamente: {motivos}. "
                                        "En cada extremo impropio se calcula el límite de la primitiva.",
                                        motivos="; ".join(motivos)), ""))
            if len(tramos) > 1:
                pasos.append(PasoCalculo(tr("Dividir el intervalo"),
                                         tr("Se separa en {n} integrales: {tramos}.", n=len(tramos),
                                            tramos=", ".join(tr("de {inferior} a {superior}", inferior=l, superior=r)
                                                             for l, r in tramos)), ""))
            for i, ((l, r), (vl, vr), pieza, div) in enumerate(zip(tramos, evaluados, piezas, diverge), 1):
                izq = self._extremo(var, l, "+") if l in impropios else f"F({l})"
                der = self._extremo(var, r, "-") if r in impropios else f"F({r})"
                estado = tr("diverge") if div else tr("converge")
                pasos.append(PasoCalculo(tr("Tramo de {inferior} a {superior}", inferior=l, superior=r),
                                         tr("Este tramo {estado}.", estado=estado),
                                         f"{der} − {izq} = {self._texto_valor(vr)} − {self._restando(vl)} = {self._texto_valor(pieza)}"))
            if any(diverge):
                pasos.append(PasoCalculo(tr("Conclusión"),
                                         tr("Al menos un tramo diverge, así que la integral diverge."), ""))
            elif len(tramos) > 1:
                pasos.append(PasoCalculo(tr("Conclusión"),
                                         tr("Todos los tramos convergen: la integral converge y vale la suma."),
                                         " + ".join(f"({p})" for p in piezas)))
            metodo = N_("Integral impropia")

        total = sympy.Add(*piezas)
        if any(diverge) and total not in (sympy.oo, -sympy.oo):
            total = sympy.nan  # +∞ − ∞ o un tramo que oscila: no existe
        elif not any(diverge):
            total = sympy.simplify(total)
        if signo == -1:
            pasos.append(PasoCalculo(tr("Cambiar el signo"), tr("Por la inversión de los límites."),
                                     f"−({self._texto_valor(total)}) = {self._texto_valor(-total)}"))
            total = -total
        return total, pasos, metodo

    def _evaluar_tramo(self, F: Any, var: Symbol, l: Any, r: Any, impropios: set) -> Tuple[Any, Any]:
        """(F en l, F en r): límite lateral hacia dentro del tramo en los extremos impropios."""
        def en(punto, lado):
            if punto in impropios:
                return sympy.limit(F, var, punto, lado)
            return sympy.simplify(F.subs(var, punto))
        return en(l, "+"), en(r, "-")

    @staticmethod
    def _es_finito(valor: Any) -> bool:
        if valor in (sympy.nan, sympy.zoo) or isinstance(valor, sympy.AccumBounds):
            return False
        return valor.is_finite is not False and not valor.has(sympy.oo, -sympy.oo, sympy.zoo, sympy.AccumBounds)

    @staticmethod
    def _extremo(var: Symbol, punto: Any, lado: str) -> str:
        """'lim x→0+ F(x)'; hacia ±oo no se indica el lado."""
        return f"lim {var}→{punto}{'' if punto.is_infinite else lado} F({var})"

    @staticmethod
    def _restando(valor: Any) -> str:
        """Valor tras un signo menos: entre paréntesis si es negativo o una suma (− (−1), − (a + b))."""
        texto = Calculo._texto_valor(valor)
        return f"({texto})" if texto.startswith("-") or getattr(valor, "is_Add", False) else texto

    @staticmethod
    def _texto_valor(valor: Any) -> str:
        if isinstance(valor, sympy.AccumBounds):
            return tr("no existe (oscila)")
        return str(valor)

    @staticmethod
    def _coinciden(nuestro: Any, de_sympy: Any) -> bool:
        """El valor de la explicación es el mismo que el de SymPy (o los dos divergen)."""
        if de_sympy.has(sympy.Integral):
            return True  # SymPy no lo cerró: no hay con qué comparar
        fin_nuestro, fin_sympy = Calculo._es_finito(nuestro), Calculo._es_finito(de_sympy)
        if not fin_nuestro or not fin_sympy:
            return not fin_nuestro and not fin_sympy
        diferencia = nuestro - de_sympy
        if diferencia.is_number:
            return abs(complex(sympy.N(diferencia, 30))) < 1e-12
        return sympy.simplify(diferencia) == 0

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

            explicar = True
            for i in range(1, n + 1):
                anterior = actual
                actual = sympy.diff(actual, var)

                if i % simplificar_cada == 0 or i == n:
                    actual = sympy.simplify(actual)

                if explicar:
                    explicador = ExplicadorDerivada(var)
                    sub_pasos = self._explicar_derivada(explicador, anterior, actual, avisos)
                    # Una explicación demasiado larga ya no ayuda: el resto, solo los resultados
                    explicar = bool(sub_pasos) and len(sub_pasos) <= MAX_PASOS_DERIVADA and len(pasos) <= MAX_PASOS_ENESIMA
                    if explicar:
                        pasos.append(PasoCalculo(tr("Derivada {i}", i=i),
                                                 tr("Derivamos el resultado anterior, {expresion}.", expresion=texto(anterior))))
                        pasos.extend(sub_pasos)
                        continue
                    if sub_pasos:
                        avisos.append(tr("Desde la derivada {i} se muestra solo el resultado de cada derivada: "
                                         "la explicación completa sería demasiado larga.", i=i))
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
        res_str = res.texto_resultado or str(res.resultado)
        if res.requiere_constante:
            res_str += " + C"
        txt.append(tr("RESULTADO: {valor}", valor=res_str))
        txt.append("=" * 30)

        txt.append(tr("OPERACIÓN: {operacion}", operacion=tr(res.tipo)))
        txt.append(tr("Expresión: {expresion}", expresion=res.expresion_input))
        if res.variable:
            txt.append(tr("Variable: {variable}", variable=res.variable))
        if res.limites:
            txt.append(tr("Intervalo: de {inferior} a {superior}", inferior=res.limites[0], superior=res.limites[1]))

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
                txt.append(texto_paso(i, p))

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
