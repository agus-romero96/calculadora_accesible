import sympy
from dataclasses import dataclass, field
from typing import List, Any, Optional, Tuple
from sympy import Integer, Float, Rational, Symbol


# =============================================================
# 1) DTO (Contrato de datos)
# =============================================================

@dataclass(frozen=True)
class ResultadoAritmetica:
    es_exitoso: bool
    operacion: str
    expresion_original: Any
    resultado: Optional[Any]  # SymPy si éxito, None si error

    diagnostico: str = ""
    estrategia: str = ""
    justificacion: str = ""
    pasos: List[str] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)

    # UX
    es_trivial: bool = False

    # Error
    mensaje_error: str = ""


# =============================================================
# 2) MOTOR LÓGICO
# =============================================================

class Aritmetica:
    """
    Módulo V6: Aritmética Enterprise (Rigor + Pedagogía honesta).

    Principios:
    - La "verdad" la determina SymPy (simplify/factor).
    - La "explicación" solo se emite si el patrón se verifica estructuralmente.
    - No strings mágicos para errores: DTO lleva es_exitoso/mensaje_error.
    """

    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # ---------------------------------------------------------
    # API pública (texto + DTO)
    # ---------------------------------------------------------

    def evaluar(self, expresion: str) -> ResultadoAritmetica:
        """
        Evaluación numérica estricta:
        - Si hay símbolos libres -> error (no adivinamos valores).
        - Devuelve exacto si es entero/float/racional simple.
        - Si es irracional u objeto exacto grande, devuelve decimal como principal
          y deja el exacto en pasos.
        """
        try:
            expr = self.parser.parsear(expresion)

            if expr.free_symbols:
                syms = ", ".join(sorted([s.name for s in expr.free_symbols]))
                return self._error("Evaluación Numérica", expr,
                                   f"La expresión contiene variables ({syms}). Reemplace variables por números o use Simplificar.")

            # "Evaluar" significa: ejecutar aritmética exacta primero
            exacto = sympy.simplify(expr)

            pasos: List[str] = []
            advertencias: List[str] = []

            # Trivialidad (UX): entero, float, racional pequeño
            es_trivial = (
                isinstance(exacto, Integer) or
                isinstance(exacto, Float) or
                (isinstance(exacto, Rational) and max(abs(exacto.p), abs(exacto.q)) < 1000)
            )

            resultado_final = exacto

            # Si no es trivial, suele ser irracional (pi, sqrt(2), etc.) o racional enorme
            # Política: en "evaluar" se prioriza decimal como resultado principal,
            # pero se conserva exacto como paso.
            if not es_trivial:
                decimal = sympy.N(exacto, 20)
                pasos.append(f"Valor exacto: {exacto}")
                pasos.append(f"Aproximación decimal: {decimal:.10f}".rstrip("0").rstrip("."))
                advertencias.append("Resultado aproximado: se muestra una evaluación decimal.")
                resultado_final = decimal

            return ResultadoAritmetica(
                es_exitoso=True,
                operacion="Evaluación Numérica",
                expresion_original=expr,
                resultado=resultado_final,
                diagnostico="Expresión numérica (sin variables).",
                estrategia="Cálculo directo",
                justificacion="Se simplifica la expresión para obtener el valor numérico.",
                pasos=pasos,
                advertencias=advertencias,
                es_trivial=es_trivial,
            )

        except Exception as e:
            return self._error("Evaluación Numérica", expresion, str(e))

    def simplificar(self, expresion: str) -> ResultadoAritmetica:
        """
        Simplificación algebraica:
        - Intenta primero herramientas específicas (collect univariado, cancel en fracciones).
        - Luego simplify como verdad final.
        """
        try:
            expr = self.parser.parsear(expresion)
            pasos: List[str] = []
            estrategia = "Simplificación general"
            justificacion = "Aplicación de transformaciones equivalentes para reducir complejidad."

            # Agrupación (solo univariado)
            syms = sorted(list(expr.free_symbols), key=lambda s: s.name)
            if expr.is_Add and len(syms) == 1:
                var = syms[0]
                collected = sympy.collect(expr, var)
                if collected != expr:
                    pasos.append(f"Agrupación por potencias de {var}: {collected}")
                    estrategia = "Agrupación (collect)"

            # Cancelación en racionales
            num, den = sympy.fraction(expr)
            if den != 1:
                cancelado = sympy.cancel(expr)
                if cancelado != expr:
                    pasos.append(f"Cancelación de factores comunes: {cancelado}")
                    estrategia = "Cancelación (cancel)"

            # Verdad final
            resultado = sympy.simplify(expr)
            if resultado == expr and not pasos:
                pasos.append("La expresión ya estaba en una forma simple (no hubo cambios detectables).")

            return ResultadoAritmetica(
                es_exitoso=True,
                operacion="Simplificación",
                expresion_original=expr,
                resultado=resultado,
                diagnostico=self._diagnosticar_tipo(expr),
                estrategia=estrategia,
                justificacion=justificacion,
                pasos=pasos,
                es_trivial=False
            )

        except Exception as e:
            return self._error("Simplificación", expresion, str(e))

    def factorizar(self, expresion: str) -> ResultadoAritmetica:
        """
        Factorización con inferencia estructural:
        - Primero extrae factor común (factor_terms).
        - Luego factoriza completamente (factor) como verdad.
        - Clasifica SOLO si el patrón se verifica.
        """
        try:
            expr = self.parser.parsear(expresion)
            pasos: List[str] = []
            advertencias: List[str] = []

            # 1) Extraer factor común (pedagógico)
            comun = sympy.factor_terms(expr)
            nucleo = expr
            factor_comun = sympy.Integer(1)

            # Si factor_terms cambió, intentamos separar "constante" vs "núcleo"
            # Política: si hay una variable principal (univariado), todo lo que no depende de ella se trata como constante.
            syms = sorted(list(expr.free_symbols), key=lambda s: s.name)
            var_principal = syms[0] if len(syms) == 1 else None

            if comun != expr:
                pasos.append(f"Extracción de factor común: {comun}")

                if comun.is_Mul and var_principal is not None:
                    consts = [a for a in comun.args if not a.has(var_principal)]
                    vars_ = [a for a in comun.args if a.has(var_principal)]
                    if consts:
                        factor_comun = sympy.Mul(*consts)
                        nucleo = sympy.Mul(*vars_) if vars_ else sympy.Integer(1)
                    else:
                        nucleo = comun
                else:
                    # Si no podemos separar limpiamente, al menos analizamos el "comun" como núcleo
                    nucleo = comun

            # 2) Verdad final
            resultado = sympy.factor(expr)

            # Irreducible (en Q, según SymPy por defecto)
            if expr == resultado:
                advertencias.append("No se encontraron factores más simples en los racionales (Q).")
                return ResultadoAritmetica(
                    es_exitoso=True,
                    operacion="Factorización",
                    expresion_original=expr,
                    resultado=resultado,
                    diagnostico=self._diagnosticar_tipo(expr),
                    estrategia="Irreducible",
                    justificacion="SymPy no encontró una factorización no trivial sobre los racionales.",
                    pasos=pasos,
                    advertencias=advertencias,
                    es_trivial=False
                )

            # 3) Inferencia desde la estructura del resultado, pero sobre el núcleo (sin el factor común)
            caso, explicacion = self._inferir_caso(nucleo, resultado)

            estrategia = caso or ("Factor común" if comun != expr else "Factorización general")
            justificacion = explicacion if caso else "Factorización algebraica estándar (sin patrón escolar único verificable)."

            if caso:
                pasos.append(f"Patrón identificado: {justificacion}")

            return ResultadoAritmetica(
                es_exitoso=True,
                operacion="Factorización",
                expresion_original=expr,
                resultado=resultado,
                diagnostico=self._diagnosticar_tipo(expr),
                estrategia=estrategia,
                justificacion=justificacion,
                pasos=pasos,
                advertencias=advertencias,
                es_trivial=False
            )

        except Exception as e:
            return self._error("Factorización", expresion, str(e))

    # ---------------------------------------------------------
    # Inferencia de patrones (sin inventar)
    # ---------------------------------------------------------

    def _inferir_caso(self, nucleo, factorizada) -> Tuple[Optional[str], str]:
        """
        Devuelve (caso, explicación). Caso None si no puede verificarse con rigor.
        La verificación se apoya en:
        - forma del resultado
        - conteo de términos del núcleo original
        - consistencia por expansión
        """
        # Normalizar: comparar expandido del resultado con el núcleo expandido
        try:
            nucleo_exp = sympy.expand(nucleo)
            fact_exp = sympy.expand(factorizada)
            if sympy.simplify(nucleo_exp - fact_exp) != 0:
                # Si ni siquiera coincide, no intentamos clasificar.
                return None, "La factorización no coincide con el núcleo bajo expansión (no clasificable)."
        except Exception:
            # Si falla la comparación, no afirmamos patrones
            return None, "No se pudo verificar equivalencia estructural por expansión."

        # Conteo de términos del núcleo
        try:
            t_nucleo = sympy.Add.make_args(nucleo_exp)
            n_terms = len(t_nucleo)
        except Exception:
            n_terms = None

        # ---- 1) TCP: (a±b)^2 y el núcleo es trinomio
        if factorizada.is_Pow and factorizada.exp == 2:
            base = sympy.expand(factorizada.base)
            if base.is_Add and len(sympy.Add.make_args(base)) == 2 and n_terms == 3:
                return "Trinomio cuadrado perfecto", "Forma a^2 ± 2ab + b^2 = (a±b)^2 (verificado por estructura)."

        # ---- 2) Cubo perfecto: (a±b)^3 y el núcleo tiene 4 términos
        if factorizada.is_Pow and factorizada.exp == 3:
            base = sympy.expand(factorizada.base)
            if base.is_Add and len(sympy.Add.make_args(base)) == 2 and n_terms == 4:
                return "Cubo perfecto de binomio", "Forma (a±b)^3 (verificado por estructura)."

        # ---- 3) Diferencia de cuadrados: (a-b)(a+b) y el núcleo es binomio con signos opuestos
        # Requisito fuerte: dos factores, ambos binomios, y son conjugados.
        if factorizada.is_Mul and len(factorizada.args) == 2 and n_terms == 2:
            f1, f2 = factorizada.args
            f1e = sympy.expand(f1)
            f2e = sympy.expand(f2)

            if f1e.is_Add and f2e.is_Add:
                a1, b1 = sympy.Add.make_args(f1e)
                a2, b2 = sympy.Add.make_args(f2e)

                # Construimos "A" y "B" a partir de (f1+f2)/2 y (f1-f2)/2
                A = sympy.simplify((f1e + f2e) / 2)
                B = sympy.simplify((f1e - f2e) / 2)

                # Si f1 = A + B y f2 = A - B (o viceversa), entonces:
                # producto = A^2 - B^2
                # Verificamos exactamente esa identidad
                if sympy.simplify(sympy.expand(A**2 - B**2) - nucleo_exp) == 0:
                    return "Diferencia de cuadrados", "Forma a^2 - b^2 = (a-b)(a+b) (verificada)."

        # ---- 4) Suma/Diferencia de cubos: (a±b)(a^2 ∓ ab + b^2) con núcleo binomial
        # Requisito mínimo confiable: dos factores, uno lineal (binomio) y otro cuadrático (trinomio),
        # y núcleo con 2 términos.
        if factorizada.is_Mul and len(factorizada.args) == 2 and n_terms == 2:
            f1, f2 = factorizada.args
            d1 = sympy.total_degree(f1)
            d2 = sympy.total_degree(f2)
            # Para cubos: grados típicos 1 y 2 (en univariado), o en general "menor" y "mayor"
            if {d1, d2} == {1, 2}:
                return "Suma/diferencia de cubos", "Estructura (lineal)*(cuadrática) compatible con a^3 ± b^3 (verificación parcial)."

        # ---- 5) Trinomio cuadrático univariado: producto de dos lineales
        if factorizada.is_Mul and len(factorizada.args) == 2 and n_terms == 3:
            syms = sorted(list(nucleo.free_symbols), key=lambda s: s.name)
            if len(syms) == 1:
                var = syms[0]
                try:
                    p = sympy.Poly(nucleo_exp, var)
                    if p.degree() == 2:
                        # Dos factores lineales en var
                        if all(sympy.Poly(sympy.expand(f), var).degree() == 1 for f in factorizada.args):
                            a = p.LC()
                            if a == 1:
                                return "Trinomio x^2 + bx + c", "Factorización en dos binomios lineales (coeficiente líder 1)."
                            return "Trinomio ax^2 + bx + c", "Factorización en dos binomios lineales (coeficiente líder ≠ 1)."
                except Exception:
                    pass

        return None, "No se pudo verificar un patrón escolar único con rigor."

    # ---------------------------------------------------------
    # Diagnóstico y errores
    # ---------------------------------------------------------

    def _diagnosticar_tipo(self, expr) -> str:
        try:
            if expr.is_polynomial():
                return f"Polinomio (Grado {sympy.total_degree(expr)})"
        except Exception:
            pass

        try:
            _, den = sympy.fraction(expr)
            if den != 1:
                return "Expresión racional (fracción)"
        except Exception:
            pass

        return "Expresión algebraica"

    def _error(self, operacion: str, expr_original: Any, msg: str) -> ResultadoAritmetica:
        return ResultadoAritmetica(
            es_exitoso=False,
            operacion=operacion,
            expresion_original=expr_original,
            resultado=None,
            diagnostico="Error",
            estrategia="Ninguna",
            justificacion="No se pudo completar la operación.",
            pasos=[],
            advertencias=[],
            es_trivial=True,
            mensaje_error=msg
        )

    # ---------------------------------------------------------
    # Render accesible (texto)
    # ---------------------------------------------------------

    def renderizar(self, dto: ResultadoAritmetica) -> str:
        if not dto.es_exitoso:
            return f"ERROR ({dto.operacion}):\n{dto.mensaje_error}"

        if dto.es_trivial:
            val = dto.resultado
            if isinstance(val, Float):
                val = f"{val:.6f}".rstrip("0").rstrip(".")
            return f"RESULTADO: {val}"

        txt = []
        txt.append(f"OPERACIÓN: {dto.operacion.upper()}")
        txt.append(f"Expresión: {dto.expresion_original}")
        txt.append("-" * 30)

        txt.append("1. DIAGNÓSTICO")
        txt.append(f"   {dto.diagnostico}")

        txt.append("\n2. ESTRATEGIA")
        txt.append(f"   {dto.estrategia}")
        txt.append(f"   Nota: {dto.justificacion}")

        if dto.pasos:
            txt.append("\n3. DESARROLLO")
            for p in dto.pasos:
                txt.append(f"   • {p}")

        if dto.advertencias:
            txt.append("\n[!] AVISOS:")
            for adv in dto.advertencias:
                txt.append(f"   - {adv}")

        txt.append("-" * 30)
        txt.append(f"RESULTADO FINAL: {dto.resultado}")
        return "\n".join(txt)

    # Facades tipo “texto directo” (compatibilidad con tu estilo)
    def evaluar_texto(self, e: str) -> str:
        return self.renderizar(self.evaluar(e))

    def simplificar_texto(self, e: str) -> str:
        return self.renderizar(self.simplificar(e))

    def factorizar_texto(self, e: str) -> str:
        return self.renderizar(self.factorizar(e))
