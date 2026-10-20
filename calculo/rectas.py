"""
Recta tangente y recta normal a la curva y = f(x) en x = x0, explicadas con el formato de
calculo/pasos.py (Regla, En este caso, las cuentas y Queda):

  1. Punto de tangencia: y0 = f(x0), con cada operación de la cuenta (pasos_aritmetica).
  2. La derivada f'(x), con el paso a paso de Derivar.
  3. Pendiente de la tangente: m = f'(x0), con sus cuentas.
  4. Recta tangente: y - y0 = m*(x - x0), despejando y (algebra/ecuaciones.despejar).
  5. Pendiente de la normal: m_n = -1/m (si m = 0, la normal es vertical).
  6. Recta normal, igual que la tangente.
  7. Comprobación: las dos rectas pasan por el punto y m*m_n = -1.

Se verifican continuidad, dominio y cocientes incrementales laterales. Una tangente
vertical exige límites infinitos compatibles; los extremos unilaterales se identifican.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import sympy
from sympy import S

from algebra.ecuaciones import despejar, sustituir
from calculo.calculo import Calculo
from calculo.derivabilidad import cocientes, avisar_potencias
from calculo.pasos import PasoCalculo, entre_parentesis, suma_texto, texto, texto_paso
from i18n import tr
from pasos_aritmetica import ExplicadorEvaluar, SinExplicacion


@dataclass
class ResultadoRectas:
    texto: str
    es_error: bool = False
    tangente: Any = None          # Eq(y, ...) o Eq(x, x0) si es vertical
    normal: Any = None
    variable: Any = None
    expresion: Any = None
    punto: Any = None             # (x0, y0)
    avisos: List[str] = field(default_factory=list)


def _restado(v: Any) -> str:
    """Un número tras un signo menos: entre paréntesis solo si es negativo o una suma (y - (-1), y - sqrt(2)/2)."""
    v = sympy.sympify(v)
    return f"({texto(v)})" if v.could_extract_minus_sign() or v.is_Add else texto(v)


def recta_texto(expr: Any, x: Any) -> str:
    """El lado derecho de y = m*x + b, en ese orden: -x + 7 (SymPy escribiría 7 - x)."""
    expr = sympy.expand(expr)
    m = expr.coeff(x)
    b = sympy.expand(expr - m * x)
    terminos = ([m * x] if m != 0 else []) + [t for t in sympy.Add.make_args(b) if t != 0]
    return suma_texto(terminos) if terminos else "0"


def ecuacion_recta(recta: Any, x: Any) -> str:
    """'y = -x + 7', o 'x = 2' si la recta es vertical."""
    if recta.lhs == x:
        return f"{x} = {texto(recta.rhs)}"
    return f"{texto(recta.lhs)} = {recta_texto(recta.rhs, x)}"


def cuentas_sustitucion(expr: Any, x: Any, x0: Any, valor: Any) -> List[str]:
    """
    La expresión con x0 sustituido y cada operación hasta el valor, una por línea:
    '1^3 = 1*1*1 = 1. Queda 1 - 2*1.' Si la cuenta no se puede explicar, solo el resultado.
    """
    cuenta = sustituir(expr, {x: x0})
    lineas = [tr("Sustituimos {variable} = {valor}: {cuenta}.", variable=x, valor=texto(x0), cuenta=cuenta)]
    try:
        pasos = ExplicadorEvaluar().explicar(cuenta, valor)
    except (SinExplicacion, Exception):
        if cuenta != texto(valor):
            lineas.append(tr("Operamos: {antes} = {despues}.", antes=cuenta, despues=texto(valor)))
        return lineas
    for paso in pasos:
        if not paso.calculo:
            continue  # el resumen de la jerarquía: las operaciones ya dicen su cuenta
        linea = " ".join(paso.calculo)
        if paso.queda and paso.queda != texto(valor):
            linea += " " + tr("Queda {ecuacion}.", ecuacion=paso.queda)
        lineas.append(linea)
    return lineas


class MotorRectas:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido
        self.calculo = Calculo(parser_compartido)

    _cuentas = staticmethod(cuentas_sustitucion)

    # --- Ecuación de una recta por un punto ---

    def _recta(self, m: Any, x0: Any, y0: Any, x: Any, y: Any) -> Tuple[List[str], Any]:
        """Líneas de y - y0 = m*(x - x0) hasta y = ..., y la expresión de y."""
        izquierda_txt = f"{y} - {_restado(y0)}"
        diferencia = x - x0
        diferencia_txt = f"{x} - {_restado(x0)}"
        derecha_txt = f"{entre_parentesis(m)}*({diferencia_txt})"
        lineas = [tr("Sustituimos: {ecuacion}.", ecuacion=f"{izquierda_txt} = {derecha_txt}")]
        # Signos: y - (-1) = y + 1; x - 0 = x
        izquierda = y - y0
        if izquierda_txt != texto(izquierda):
            lineas.append(tr("Operamos: {antes} = {despues}.", antes=izquierda_txt, despues=texto(izquierda)))
        if diferencia_txt != texto(diferencia):
            lineas.append(tr("Operamos: {antes} = {despues}.", antes=diferencia_txt, despues=texto(diferencia)))
        if m == 0:
            derecha = S.Zero
            lineas.append(tr("Multiplicar por 0 da 0: {antes} = 0.", antes=f"0*{entre_parentesis(diferencia)}"))
        elif m == 1:
            derecha = diferencia
            lineas.append(tr("Multiplicar por 1 no cambia nada: {antes} = {despues}.",
                             antes=f"1*{entre_parentesis(diferencia)}", despues=texto(diferencia)))
        elif diferencia.is_Add:
            derecha = sympy.Mul(m, diferencia, evaluate=False)
        else:
            derecha = m * diferencia
        if izquierda == y:
            valor = sympy.expand(derecha.doit() if hasattr(derecha, "doit") else derecha)
            if texto(derecha) != texto(valor):
                lineas.append(tr("Quitamos paréntesis (propiedad distributiva): {antes} = {despues}.",
                                 antes=texto(derecha), despues=texto(valor)))
        else:
            cuentas, valor = despejar(izquierda, derecha, y)
            lineas += cuentas
        if texto(valor) != recta_texto(valor, x):
            lineas.append(tr("Ordenamos como y = m*x + b: {recta}.", recta=f"{y} = {recta_texto(valor, x)}"))
        return lineas, valor

    # --- Fachada ---

    def resolver(self, expresion: str, variable: Optional[str], punto: str) -> ResultadoRectas:
        try:
            original = self.parser.parsear(expresion)
            expr = original.doit()
            x, avisos = self.calculo._resolver_variable(expr, variable, "DERIVADA")
            avisar_potencias(original, avisos)
            if not str(punto or "").strip():
                raise ValueError(tr("Falta el punto x0 donde se traza la tangente."))
            x0 = self.parser.parsear(punto).doit()
            if x0.free_symbols or not x0.is_real or not x0.is_finite:
                raise ValueError(tr("El punto debe ser un número real (ej: 1, -2, pi/4)."))
            y = self.parser.simbolo("y" if x.name != "y" else "z")
            return self._explicar(expresion, expr, x, y, x0, avisos, original)
        except ValueError as e:
            return ResultadoRectas(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except Exception as e:
            return ResultadoRectas(tr("Error del Sistema: {error}", error=str(e)), es_error=True)

    def _explicar(self, entrada: str, expr: Any, x: Any, y: Any, x0: Any, avisos: List[str], original: Any = None) -> ResultadoRectas:
        nombre = f"{x}0"
        # 1. El punto de tangencia
        y0 = sympy.simplify(expr.subs(x, x0))
        if not y0.is_finite or y0.has(sympy.I) or y0 is S.NaN or not y0.is_real:
            raise ValueError(tr("La función no está definida en {variable} = {valor}: no hay punto de la curva ahí.",
                                variable=x, valor=texto(x0)))
        pasos = [PasoCalculo(
            tr("Punto de tangencia"),
            regla=tr("la recta tangente toca la curva en el punto ({x0}, f({x0})): su segunda coordenada es el valor de "
                     "la función en {x0}.", x0=nombre),
            partes=tr("f({variable}) = {funcion} y {x0} = {valor}.", variable=x, funcion=texto(expr), x0=nombre,
                      valor=texto(x0)),
            calculo=tuple(self._cuentas(expr, x, x0, y0)),
            queda=tr("f({x0}) = {y0}: el punto es ({x0v}, {y0}).", x0=texto(x0), y0=texto(y0), x0v=texto(x0)))]

        # 2. La derivada
        derivada = self.calculo.CalcularDerivada(entrada, str(x))
        if not derivada.es_exitoso:
            raise ValueError(derivada.mensaje_error)
        df = derivada.resultado
        pasos.append(PasoCalculo(
            tr("Derivar la función"),
            regla=tr("la pendiente de la recta tangente en {x0} es la derivada de la función en ese punto: m = f'({x0}). "
                     "Primero se calcula f'({variable}).", x0=nombre, variable=x),
            partes=tr("f({variable}) = {funcion}.", variable=x, funcion=texto(expr)),
            calculo=(tr("Los pasos de la derivada van a continuación."),) if derivada.pasos else (),
            queda=f"f'({x}) = {texto(df)}"))
        pasos.extend(derivada.pasos)
        avisos += [a for a in derivada.advertencias if a not in avisos]

        # 3. La pendiente
        lados = cocientes(expr if original is None else original, expr, x, x0)
        laterales = list(lados.values())
        if len(laterales) == 2 and sympy.simplify(laterales[0] - laterales[1]) != 0 and laterales[0] != laterales[1]:
            izquierda, derecha = laterales
            tipo = tr("cúspide") if all(v in (S.Infinity, S.NegativeInfinity) for v in laterales) else tr("esquina o punto no derivable")
            raise ValueError(tr("La función no es derivable en {variable} = {valor} (la derivada vale {izquierda} por la "
                                "izquierda y {derecha} por la derecha): {tipo}. No se ofrece una tangente única.",
                                variable=x, valor=texto(x0), izquierda=texto(izquierda), derecha=texto(derecha), tipo=tipo))
        if not laterales:
            raise ValueError(tr("No concluyente: no se puede certificar un entorno real lateral."))
        m = laterales[0]
        vertical = m in (S.Infinity, S.NegativeInfinity) and all(v == m for v in laterales)
        if not vertical and (m.is_real is not True or m.is_finite is not True):
            raise ValueError(tr("La derivada no existe en {variable} = {valor}: no hay recta tangente.",
                                variable=x, valor=texto(x0)))
        if len(lados) == 1:
            avisos.append(tr("Extremo unilateral del dominio: se ofrece la tangente lateral, no una derivada bilateral."))
        avisos.append(tr("Cociente incremental: {laterales}.", laterales="; ".join(
            (tr("izquierda") if lado == "-" else tr("derecha")) + ": " + texto(v) for lado, v in lados.items())))
        pendiente = PasoCalculo(
            tr("Pendiente de la recta tangente"),
            regla=tr("la pendiente se obtiene del límite del cociente incremental; en un borde solo se usa el lado real disponible. Un límite infinito no es una derivada real finita."),
            partes=tr("f'({variable}) = {derivada} y {x0} = {valor}.", variable=x, derivada=texto(df), x0=nombre,
                      valor=texto(x0)),
            calculo=tuple(self._cuentas(df, x, x0, m)) if not vertical else (
                tr("El cociente incremental tiende al mismo infinito por todos los lados reales disponibles: la pendiente es infinita y la tangente es vertical."),),
            queda=f"m = {texto(m)}" if not vertical else tr("pendiente infinita: tangente vertical"))
        pasos.append(pendiente)

        if vertical:
            return self._vertical(entrada, expr, x, y, x0, y0, pasos, avisos)

        # 4. La recta tangente
        lineas, tangente = self._recta(m, x0, y0, x, y)
        pasos.append(PasoCalculo(
            tr("Ecuación de la recta tangente"),
            regla=tr("la recta que pasa por el punto ({x0}, {y0}) con pendiente m es y - {y0} = m*(x - {x0}) (ecuación "
                     "punto-pendiente); se despeja y para escribirla como y = m*x + b.", x0=nombre, y0=f"{y}0"),
            partes=tr("el punto es ({x0}, {y0}) y m = {m}.", x0=texto(x0), y0=texto(y0), m=texto(m)),
            calculo=tuple(lineas),
            queda=f"{y} = {recta_texto(tangente, x)}"))

        # 5. La pendiente de la normal
        if m == 0:
            pasos.append(PasoCalculo(
                tr("Recta normal"),
                regla=tr("la recta normal es la perpendicular a la tangente en el mismo punto. Si la tangente es "
                         "horizontal (m = 0), la normal es vertical: x = {x0}.", x0=nombre),
                partes=tr("m = 0 y {x0} = {valor}.", x0=nombre, valor=texto(x0)),
                calculo=(tr("No se puede dividir entre 0, así que -1/m no existe: la normal no tiene pendiente, es "
                            "vertical."),),
                queda=f"{x} = {texto(x0)}"))
            normal = sympy.Eq(x, x0)
            mn = None
        else:
            mn = sympy.simplify(-1 / m)
            division = f"-1/{entre_parentesis(m)}"
            pasos.append(PasoCalculo(
                tr("Pendiente de la recta normal"),
                regla=tr("la recta normal es la perpendicular a la tangente en el mismo punto. Dos rectas son "
                         "perpendiculares si el producto de sus pendientes es -1, así que m_n = -1/m."),
                partes=tr("m = {m}.", m=texto(m)),
                calculo=(f"m_n = {division} = {texto(mn)}." if division != texto(mn) else f"m_n = {texto(mn)}.",),
                queda=f"m_n = {texto(mn)}"))
            lineas, valor_normal = self._recta(mn, x0, y0, x, y)
            pasos.append(PasoCalculo(
                tr("Ecuación de la recta normal"),
                regla=tr("la misma ecuación punto-pendiente, con el mismo punto y la pendiente de la normal: "
                         "y - {y0} = m_n*(x - {x0}).", x0=nombre, y0=f"{y}0"),
                partes=tr("el punto es ({x0}, {y0}) y m_n = {m}.", x0=texto(x0), y0=texto(y0), m=texto(mn)),
                calculo=tuple(lineas),
                queda=f"{y} = {recta_texto(valor_normal, x)}"))
            normal = sympy.Eq(y, valor_normal)
        tangente = sympy.Eq(y, tangente)

        # Comprobar las rectas con la pendiente certificada por cocientes incrementales.
        m_verdad = m
        t_verdad = expr.subs(x, x0) + m_verdad * (x - x0)
        coinciden = sympy.simplify(tangente.rhs - t_verdad) == 0
        if mn is not None:
            coinciden = coinciden and sympy.simplify(normal.rhs - (expr.subs(x, x0) - (x - x0) / m_verdad)) == 0
        if not coinciden:
            avisos.append(tr("AVISO: la explicación no llegó al resultado de SymPy; se muestra el resultado sin pasos."))
            tangente = sympy.Eq(y, sympy.expand(t_verdad))
            normal = (sympy.Eq(x, x0) if m_verdad == 0 else
                      sympy.Eq(y, sympy.expand(expr.subs(x, x0) - (x - x0) / m_verdad)))
            pasos = []
        else:
            pasos.append(self._comprobacion(x, y, x0, y0, tangente, normal, m, mn))
        return self._componer(entrada, expr, x, y, x0, y0, tangente, normal, pasos, avisos)

    def _vertical(self, entrada, expr, x, y, x0, y0, pasos, avisos) -> ResultadoRectas:
        tangente, normal = sympy.Eq(x, x0), sympy.Eq(y, y0)
        pasos.append(PasoCalculo(
            tr("Rectas tangente y normal"),
            regla=tr("si la pendiente de la tangente es infinita, la tangente es la recta vertical x = {x0}, y la normal, "
                     "perpendicular a ella, es la horizontal y = {y0}.", x0=f"{x}0", y0=f"{y}0"),
            partes=tr("el punto es ({x0}, {y0}).", x0=texto(x0), y0=texto(y0)),
            calculo=(tr("Tangente: {recta}.", recta=f"{x} = {texto(x0)}"),
                     tr("Normal: {recta}.", recta=f"{y} = {texto(y0)}")),
            queda=f"{x} = {texto(x0)}; {y} = {texto(y0)}"))
        return self._componer(entrada, expr, x, y, x0, y0, tangente, normal, pasos, avisos)

    def _comprobacion(self, x, y, x0, y0, tangente, normal, m, mn) -> PasoCalculo:
        lineas = []
        for nombre, recta in ((tr("Tangente"), tangente), (tr("Normal"), normal)):
            if recta.lhs == x:  # vertical: x = x0
                lineas.append(tr("{recta} ({ecuacion}): es vertical y pasa por {variable} = {valor}: se cumple.",
                                 recta=nombre, ecuacion=f"{x} = {texto(x0)}", variable=x, valor=texto(x0)))
                continue
            cuenta = sustituir(recta.rhs, {x: x0})
            valor = sympy.simplify(recta.rhs.subs(x, x0))
            cuenta = cuenta if cuenta == texto(valor) else f"{cuenta} = {texto(valor)}"
            lineas.append(tr("{recta} ({ecuacion}): con {variable} = {valor}, {y} = {cuenta}, que es {y0}: {veredicto}.",
                             recta=nombre, ecuacion=f"{y} = {recta_texto(recta.rhs, x)}", variable=x, valor=texto(x0), y=y,
                             cuenta=cuenta, y0=texto(y0),
                             veredicto=tr("se cumple") if sympy.simplify(valor - y0) == 0 else tr("NO se cumple")))
        if mn is not None:
            producto = sympy.simplify(m * mn)
            lineas.append(tr("Perpendiculares: m*m_n = {m}*{mn} = {producto}: {veredicto}.", m=entre_parentesis(m),
                             mn=entre_parentesis(mn), producto=texto(producto),
                             veredicto=tr("se cumple") if producto == -1 else tr("NO se cumple")))
        elif m == 0:
            lineas.append(tr("Perpendiculares: la tangente es horizontal y la normal vertical: se cumple."))
        return PasoCalculo(
            tr("Comprobación"),
            regla=tr("las dos rectas deben pasar por el punto de tangencia (al sustituir {x0}, sale {y0}), y el "
                     "producto de sus pendientes debe ser -1.", x0=f"{x}0", y0=f"{y}0"),
            partes=tr("el punto es ({x0}, {y0}).", x0=texto(x0), y0=texto(y0)),
            calculo=tuple(lineas),
            queda=tr("tangente: {t}; normal: {n}", t=ecuacion_recta(tangente, x),
                     n=ecuacion_recta(normal, x)))

    def _componer(self, entrada, expr, x, y, x0, y0, tangente, normal, pasos, avisos) -> ResultadoRectas:
        lineas = [tr("RESULTADO:"),
                  tr("Recta tangente: {recta}", recta=ecuacion_recta(tangente, x)),
                  tr("Recta normal: {recta}", recta=ecuacion_recta(normal, x))]
        lineas += avisos + ["=" * 30,
                            tr("Función: f({variable}) = {funcion}", variable=x, funcion=texto(expr)),
                            tr("Punto: {x0} = {valor}; punto de tangencia ({valor}, {y0})", x0=f"{x}0",
                               valor=texto(x0), y0=texto(y0))]
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoRectas("\n".join(lineas), tangente=tangente, normal=normal, variable=x, expresion=expr,
                               punto=(x0, y0), avisos=avisos)
