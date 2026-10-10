from __future__ import annotations

from typing import Any, List, Optional

import sympy

from calculo.pasos import PasoCalculo, entre_parentesis, texto
from i18n import N_, tr
from ._pasos import paso_evaluacion, paso_sustitucion, tendencia
from ._base import (
    Estrategia,
    ResultadoEstrategia,
    ESTADO_FINITO,
    ESTADO_NO_CONCLUYENTE,
    es_punto_finito,
)


class SimplificacionCancelacion(Estrategia):
    """
    Estrategia: Simplificación / Cancelación (álgebra previa)

    Objetivo:
      - Resolver límites 0/0 en un punto finito que se arreglan con álgebra básica:
        * fracciones anidadas
        * factores comunes que se cancelan (ej: (x^2-1)/(x-1) en x=1)

    Solo "gana" si la cancelación realmente elimina la indeterminación:
      1) la sustitución directa en la forma original da 0/0, y
      2) tras simplificar, la sustitución directa da un valor finito.
    Si no se cumple, devuelve NO_CONCLUYENTE y el router prueba otra estrategia
    (así no se atribuye a "simplificación" un límite que en realidad resolvió SymPy).

    Herramientas (suaves):
      - together(): pone todo en una sola fracción sin reescribir agresivo
      - cancel(): cancela factores comunes en fracciones racionales/simbólicas
      - factor(): opcional, ayuda a revelar factores
    """

    def nombre(self) -> str:
        return N_("Simplificación y cancelación")

    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        try:
            return es_punto_finito(punto) and var in expr.free_symbols
        except Exception:
            return False

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        dir_ = kwargs.get("dir", None)

        # 0) ¿Hay realmente una indeterminación 0/0 que cancelar?
        try:
            num0, den0 = sympy.together(expr).as_numer_denom()
            n0 = sympy.simplify(num0.subs(var, punto))
            d0 = sympy.simplify(den0.subs(var, punto))
        except Exception:
            return self._no_concluyente(expr, expr, [], tr("No se pudo evaluar la sustitución directa."))

        if not (n0 == 0 and d0 == 0):
            return self._no_concluyente(expr, expr, [], tr("La sustitución directa no produce 0/0: no hay factor que cancelar."))

        paso_inicial, _ = paso_sustitucion(expr, var, punto, dir_)
        pasos: List[PasoCalculo] = [paso_inicial] if paso_inicial else []

        # 1) Una sola fracción (fracción de fracciones -> fracción simple)
        try:
            junta = sympy.together(expr)
        except Exception:
            junta = expr
        if junta != expr:
            pasos.append(PasoCalculo(
                tr("Una sola fracción"),
                regla=tr("para cancelar factores, primero se escribe todo como una sola fracción (común denominador)."),
                partes=tr("{antes} = {despues}.", antes=texto(expr), despues=texto(junta)),
                queda=texto(junta)))

        # 2) Factorizar y cancelar el factor común
        num, den = junta.as_numer_denom()
        try:
            num_f, den_f = sympy.factor(num), sympy.factor(den)
            comun = sympy.gcd(num, den)
            expr_trabajo = sympy.cancel(junta)
        except Exception:
            return self._no_concluyente(expr, expr, pasos, tr("La simplificación no eliminó la indeterminación."))
        if comun.is_number:
            return self._no_concluyente(expr, expr_trabajo, pasos, tr("La simplificación no eliminó la indeterminación."))

        calculo = []
        for etiqueta, original, factorizado in ((tr("Factorizamos el numerador: {antes} = {despues}."), num, num_f),
                                                (tr("Factorizamos el denominador: {antes} = {despues}."), den, den_f)):
            if factorizado != original:
                calculo.append(etiqueta.format(antes=texto(original), despues=texto(factorizado)))
        calculo.append(tr("El factor común es {factor}: vale 0 en {variable} = {punto}, y es lo que producía el 0/0.",
                          factor=texto(comun), variable=var, punto=punto))
        calculo.append(tr("Cancelamos {factor}: {antes} = {despues}.", factor=texto(comun),
                          antes=f"{texto(num_f) if num_f.is_Mul else entre_parentesis(num_f)}/{entre_parentesis(den_f)}",
                          despues=texto(expr_trabajo)))
        pasos.append(PasoCalculo(
            tr("Factorizar y cancelar"),
            regla=tr("si un polinomio vale 0 en {variable} = a, tiene el factor ({variable} - a). Se factorizan "
                     "numerador y denominador y se cancela el factor común: mientras {variable} se acerca a a sin "
                     "llegar, ese factor no es 0, así que cancelarlo no cambia el límite.", variable=var),
            partes=tr("el numerador es {num} y el denominador es {den}.", num=texto(num), den=texto(den)),
            calculo=tuple(calculo),
            queda=tr("lim {expresion} cuando {tendencia}", expresion=texto(expr_trabajo),
                     tendencia=tendencia(var, punto, dir_))))

        # 3) Tras simplificar, ¿la sustitución directa ya es un valor finito?
        try:
            val = sympy.simplify(expr_trabajo.subs(var, punto))
        except Exception:
            val = None

        if val is None or val.is_finite is not True:
            return self._no_concluyente(expr, expr_trabajo, pasos, tr("La simplificación no eliminó la indeterminación."))

        pasos.append(paso_evaluacion(expr_trabajo, var, punto, dir_, val))

        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_FINITO,
            resultado=val,
            nombre_estrategia=self.nombre(),
            explicacion=N_("Cancelar el factor común eliminó la indeterminación 0/0."),
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr_trabajo,
        )

    def _no_concluyente(self, expr: Any, expr_trabajo: Any, pasos: List[str], explicacion: str) -> ResultadoEstrategia:
        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_NO_CONCLUYENTE,
            resultado=None,
            nombre_estrategia=self.nombre(),
            explicacion=explicacion,
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr_trabajo,
        )
