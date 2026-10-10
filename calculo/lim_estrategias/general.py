"""
Modo General: los límites que no resuelve ninguna estrategia concreta, explicados con el
mismo formato que el resto (Regla, En este caso, cuentas, Queda).

Sigue el orden de clase:
  1. En un punto finito sin lado, si los límites laterales no coinciden (abs(x)/x) o el
     límite es infinito con signos distintos (1/x), se estudia cada lado.
  2. Sustituir: si la función es continua en el punto, el límite es su valor.
  3. Según la forma que salga:
       - 0/0 o ∞/∞: regla de L'Hôpital (derivadas del numerador y del denominador);
       - k/0: crece sin límite, con el signo de numerador y denominador a ese lado;
       - 1^∞, 0^0, ∞^0: f^g = exp(g*log(f)), y el límite del exponente;
       - 0*∞: se escribe como cociente; ∞ - ∞: como una sola fracción;
       - un polinomio en el infinito: su término de mayor grado.
  4. Si nada de eso se aplica, el límite de funciones conocidas (exp(-x) → 0 en oo).

El valor siempre es el de SymPy: la explicación solo se muestra si llega a él.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

import sympy
from sympy import S

from calculo.pasos import PasoCalculo, entre_parentesis, texto
from i18n import N_, tr

from ._base import es_punto_finito, limite_seguro
from ._pasos import (FORMA_CERO_CERO, FORMA_INF_INF, FORMA_K_CERO, cuenta, es_infinito, forma_del_cociente,
                     paso_evaluacion, paso_sustitucion, tendencia, valor_texto)

SUSTITUCION = N_("sustitución directa")
LHOPITAL = N_("regla de L'Hôpital")
LATERALES = N_("límites laterales")
EXPONENCIAL = N_("forma exponencial")
PRINCIPAL = N_("término de mayor grado")
DIRECTO = N_("límite de funciones conocidas")

MAX_LHOPITAL = 4


class SinExplicacion(Exception):
    pass


def equivalentes(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return False
    if a in (S.Infinity, S.NegativeInfinity, sympy.nan, sympy.zoo) or b in (S.Infinity, S.NegativeInfinity, sympy.nan, sympy.zoo):
        return a == b
    try:
        return sympy.simplify(a - b) == 0
    except Exception:
        return False


def signo_cerca(expr: Any, var: sympy.Symbol, punto: Any, lado: str) -> int:
    """Signo de expr un poco a la izquierda ('-') o a la derecha ('+') del punto (0 si no se sabe)."""
    for h in (1e-6, 1e-4):
        try:
            x0 = float(punto) + (h if lado == "+" else -h)
            valor = complex(sympy.N(expr.subs(var, x0)))
        except Exception:
            continue
        if abs(valor.imag) > 1e-9 or valor.real == 0:
            continue
        return 1 if valor.real > 0 else -1
    return 0


class LimiteGeneral:
    def explicar(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str],
                 valor: Any) -> Optional[Tuple[List[PasoCalculo], str]]:
        """(pasos, técnica principal) que llegan a valor, o None si no se puede explicar."""
        self.pasos: List[PasoCalculo] = []
        try:
            tecnica, obtenido = self._limite(expr, var, punto, dir_, profundidad=0)
        except Exception:
            return None
        if not self.pasos or not equivalentes(obtenido, valor):
            return None
        return self.pasos, tecnica

    # ---------------- Selección del método ----------------

    def _limite(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str], profundidad: int) -> Tuple[str, Any]:
        if profundidad > 8:
            raise SinExplicacion()

        # 1) Punto finito sin lado: si los laterales no coinciden, cada lado por separado
        if es_punto_finito(punto) and dir_ is None:
            bilateral = limite_seguro(expr, var, punto)
            if bilateral is sympy.nan or bilateral is sympy.zoo:
                return self._laterales(expr, var, punto, profundidad)

        # 2) Una constante (tras L'Hôpital, por ejemplo), o sustitución directa
        if not expr.has(var):
            self.pasos.append(PasoCalculo(
                tr("Límite de una constante"),
                regla=tr("una constante no depende de la variable: su límite es ella misma."),
                partes=tr("buscamos el límite de {expresion} cuando {tendencia}.", expresion=texto(expr),
                          tendencia=tendencia(var, punto, dir_)),
                queda=valor_texto(expr)))
            return DIRECTO, expr
        texto_cuenta = cuenta(expr, var, punto)
        if texto_cuenta is not None:
            valor = sympy.simplify(expr.subs(var, punto))
            self.pasos.append(PasoCalculo(
                tr("Sustitución directa"),
                regla=tr("si la función es continua en el punto (está definida ahí y no salta), el límite es su valor: "
                         "basta con sustituir."),
                partes=tr("buscamos el límite de {expresion} cuando {tendencia}.", expresion=texto(expr),
                          tendencia=tendencia(var, punto, dir_)),
                calculo=(tr("Sustituimos: {cuenta}.", cuenta=texto_cuenta),),
                queda=valor_texto(valor)))
            return SUSTITUCION, valor

        # 3) Valor absoluto a un lado del punto: se quita según el signo de lo de dentro
        if es_punto_finito(punto) and dir_ in ("+", "-") and expr.has(sympy.Abs):
            sin_abs = self._quitar_abs(expr, var, punto, dir_)
            if sin_abs is not None:
                return self._limite(sin_abs, var, punto, dir_, profundidad + 1)

        # 4) Cociente: L'Hôpital, k/0 o la regla del cociente
        num, den = sympy.together(expr).as_numer_denom()
        if den.has(var):
            num_lim = limite_seguro(num, var, punto, dir_)
            den_lim = limite_seguro(den, var, punto, dir_)
            forma = forma_del_cociente(num_lim, den_lim)
            if forma in (FORMA_CERO_CERO, FORMA_INF_INF):
                return self._lhopital(expr, num, den, var, punto, dir_, profundidad)
            if forma == FORMA_K_CERO:
                return self._k_entre_cero(expr, num, den, num_lim, var, punto, dir_)
            valor = limite_seguro(expr, var, punto, dir_)
            self.pasos.append(paso_evaluacion(expr, var, punto, dir_, valor))
            return DIRECTO, valor

        # 5) Potencia con la variable en el exponente: 1^∞, 0^0, ∞^0
        if expr.is_Pow and expr.exp.has(var):
            return self._exponencial(expr, var, punto, dir_, profundidad)

        # 6) Producto 0*∞ y suma ∞ - ∞
        if expr.is_Mul:
            cociente = self._producto_cero_por_infinito(expr, var, punto, dir_)
            if cociente is not None:
                return self._lhopital(expr, *cociente, var, punto, dir_, profundidad + 1, sustituir=False)
        if expr.is_Add:
            reescrita = self._resta_de_infinitos(expr, var, punto, dir_)
            if reescrita is not None:
                return self._limite(reescrita, var, punto, dir_, profundidad + 1)

        # 7) Polinomio en el infinito: manda el término de mayor grado
        if es_infinito(punto) and expr.is_polynomial(var):
            return self._termino_principal(expr, var, punto)

        # 8) Funciones conocidas (exp(-x) en oo...)
        valor = limite_seguro(expr, var, punto, dir_)
        if valor is None or isinstance(valor, sympy.Limit):
            raise SinExplicacion()
        self.pasos.append(paso_evaluacion(expr, var, punto, dir_, valor))
        return DIRECTO, valor

    # ---------------- Métodos ----------------

    def _laterales(self, expr: Any, var: sympy.Symbol, punto: Any, profundidad: int) -> Tuple[str, Any]:
        valores = {}
        for lado in ("-", "+"):
            _, valores[lado] = self._limite(expr, var, punto, lado, profundidad + 1)
        izquierda, derecha = valores["-"], valores["+"]
        calculo = [tr("Por la izquierda ({tendencia}): {valor}.", tendencia=tendencia(var, punto, "-"),
                      valor=valor_texto(izquierda)),
                   tr("Por la derecha ({tendencia}): {valor}.", tendencia=tendencia(var, punto, "+"),
                      valor=valor_texto(derecha))]
        if equivalentes(izquierda, derecha):
            resultado = izquierda
            calculo.append(tr("Coinciden: el límite existe y vale {valor}.", valor=valor_texto(resultado)))
        elif {izquierda, derecha} == {S.Infinity, S.NegativeInfinity}:
            resultado = sympy.zoo
            calculo.append(tr("Uno es +oo y el otro -oo: el límite no existe (diverge a infinitos de distinto signo)."))
        else:
            resultado = sympy.nan
            calculo.append(tr("No coinciden: el límite no existe."))
        self.pasos.append(PasoCalculo(
            tr("Comparar los límites laterales"),
            regla=tr("el límite en un punto existe solo si el límite por la izquierda y el límite por la derecha "
                     "existen y coinciden."),
            partes=tr("se han calculado los dos lados de {variable} = {punto} en los pasos anteriores.",
                      variable=var, punto=punto),
            calculo=tuple(calculo),
            queda=valor_texto(resultado)))
        return LATERALES, resultado

    def _quitar_abs(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: str) -> Optional[Any]:
        cambios = {}
        lineas = []
        for absoluto in expr.atoms(sympy.Abs):
            dentro = absoluto.args[0]
            signo = signo_cerca(dentro, var, punto, dir_)
            if signo == 0:
                return None
            cambios[absoluto] = dentro if signo > 0 else -dentro
            lineas.append(tr("{dentro} es {signo} cerca de {punto} por la {lado}, así que {absoluto} = {sin_abs}.",
                             dentro=texto(dentro), signo=tr("positivo") if signo > 0 else tr("negativo"), punto=punto,
                             lado=tr("derecha") if dir_ == "+" else tr("izquierda"), absoluto=texto(absoluto),
                             sin_abs=texto(cambios[absoluto])))
        sin_abs = sympy.simplify(expr.xreplace(cambios))
        # Sin evaluar (xreplace daría ya -x/x = -1): el texto con cada |u| cambiado
        antes = texto(expr)
        for absoluto, nuevo in cambios.items():
            antes = antes.replace(texto(absoluto), entre_parentesis(nuevo))
        lineas.append(tr("La expresión queda {antes} = {despues}.", antes=antes, despues=texto(sin_abs))
                      if antes != texto(sin_abs) else tr("La expresión queda {despues}.", despues=texto(sin_abs)))
        self.pasos.append(PasoCalculo(
            tr("Quitar el valor absoluto"),
            regla=tr("|u| = u si u es positivo y |u| = -u si u es negativo: a un lado del punto, el signo de u se "
                     "conoce y el valor absoluto se puede quitar."),
            partes=tr("buscamos el límite de {expresion} cuando {tendencia}.", expresion=texto(expr),
                      tendencia=tendencia(var, punto, dir_)),
            calculo=tuple(lineas),
            queda=tr("lim {expresion} cuando {tendencia}", expresion=texto(sin_abs), tendencia=tendencia(var, punto, dir_))))
        return sin_abs

    def _lhopital(self, expr: Any, num: Any, den: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str],
                  profundidad: int, sustituir: bool = True) -> Tuple[str, Any]:
        """sustituir: mostrar antes la sustitución (no tras reescribir un 0*∞, que ya dice a qué tiende cada parte)."""
        if profundidad >= MAX_LHOPITAL + 2:
            raise SinExplicacion()
        if sustituir:
            paso, forma = paso_sustitucion(expr, var, punto, dir_)
            if paso:
                self.pasos.append(paso)
        else:
            forma = forma_del_cociente(limite_seguro(num, var, punto, dir_), limite_seguro(den, var, punto, dir_))
            if forma not in (FORMA_CERO_CERO, FORMA_INF_INF):
                raise SinExplicacion()
        d_num, d_den = sympy.diff(num, var), sympy.diff(den, var)
        if d_den == 0:
            raise SinExplicacion()
        nuevo = sympy.cancel(d_num / d_den) if (d_num / d_den).is_rational_function(var) else sympy.simplify(d_num / d_den)
        cociente = f"{entre_parentesis(d_num)}/{entre_parentesis(d_den)}"
        calculo = [tr("Derivamos el numerador: ({f})' = {derivada}.", f=texto(num), derivada=texto(d_num)),
                   tr("Derivamos el denominador: ({g})' = {derivada}.", g=texto(den), derivada=texto(d_den)),
                   tr("El nuevo cociente es {cociente}.", cociente=cociente)]
        if texto(nuevo) != cociente and texto(nuevo) != texto(d_num / d_den):
            calculo.append(tr("Simplificamos: {antes} = {despues}.", antes=cociente, despues=texto(nuevo)))
        self.pasos.append(PasoCalculo(
            tr("Regla de L'Hôpital"),
            regla=tr("si al sustituir sale 0/0 o ∞/∞, el límite de f/g es el mismo que el de f'/g', el cociente "
                     "de las derivadas (si este existe). Se deriva el numerador y el denominador por separado, "
                     "no como un cociente."),
            partes=tr("la forma es {forma}, con f = {f} (numerador) y g = {g} (denominador).", forma=forma,
                      f=texto(num), g=texto(den)),
            calculo=tuple(calculo),
            queda=tr("lim {expresion} cuando {tendencia}", expresion=texto(nuevo), tendencia=tendencia(var, punto, dir_))))
        _, valor = self._limite(nuevo, var, punto, dir_, profundidad + 1)
        return LHOPITAL, valor

    def _k_entre_cero(self, expr: Any, num: Any, den: Any, num_lim: Any, var: sympy.Symbol, punto: Any,
                      dir_: Optional[str]) -> Tuple[str, Any]:
        signo_num = 1 if num_lim.is_positive else -1 if num_lim.is_negative else 0
        # Sin lado (1/x^2 en 0), los dos: el denominador debe tener el mismo signo a ambos lados
        lados = (dir_,) if dir_ in ("+", "-") else ("-", "+")
        signos_den = [signo_cerca(den, var, punto, lado) for lado in lados]
        if signo_num == 0 or 0 in signos_den or len(set(signos_den)) > 1:
            raise SinExplicacion()  # signos distintos a cada lado: lo resuelven los laterales
        signo_den = signos_den[0]
        valor = S.Infinity if signo_num * signo_den > 0 else S.NegativeInfinity
        lado = (tr("derecha") if dir_ == "+" else tr("izquierda")) if len(lados) == 1 else tr("izquierda y por la derecha")
        self.pasos.append(PasoCalculo(
            tr("Número entre cero"),
            regla=tr("un número distinto de 0 dividido entre algo que tiende a 0 crece sin límite: el resultado es "
                     "+oo o -oo según los signos del numerador y del denominador (más entre más, o menos entre "
                     "menos, da +oo; con signos distintos, -oo)."),
            partes=tr("buscamos el límite de {expresion} cuando {tendencia}.", expresion=texto(expr),
                      tendencia=tendencia(var, punto, dir_)),
            calculo=(tr("El numerador, {num}, tiende a {valor}, que es {signo}.", num=texto(num), valor=valor_texto(num_lim),
                        signo=tr("positivo") if signo_num > 0 else tr("negativo")),
                     tr("El denominador, {den}, tiende a 0 con valores {signo} por la {lado}.", den=texto(den),
                        signo=tr("positivos") if signo_den > 0 else tr("negativos"), lado=lado),
                     tr("{signo_num} entre {signo_den}: {valor}.", signo_num=tr("Positivo") if signo_num > 0 else tr("Negativo"),
                        signo_den=tr("positivo") if signo_den > 0 else tr("negativo"), valor=valor_texto(valor))),
            queda=valor_texto(valor)))
        return LATERALES, valor

    def _exponencial(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str],
                     profundidad: int) -> Tuple[str, Any]:
        base, exponente = expr.as_base_exp()
        lim_base = limite_seguro(base, var, punto, dir_)
        lim_exp = limite_seguro(exponente, var, punto, dir_)
        if lim_base is None or lim_exp is None:
            raise SinExplicacion()
        logaritmo = exponente * sympy.log(base)
        # 1/x en 0 tiende a infinito con signo distinto a cada lado (zoo): también es 1^∞
        if lim_base == 1 and (es_infinito(lim_exp) or lim_exp is sympy.zoo):
            forma = "1^∞"
        elif lim_base == 0 and lim_exp == 0:
            forma = "0^0"
        elif es_infinito(lim_base) and lim_exp == 0:
            forma = "∞^0"
        else:
            raise SinExplicacion()  # sin indeterminación: lo cubre el límite de funciones conocidas
        self.pasos.append(PasoCalculo(
            tr("Forma exponencial"),
            regla=tr("una potencia f^g se puede escribir como exp(g*log(f)). Como exp es continua, el límite es exp "
                     "del límite de g*log(f), que ya no es una potencia."),
            partes=tr("la base f = {f} tiende a {lf} y el exponente g = {g} tiende a {lg}: forma {forma}, "
                      "indeterminada.", f=texto(base), lf=valor_texto(lim_base), g=texto(exponente),
                      lg=valor_texto(lim_exp), forma=forma),
            calculo=(tr("Reescribimos: {expresion} = exp({exponente}).", expresion=texto(expr), exponente=texto(logaritmo)),),
            queda=tr("exp(lim {exponente} cuando {tendencia})", exponente=texto(logaritmo),
                     tendencia=tendencia(var, punto, dir_))))
        _, valor_exponente = self._limite(logaritmo, var, punto, dir_, profundidad + 1)
        valor = sympy.exp(valor_exponente) if not es_infinito(valor_exponente) else (
            S.Infinity if valor_exponente == S.Infinity else S.Zero)
        self.pasos.append(PasoCalculo(
            tr("Volver a la potencia"),
            regla=tr("el límite de la potencia es exp del límite del exponente (exp(oo) = oo y exp(-oo) = 0)."),
            partes=tr("el límite de {exponente} es {valor}.", exponente=texto(logaritmo), valor=valor_texto(valor_exponente)),
            calculo=(tr("exp({valor}) = {resultado}.", valor=valor_texto(valor_exponente), resultado=valor_texto(valor)),),
            queda=valor_texto(valor)))
        return EXPONENCIAL, valor

    def _producto_cero_por_infinito(self, expr: Any, var: sympy.Symbol, punto: Any,
                                    dir_: Optional[str]) -> Optional[Tuple[Any, Any]]:
        """(numerador, denominador) del cociente equivalente a un producto 0*∞, o None."""
        factores = expr.as_ordered_factors()
        limites = [limite_seguro(f, var, punto, dir_) for f in factores]
        ceros = [f for f, l in zip(factores, limites) if l == 0]
        infinitos = [f for f, l in zip(factores, limites) if es_infinito(l)]
        if not ceros or not infinitos:
            return None
        cero = sympy.Mul(*ceros)
        resto = sympy.Mul(*[f for f in factores if f not in ceros])
        # Qué factor baja como 1/(...): el que deja un cociente fácil de derivar. Un logaritmo va
        # arriba (x*log(x) = log(x)/(1/x)); una potencia de x baja (x*log(1 + 1/x) = log(1 + 1/x)/(1/x));
        # una exponencial que tiende a 0 baja como exp(+...) (x*exp(-x) = x/exp(x))
        algebraico = resto.is_polynomial(var) or (resto.is_Pow and resto.base == var)
        if not cero.has(sympy.exp) and algebraico:
            num, den = cero, 1 / resto
        else:
            num, den = resto, 1 / cero
        cociente = f"{entre_parentesis(num)}/{entre_parentesis(den)}"
        self.pasos.append(PasoCalculo(
            tr("Forma 0*∞"),
            regla=tr("un producto en el que un factor tiende a 0 y otro a infinito es indeterminado: se escribe como "
                     "cociente, a*b = a/(1/b), para llegar a 0/0 o ∞/∞."),
            partes=tr("{cero} tiende a 0 y {infinito} tiende a infinito.", cero=texto(cero),
                      infinito=texto(sympy.Mul(*infinitos))),
            calculo=(tr("Reescribimos: {expresion} = {cociente}.", expresion=texto(expr), cociente=cociente),),
            queda=tr("lim {expresion} cuando {tendencia}", expresion=cociente, tendencia=tendencia(var, punto, dir_))))
        return num, den

    def _resta_de_infinitos(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str]) -> Optional[Any]:
        limites = [limite_seguro(t, var, punto, dir_) for t in expr.args]
        if not (S.Infinity in limites and S.NegativeInfinity in limites):
            return None
        junta = sympy.together(expr)
        if not sympy.fraction(junta)[1].has(var):
            junta = sympy.factor(expr)
            if junta == expr:
                return None
        self.pasos.append(PasoCalculo(
            tr("Forma ∞ - ∞"),
            regla=tr("una resta de dos cantidades que crecen sin límite es indeterminada: se escribe como una sola "
                     "fracción (o se saca factor común) para ver cuál crece más deprisa."),
            partes=tr("buscamos el límite de {expresion} cuando {tendencia}.", expresion=texto(expr),
                      tendencia=tendencia(var, punto, dir_)),
            calculo=(tr("Reescribimos: {antes} = {despues}.", antes=texto(expr), despues=texto(junta)),),
            queda=tr("lim {expresion} cuando {tendencia}", expresion=texto(junta), tendencia=tendencia(var, punto, dir_))))
        return junta

    def _termino_principal(self, expr: Any, var: sympy.Symbol, punto: Any) -> Tuple[str, Any]:
        grado = int(sympy.degree(expr, var))
        coeficiente = sympy.LC(expr, var)
        if grado < 1:
            raise SinExplicacion()
        principal = coeficiente * var ** grado
        if grado % 2 == 0 or punto == S.Infinity:
            signo_potencia = 1
        else:
            signo_potencia = -1
        signo = signo_potencia * (1 if coeficiente.is_positive else -1 if coeficiente.is_negative else 0)
        if signo == 0:
            raise SinExplicacion()
        valor = S.Infinity if signo > 0 else S.NegativeInfinity
        paridad = tr("par") if grado % 2 == 0 else tr("impar")
        self.pasos.append(PasoCalculo(
            tr("Término de mayor grado"),
            regla=tr("cuando {x} → ±∞, un polinomio se comporta como su término de mayor grado, porque los demás "
                     "crecen más despacio.", x=var),
            partes=tr("el término de mayor grado de {expresion} es {principal}.", expresion=texto(expr),
                      principal=texto(principal)),
            calculo=(tr("{x}^{n} tiene exponente {paridad}: cuando {tendencia} es {signo}.", x=var, n=grado, paridad=paridad,
                        tendencia=tendencia(var, punto), signo=tr("positivo") if signo_potencia > 0 else tr("negativo")),
                     tr("Por el coeficiente {c}: el límite es {valor}.", c=texto(coeficiente), valor=valor_texto(valor))),
            queda=valor_texto(valor)))
        return PRINCIPAL, valor
