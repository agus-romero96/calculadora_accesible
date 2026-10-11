"""
Derivada implícita dy/dx de una curva F(x, y) = G(x, y), explicada con el formato de
calculo/pasos.py (Regla, En este caso, las cuentas y Queda):

  1. Planteamiento: y depende de x (y = y(x)); se derivan los dos lados respecto a x, y cada vez
     que se deriva algo con y, la regla de la cadena añade el factor y' = dy/dx.
  2. Cada término, con el paso a paso de Derivar:
       - solo con x: la derivada de siempre;
       - solo con y, c*h(y): h'(y) respecto a y y la regla de la cadena, h'(y)*y';
       - producto g(x)*h(y): regla del producto, con la parte de y por la regla de la cadena.
  3. La ecuación derivada, y el despeje de y': pasar los términos con y' a un lado, sacar y'
     factor común, dividir (el divisor debe ser distinto de 0) y simplificar.

Se compara con idiff de SymPy. Los términos que mezclan x e y sin separarse (sin(x*y),
exp(x + y)) se resuelven con SymPy, sin pasos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import sympy

from algebra.ecuaciones import _pasar
from calculo.calculo import Calculo
from calculo.derivadas import ExplicadorDerivada
from calculo.pasos import PasoCalculo, entre_parentesis, suma_texto, texto, texto_paso
from i18n import tr


class SinExplicacion(Exception):
    """Un término que no se sabe explicar: se da el resultado de SymPy."""


@dataclass
class ResultadoImplicita:
    texto: str
    es_error: bool = False
    derivada: Any = None
    x: Any = None
    y: Any = None
    ecuacion: Any = None
    avisos: List[str] = field(default_factory=list)


def _terminos(expr: Any) -> List[Any]:
    return [t for t in sympy.Add.make_args(sympy.expand(expr)) if t != 0]


def _grado(t: Any) -> int:
    try:
        return sympy.Poly(t).total_degree() if t.free_symbols else 0
    except Exception:
        return 0


def _ordenados(terminos: List[Any]) -> List[Any]:
    """Como se escriben a mano: de mayor a menor grado, y un término positivo delante (2*y - x^2, no -x^2 + 2*y)."""
    por_grado = sorted(terminos, key=lambda t: -_grado(t))
    positivos = [t for t in por_grado if not t.could_extract_minus_sign()]
    if positivos and por_grado[0].could_extract_minus_sign():
        por_grado.remove(positivos[0])
        por_grado.insert(0, positivos[0])
    return por_grado


def _fraccion_texto(numerador: Any, denominador: Any) -> str:
    """'(6*y - 3*x^2)/(3*y^2 - 6*x)', con paréntesis solo donde hacen falta."""
    if denominador == 1:
        return texto(numerador)
    return f"{entre_parentesis(numerador)}/{entre_parentesis(denominador)}"


class MotorImplicita:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # --- Lectura ---

    def _leer(self, entrada: str) -> Tuple[Any, Any, Any, Any, List[str]]:
        """(izquierda, derecha, x, y, avisos): la ecuación y qué variable depende de cuál."""
        if entrada.count("=") != 1:
            raise ValueError(tr("Escriba una ecuación con un signo = entre las dos variables (ej: x^2 + y^2 = 25)."))
        izq_txt, der_txt = entrada.split("=")
        if not izq_txt.strip() or not der_txt.strip():
            raise ValueError(tr("Falta uno de los dos lados de la {tipo}.", tipo=tr("ecuación")))
        izquierda = self.parser.parsear(izq_txt).doit()
        derecha = self.parser.parsear(der_txt).doit()
        variables = sorted((izquierda - derecha).free_symbols | izquierda.free_symbols | derecha.free_symbols,
                           key=lambda s: s.name)
        if len(variables) != 2:
            raise ValueError(tr("La derivada implícita necesita una ecuación con dos variables, como x e y; esta tiene "
                                "{n} ({variables}).", n=len(variables),
                                variables=", ".join(v.name for v in variables) or "-"))
        nombres = [v.name for v in variables]
        avisos = []
        if "y" in nombres:
            y = variables[nombres.index("y")]
            x = variables[1 - nombres.index("y")]
        else:
            x, y = variables
            avisos.append(tr("Se toma {y} como función de {x} (se deriva respecto a {x}).", x=x, y=y))
        return izquierda, derecha, x, y, avisos

    # --- Fachada ---

    def resolver(self, entrada: str) -> ResultadoImplicita:
        try:
            izquierda, derecha, x, y, avisos = self._leer(entrada)
        except ValueError as e:
            return ResultadoImplicita(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except Exception as e:
            return ResultadoImplicita(tr("Error del Sistema: {error}", error=str(e)), es_error=True)
        if not (izquierda - derecha).has(y):
            return ResultadoImplicita(tr("Error de Validación: {error}", error=tr(
                "{y} desaparece de la ecuación: no define {y} en función de {x}.", x=x, y=y)), es_error=True)

        try:
            verdad = sympy.simplify(sympy.idiff(izquierda - derecha, y, x))
        except Exception as e:
            return ResultadoImplicita(tr("Error del Sistema: {error}", error=str(e)), es_error=True)

        yp = sympy.Symbol(f"{y}'")
        try:
            pasos, valor, derivada_txt = self._explicar(izquierda, derecha, x, y, yp, avisos)
            if sympy.simplify(valor - verdad) != 0:
                avisos.append(tr("AVISO: la explicación no llegó al resultado de SymPy; se muestra el resultado sin pasos."))
                pasos, valor = [], verdad
        except SinExplicacion:
            pasos, valor = [], verdad
            avisos.append(tr("NOTA: hay explicación paso a paso cuando cada término es un producto de una parte con {x} y "
                             "otra con {y} (como {x}^2*{y}^3 o {x}*sin({y})). Esta ecuación la resuelve SymPy, sin pasos.",
                             x=x, y=y))
        except Exception:
            pasos, valor = [], verdad
            avisos.append(tr("AVISO: no se pudo explicar paso a paso; el resultado es el que calcula SymPy."))

        if not pasos:
            derivada_txt = texto(valor)
        lineas = [tr("RESULTADO: {valor}", valor=f"d{y}/d{x} = {derivada_txt}")] + avisos + [
            "=" * 30,
            tr("Ecuación: {ecuacion}", ecuacion=f"{texto(izquierda)} = {texto(derecha)}"),
            tr("{y} es función de {x}; se deriva respecto a {x}.", x=x, y=y)]
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoImplicita("\n".join(lineas), derivada=valor, x=x, y=y,
                                  ecuacion=sympy.Eq(izquierda, derecha, evaluate=False), avisos=avisos)

    # --- La explicación ---

    def _derivada_explicada(self, expr: Any, variable: Any, avisos: List[str]) -> Tuple[List[PasoCalculo], Any]:
        """Los pasos de Derivar para expr respecto a variable (SinExplicacion si no se puede)."""
        resultado = sympy.simplify(sympy.diff(expr, variable))
        pasos = Calculo._explicar_derivada(ExplicadorDerivada(variable), expr, resultado, avisos)
        if not pasos:
            raise SinExplicacion()
        return pasos, resultado

    def _termino(self, t: Any, x: Any, y: Any, yp: Any, avisos: List[str]) -> Tuple[List[PasoCalculo], Any]:
        """(pasos, derivada respecto a x con y'): un término del tipo c, g(x), c*h(y) o g(x)*h(y)."""
        if not t.has(x) and not t.has(y):
            return [], sympy.Integer(0)
        if not t.has(y):
            return self._derivada_explicada(t, x, avisos)
        partes_x, partes_y, numero = [], [], sympy.Integer(1)
        for f in sympy.Mul.make_args(t):
            if f.has(x) and f.has(y):
                raise SinExplicacion()  # sin(x*y), exp(x + y): x e y mezclados
            if f.has(y):
                partes_y.append(f)
            elif f.has(x):
                partes_x.append(f)
            else:
                numero *= f
        h = sympy.Mul(*partes_y)
        pasos_h, dh = self._derivada_explicada(h, y, avisos) if h != y else ([], sympy.Integer(1))
        cadena = dh * yp
        pasos = list(pasos_h)
        lineas = [tr("Respecto a {y}, la derivada de {h} es {dh}.", y=y, h=texto(h), dh=texto(dh))] if h != y else [
            tr("La derivada de {y} respecto a {y} es 1.", y=y)]
        lineas.append(tr("Como {y} depende de {x}, se multiplica por {yp}: d/d{x}({h}) = {dh}*{yp} = {cadena}.",
                         y=y, x=x, yp=yp, h=texto(h), dh=entre_parentesis(dh), cadena=texto(cadena)))
        pasos.append(PasoCalculo(
            tr("Regla de la cadena en {h}", h=texto(h)),
            regla=tr("{y} es una función de {x}: al derivar respecto a {x} una expresión con {y}, se deriva respecto a "
                     "{y} y se multiplica por {yp} (la derivada de {y} respecto a {x}).", x=x, y=y, yp=yp),
            partes=tr("la parte con {y} es {h}.", y=y, h=texto(h)),
            calculo=tuple(lineas),
            queda=texto(cadena)))
        if not partes_x:
            if numero == 1:
                return pasos, cadena
            total = numero * cadena
            pasos.append(PasoCalculo(
                tr("Regla del factor constante en {termino}", termino=texto(t)),
                regla=tr("la derivada de c*f es c*f': el número multiplica a la derivada."),
                partes=tr("c = {c} y f = {f}.", c=texto(numero), f=texto(h)),
                calculo=(f"{entre_parentesis(numero)}*({texto(cadena)}) = {texto(total)}.",),
                queda=texto(total)))
            return pasos, total
        g = numero * sympy.Mul(*partes_x)
        pasos_g, dg = self._derivada_explicada(g, x, avisos)
        pasos = pasos_g + pasos
        total = dg * h + g * cadena
        pasos.append(PasoCalculo(
            tr("Regla del producto en {termino}", termino=texto(t)),
            regla=tr("la derivada de u*v es u'*v + u*v'. Aquí u solo tiene {x} y v solo tiene {y}.", x=x, y=y),
            partes=tr("u = {u} (con u' = {du}) y v = {v} (con v' = {dv}, por la regla de la cadena).", u=texto(g),
                      du=texto(dg), v=texto(h), dv=texto(cadena)),
            calculo=(tr("Sustituimos en u'*v + u*v': {cuenta} = {total}.",
                        cuenta=f"{entre_parentesis(dg)}*{entre_parentesis(h)} + {entre_parentesis(g)}*"
                               f"{entre_parentesis(cadena)}", total=texto(total)),),
            queda=texto(total)))
        return pasos, total

    def _explicar(self, izquierda, derecha, x, y, yp, avisos) -> Tuple[List[PasoCalculo], Any, str]:
        pasos = [PasoCalculo(
            tr("Planteamiento"),
            regla=tr("en la derivación implícita, {y} es una función de {x} aunque no esté despejada. Se derivan los dos "
                     "lados de la ecuación respecto a {x}; cada vez que se deriva algo con {y}, la regla de la cadena "
                     "añade el factor {yp} = d{y}/d{x}. Al final se despeja {yp}.", x=x, y=y, yp=yp),
            partes=tr("la ecuación es {ecuacion}; lado izquierdo: {izquierda}; lado derecho: {derecha}.",
                      ecuacion=f"{texto(izquierda)} = {texto(derecha)}",
                      izquierda="; ".join(texto(t) for t in _terminos(izquierda)) or "0",
                      derecha="; ".join(texto(t) for t in _terminos(derecha)) or "0"),
            queda=tr("derivar cada término respecto a {x}", x=x))]

        derivadas = []
        for lado, expr in ((tr("izquierdo"), izquierda), (tr("derecho"), derecha)):
            resultados, lineas = [], []
            for t in _terminos(expr):
                sub, d = self._termino(t, x, y, yp, avisos)
                pasos.extend(sub)
                resultados.append(d)
                if not t.has(x) and not t.has(y):
                    lineas.append(tr("{termino} es una constante: su derivada es 0.", termino=texto(t)))
                else:
                    lineas.append(f"d/d{x}({texto(t)}) = {texto(d)}.")
            total = sympy.Add(*resultados) if resultados else sympy.Integer(0)
            derivadas.append(total)
            pasos.append(PasoCalculo(
                tr("Derivada del lado {lado}", lado=lado),
                regla=tr("la derivada de una suma es la suma de las derivadas de sus términos."),
                partes=tr("el lado {lado} es {expresion}.", lado=lado, expresion=texto(expr)),
                calculo=tuple(lineas) or (tr("Es 0: su derivada es 0."),),
                queda=suma_texto([r for r in resultados if r != 0]) if any(r != 0 for r in resultados) else "0"))

        valor, final = self._despejar(derivadas[0], derivadas[1], yp, pasos)
        return pasos, valor, final

    def _despejar(self, izquierda: Any, derecha: Any, yp: Any, pasos: List[PasoCalculo]) -> Tuple[Any, str]:
        """Despeja y' de la ecuación (lineal en y'), con cada transformación."""
        lineas = []
        izq_t, der_t = _terminos(izquierda), _terminos(derecha)
        con = _ordenados([t for t in izq_t if t.has(yp)] + [-t for t in der_t if t.has(yp)])
        sin = _ordenados([t for t in der_t if not t.has(yp)] + [-t for t in izq_t if not t.has(yp)])
        for t in der_t:
            if t.has(yp):
                lineas.append(_pasar(t, tr("izquierda")))
        for t in izq_t:
            if not t.has(yp):
                lineas.append(_pasar(t, tr("derecha")))
        lado_der = suma_texto(sin) if sin else "0"
        lineas.append(tr("Queda {ecuacion}.", ecuacion=f"{suma_texto(con)} = {lado_der}"))
        coeficientes = [sympy.expand(t / yp) for t in con]
        if sympy.Add(*coeficientes) == 0:
            raise SinExplicacion()
        if len(con) > 1:
            lineas.append(tr("Sacamos {yp} factor común: {suma} = {yp}*({coeficiente}).", yp=yp, suma=suma_texto(con),
                             coeficiente=suma_texto(coeficientes)))

        def cociente(arriba: List[Any], abajo: List[Any]) -> str:
            """'(6*y - 3*x^2)/(3*y^2 - 6*x)' en el orden en que se escribieron los términos."""
            if not arriba:
                return "0"
            if len(arriba) == 1 and len(abajo) == 1:
                return texto(arriba[0] / abajo[0]) if abajo[0] != 1 else texto(arriba[0])
            if len(arriba) > 1 and all(t.could_extract_minus_sign() for t in arriba):
                return "-" + cociente([-t for t in arriba], abajo)  # -(2*x*y^3 + 1)/(...)
            simple = len(arriba) == 1 and not arriba[0].could_extract_minus_sign() and arriba[0].is_Mul \
                and sympy.fraction(arriba[0])[1] == 1
            num = f"({suma_texto(arriba)})" if len(arriba) > 1 else (texto(arriba[0]) if simple
                                                                     else entre_parentesis(arriba[0]))
            den = f"({suma_texto(abajo)})" if len(abajo) > 1 else entre_parentesis(abajo[0])
            return num if abajo == [1] else f"{num}/{den}"

        coeficientes = _ordenados(coeficientes)
        coef_txt = suma_texto(coeficientes)
        division = ((f"({suma_texto(sin)})" if len(sin) > 1 else (entre_parentesis(sin[0]) if sin else "0")) + "/"
                    + (f"({coef_txt})" if len(coeficientes) > 1 else entre_parentesis(coeficientes[0])))
        lineas.append(tr("Dividimos los dos lados entre {coeficiente} (suponiendo que no vale 0): {yp} = {division}.",
                         coeficiente=coef_txt, yp=yp, division=division))
        final = division
        if sin and any(sympy.fraction(t)[1].free_symbols for t in sin + coeficientes):
            # Con fracciones (x/y = 3): dividir entre una fracción es multiplicar por su inverso
            divisor = sympy.Add(*coeficientes)
            inverso = sympy.simplify(1 / divisor)
            valor = sympy.simplify(sympy.Add(*sin) * inverso)
            linea = tr("Dividir entre {divisor} es multiplicar por su inverso, {inverso}: {producto} = {valor}.",
                       divisor=texto(divisor), inverso=texto(inverso), valor=texto(valor),
                       producto=f"{entre_parentesis(sympy.Add(*sin))}*{entre_parentesis(inverso)}")
            lineas.append(linea)
            return self._paso_despejar(izquierda, derecha, yp, lineas, texto(valor), pasos, valor), texto(valor)
        comun = sympy.gcd(sympy.Add(*sin), sympy.Add(*coeficientes)) if sin else sympy.Integer(1)
        if comun not in (1, -1):
            sin = [sympy.expand(t / comun) for t in sin]
            coeficientes = [sympy.expand(c / comun) for c in coeficientes]
            final = cociente(sin, coeficientes)
            lineas.append(tr("El numerador y el denominador tienen el factor común {comun}: se simplifica.",
                             comun=texto(comun)))
            lineas.append(f"{yp} = {final}.")
        if coeficientes[0].could_extract_minus_sign() and len(coeficientes) > 1:
            sin, coeficientes = [-t for t in sin], [-c for c in coeficientes]
            final = cociente(sin, coeficientes)
            lineas.append(tr("Multiplicamos arriba y abajo por -1 para que el denominador no empiece con signo menos."))
            lineas.append(f"{yp} = {final}.")
        simple = cociente(sin, coeficientes)
        if simple != final:
            lineas.append(f"{yp} = {simple}.")
            final = simple
        valor = sympy.Add(*sin) / sympy.Add(*coeficientes) if sin else sympy.Integer(0)
        return self._paso_despejar(izquierda, derecha, yp, lineas, final, pasos, valor), final

    @staticmethod
    def _paso_despejar(izquierda, derecha, yp, lineas, final, pasos, valor=None) -> Any:
        """Añade el paso 'Despejar y'' y devuelve el valor de y' (el de final si no se da)."""
        pasos.append(PasoCalculo(
            tr("Despejar {yp}", yp=yp),
            regla=tr("la ecuación derivada es de primer grado en {yp}: se pasan los términos con {yp} a un lado y los "
                     "demás al otro, se saca {yp} factor común y se divide entre lo que lo multiplica.", yp=yp),
            partes=tr("la ecuación derivada es {ecuacion}.", ecuacion=f"{texto(izquierda)} = {texto(derecha)}"),
            calculo=tuple(lineas),
            queda=f"{yp} = {final}"))
        return valor
