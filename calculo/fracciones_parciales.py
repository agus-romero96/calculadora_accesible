"""
Integración de funciones racionales por fracciones parciales, explicada con el formato de
calculo/pasos.py (Regla, En este caso, las cuentas y Queda):

  1. Grados: si el grado del numerador es mayor o igual que el del denominador, se dividen
     los polinomios (cada término del cociente, cada producto y cada resta) y queda
     cociente + resto/denominador.
  2. El denominador, factorizado con los pasos de Factorizar, y el tipo de cada factor:
     lineal, lineal repetido o cuadrático irreducible (con su discriminante).
  3. El planteamiento con coeficientes indeterminados (A/(x - a) + B/(x - a)^2 + (C*x + D)/(...)).
  4. Multiplicar por el denominador común; los coeficientes se hallan sustituyendo las raíces
     de los factores lineales (todos los términos menos uno se anulan) y, los que falten,
     igualando los coeficientes de cada potencia de x y despejando ecuación a ecuación.
  5. La integral de cada fracción simple: logaritmo, potencia, o logaritmo y arcotangente
     (completando el cuadrado) para los factores cuadráticos.

Calculo comprueba derivando que la primitiva es correcta y que coincide con la de SymPy
(salvo una constante) antes de mostrar los pasos.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import sympy
from sympy import S, Symbol

from algebra.ecuaciones import despejar, sustituir
from calculo.derivadas import Regla
from calculo.pasos import PasoCalculo, entre_parentesis, suma_texto, texto
from i18n import N_, tr
from pasos_aritmetica import ExplicadorFactorizar
from pasos_aritmetica import SinExplicacion as SinFactorizacion

FRACCIONES_PARCIALES = Regla(N_("Fracciones parciales"), N_("Fracciones parciales"), "")

LETRAS = "ABCDEFGHIJKLMNPQRS"


class SinExplicacion(Exception):
    """La función no se descompone con los casos de clase: se explica con las reglas de SymPy."""


def aplica(f: Any, x: Symbol) -> bool:
    """
    Si conviene explicar f por fracciones parciales: un cociente de polinomios cuya
    descomposición tiene más de un término (o que necesita dividir antes). Si el numerador es
    un múltiplo de la derivada del denominador, el cambio de variable es más directo.
    """
    try:
        if not f.is_rational_function(x):
            return False
        num, den = sympy.fraction(sympy.cancel(sympy.together(f)))
        if not den.has(x):
            return False
        if num.is_polynomial(x) and sympy.degree(num, x) < sympy.degree(den, x):
            cociente = sympy.cancel(num / sympy.diff(den, x))
            if not cociente.has(x):
                return False  # f = c*Q'/Q: cambio de variable u = Q
        if _cuadratica_sola(num, den, x):
            # (M*x + N)/(x^2 + p*x + q) sin raíces reales: logaritmo y arcotangente completando el cuadrado.
            # 1/(x^2 + k) ya es de la tabla
            p = sympy.Poly(den, x).monic().all_coeffs()[1]
            return p != 0 or num.has(x)
        return len(sympy.Add.make_args(sympy.apart(f, x))) > 1
    except Exception:
        return False


def _cuadratica_sola(num: Any, den: Any, x: Symbol) -> bool:
    """Si num/den ya es una fracción simple: denominador cuadrático sin raíces reales y numerador de grado <= 1."""
    if sympy.degree(den, x) != 2 or (num.has(x) and sympy.degree(num, x) > 1):
        return False
    a, b, c = sympy.Poly(den, x).all_coeffs()
    return b ** 2 - 4 * a * c < 0


class ExplicadorFracciones:
    def __init__(self, var: Symbol):
        self.x = var
        self.pasos: List[PasoCalculo] = []

    @property
    def principal(self) -> Regla:
        return FRACCIONES_PARCIALES

    def _paso(self, titulo: str, regla: str = "", partes: str = "", calculo=(), queda: str = "") -> None:
        self.pasos.append(PasoCalculo(titulo, regla=regla, partes=partes, calculo=tuple(calculo), queda=queda))

    # ---------------- Fachada ----------------

    def explicar(self, f: Any) -> Any:
        """Añade los pasos y devuelve la primitiva (sin + C)."""
        x = self.x
        num, den = sympy.fraction(sympy.cancel(sympy.together(f)))
        num, den = sympy.expand(num), sympy.expand(den)
        integral = f"∫ {entre_parentesis(f)} d{x}" if not f.is_Add else f"∫ ({texto(f)}) d{x}"
        self._simplificar(f, num, den)

        if _cuadratica_sola(num, den, x):
            lc = sympy.Poly(den, x).LC()
            base = sympy.expand(den / lc)
            numerador = sympy.expand(num / lc)
            self._paso(tr("Fracción simple con un factor cuadrático"),
                       regla=tr("si el denominador es de grado 2 sin raíces reales y el numerador de grado menor, la "
                                "fracción ya es simple: se separa en la parte que es derivada del denominador (da un "
                                "logaritmo) y un número entre el denominador (da una arcotangente, completando el "
                                "cuadrado)."),
                       partes=tr("el denominador es {den}.", den=texto(den)),
                       calculo=((tr("El número {lc} del denominador pasa al numerador dividiendo: {fraccion}.", lc=texto(lc),
                                    fraccion=self._fraccion_texto(numerador, base, 1)),) if lc != 1 else ()),
                       queda=f"{integral} = ∫ {self._fraccion_texto(numerador, base, 1)} d{x}")
            return self._integrar(S.Zero, [(numerador, base, 1)])

        cociente, resto = self._division(num, den)
        lc, factores = sympy.factor_list(den, x)
        if len(factores) == 1 and factores[0][1] == 1 and sympy.degree(factores[0][0], x) == 1:
            # x + 1/x: el resto entre un solo factor lineal ya es una fracción simple
            base = factores[0][0]
            self._paso(tr("Fracción simple"),
                       regla=tr("si el denominador es un solo factor lineal, la fracción que queda ya es simple: no hay "
                                "nada que descomponer."),
                       partes=tr("el denominador es {den}.", den=texto(den)),
                       queda=f"{integral} = ∫ ({texto(cociente)} + {self._fraccion_texto(resto / lc, base, 1)}) d{x}")
            return self._integrar(cociente, [(sympy.simplify(resto / lc), base, 1)])
        lc, factores = self._factorizar(den)
        terminos, letras = self._planteamiento(resto, den, lc, factores)
        valores = self._coeficientes(resto / lc, factores, terminos, letras)
        simples = [(sympy.simplify(c.subs(valores)), base, k) for c, base, k in terminos]
        fraccion_txt = " + ".join(self._fraccion_texto(c, base, k) for c, base, k in simples)
        total_txt = (f"{texto(cociente)} + " if cociente != 0 else "") + fraccion_txt
        self._paso(tr("Descomposición en fracciones simples"),
                   regla=tr("con los coeficientes ya hallados, la función queda escrita como suma de fracciones simples, "
                            "que se integran una a una."),
                   partes=", ".join(f"{l} = {texto(valores[l])}" for l in letras) + ".",
                   calculo=(f"{texto(f)} = {total_txt}.",),
                   queda=f"{integral} = ∫ ({total_txt}) d{x}")
        return self._integrar(cociente, simples)

    # ---------------- 0. Simplificar la fracción ----------------

    def _simplificar(self, f: Any, num: Any, den: Any) -> None:
        """Si numerador y denominador tienen un factor común, se cancela antes (y se dice)."""
        x = self.x
        num0, den0 = sympy.fraction(sympy.together(f))
        num0, den0 = sympy.expand(num0), sympy.expand(den0)
        comun = sympy.gcd(num0, den0)
        if not comun.has(x):
            return
        self._paso(tr("Simplificar la fracción"),
                   regla=tr("si el numerador y el denominador tienen un factor común, se cancela: la fracción vale lo "
                            "mismo (salvo donde ese factor vale 0) y las cuentas son más sencillas."),
                   partes=tr("la fracción es {fraccion}.", fraccion=f"{entre_parentesis(num0)}/{entre_parentesis(den0)}"),
                   calculo=(tr("Factorizamos: {num} = {num_f} y {den} = {den_f}.", num=texto(num0),
                               num_f=texto(sympy.factor(num0)), den=texto(den0), den_f=texto(sympy.factor(den0))),
                            tr("El factor común {comun} se cancela.", comun=texto(sympy.factor(comun)))),
                   queda=f"{entre_parentesis(num)}/{entre_parentesis(den)}")

    # ---------------- 1. Grados y división ----------------

    def _division(self, num: Any, den: Any) -> Tuple[Any, Any]:
        x = self.x
        gn, gd = sympy.degree(num, x), sympy.degree(den, x)
        if gn < gd:
            self._paso(tr("Comparar los grados"),
                       regla=tr("las fracciones parciales se aplican a una fracción propia: el grado del numerador debe "
                                "ser menor que el del denominador. Si no, antes se dividen los polinomios."),
                       partes=tr("el numerador {num} tiene grado {gn} y el denominador {den} tiene grado {gd}.",
                                 num=texto(num), gn=gn, den=texto(den), gd=gd),
                       calculo=(tr("{gn} < {gd}: la fracción ya es propia, no hace falta dividir.", gn=gn, gd=gd),),
                       queda=tr("se descompone {fraccion} directamente", fraccion=f"{entre_parentesis(num)}/{entre_parentesis(den)}"))
            return S.Zero, num
        lineas = []
        resto, cociente = num, S.Zero
        lider_den = sympy.LT(den, x)
        while resto != 0 and sympy.degree(resto, x) >= gd:
            termino = sympy.simplify(sympy.LT(resto, x) / lider_den)
            producto = sympy.expand(termino * den)
            nuevo = sympy.expand(resto - producto)
            lineas.append(tr("Dividimos {a} entre {b}: {t}. Multiplicamos {tp}*{den} = {producto}. Restamos: "
                             "{resto} - {producto_restado} = {nuevo}.", a=texto(sympy.LT(resto, x)), b=texto(lider_den),
                             t=texto(termino), tp=entre_parentesis(termino), den=entre_parentesis(den),
                             producto=texto(producto),
                             resto=f"({texto(resto)})" if resto.is_Add else texto(resto),
                             producto_restado=entre_parentesis(producto) if not producto.is_Pow else texto(producto),
                             nuevo=texto(nuevo)))
            cociente += termino
            resto = nuevo
        lineas.append(tr("El resto, {resto}, ya tiene grado menor que el divisor: cociente {c} y resto {resto}.",
                         resto=texto(resto), c=texto(cociente)))
        lineas.append(tr("Comprobación: {den}*{c} + {resto} = {num}.", den=entre_parentesis(den),
                         c=entre_parentesis(cociente), resto=entre_parentesis(resto),
                         num=texto(sympy.expand(den * cociente + resto))))
        queda = (f"{texto(cociente)} + {entre_parentesis(resto)}/{entre_parentesis(den)}" if resto != 0
                 else texto(cociente))
        self._paso(tr("Dividir los polinomios"),
                   regla=tr("si el grado del numerador es mayor o igual que el del denominador, se dividen: "
                            "P/Q = cociente + resto/Q, con el resto de grado menor que Q. En cada vuelta se divide el "
                            "término de mayor grado entre el del divisor, se multiplica y se resta."),
                   partes=tr("el numerador {num} tiene grado {gn} y el denominador {den} tiene grado {gd}: {gn} >= {gd}.",
                             num=texto(num), gn=gn, den=texto(den), gd=gd),
                   calculo=lineas, queda=queda)
        if resto == 0:
            raise SinExplicacion()  # división exacta: no hay fracciones (lo explican las reglas de SymPy)
        return cociente, resto

    # ---------------- 2. Factorizar el denominador ----------------

    def _factorizar(self, den: Any) -> Tuple[Any, List[Tuple[Any, int]]]:
        x = self.x
        lc, factores = sympy.factor_list(den, x)
        for base, _ in factores:
            grado = sympy.degree(base, x)
            if grado > 2:
                raise SinExplicacion()
            if grado == 2:
                a, b, c = sympy.Poly(base, x).all_coeffs()
                if b ** 2 - 4 * a * c >= 0:
                    raise SinExplicacion()  # x^2 - 2: raíces irracionales (no es de los casos de clase)
        factorizado = sympy.factor(den)
        if len(factores) > 1 or any(k > 1 for _, k in factores) or lc != 1:
            if texto(factorizado) != texto(den):
                explicador = ExplicadorFactorizar()
                try:
                    explicador.explicar(den)
                    self.pasos.extend(explicador.pasos)
                except SinFactorizacion:
                    pass
        lineas = []
        for base, k in factores:
            if sympy.degree(base, x) == 1:
                raiz = sympy.solve(base, x)[0]
                if k == 1:
                    lineas.append(tr("{factor}: lineal, se anula en {variable} = {raiz}; aporta una fracción "
                                     "c/({factor}), con un número c por hallar.", factor=texto(base), variable=x, raiz=texto(raiz)))
                else:
                    lineas.append(tr("({factor})^{k}: lineal repetido {k} veces (se anula en {variable} = {raiz}); aporta "
                                     "una fracción por cada potencia: {lista}.", factor=texto(base), k=k, variable=x,
                                     raiz=texto(raiz), lista=" + ".join(f"c{i}/({texto(base)})^{i}" if i > 1 else
                                                                        f"c{i}/({texto(base)})" for i in range(1, k + 1))))
            else:
                a, b, c = sympy.Poly(base, x).all_coeffs()
                delta = b ** 2 - 4 * a * c
                lineas.append(tr("{factor}: cuadrático irreducible (su discriminante es {cuenta} = {delta}, negativo: no "
                                 "tiene raíces reales); aporta (c*{variable} + d)/({factor}).", factor=texto(base),
                                 cuenta=f"{entre_parentesis(b)}^2 - 4*{entre_parentesis(a)}*{entre_parentesis(c)}",
                                 delta=texto(delta), variable=x))
        self._paso(tr("Tipos de factores del denominador"),
                   regla=tr("cada factor del denominador aporta fracciones simples: un factor lineal (x - a), "
                            "A/(x - a); uno repetido (x - a)^k, una fracción por cada potencia hasta k; uno cuadrático sin "
                            "raíces reales, (A*x + B)/(cuadrático)."),
                   partes=tr("el denominador factorizado es {factorizado}.", factorizado=texto(factorizado)),
                   calculo=lineas, queda=texto(factorizado))
        return lc, factores

    # ---------------- 3. Planteamiento ----------------

    def _planteamiento(self, resto, den, lc, factores) -> Tuple[List[Tuple[Any, Any, int]], List[Symbol]]:
        x = self.x
        letras: List[Symbol] = []

        def nueva() -> Symbol:
            letra = Symbol(LETRAS[len(letras)])
            letras.append(letra)
            return letra

        terminos = []  # (numerador con letras, base, potencia)
        for base, k in factores:
            if sympy.degree(base, x) == 1:
                for i in range(1, k + 1):
                    terminos.append((nueva(), base, i))
            else:
                for i in range(1, k + 1):
                    a, b = nueva(), nueva()
                    terminos.append((a * x + b, base, i))
        planteo = " + ".join(self._fraccion_texto(c, base, k) for c, base, k in terminos)
        izquierda = f"{entre_parentesis(resto)}/{entre_parentesis(sympy.factor(den))}"
        calculo = []
        if lc != 1:
            calculo.append(tr("El número {lc} del denominador pasa al numerador dividiendo: ({resto})/{lc} = {nuevo}.",
                              lc=texto(lc), resto=texto(resto), nuevo=texto(sympy.expand(resto / lc))))
        self._paso(tr("Planteamiento con coeficientes indeterminados"),
                   regla=tr("se escribe la fracción como suma de las fracciones simples que aportan sus factores, con "
                            "coeficientes desconocidos (letras mayúsculas) que hay que hallar."),
                   partes=tr("las incógnitas son {letras}.", letras=", ".join(l.name for l in letras)),
                   calculo=calculo, queda=f"{izquierda} = {planteo}")
        return terminos, letras

    def _fraccion_texto(self, numerador: Any, base: Any, k: int) -> str:
        num = entre_parentesis(numerador)  # (1/2)/(x - 1), no 1/2/(x - 1)
        den = entre_parentesis(base) if k == 1 else f"({texto(base)})^{k}"  # 1/x, 1/(x - 1), 1/(x - 1)^2
        if sympy.sympify(base).is_Symbol and k > 1:
            den = f"{texto(base)}^{k}"
        return f"{num}/{den}"

    # ---------------- 4. Coeficientes ----------------

    def _coeficientes(self, numerador, factores, terminos, letras) -> Dict[Symbol, Any]:
        x = self.x
        numerador = sympy.expand(numerador)
        comun = sympy.Mul(*[base ** k for base, k in factores])
        # numerador = suma de coef * (común / base^k)
        productos = [(c, sympy.cancel(comun / base ** k)) for c, base, k in terminos]
        derecha_txt = " + ".join(f"{entre_parentesis(c)}*{entre_parentesis(sympy.factor(m))}" if m != 1
                                 else entre_parentesis(c) for c, m in productos)
        self._paso(tr("Multiplicar por el denominador común"),
                   regla=tr("se multiplican los dos lados por el denominador común: desaparecen las fracciones y queda una "
                            "igualdad de polinomios que se cumple para todo {variable}.", variable=x),
                   partes=tr("el denominador común es {comun}.", comun=texto(sympy.factor(comun))),
                   calculo=(tr("Cada fracción simple, por el denominador común, deja su numerador multiplicado por los "
                               "factores que le faltan."),),
                   queda=f"{texto(numerador)} = {derecha_txt}")

        valores: Dict[Symbol, Any] = {}
        # a) Las raíces de los factores lineales: todos los términos menos uno se anulan
        lineas = []
        for c, m in productos:
            if not isinstance(c, Symbol):
                continue
            base, k = next((b, kk) for cc, b, kk in terminos if cc == c)
            maximo = max(kk for _, b, kk in terminos if b == base)
            if sympy.degree(base, x) != 1 or k != maximo:
                continue
            raiz = sympy.solve(base, x)[0]
            izq = sympy.simplify(numerador.subs(x, raiz))
            mul = sympy.simplify(m.subs(x, raiz))
            cuenta_izq = sustituir(numerador, {x: raiz})
            cuenta_izq = cuenta_izq if cuenta_izq == texto(izq) else f"{cuenta_izq} = {texto(izq)}"
            cuenta_der = sustituir(m, {x: raiz})
            producto = f"{c}" if mul == 1 else f"{entre_parentesis(mul)}*{c}"  # 1*A es A
            derecha = f"{c}*({cuenta_der}) = {producto}" if cuenta_der != texto(mul) else producto
            valor = sympy.simplify(izq / mul)
            division = f"{entre_parentesis(izq)}/{entre_parentesis(mul)}"
            despeje = (f"{c} = {texto(valor)}" if mul == 1 or division == texto(valor)
                       else f"{c} = {division} = {texto(valor)}")
            lineas.append(tr("{variable} = {raiz} (raíz de {factor}): todos los términos tienen el factor {factor} y "
                             "se anulan, salvo el de {letra}. Izquierda: {izquierda}. Derecha: {derecha}. Así "
                             "{ecuacion}, y {despeje}.", variable=x, raiz=texto(raiz),
                             factor=texto(base), letra=c, izquierda=cuenta_izq, derecha=derecha,
                             ecuacion=f"{producto} = {texto(izq)}", despeje=despeje)
                          if mul != 1 else
                          tr("{variable} = {raiz} (raíz de {factor}): todos los términos tienen el factor {factor} y "
                             "se anulan, salvo el de {letra}. Izquierda: {izquierda}. Derecha: {derecha}. Así "
                             "{despeje}.", variable=x, raiz=texto(raiz), factor=texto(base), letra=c,
                             izquierda=cuenta_izq, derecha=derecha, despeje=despeje))
            valores[c] = valor
        if lineas:
            self._paso(tr("Sustituir las raíces"),
                       regla=tr("la igualdad vale para todo {variable}: al sustituir la raíz de un factor lineal, todos "
                                "los términos que lo contienen valen 0 y queda una ecuación con una sola incógnita.",
                                variable=x),
                       partes=tr("raíces de los factores lineales: {raices}.", raices=", ".join(
                           texto(sympy.solve(b, x)[0]) for b, _ in factores if sympy.degree(b, x) == 1)),
                       calculo=lineas,
                       queda=", ".join(f"{l} = {texto(v)}" for l, v in valores.items()))

        # b) Los que falten: igualar los coeficientes de cada potencia de x
        faltan = [l for l in letras if l not in valores]
        if faltan:
            derecha = sympy.expand(sum(c * m for c, m in productos))
            poli = sympy.Poly(derecha, x)
            grado = max(poli.degree(), sympy.degree(numerador, x) if numerador.has(x) else 0)
            ecuaciones = []
            lineas = [tr("Desarrollamos el lado derecho y agrupamos por potencias de {variable}: {derecha}.",
                         variable=x, derecha=texto(sympy.collect(derecha, x)))]
            for g in range(grado, -1, -1):
                izq = numerador.coeff(x, g) if g else numerador.subs(x, 0)
                der = derecha.coeff(x, g) if g else derecha.subs(x, 0)
                if der == 0 and izq == 0:
                    continue
                potencia = f"{x}^{g}" if g > 1 else (str(x) if g == 1 else tr("término independiente"))
                lineas.append(tr("{potencia}: {derecha} = {izquierda}.", potencia=potencia, derecha=texto(der),
                                 izquierda=texto(izq)))
                ecuaciones.append((der, izq))
            if valores:
                lineas.append(tr("Sustituimos los valores ya hallados ({valores}).", valores=", ".join(
                    f"{l} = {texto(v)}" for l, v in valores.items())))
            pendientes = list(faltan)
            vueltas = 0
            while pendientes and vueltas < 20:
                vueltas += 1
                for der, izq in ecuaciones:
                    der_v = sympy.expand(der.subs(valores))
                    incognitas = [l for l in pendientes if der_v.has(l)]
                    if len(incognitas) == 1:
                        letra = incognitas[0]
                        cuentas, valor = despejar(der_v, izq, letra)
                        if der_v == letra:
                            lineas.append(f"{letra} = {texto(valor)}.")  # ya despejada: C = 0
                        else:
                            lineas.append(tr("Con {ecuacion}: {cuentas}", ecuacion=f"{texto(der_v)} = {texto(izq)}",
                                             cuentas=" ".join(cuentas) if cuentas else f"{letra} = {texto(valor)}."))
                            if cuentas and not cuentas[-1].endswith(f"{letra} = {texto(valor)}."):
                                lineas.append(f"{letra} = {texto(valor)}.")
                        valores[letra] = valor
                        pendientes.remove(letra)
                        break
                else:
                    raise SinExplicacion()  # haría falta resolver varias a la vez
            if pendientes:
                raise SinExplicacion()
            self._paso(tr("Igualar coeficientes"),
                       regla=tr("dos polinomios iguales tienen el mismo coeficiente en cada potencia de {variable}: cada "
                                "potencia da una ecuación. Se resuelven de una en una, empezando por las que tienen una "
                                "sola incógnita.", variable=x),
                       partes=tr("faltan {letras}.", letras=", ".join(l.name for l in faltan)),
                       calculo=lineas,
                       queda=", ".join(f"{l} = {texto(valores[l])}" for l in letras))
        return valores

    # ---------------- 5. Integrar ----------------

    def _integrar(self, cociente: Any, simples: List[Tuple[Any, Any, int]]) -> Any:
        x = self.x
        partes, lineas = [], []
        if cociente != 0:
            primitiva = sympy.integrate(cociente, x)
            lineas.append(tr("Parte polinómica: ∫ ({c}) d{variable} = {p} (regla de la potencia en cada término: "
                             "x^n da x^(n+1)/(n+1)).", c=texto(cociente), variable=x, p=texto(primitiva)))
            partes.append(primitiva)
        for c, base, k in simples:
            if c == 0:
                continue
            if sympy.degree(base, x) == 1:
                a = sympy.Poly(base, x).LC()
                if k == 1:
                    primitiva = c / a * sympy.log(base)
                    extra = tr(" (y como la derivada de {factor} es {a}, se divide entre {a})", factor=texto(base),
                               a=texto(a)) if a != 1 else ""
                    if c == 1 and a == 1:
                        lineas.append(tr("∫ {fraccion} d{variable} = {p}: ∫ 1/u du = log(u).",
                                         fraccion=self._fraccion_texto(c, base, k), variable=x, p=texto(primitiva)))
                    else:
                        lineas.append(tr("∫ {fraccion} d{variable} = {c}*log({factor}){extra} = {p}: ∫ 1/u du = log(u).",
                                         fraccion=self._fraccion_texto(c, base, k), variable=x, c=entre_parentesis(c),
                                         factor=texto(base), extra=extra, p=texto(primitiva)))
                else:
                    primitiva = c / a * base ** (1 - k) / (1 - k)
                    lineas.append(tr("∫ {fraccion} d{variable} = {c}*({factor})^({exp})/({exp}) = {p}: regla de la "
                                     "potencia, ∫ u^n du = u^(n+1)/(n+1) con n = -{k}.",
                                     fraccion=self._fraccion_texto(c, base, k), variable=x, c=entre_parentesis(c / a),
                                     factor=texto(base), exp=1 - k, p=texto(primitiva), k=k))
                partes.append(primitiva)
                continue
            if k != 1:
                raise SinExplicacion()  # cuadrático repetido: fuera de los casos de clase
            partes.extend(sympy.Add.make_args(self._cuadratico(c, base, lineas)))  # logaritmo y arcotangente
        primitiva = sympy.Add(*partes)
        self._paso(tr("Integrar cada fracción simple"),
                   regla=tr("la integral de la suma es la suma de las integrales. Las fracciones con un factor lineal dan "
                            "logaritmos (o potencias, si está repetido); las de un factor cuadrático, un logaritmo y una "
                            "arcotangente."),
                   partes=tr("hay {n} integrales que hacer.", n=len(partes)),
                   calculo=lineas + [tr("Juntamos: {suma}.", suma=suma_texto(partes))],
                   queda=texto(primitiva))
        return primitiva

    def _cuadratico(self, numerador: Any, base: Any, lineas: List[str]) -> Any:
        """∫ (M*x + N)/(x^2 + p*x + q) dx: un logaritmo y una arcotangente, completando el cuadrado."""
        x = self.x
        a, p, q = sympy.Poly(base, x).all_coeffs()
        if a != 1:
            raise SinExplicacion()
        m = sympy.expand(numerador).coeff(x, 1)
        n = sympy.expand(numerador).subs(x, 0)
        derivada = 2 * x + p
        resto = sympy.simplify(n - m * p / 2)
        primitiva = S.Zero
        if m != 0:
            log = m / 2 * sympy.log(base)
            lineas.append(tr("En ({numerador})/({base}), la derivada del denominador es {derivada}: escribimos "
                             "{numerador} = {mitad}*({derivada}) + {resto}.", numerador=texto(numerador), base=texto(base),
                             derivada=texto(derivada), mitad=entre_parentesis(m / 2), resto=entre_parentesis(resto)))
            lineas.append(tr("∫ {mitad}*({derivada})/({base}) d{variable} = {p}: el numerador es la derivada del "
                             "denominador (cambio de variable u = {base}).", mitad=entre_parentesis(m / 2),
                             derivada=texto(derivada), base=texto(base), variable=x, p=texto(log)))
            primitiva += log
        if resto != 0:
            h = p / 2
            k2 = sympy.simplify(q - h ** 2)
            k = sympy.sqrt(k2)
            arco = resto / k * sympy.atan((x + h) / k)
            cuadrado = (x + h) ** 2
            lineas.append(tr("Completamos el cuadrado: {base} = {cuadrado} + {k2} (porque {q} - {h2} = {k2}).",
                             base=texto(base), cuadrado=texto(cuadrado), k2=texto(k2), q=texto(q), h2=texto(h ** 2)))
            coeficiente = sympy.simplify(resto / k)
            cuenta = f"{entre_parentesis(resto)}*(1/{entre_parentesis(k)})"
            lineas.append(tr("∫ {resto}/({cuadrado} + {k2}) d{variable}: ∫ 1/(u^2 + k^2) du = (1/k)*atan(u/k), con "
                             "u = {u} y k = sqrt({k2}) = {k}.", resto=entre_parentesis(resto), cuadrado=texto(cuadrado),
                             k2=texto(k2), variable=x, u=texto(x + h), k=texto(k)))
            lineas.append(tr("El número que multiplica: {cuenta} = {coeficiente}; queda {p}.", cuenta=cuenta,
                             coeficiente=texto(coeficiente), p=texto(arco))
                          if k != 1 else
                          tr("Queda {ecuacion}.", ecuacion=texto(arco)))
            primitiva += arco
        return primitiva
