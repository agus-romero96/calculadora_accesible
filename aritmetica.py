import sympy
from dataclasses import dataclass, field
from typing import List, Any, Optional, Tuple
from sympy import Integer, Float, Rational, Symbol

from calculo.pasos import PasoCalculo, texto, texto_paso
from i18n import N_, tr
from dominios import aviso_restricciones, restricciones_denominadores
from pasos_aritmetica import (IRREDUCIBLE, ExplicadorEvaluar, ExplicadorFactorizar, ExplicadorSimplificar,
                              SinExplicacion, paso_decimal)

SIN_PASOS = N_("No se pudo explicar paso a paso; el resultado es el que calcula SymPy.")


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
    pasos: List[PasoCalculo] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)
    entrada: str = ""  # tal como se escribió

    # UX
    es_trivial: bool = False

    # Error
    mensaje_error: str = ""
    restricciones: Tuple[Any, ...] = ()


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
                return self._error(N_("Evaluación Numérica"), expr,
                                   tr("La expresión contiene variables ({variables}). Reemplace variables por números o use Simplificar.",
                                      variables=syms))

            # "Evaluar" significa: ejecutar aritmética exacta primero
            exacto = sympy.simplify(expr)
            if exacto.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo):
                return self._error(N_("Evaluación Numérica"), expr, tr("No se puede dividir entre 0."))
            if exacto.is_real is False:
                return self._error(N_("Evaluación Numérica"), expr, tr("El resultado no es un número real."))

            advertencias: List[str] = []
            try:
                pasos = ExplicadorEvaluar().explicar(expresion, exacto)
            except SinExplicacion:
                pasos = []
                advertencias.append(tr(SIN_PASOS))

            # Trivialidad (UX): entero, float, racional pequeño
            es_trivial = (
                isinstance(exacto, Integer) or
                isinstance(exacto, Float) or
                (isinstance(exacto, Rational) and max(abs(exacto.p), abs(exacto.q)) < 1000)
            )

            resultado_final = exacto
            # Si no es trivial, suele ser irracional (pi, sqrt(2)...) o un racional enorme: el resultado
            # principal es el decimal, y el valor exacto queda en los pasos
            if not es_trivial:
                decimal = sympy.N(exacto, 20)
                pasos.append(paso_decimal(exacto, f"{decimal:.10f}".rstrip("0").rstrip(".")))
                advertencias.append(tr("Resultado aproximado: se muestra una evaluación decimal."))
                resultado_final = decimal

            return ResultadoAritmetica(
                es_exitoso=True,
                operacion=N_("Evaluación Numérica"),
                expresion_original=expr,
                resultado=resultado_final,
                diagnostico=N_("Expresión numérica (sin variables)."),
                estrategia=N_("Jerarquía de las operaciones"),
                pasos=pasos,
                advertencias=advertencias,
                es_trivial=es_trivial,
                entrada=expresion,
            )

        except Exception as e:
            return self._error(N_("Evaluación Numérica"), expresion, str(e))

    def simplificar(self, expresion: str) -> ResultadoAritmetica:
        """
        Simplificación algebraica:
        - Intenta primero herramientas específicas (collect univariado, cancel en fracciones).
        - Luego simplify como verdad final.
        """
        try:
            # El parser no evalúa (evaluate=False): el árbol sin evaluar conserva los paréntesis y los
            # términos sin agrupar que hay que explicar; doit() da la forma normal para calcular
            crudo = self.parser.parsear(expresion)
            restricciones = restricciones_denominadores(crudo)
            if sympy.S.false in restricciones:
                return self._error(N_("Simplificación"), crudo, aviso_restricciones(restricciones))
            expr = crudo.doit()
            resultado = sympy.simplify(expr)  # la verdad matemática
            advertencias: List[str] = [aviso_restricciones(restricciones)] if restricciones else []
            try:
                pasos = ExplicadorSimplificar().explicar(crudo, expr, resultado)
            except (SinExplicacion, Exception):
                pasos = []
                advertencias.append(tr(SIN_PASOS))

            return ResultadoAritmetica(
                es_exitoso=True,
                operacion=N_("Simplificación"),
                expresion_original=crudo if restricciones else expr,
                resultado=resultado,
                diagnostico=self._diagnosticar_tipo(expr),
                estrategia=N_("Simplificación algebraica"),
                pasos=pasos,
                advertencias=advertencias,
                es_trivial=False,
                entrada=expresion,
                restricciones=restricciones,
            )

        except Exception as e:
            return self._error(N_("Simplificación"), expresion, str(e))

    def factorizar(self, expresion: str) -> ResultadoAritmetica:
        """
        Factorización con inferencia estructural:
        - Primero extrae factor común (factor_terms).
        - Luego factoriza completamente (factor) como verdad.
        - Clasifica SOLO si el patrón se verifica.
        """
        try:
            # El parser no evalúa (evaluate=False): doit() lleva la expresión a su forma
            # normal para que las comparaciones (¿cambió algo?) sean fiables.
            crudo = self.parser.parsear(expresion)
            restricciones = restricciones_denominadores(crudo)
            if sympy.S.false in restricciones:
                return self._error(N_("Factorización"), crudo, aviso_restricciones(restricciones))
            expr = crudo.doit()
            resultado = sympy.factor(expr)  # la verdad matemática
            advertencias: List[str] = [aviso_restricciones(restricciones)] if restricciones else []
            explicador = ExplicadorFactorizar()
            pasos: List[PasoCalculo] = []
            try:
                obtenido = explicador.explicar(expr)
                if sympy.expand(obtenido - expr) != 0:
                    raise SinExplicacion()
                pasos = list(explicador.pasos)
                if (pasos and sympy.expand(obtenido) != obtenido
                        and sympy.expand(obtenido - resultado) == 0):
                    resultado = obtenido
                if pasos and sympy.expand(obtenido) != obtenido:  # sin factores no hay nada que comprobar
                    pasos.append(PasoCalculo(
                        tr("Comprobación"),
                        regla=tr("una factorización es correcta si al multiplicar los factores sale la expresión original."),
                        partes=tr("los factores son {factores}.", factores=texto(obtenido)),
                        calculo=(tr("Multiplicando: {factores} = {expandida}, que es la expresión original.",
                                    factores=texto(obtenido), expandida=texto(sympy.expand(obtenido))),),
                        queda=texto(resultado)))
            except (SinExplicacion, Exception):
                pasos = []
                advertencias.append(tr(SIN_PASOS))

            if sympy.expand(resultado) == resultado:
                advertencias.append(tr("No se encontraron factores más simples en los racionales (Q)."))
                estrategia = IRREDUCIBLE
            else:
                # El caso de la expresión sin el factor común (2*x^2 - 18: diferencia de cuadrados)
                casos = [c for c in explicador.casos if c != N_("Factor común")]
                estrategia = casos[0] if casos else (explicador.casos[0] if explicador.casos else N_("Factorización general"))
            if not pasos and estrategia == IRREDUCIBLE:
                advertencias = [a for a in advertencias if a != tr(SIN_PASOS)]
                pasos = [PasoCalculo(
                    tr("Sin factores"),
                    regla=tr("una expresión es irreducible en los racionales si no tiene factor común, no encaja en ningún "
                             "producto notable y no tiene raíces racionales."),
                    partes=tr("{expresion} no tiene factor común, no es un producto notable y no tiene raíces racionales.",
                              expresion=texto(expr)),
                    queda=texto(expr))]

            return ResultadoAritmetica(
                es_exitoso=True,
                operacion=N_("Factorización"),
                expresion_original=crudo if restricciones else expr,
                resultado=resultado,
                diagnostico=self._diagnosticar_tipo(expr),
                estrategia=estrategia,
                pasos=pasos,
                advertencias=advertencias,
                es_trivial=False,
                entrada=expresion,
                restricciones=restricciones,
            )

        except Exception as e:
            return self._error(N_("Factorización"), expresion, str(e))

    # ---------------------------------------------------------
    # Diagnóstico y errores
    # ---------------------------------------------------------

    def _diagnosticar_tipo(self, expr) -> str:
        try:
            if expr.is_polynomial():
                return tr("Polinomio (Grado {grado})", grado=sympy.total_degree(expr))
        except Exception:
            pass

        try:
            _, den = sympy.fraction(expr)
            if den != 1:
                return N_("Expresión racional (fracción)")
        except Exception:
            pass

        return N_("Expresión algebraica")

    def _error(self, operacion: str, expr_original: Any, msg: str) -> ResultadoAritmetica:
        return ResultadoAritmetica(
            es_exitoso=False,
            operacion=operacion,
            expresion_original=expr_original,
            resultado=None,
            diagnostico=N_("Error"),
            estrategia=N_("Ninguna"),
            justificacion=N_("No se pudo completar la operación."),
            pasos=[],
            advertencias=[],
            es_trivial=True,
            mensaje_error=msg
        )

    # ---------------------------------------------------------
    # Render accesible (texto)
    # ---------------------------------------------------------

    def renderizar(self, dto: ResultadoAritmetica) -> str:
        """RESULTADO primero, como el resto de la calculadora, y después el paso a paso."""
        if not dto.es_exitoso:
            return tr("ERROR ({operacion}):", operacion=tr(dto.operacion)) + f"\n{dto.mensaje_error}"

        val = dto.resultado
        if isinstance(val, Float) and dto.es_trivial:
            val = f"{val:.6f}".rstrip("0").rstrip(".")
        txt = [tr("RESULTADO: {valor}", valor=val), "=" * 30,
               tr("OPERACIÓN: {operacion}", operacion=tr(dto.operacion).upper()),
               tr("Expresión: {expresion}", expresion=dto.entrada or dto.expresion_original)]
        if dto.estrategia:
            txt.append(tr("Estrategia: {estrategia}", estrategia=tr(dto.estrategia)))
        if dto.pasos:
            txt.append("\n" + tr("PASO A PASO:"))
            txt.extend(texto_paso(i, p) for i, p in enumerate(dto.pasos, 1))
        if dto.advertencias:
            txt.append("\n" + tr("[!] AVISOS:"))
            txt.extend(f" - {a}" for a in dto.advertencias)
        return "\n".join(txt)

    # Facades tipo “texto directo” (compatibilidad con tu estilo)
    def evaluar_texto(self, e: str) -> str:
        return self.renderizar(self.evaluar(e))

    def simplificar_texto(self, e: str) -> str:
        return self.renderizar(self.simplificar(e))

    def factorizar_texto(self, e: str) -> str:
        return self.renderizar(self.factorizar(e))
