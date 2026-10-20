"""
Ecuaciones diferenciales ordinarias, explicadas con el formato de calculo/pasos.py (Regla,
En este caso, las cuentas y Queda). Una sola operación: se reconoce el tipo de la ecuación y
se aplica su método, como Integrar elige entre partes, sustitución o fracciones parciales.

  1. Lectura: y', y'', dy/dx, d2y/dx2 y y(x); condiciones iniciales opcionales separadas por
     comas o punto y coma (y' = 2*x*y, y(0) = 1).
  2. Planteamiento: el orden de la ecuación y, si hace falta, el despeje de y'.
  3. El método:
       - separable, y' = g(x)*h(y): separar las variables, integrar los dos lados (con el paso
         a paso de Integrar) y despejar y; las soluciones constantes, h(y) = 0, aparte;
       - reducible a separable, y' = F(a*x + b*y + c): el cambio u = a*x + b*y + c deja una
         separable en u; al final se deshace el cambio.
  4. La comprobación: se deriva la solución y se sustituye en la ecuación.
  5. Con condiciones iniciales, el valor de la constante y la solución particular.

La solución se comprueba con checkodesol de SymPy. Las ecuaciones de otros tipos se
resuelven con dsolve, sin pasos y con una nota.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import sympy

from algebra.ecuaciones import _pasar, despejar
from calculo.calculo import Calculo
from calculo.pasos import PasoCalculo, texto_paso
from i18n import tr
from calculo.fracciones_parciales import ExplicadorFracciones
from pasos_aritmetica import ExplicadorFactorizar
from pasos_aritmetica import SinExplicacion as SinFactorizacion
from sympy.printing.str import StrPrinter


class SinExplicacion(Exception):
    """Un paso que no se sabe explicar: la ecuación la resuelve SymPy, sin pasos."""


@dataclass
class Condicion:
    orden: int      # 0: y(x0) = v; 1: y'(x0) = v...
    punto: Any
    valor: Any


@dataclass
class Edo:
    izquierda: Any            # con los símbolos y, y', y''... (Symbol("y'"))
    derecha: Any
    x: Any
    y: Any
    derivadas: List[Any]      # [y', y'', ...] hasta el orden
    orden: int
    condiciones: List[Condicion] = field(default_factory=list)
    escrita: str = ""         # la ecuación tal como se escribió (para mostrarla en ese orden)
    diferencial: bool = False  # escrita como M dx + N dy = 0 (se lee como M + N*y' = 0)
    laplace: bool = False      # se pidió la transformada de Laplace
    y1: Any = None             # una solución conocida de la homogénea (reducción de orden)
    serie: bool = False        # se pidió la solución en serie de potencias

    @property
    def enunciado(self) -> str:
        return self.escrita or f"{texto(self.izquierda)} = {texto(self.derecha)}"


@dataclass
class ResultadoEdo:
    texto: str
    es_error: bool = False
    soluciones: List[Any] = field(default_factory=list)  # Eq(y, ...) o una ecuación implícita
    x: Any = None
    y: Any = None
    planteamiento: List[Any] = field(default_factory=list)
    metodo: str = ""
    avisos: List[str] = field(default_factory=list)


# ---------------------------------------------------------
# Expresiones: la constante C, al final (x^2 + C, tan(x + C))
# ---------------------------------------------------------

C = sympy.Symbol("C", real=True)


class _Impresora(StrPrinter):
    def _as_ordered_terms(self, expr, order=None):
        terminos = super()._as_ordered_terms(expr, order=order)
        con_c = [t for t in terminos if any(re.fullmatch(r"C\d*", s.name) for s in t.free_symbols
                                            if isinstance(s, sympy.Symbol))]
        return [t for t in terminos if t not in con_c] + con_c

    def _print_Add(self, expr, order=None):
        # Una serie: C1*(1 + x^3/6 + ...) + C2*(x + ...) + O(x^7), con las potencias de menor a mayor
        if any(isinstance(a, sympy.Order) for a in expr.args):
            partes = [a for a in expr.args if not isinstance(a, sympy.Order)]
            orden = [a for a in expr.args if isinstance(a, sympy.Order)]
            textos = [self._serie(a) for a in partes] + [self._print(o) for o in orden]
            return " + ".join(textos).replace("+ -", "- ")
        return super()._print_Add(expr, order=order)

    def _serie(self, termino):
        constante = [f for f in sympy.Mul.make_args(termino) if es_constante(f)]
        resto = sympy.Mul(*[f for f in sympy.Mul.make_args(termino) if not es_constante(f)])
        variables = sorted(resto.free_symbols, key=lambda s: s.name)
        if resto == 1 and constante:
            return self._print(constante[0])
        if resto.is_Add and variables:
            terminos = sorted(sympy.Add.make_args(resto), key=lambda t: sympy.Poly(t, *variables).total_degree())
            cuerpo = self._print(terminos[0]) + "".join(
                (" - " + self._print(-t)) if t.could_extract_minus_sign() else (" + " + self._print(t))
                for t in terminos[1:])
            return f"{self._print(constante[0])}*({cuerpo})" if constante else cuerpo
        return self._print(termino)

    def _print_Pow(self, expr, rational=False):
        # x^(-2) se escribe 1/x^2, como 1/x
        if expr.exp.is_Integer and expr.exp < -1:
            return "1/" + self.parenthesize(sympy.Pow(expr.base, -expr.exp, evaluate=False), 50)
        return super()._print_Pow(expr, rational=rational)


def texto(expr: Any) -> str:
    return _Impresora().doprint(sympy.sympify(expr)).replace("**", "^")


def entre_parentesis(expr: Any) -> str:
    """Como calculo.pasos.entre_parentesis, con la C al final."""
    expr = sympy.sympify(expr)
    simple = (expr.is_Symbol or (expr.is_Integer and expr >= 0) or expr.is_Function
              or (expr.is_Pow and expr.exp.is_Integer and expr.exp > 0 and expr.base.is_Symbol))
    return texto(expr) if simple else f"({texto(expr)})"


def factor(expr: Any) -> str:
    """Un factor de un producto: entre paréntesis solo si es una suma (2*x*y, (x + 1)*y)."""
    expr = sympy.sympify(expr)
    compuesto = (expr.is_Add or (expr.is_Number and expr < 0) or expr.could_extract_minus_sign()
                 or ((expr.is_Mul or expr.is_Pow or expr.is_Rational) and sympy.fraction(expr)[1] != 1))
    return f"({texto(expr)})" if compuesto else texto(expr)


def producto(a: Any, b: Any) -> str:
    """'a*b' sin el factor 1: g(x)*h(y) tal como se lee."""
    if a == 1:
        return texto(b)
    if b == 1:
        return texto(a)
    return f"{factor(a)}*{factor(b)}"


def sustituir(expr: Any, valores: Dict[Any, Any]) -> str:
    """
    La expresión con cada letra cambiada por su valor, sin operar y en el orden escrito:
    x + y con y = -x - 1 + C*exp(x) da 'x + (-x - 1 + C*exp(x))'. Un valor va entre paréntesis
    si es una suma o negativo, si se eleva a una potencia, o si va detrás de una división y es un
    producto (sustituir y' antes que y).
    """
    expr = sympy.sympify(expr)
    if expr in valores:
        return texto(valores[expr])
    escrita = texto(expr)
    nombres = sorted(valores, key=lambda v: -len(v.name))
    marcas = {v: f"\x00{i}\x00" for i, v in enumerate(nombres)}
    for v in nombres:
        escrita = re.sub(rf"(?<![\w.']){re.escape(v.name)}(?![\w('])", marcas[v], escrita)

    def poner(m):
        valor = sympy.sympify(valores[nombres[int(m.group(1))]])
        nombre = texto(valor)
        if valor.is_Symbol or (valor.is_Integer and valor >= 0):
            return nombre
        antes = m.string[m.start() - 1] if m.start() > 0 else ""
        despues = m.string[m.end()] if m.end() < len(m.string) else ""
        if (valor.is_Add or valor.could_extract_minus_sign() or despues == "^"
                or (antes == "/" and (valor.is_Mul or valor.is_Pow or valor.is_Rational))
                or ("*" in (antes, despues) and valor.is_Mul)
                or (valor.is_Rational and not valor.is_Integer)):
            nombre = f"({nombre})"
        return nombre
    return re.sub(r"\x00(\d+)\x00", poner, escrita)


def _mas(coeficiente: Any, variable: Any) -> str:
    """' + 2*y', ' - y', ' + (1/x)*y': el término coeficiente*variable de una suma, con su signo."""
    coeficiente = sympy.sympify(coeficiente)
    if coeficiente == 0:
        return ""
    signo, valor = (" - ", -coeficiente) if coeficiente.could_extract_minus_sign() else (" + ", coeficiente)
    if variable == 1:
        return signo + (f"({texto(valor)})" if valor.is_Add else texto(valor))
    if sympy.fraction(valor)[1] != 1 and not valor.is_Add:
        return signo + texto(valor * variable)  # y/x, no (1/x)*y
    return signo + producto(valor, variable)


# ---------------------------------------------------------
# Lectura de la entrada
# ---------------------------------------------------------

def _partir(entrada: str) -> List[str]:
    """Separa la ecuación y las condiciones por comas o punto y coma fuera de paréntesis."""
    partes, nivel, actual = [], 0, ""
    for c in entrada:
        if c in "([":
            nivel += 1
        elif c in ")]":
            nivel -= 1
        if c in ",;" and nivel == 0:
            partes.append(actual)
            actual = ""
        else:
            actual += c
    partes.append(actual)
    return [p.strip() for p in partes if p.strip()]


def _marcador(dependiente: str, n: int) -> str:
    return f" d{n}_{dependiente} "


_CONDICION = re.compile(r"^([a-z])\s*('*)\s*\((.+)\)\s*=\s*(.+)$")


def nombre_derivada(y: Any, n: int) -> str:
    return f"{y}" + "'" * n


# ---------------------------------------------------------
# Constantes de integración
# ---------------------------------------------------------

def _con_abs(expr: Any) -> Any:
    """log(u) -> log(Abs(u)) si u puede ser negativo: la primitiva de 1/u que vale a los dos lados."""
    return expr.replace(lambda e: isinstance(e, sympy.log) and not e.args[0].is_positive
                        and not isinstance(e.args[0], sympy.Abs),
                        lambda e: sympy.log(sympy.Abs(e.args[0])))


def _solo_constante(expr: Any, variables: Sequence[Any]) -> bool:
    return expr.has(C) and not any(expr.has(v) for v in variables)


def _renombrar(expr: Any, variables: Sequence[Any], lineas: List[str]) -> Any:
    """
    Una expresión que solo depende de C (2*C, C + 3, -C) es otra constante cualquiera: se
    sigue llamando C. Se mira el término o el factor que la contiene.
    """
    if expr == C or not expr.has(C):
        return expr
    if _solo_constante(expr, variables):
        lineas.append(tr("{expresion} es también una constante cualquiera: la seguimos llamando C.",
                         expresion=texto(expr)))
        return C
    if expr.is_Add:
        con, sin = sympy.S.Zero, sympy.S.Zero
        for t in expr.args:
            if _solo_constante(t, variables):
                con += t
            else:
                sin += t
        if con != 0 and con != C:
            lineas.append(tr("{expresion} es también una constante cualquiera: la seguimos llamando C.",
                             expresion=texto(con)))
            return sin + C
        return expr
    if expr.is_Mul:
        con, sin = sympy.S.One, sympy.S.One
        for f in expr.args:
            if _solo_constante(f, variables) or (f.is_number and expr.has(C)):
                con *= f
            else:
                sin *= f
        if con != C and con.has(C):
            lineas.append(tr("{expresion} es también una constante cualquiera: la seguimos llamando C.",
                             expresion=texto(con)))
            return C * sin
    return expr


K = sympy.Symbol("k", integer=True)


def _raices_reales(h: Any, y: Any, x: Any) -> List[Any]:
    """
    Los números r con h(r) = 0. Si son periódicas (cos(y) = 0), una familia con k entero:
    pi/2 + pi*k (las dos de periodo 2*pi que se diferencian en pi se juntan).
    """
    try:
        conjunto = sympy.solveset(h, y, sympy.S.Reals)
    except Exception:
        return []
    if isinstance(conjunto, sympy.FiniteSet):
        return [r for r in conjunto if not r.has(x)]
    piezas = conjunto.args if isinstance(conjunto, sympy.Union) else (conjunto,)
    familias = []
    for pieza in piezas:
        if not isinstance(pieza, sympy.ImageSet) or pieza.base_sets[0] != sympy.S.Integers:
            return []
        n = pieza.lamda.variables[0]
        expr = pieza.lamda.expr
        periodo, inicio = expr.coeff(n), expr.subs(n, 0)
        familias.append((periodo, inicio))
    juntas = []
    for periodo, inicio in familias:
        pareja = (periodo, inicio + periodo / 2)
        if pareja in familias and (periodo / 2, inicio) not in juntas:
            juntas.append((periodo / 2, inicio))
        elif not any(p == periodo * 2 and (inicio - i) % p in (0, periodo) for p, i in juntas)                 and (periodo, inicio - periodo / 2) not in familias:
            juntas.append((periodo, inicio))
    return [i + p * K if i != 0 else p * K for p, i in juntas]


# ---------------------------------------------------------
# Despejar una incógnita, función a función
# ---------------------------------------------------------

class Despeje:
    """
    Despeja incognita en izquierda = derecha deshaciendo, de fuera hacia dentro, lo que la
    envuelve: términos que suman, factores que multiplican, potencias, logaritmos,
    exponenciales, valores absolutos y funciones trigonométricas inversas. Si las demás
    letras dejan una constante C aislada, se renombra (2*C es otra constante: C).
    Devuelve las ramas (una, o dos con ±) o lanza SinExplicacion.
    """

    def __init__(self, incognita: Any, variables: Sequence[Any], constantes: bool = True):
        self.incognita = incognita
        self.variables = list(variables)
        self.constantes = constantes
        self.lineas: List[str] = []
        self.restricciones: List[Any] = []

    def _renombrar(self, expr: Any) -> Any:
        return _renombrar(expr, self.variables, self.lineas) if self.constantes else expr

    def resolver(self, izquierda: Any, derecha: Any) -> List[Any]:
        ramas = [(izquierda, derecha)]
        soluciones = []
        for _ in range(30):
            if not ramas:
                return soluciones
            pendientes = []
            for izq, der in ramas:
                if izq == self.incognita:
                    soluciones.append(der)
                else:
                    pendientes.extend(self._paso(izq, der))
            ramas = pendientes
        raise SinExplicacion()

    def _igualdad(self, izq: Any, der: Any) -> str:
        return f"{texto(izq)} = {texto(der)}"

    def _paso(self, izq: Any, der: Any) -> List[Tuple[Any, Any]]:
        u = self.incognita
        if izq.is_Add:
            sin_u = [t for t in izq.args if not t.has(u)]
            con_u = [t for t in izq.args if t.has(u)]
            if sin_u:
                for t in sin_u:
                    self.lineas.append(_pasar(t, tr("derecha")))
                nueva_der = self._renombrar(der - sympy.Add(*sin_u))
                nueva_izq = sympy.Add(*con_u)
                self.lineas.append(tr("Queda {ecuacion}.", ecuacion=self._igualdad(nueva_izq, nueva_der)))
                return [(nueva_izq, nueva_der)]
            juntos = self._juntar_logaritmos(izq)
            if juntos is not None:
                self.lineas.append(tr("Propiedades de los logaritmos: log(a) + log(b) = log(a*b), log(a) - log(b) = "
                                      "log(a/b) y k*log(a) = log(a^k). Queda {ecuacion}.",
                                      ecuacion=self._igualdad(juntos, der)))
                return [(juntos, der)]
            return self._racional(izq, der)
        if izq.is_Mul:
            numero, resto = izq.as_independent(u, as_Add=False)
            if numero != 1:
                cociente = sympy.expand(der / numero) if der.is_Add else der / numero
                if numero == -1:
                    self.lineas.append(tr("Cambiamos el signo de los dos lados: {ecuacion}.",
                                          ecuacion=self._igualdad(resto, cociente)))
                elif sympy.fraction(numero)[0] == 1:
                    self.lineas.append(tr("Multiplicamos los dos lados por {k}: {ecuacion}.", k=texto(1 / numero),
                                          ecuacion=self._igualdad(resto, cociente)))
                else:
                    self.lineas.append(tr("Dividimos los dos lados entre {k}: {ecuacion}.", k=texto(numero),
                                          ecuacion=self._igualdad(resto, cociente)))
                nueva = self._renombrar(cociente)
                if nueva != cociente:
                    self.lineas.append(tr("Queda {ecuacion}.", ecuacion=self._igualdad(resto, nueva)))
                return [(resto, nueva)]
            return self._racional(izq, der)
        if izq.is_Pow:
            base, exponente = izq.args
            if base.has(u) and not exponente.has(u):
                return self._potencia(base, exponente, der)
            if exponente.has(u) and not base.has(u):
                # a^u = R: u = log(R)/log(a)
                nueva = sympy.log(der) / sympy.log(base) if base != sympy.E else sympy.log(der)
                self.lineas.append(tr("Tomamos logaritmos en los dos lados (la inversa de la exponencial): {ecuacion}.",
                                      ecuacion=self._igualdad(exponente, nueva)))
                return [(exponente, self._renombrar(nueva))]
        if isinstance(izq, sympy.exp):
            nueva = sympy.log(der)
            self.lineas.append(tr("Tomamos logaritmos en los dos lados (el logaritmo deshace la exponencial; "
                                  "hace falta que {derecha} sea positivo): {ecuacion}.",
                                  derecha=texto(der), ecuacion=self._igualdad(izq.args[0], nueva)))
            return [(izq.args[0], nueva)]
        if isinstance(izq, sympy.log):
            return self._logaritmo(izq.args[0], der)
        if isinstance(izq, sympy.Abs):
            dentro = izq.args[0]
            self.restricciones.append(sympy.Ge(der, 0))
            self.lineas.append(tr("Quitamos el valor absoluto: {dentro} = {derecha} o {dentro} = -({derecha}).",
                                  dentro=texto(dentro), derecha=texto(der)))
            return [(dentro, der), (dentro, -der)]
        inversas = {sympy.atan: sympy.tan, sympy.asin: sympy.sin, sympy.acos: sympy.cos,
                    sympy.tan: sympy.atan, sympy.sin: sympy.asin, sympy.cos: sympy.acos}
        for funcion, inversa in inversas.items():
            if isinstance(izq, funcion):
                nueva = inversa(der)
                if funcion in (sympy.atan, sympy.asin, sympy.acos):
                    self.lineas.append(tr("Aplicamos {inversa} a los dos lados ({inversa} deshace {funcion}): "
                                          "{ecuacion}.", inversa=inversa.__name__, funcion=funcion.__name__,
                                          ecuacion=self._igualdad(izq.args[0], nueva)))
                else:
                    self.lineas.append(tr("Aplicamos {inversa} a los dos lados (se toma el valor principal de "
                                          "{inversa}): {ecuacion}.", inversa=inversa.__name__,
                                          ecuacion=self._igualdad(izq.args[0], nueva)))
                return [(izq.args[0], nueva)]
        raise SinExplicacion()

    def _potencia(self, base: Any, exponente: Any, der: Any) -> List[Tuple[Any, Any]]:
        if exponente == -1:
            nueva = 1 / der
            self.lineas.append(tr("Tomamos el inverso de los dos lados: {ecuacion}.",
                                  ecuacion=self._igualdad(base, nueva)))
            return [(base, nueva)]
        if not exponente.is_Rational:
            raise SinExplicacion()
        if exponente.is_negative:
            self.lineas.append(tr("Un exponente negativo es el inverso: {potencia} = 1/{positiva}; tomamos el "
                                  "inverso de los dos lados: {ecuacion}.",
                                  potencia=f"{entre_parentesis(base)}^{entre_parentesis(exponente)}",
                                  positiva=f"{entre_parentesis(base)}^{entre_parentesis(-exponente)}",
                                  ecuacion=self._igualdad(base ** -exponente, 1 / der)))
            return [(base ** -exponente, 1 / der)]
        inverso = 1 / exponente
        nueva = der ** inverso
        if der.is_Pow and der.exp == -1:  # (1/a)^(1/2) se escribe 1/a^(1/2)
            nueva = 1 / der.base ** inverso
        p = exponente.p  # base^(p/q) = R: base = R^(q/p); con p par, ±
        if exponente == 2:
            self.lineas.append(tr("Sacamos la raíz cuadrada de los dos lados (deshace el cuadrado); hay dos signos: "
                                  "{base} = ±{valor}.", base=texto(base), valor=factor(nueva)))
            return [(base, nueva), (base, -nueva)]
        if p % 2 == 0:
            self.lineas.append(tr("Elevamos los dos lados a {inverso} (deshace el exponente {exponente}); hay dos "
                                  "signos: {base} = ±{valor}.", inverso=texto(inverso), exponente=texto(exponente),
                                  base=texto(base), valor=factor(nueva)))
            return [(base, nueva), (base, -nueva)]
        if exponente.q % 2 == 0:
            self.restricciones.append(sympy.Ge(der, 0))
        if exponente == sympy.Rational(1, 2):
            self.lineas.append(tr("Elevamos al cuadrado los dos lados (deshace la raíz cuadrada): {ecuacion}.",
                                  ecuacion=self._igualdad(base, nueva)))
            return [(base, nueva)]
        self.lineas.append(tr("Elevamos los dos lados a {inverso} (deshace el exponente {exponente}): {ecuacion}.",
                              inverso=texto(inverso), exponente=texto(exponente),
                              ecuacion=self._igualdad(base, nueva)))
        return [(base, nueva)]

    def _logaritmo(self, dentro: Any, der: Any) -> List[Tuple[Any, Any]]:
        valor_abs = isinstance(dentro, sympy.Abs)
        interior = dentro.args[0] if valor_abs else dentro
        self.lineas.append(tr("Aplicamos la exponencial a los dos lados (exp deshace log): {ecuacion}.",
                              ecuacion=self._igualdad(dentro, sympy.exp(der))))
        if not (self.constantes and der.has(C) and not sympy.expand(der - C).has(C)):
            if valor_abs:
                self.lineas.append(tr("Quitamos el valor absoluto: {dentro} = ±{valor}.", dentro=texto(interior),
                                      valor=entre_parentesis(sympy.exp(der))))
                return [(interior, sympy.exp(der)), (interior, -sympy.exp(der))]
            return [(interior, sympy.exp(der))]
        resto = sympy.expand(der - C)
        if resto != 0:
            linea = tr("Propiedad de las potencias: {antes} = exp(C)*{despues}.",
                       antes=texto(sympy.exp(der, evaluate=False)), despues=entre_parentesis(sympy.exp(resto)))
            if resto.has(sympy.log):
                linea += " " + tr("(exp y log se deshacen: exp(log(a)) = a.)")
            self.lineas.append(linea)
        if valor_abs:
            self.lineas.append(tr("Quitamos el valor absoluto: {dentro} = ±exp(C)*{despues}.", dentro=texto(interior),
                                  despues=entre_parentesis(sympy.exp(resto))))
            self.lineas.append(tr("exp(C) es positivo y C es cualquier número: ±exp(C) es cualquier número distinto "
                                  "de 0. Lo llamamos C."))
        else:
            self.lineas.append(tr("exp(C) es una constante positiva cualquiera: la llamamos C."))
        nueva = C * sympy.exp(resto)
        if valor_abs:
            nueva = self._sin_abs(nueva)
        self.lineas.append(tr("Queda {ecuacion}.", ecuacion=self._igualdad(interior, nueva)))
        return [(interior, nueva)]

    def _sin_abs(self, expr: Any) -> Any:
        """C*Abs(x) -> C*x: en cada intervalo donde x no cambia de signo, el signo lo absorbe C."""
        cambios = {}
        for f in sympy.Mul.make_args(expr):
            base = f.base if f.is_Pow and f.exp.is_Integer else f
            if isinstance(base, sympy.Abs) and not base.has(C):
                cambios[base] = base.args[0]
        if not cambios:
            return expr
        for a, b in cambios.items():
            self.lineas.append(tr("En cada intervalo en que {u} no cambia de signo, {abs} es {u} o -{u}: el signo lo "
                                  "absorbe C.", u=texto(b), abs=texto(a)))
        return expr.xreplace(cambios)

    def _juntar_logaritmos(self, izq: Any) -> Optional[Any]:
        """k1*log(a) + k2*log(b) -> log(a^k1*b^k2), si todos los términos son logaritmos."""
        dentro, todos_abs = sympy.S.One, True
        for t in izq.args:
            k, resto = t.as_coeff_Mul()
            if not isinstance(resto, sympy.log) or not k.is_Rational:
                return None
            argumento = resto.args[0]
            todos_abs = todos_abs and isinstance(argumento, sympy.Abs)
            dentro *= (argumento.args[0] if isinstance(argumento, sympy.Abs) else argumento) ** k
        return sympy.log(sympy.Abs(dentro)) if todos_abs else sympy.log(dentro)

    def _racional(self, izq: Any, der: Any) -> List[Tuple[Any, Any]]:
        """Una fracción con la incógnita (u/(u - 1) = K): se quita el denominador y queda de primer grado."""
        u = self.incognita
        numerador, denominador = sympy.fraction(sympy.together(izq))
        if denominador.has(u):
            self.lineas.append(tr("Multiplicamos los dos lados por {denominador}: {ecuacion}.",
                                  denominador=texto(denominador),
                                  ecuacion=f"{texto(numerador)} = {entre_parentesis(der)}*{entre_parentesis(denominador)}"))
            izq, der = numerador, der * denominador
        polinomio = sympy.expand(izq - der)
        if sympy.degree(polinomio, u) != 1 if polinomio.is_polynomial(u) else True:
            raise SinExplicacion()
        # De primer grado en u: los términos con u a la izquierda, u factor común y dividir
        coeficiente = sympy.factor_terms(polinomio.coeff(u))
        resto = sympy.expand(-(polinomio - polinomio.coeff(u) * u))
        con_u = [t for t in sympy.Add.make_args(sympy.expand(izq)) if t.has(u)] + \
                [-t for t in sympy.Add.make_args(sympy.expand(der)) if t.has(u)]
        sin_u = [t for t in sympy.Add.make_args(sympy.expand(der)) if not t.has(u)] + \
                [-t for t in sympy.Add.make_args(sympy.expand(izq)) if not t.has(u) and t != 0]
        izquierda_txt = texto(sympy.Add(*con_u))
        if sympy.expand(izq) != sympy.Add(*con_u) or sympy.expand(der) != sympy.Add(*sin_u):
            self.lineas.append(tr("Dejamos a la izquierda los términos con {u} y a la derecha los demás: {ecuacion}.",
                                  u=u, ecuacion=f"{izquierda_txt} = {texto(resto)}"))
        if len(con_u) > 1:
            self.lineas.append(tr("Sacamos {u} factor común: {suma} = {u}*{coeficiente}.", u=u, suma=izquierda_txt,
                                  coeficiente=factor(coeficiente)))
        valor = sympy.factor_terms(resto / coeficiente)
        if coeficiente != 1:
            self.lineas.append(tr("Dividimos los dos lados entre {k} (suponiendo que no vale 0): {ecuacion}.",
                                  k=texto(coeficiente), ecuacion=self._igualdad(u, valor)))
        return [(u, valor)]


# ---------------------------------------------------------
# El motor
# ---------------------------------------------------------

class MotorEdo:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido
        self.calculo = Calculo(parser_compartido)

    # --- Lectura ---

    def _leer(self, entrada: str) -> Edo:
        partes = _partir(entrada.lower().replace("’", "'").replace("′", "'"))
        if not partes:
            raise ValueError(tr("La expresión está vacía."))
        ecuacion, condiciones_txt = partes[0], partes[1:]
        escrita = re.sub(r"\s+", " ", ecuacion).strip()
        independiente = None
        def fijar_variable(variable):
            nonlocal independiente
            if independiente is not None and independiente != variable:
                raise ValueError(tr("Las derivadas deben usar la misma variable independiente."))
            independiente = variable

        # Se consume la notación completa antes de enviarla al parser algebraico.
        def derivada_leibniz(m):
            superior, dependiente, argumento, variable, inferior = m.groups()
            n = int(superior or 1)
            if n != int(inferior or 1) or n < 1:
                raise ValueError(tr("Los órdenes del numerador y denominador de la derivada no coinciden."))
            if argumento and argumento != variable:
                raise ValueError(tr("El argumento de la función no coincide con la variable de derivación."))
            fijar_variable(variable)
            return dependiente + "'" * n
        ecuacion = re.sub(
            r"(?<![a-z_])d\s*\^?\s*(\d+)?\s*([a-z])(?:\(\s*([a-z])\s*\))?\s*/\s*d\s*([a-z])\s*(?:\^?\s*(\d+))?",
            derivada_leibniz, ecuacion)
        def funcion_prima(m):
            fijar_variable(m.group(3))
            return m.group(1) + m.group(2)
        ecuacion = re.sub(r"([a-z])\s*('+)[ ]*\(\s*([a-z])\s*\)", funcion_prima, ecuacion)
        def funcion(m):
            fijar_variable(m.group(2))
            return m.group(1)
        ecuacion = re.sub(r"(?<![a-z_])([a-z])\s*\(\s*([a-z])\s*\)", funcion, ecuacion)
        if re.search(r"'\s*\(", ecuacion):
            raise ValueError(tr("No se reconoce la notación de la derivada."))
        if re.search(r"\bd\s*\^?\s*\d*[a-z]\s*(?:\(|/)", ecuacion):
            raise ValueError(tr("No se reconoce la notación de la derivada."))
        con_primas = set(re.findall(r"([a-z])\s*'", ecuacion))
        diferencial = None
        if not con_primas:
            # Forma diferencial, M dx + N dy = 0: se lee como M + N*y' = 0 (dividiendo entre dx)
            patron = r"(?<![a-z])d([a-z])(?![a-z0-9_(])"
            letras = sorted(set(re.findall(patron, ecuacion)))
            if len(letras) == 2:
                dependiente_dif = "y" if "y" in letras else letras[1]
                independiente = letras[0] if letras[1] == dependiente_dif else letras[1]
                diferencial = (dependiente_dif, independiente)
                ecuacion = re.sub(patron, lambda m: f"{m.group(1)}'" if m.group(1) == dependiente_dif
                                  else f" dif_{m.group(1)} ", ecuacion)
                con_primas = {dependiente_dif}
        if not con_primas:
            raise ValueError(tr("No hay ninguna derivada: escriba la ecuación con y' (o dy/dx), por ejemplo "
                                "y' = 2*x*y. Para una ecuación sin derivadas, use Resolver ecuación (Ctrl+R)."))
        if len(con_primas) > 1:
            raise ValueError(tr("Hay derivadas de varias funciones ({funciones}): escriba una ecuación con una sola "
                                "función.", funciones=", ".join(sorted(con_primas))))
        dependiente = con_primas.pop()
        if "=" not in ecuacion:
            ecuacion += " = 0"
        if ecuacion.count("=") != 1:
            raise ValueError(tr("Escriba la ecuación con un solo signo = (ej: y' = 2*x*y)."))
        ecuacion = re.sub(rf"(?<![a-z_]){dependiente}\s*\(\s*([a-z])\s*\)",
                          lambda m: f" {dependiente} ", ecuacion)
        orden = 0

        def prima(m):
            nonlocal orden
            n = len(m.group(1))
            orden = max(orden, n)
            return _marcador(dependiente, n)
        ecuacion = re.sub(rf"{dependiente}\s*('+)", prima, ecuacion)
        if "'" in ecuacion:
            raise ValueError(tr("No se reconoce la notación de la derivada."))
        izq_txt, der_txt = ecuacion.split("=")
        if not izq_txt.strip() or not der_txt.strip():
            raise ValueError(tr("Falta uno de los dos lados de la {tipo}.", tipo=tr("ecuación")))
        izquierda = self.parser.parsear(izq_txt).doit()
        derecha = self.parser.parsear(der_txt).doit()

        y = self.parser.simbolo(dependiente)
        marcas = {self.parser.simbolo(f"d{n}_{dependiente}"): sympy.Symbol(nombre_derivada(y, n))
                  for n in range(1, orden + 1)}
        izquierda, derecha = izquierda.xreplace(marcas), derecha.xreplace(marcas)
        if diferencial:
            dx = self.parser.simbolo(f"dif_{diferencial[1]}")
            dy = marcas[self.parser.simbolo(f"d1_{dependiente}")]
            todo = sympy.expand(izquierda - derecha)
            terminos = sympy.Add.make_args(todo)
            if not all(sympy.Poly(t, dx, dy).total_degree() == 1 for t in terminos if t != 0) \
                    or not todo.is_polynomial(dx, dy):
                raise ValueError(tr("En la forma diferencial, cada término debe llevar d{x} o d{y} una sola vez "
                                    "(ej: (2*x*y + 3) dx + (x^2 - 1) dy = 0).", x=diferencial[1], y=dependiente))
            izquierda, derecha = izquierda.subs(dx, 1), derecha.subs(dx, 1)
        otras = (izquierda.free_symbols | derecha.free_symbols) - set(marcas.values()) - {y}
        nombres = {s.name: s for s in otras}
        if independiente:
            x = self.parser.simbolo(independiente)
        elif "x" in nombres and dependiente != "x":
            x = nombres["x"]
        elif "t" in nombres and dependiente != "t":
            x = nombres["t"]
        else:
            x = self.parser.simbolo("t" if dependiente == "x" else "x")
        if x == y:
            raise ValueError(tr("La función y la variable no pueden ser la misma letra."))

        condiciones = []
        laplace, y1, serie = False, None, False
        for c in condiciones_txt:
            if c.strip() == "laplace":
                laplace = True
                continue
            if c.strip() == "serie":
                serie = True
                continue
            m_y1 = re.match(r"^\s*y1\s*=\s*(.+)$", c)
            if m_y1:
                y1 = self.parser.parsear(m_y1.group(1)).doit()
                continue
            m = _CONDICION.match(c.strip())
            if not m or m.group(1) != dependiente:
                raise ValueError(tr("No se entiende la condición '{condicion}': escríbala como {y}(0) = 1 o "
                                    "{y}'(0) = 0.", condicion=c, y=dependiente))
            k = len(m.group(2))
            if k >= orden:
                raise ValueError(tr("La condición '{condicion}' tiene una derivada de orden {k}; en una ecuación de "
                                    "orden {orden} las condiciones llegan hasta la derivada {maximo}.", condicion=c,
                                    k=k, orden=orden, maximo=orden - 1))
            if any(cond.orden == k for cond in condiciones):
                raise ValueError(tr("Hay dos condiciones para {nombre}.", nombre=nombre_derivada(y, k)))
            condiciones.append(Condicion(k, self.parser.parsear(m.group(3)).doit(),
                                         self.parser.parsear(m.group(4)).doit()))
        derivadas = [marcas[s] for s in sorted(marcas, key=lambda s: s.name)]
        if "=" not in escrita:
            escrita += " = 0"
        return Edo(izquierda, derecha, x, y, derivadas, orden, sorted(condiciones, key=lambda c: c.orden), escrita,
                   diferencial=bool(diferencial), laplace=laplace, y1=y1, serie=serie)

    # --- Fachada ---

    def resolver(self, entrada: str) -> ResultadoEdo:
        partes = _partir(entrada.lower().replace("’", "'").replace("′", "'"))
        # Un sistema: varias ecuaciones x' = ..., y' = ... (o dx/dt = ...), de funciones distintas
        derivadas = [m.group(1) or m.group(2) for p in partes
                     for m in [re.match(r"^\s*(?:([a-z])\s*'\s*=(?!=)|d\s*([a-z])\s*/\s*d\s*[a-z]\s*=)", p)] if m]
        if len(set(derivadas)) >= 2:
            return self._resolver_sistema(partes)
        try:
            edo = self._leer(entrada)
        except ValueError as e:
            return ResultadoEdo(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except Exception as e:
            return ResultadoEdo(tr("Error del Sistema: {error}", error=str(e)), es_error=True)

        x, y = edo.x, edo.y
        Y = sympy.Function(y.name, real=True)(x)
        ode = sympy.Eq(self._a_sympy(edo.izquierda, edo), self._a_sympy(edo.derecha, edo))
        planteamiento = [sympy.Eq(self._a_derivadas(edo.izquierda, edo), self._a_derivadas(edo.derecha, edo),
                                  evaluate=False)]
        for cond in edo.condiciones:
            izq = Y.diff(x, cond.orden).subs(x, cond.punto) if cond.orden else Y.subs(x, cond.punto)
            planteamiento.append(sympy.Eq(izq, cond.valor, evaluate=False))

        avisos: List[str] = []
        pasos: List[PasoCalculo] = []
        metodo = ""
        try:
            soluciones, metodo = self._explicar(edo, pasos, avisos)
            if not self._comprobadas(ode, soluciones, edo, Y):
                avisos = [tr("AVISO: la explicación no llegó a una solución correcta; se muestra el resultado "
                             "de SymPy sin pasos.")]
                pasos, soluciones = [], None
        except SinExplicacion:
            pasos, soluciones, avisos = [], None, list(getattr(self, "_notas_metodo", []))
        except Exception:
            pasos, soluciones = [], None
            avisos = [tr("AVISO: no se pudo explicar paso a paso; el resultado es el que calcula SymPy.")]
        if soluciones is None:
            metodo = ""
            try:
                soluciones = self._con_sympy(ode, edo, Y, avisos)
            except NotImplementedError:
                soluciones = None
            except Exception as e:
                return ResultadoEdo(tr("Error del Sistema: {error}", error=str(e)), es_error=True)
            if soluciones is None:
                return ResultadoEdo(tr("Error de Validación: {error}", error=tr(
                    "no se encontró una solución en forma cerrada para esta ecuación.")), es_error=True)

        # La salida de respaldo también debe superar la comprobación independiente.
        if not self._comprobadas(ode, soluciones, edo, Y):
            return ResultadoEdo(tr("No se pudo verificar la solución en la EDO original."), es_error=True)
        for solucion in soluciones:
            if solucion.lhs != y or solucion.has(sympy.Order):
                continue
            if not all(sympy.simplify(sympy.diff(solucion.rhs, x, c.orden).subs(x, c.punto) - c.valor) == 0
                       for c in edo.condiciones):
                return ResultadoEdo(tr("La solución no satisface las condiciones iniciales."), es_error=True)
            restricciones = self._dominio_solucion(solucion, edo)
            if restricciones:
                avisos.append(tr("Dominio de {solucion}: en intervalos donde {restricciones}.",
                                 solucion=self._solucion_texto(solucion),
                                 restricciones="; ".join(texto(r) for r in restricciones)))

        valores = "; ".join(self._solucion_texto(s) for s in soluciones)
        if any(s.has(K) for s in soluciones):
            valores += " " + tr("({k}: cualquier número entero)", k=K)
        lineas = [tr("RESULTADO: {valor}", valor=valores)] + avisos + [
            "=" * 30,
            tr("Ecuación: {ecuacion}", ecuacion=edo.enunciado)]
        for cond in edo.condiciones:
            lineas.append(tr("Condición inicial: {condicion}", condicion=self._condicion_texto(cond, y)))
        if metodo:
            lineas.append(tr("Método: {metodo}", metodo=metodo))
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoEdo("\n".join(lineas), soluciones=soluciones, x=x, y=y, planteamiento=planteamiento,
                            metodo=metodo, avisos=avisos)

    # --- Sistemas ---

    def _leer_sistema(self, partes: List[str]) -> Tuple[Any, List[Any], Any, Dict[Any, Any], List[str]]:
        """(t, funciones, A, condiciones en 0, ecuaciones escritas) de x' = a*x + b*y; y' = c*x + d*y; x(0) = 1..."""
        independiente = None
        ecuaciones, condiciones = [], []
        for parte in partes:
            m = re.match(r"^\s*d\s*([a-z])\s*/\s*d\s*([a-z])\s*=(.*)$", parte)
            if m:
                independiente = m.group(2)
                parte = f"{m.group(1)}' ={m.group(3)}"
            m = re.match(r"^\s*([a-z])\s*'\s*=(.+)$", parte)
            if m:
                ecuaciones.append((m.group(1), m.group(2), re.sub(r"\s+", " ", parte).strip()))
            else:
                condiciones.append(parte)
        letras = [e[0] for e in ecuaciones]
        if len(set(letras)) != len(letras):
            raise ValueError(tr("En un sistema, cada ecuación es la derivada de una función distinta "
                                "(ej: x' = x + 2*y; y' = 3*x + 2*y)."))
        nombre_t = independiente or "t"
        if nombre_t in letras:
            raise ValueError(tr("La función y la variable no pueden ser la misma letra."))
        t = self.parser.simbolo(nombre_t)
        funciones = [self.parser.simbolo(l) for l in letras]
        filas = []
        for letra, derecha, _ in ecuaciones:
            if "'" in derecha:
                raise SinExplicacion()
            expr = sympy.expand(self.parser.parsear(derecha).doit())
            fila = [expr.coeff(f) for f in funciones]
            resto = sympy.expand(expr - sum(c * f for c, f in zip(fila, funciones)))
            if resto != 0 or any(not c.is_number for c in fila):
                raise SinExplicacion()
            filas.append(fila)
        valores = {}
        for c in condiciones:
            m = re.match(r"^\s*([a-z])\s*\(\s*0\s*\)\s*=\s*(.+)$", c)
            if not m or m.group(1) not in letras:
                raise ValueError(tr("En un sistema, las condiciones se escriben en 0 para cada función (ej: x(0) = 1)."))
            valores[self.parser.simbolo(m.group(1))] = self.parser.parsear(m.group(2)).doit()
        return t, funciones, sympy.Matrix(filas), valores, [e[2] for e in ecuaciones]

    def _resolver_sistema(self, partes: List[str]) -> ResultadoEdo:
        try:
            t, funciones, A, valores, escritas = self._leer_sistema(partes)
        except ValueError as e:
            return ResultadoEdo(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except SinExplicacion:
            return ResultadoEdo(tr("Error de Validación: {error}", error=tr(
                "por ahora se resuelven los sistemas lineales homogéneos con coeficientes constantes, X' = A*X "
                "(ej: x' = x + 2*y; y' = 3*x + 2*y).")), es_error=True)
        Fs = [sympy.Function(f.name, real=True)(t) for f in funciones]
        planteamiento = [sympy.Eq(sympy.Derivative(F, t), sum(A[i, j] * G for j, G in enumerate(Fs)), evaluate=False)
                         for i, F in enumerate(Fs)]
        planteamiento += [sympy.Eq(F.subs(t, 0), valores[f], evaluate=False) for f, F in zip(funciones, Fs)
                          if f in valores]
        pasos: List[PasoCalculo] = []
        avisos: List[str] = []
        sistema = _Sistema(self, t, funciones, A, pasos)
        try:
            X = sistema.resolver()
            if valores:
                X = sistema.condiciones(X, valores)
            if not sistema.comprobar(X):
                raise SinExplicacion()
            soluciones = [sympy.Eq(f, e) for f, e in zip(funciones, X)]
            metodo = tr("sistema lineal (valores y vectores propios)")
        except Exception:
            pasos, metodo = [], ""
            avisos.append(tr("NOTA: este sistema lo resuelve SymPy, sin pasos."))
            try:
                ics = {F.subs(t, 0): valores[f] for f, F in zip(funciones, Fs) if f in valores}
                resultado = sympy.dsolve([sympy.Eq(F.diff(t), sum(A[i, j] * G for j, G in enumerate(Fs)))
                                          for i, F in enumerate(Fs)], Fs, ics=ics or None)
            except Exception as e:
                return ResultadoEdo(tr("Error del Sistema: {error}", error=str(e)), es_error=True)
            cambio = {F: f for f, F in zip(funciones, Fs)}
            soluciones = [sympy.Eq(r.lhs.xreplace(cambio), r.rhs.xreplace(cambio)) for r in resultado]
        lineas = [tr("RESULTADO: {valor}", valor="; ".join(self._solucion_texto(s) for s in soluciones))] + avisos
        lineas += ["=" * 30] + [tr("Ecuación: {ecuacion}", ecuacion=e) for e in escritas]
        lineas += [tr("Condición inicial: {condicion}", condicion=f"{f}(0) = {texto(v)}") for f, v in valores.items()]
        if metodo:
            lineas.append(tr("Método: {metodo}", metodo=metodo))
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoEdo("\n".join(lineas), soluciones=soluciones, x=t, y=", ".join(str(f) for f in funciones),
                            planteamiento=planteamiento, metodo=metodo, avisos=avisos)

    # --- Conversión a SymPy y comprobación ---

    def _a_sympy(self, expr: Any, edo: Edo) -> Any:
        """y, y', y'' -> y(x), y(x).diff(x)... para dsolve y checkodesol."""
        Y = sympy.Function(edo.y.name, real=True)(edo.x)
        cambios = {d: Y.diff(edo.x, n) for n, d in enumerate(edo.derivadas, 1)}
        cambios[edo.y] = Y
        return expr.xreplace(cambios)

    def _a_derivadas(self, expr: Any, edo: Edo) -> Any:
        """Lo mismo, con las derivadas sin evaluar (para el planteamiento que se exporta)."""
        Y = sympy.Function(edo.y.name, real=True)(edo.x)
        cambios = {d: sympy.Derivative(Y, (edo.x, n)) for n, d in enumerate(edo.derivadas, 1)}
        cambios[edo.y] = Y
        return expr.xreplace(cambios)

    def _comprobadas(self, ode: Any, soluciones: List[Any], edo: Edo, Y: Any) -> bool:
        for s in soluciones:
            if s in getattr(self, "_por_tramos", set()):
                continue
            if s in getattr(self, "_restricciones", {}):
                cambios = {edo.y: s.rhs}
                cambios.update({d: sympy.diff(s.rhs, edo.x, n)
                                for n, d in enumerate(edo.derivadas, 1)})
                residuo = (edo.izquierda - edo.derecha).xreplace(cambios)
                supuestos = sympy.And(*[sympy.Q.nonnegative(r.lhs - r.rhs)
                                        for r in self._restricciones[s]])
                residuo = sympy.refine(residuo, supuestos)
                # La simplificación puede escribir |x-2| cuando la condición
                # guardada es 1-x/2 >= 0. Se demuestra la proporcionalidad.
                cambios_abs = {}
                for absoluto in residuo.atoms(sympy.Abs):
                    for restriccion in self._restricciones[s]:
                        base = restriccion.lhs - restriccion.rhs
                        razon = sympy.simplify(absoluto.args[0] / base)
                        if razon.is_positive:
                            cambios_abs[absoluto] = absoluto.args[0]
                        elif razon.is_negative:
                            cambios_abs[absoluto] = -absoluto.args[0]
                if sympy.simplify(residuo.xreplace(cambios_abs)) != 0:
                    return False
                continue
            if s in getattr(self, "_condiciones", {}):
                continue
            if s.lhs != edo.y and edo.orden == 1:
                # Implícita, F(x, y) = 0: y' = -F_x/F_y (derivación implícita) cumple la ecuación
                # log(Abs(u)) y log(u) tienen la misma derivada: sin el valor absoluto se simplifica mejor
                F = (s.lhs - s.rhs).replace(lambda e: isinstance(e, sympy.Abs), lambda e: e.args[0])
                derivada = -sympy.diff(F, edo.x) / sympy.diff(F, edo.y)
                resto = (edo.izquierda - edo.derecha).xreplace({edo.derivadas[0]: derivada})
                if sympy.simplify(resto) != 0:
                    return False
                continue
            if s.lhs == edo.y and self._cumple(s.rhs, edo):
                continue
            s = s.xreplace({edo.y: Y})
            try:
                ok, _ = sympy.checkodesol(ode, s, solve_for_func=False)
            except Exception:
                ok = False
            if not ok:
                return False
        return True

    @staticmethod
    def _cumple(valor: Any, edo: Edo) -> bool:
        """
        y = valor cumple la ecuación: se deriva y se sustituye. log(Abs(u)) se deriva como log(u) (es la
        misma derivada): con el valor absoluto, checkodesol se quedaba atascado simplificando.
        """
        sin_abs = valor.replace(lambda e: isinstance(e, sympy.log) and isinstance(e.args[0], sympy.Abs),
                                lambda e: sympy.log(e.args[0].args[0]))
        cambios = {edo.y: sin_abs}
        derivada = sin_abs
        for d in edo.derivadas:
            derivada = sympy.diff(derivada, edo.x)
            cambios[d] = derivada
        try:
            residuo = (edo.izquierda - edo.derecha).xreplace(cambios)
            if sympy.simplify(residuo) == 0:
                return True
            # exp de un exponente real es positivo, también fuera del caso
            # aditivo que SymPy simplifica automáticamente.
            cambios_log = {log: log.args[0].args[0] for log in residuo.atoms(sympy.log)
                           if log.args[0].func == sympy.exp
                           and log.args[0].args[0].is_real is not False}
            return sympy.simplify(residuo.xreplace(cambios_log)) == 0
        except Exception:
            return False

    def _con_sympy(self, ode: Any, edo: Edo, Y: Any, avisos: List[str]) -> Optional[List[Any]]:
        """La solución de dsolve, sin pasos (con las condiciones, si las hay)."""
        ics = {}
        for cond in edo.condiciones:
            izq = Y.diff(edo.x, cond.orden).subs(edo.x, cond.punto) if cond.orden else Y.subs(edo.x, cond.punto)
            ics[izq] = cond.valor
        try:
            resultado = sympy.dsolve(ode, Y, ics=ics or None)
        except NotImplementedError:
            raise
        except Exception:
            # Algún método de SymPy falla por dentro (el de Riccati, con y' = y^2 + x^2): se prueban los demás
            resultado = None
            for metodo in sympy.classify_ode(ode, Y):
                if metodo.endswith("_Integral") or metodo == "default" or metodo == "order":
                    continue
                try:
                    resultado = sympy.dsolve(ode, Y, ics=ics or None, hint=metodo)
                    break
                except Exception:
                    continue
            if resultado is None:
                raise NotImplementedError()
        resultado = resultado if isinstance(resultado, list) else [resultado]
        constantes = sorted({s for r in resultado for s in r.free_symbols if re.fullmatch(r"C\d+", s.name)},
                            key=lambda s: s.name)
        cambio = {Y: edo.y}
        if len(constantes) == 1:
            cambio[constantes[0]] = C
        soluciones = [sympy.Eq(r.lhs.xreplace(cambio), r.rhs.xreplace(cambio)) for r in resultado]
        if any(s.has(sympy.Order) for s in soluciones):
            avisos.append(tr("NOTA: SymPy da la solución como una serie de potencias: es aproximada, y O(...) indica el "
                             "orden de los términos que se dejan fuera."))
        avisos.append(tr("NOTA: por ahora hay explicación paso a paso para las ecuaciones de primer orden "
                         "separables, lineales, de Bernoulli, homogéneas, exactas (o con factor integrante) y "
                         "reducibles a separables, y' = F(a*x + b*y + c); para las lineales de orden superior con "
                         "coeficientes constantes y las de Cauchy-Euler (y las no homogéneas de orden 2, por "
                         "coeficientes indeterminados o variación de parámetros), con una solución conocida (y1 = ...), "
                         "por la transformada de Laplace o en serie de potencias (con coeficientes polinómicos y x = 0 "
                         "punto ordinario); y para las de Riccati (con y1 = ...), Clairaut y las de orden 2 sin y o sin "
                         "x. Esta ecuación la resuelve SymPy, sin pasos."))
        return soluciones

    # --- Textos ---

    def _dominio_solucion(self, solucion: Any, edo: Edo) -> List[Any]:
        """Restricciones reales antes de simplificar la sustitución en la EDO.

        Se expresan como condiciones, sin inventar extremos de intervalos con
        constantes simbólicas. Incluyen la solución y todos los lados originales.
        """
        cambios = {edo.y: solucion.rhs}
        cambios.update({d: sympy.diff(solucion.rhs, edo.x, n)
                        for n, d in enumerate(edo.derivadas, 1)})
        restricciones = list(getattr(self, "_restricciones", {}).get(solucion, []))
        for expr in (solucion.rhs, edo.izquierda, edo.derecha, *cambios.values()):
            for nodo in sympy.preorder_traversal(expr):
                condicion = None
                if nodo.func == sympy.log:
                    argumento = nodo.args[0].xreplace(cambios)
                    condicion = (sympy.Ne(argumento.args[0], 0) if argumento.func == sympy.Abs
                                 else sympy.Gt(argumento, 0))
                elif nodo.is_Pow and nodo.exp.is_Rational:
                    base = nodo.base.xreplace(cambios)
                    if nodo.exp.q % 2 == 0:
                        condicion = sympy.Gt(base, 0) if nodo.exp < 0 else sympy.Ge(base, 0)
                    elif nodo.exp < 0:
                        condicion = sympy.Ne(base, 0)
                elif nodo.func in (sympy.tan, sympy.sec):
                    condicion = sympy.Ne(sympy.cos(nodo.args[0].xreplace(cambios)), 0)
                elif nodo.func in (sympy.cot, sympy.csc):
                    condicion = sympy.Ne(sympy.sin(nodo.args[0].xreplace(cambios)), 0)
                if condicion is not None and condicion != sympy.true and condicion not in restricciones:
                    restricciones.append(condicion)
        return restricciones

    @staticmethod
    def _solucion_texto(s: Any) -> str:
        return f"{texto(s.lhs)} = {texto(s.rhs)}"

    @staticmethod
    def _condicion_texto(cond: Condicion, y: Any) -> str:
        return f"{nombre_derivada(y, cond.orden)}({texto(cond.punto)}) = {texto(cond.valor)}"

    # --- La explicación ---

    def _explicar(self, edo: Edo, pasos: List[PasoCalculo], avisos: List[str]) -> Tuple[List[Any], str]:
        x, y = edo.x, edo.y
        self._edo_actual = edo
        self._restricciones = {}
        # Soluciones que valen con una condición (y = v^2 con v = sqrt(y) >= 0): el método las comprueba
        # por su cuenta y la comprobación dice dónde valen
        self._condiciones: Dict[Any, str] = {}
        self._avisos = avisos
        self._notas_metodo: List[str] = []  # por qué no se usó un método pedido: se conservan siempre
        pasos.append(PasoCalculo(
            tr("Planteamiento"),
            regla=tr("una ecuación diferencial relaciona una función {y}({x}) con sus derivadas. Resolverla es hallar "
                     "todas las funciones que la cumplen: la solución general, con tantas constantes como el orden. "
                     "El orden es el de la derivada más alta.", x=x, y=y),
            partes=tr("la ecuación es {ecuacion}; la incógnita es la función {y}({x}); la derivada más alta es {d}, "
                      "así que es de orden {orden}.", ecuacion=edo.enunciado,
                      x=x, y=y, d=edo.derivadas[-1], orden=edo.orden),
            queda=tr("ecuación de orden {orden}", orden=edo.orden)))
        self._por_tramos: set = set()
        saltos = _con_saltos(edo.izquierda - edo.derecha)
        if edo.laplace or saltos:
            pasos_laplace: List[PasoCalculo] = []
            resultado = _Laplace(self, edo, pasos_laplace, avisos).resolver()
            if resultado is not None:
                pasos.extend(pasos_laplace)
                soluciones, metodo = resultado
                self._comprobacion(edo, [s for s in soluciones if s not in self._por_tramos], pasos)
                return soluciones, metodo
            if saltos:
                raise SinExplicacion()  # con escalones o deltas no hay otro método con pasos
        if edo.orden > 1:
            orden_superior = _OrdenSuperior(self, edo, pasos, avisos)
            antes = len(pasos)
            resultado = orden_superior.resolver()
            if resultado is None:
                del pasos[antes:]
                if edo.orden == 2 and edo.y1 is None:
                    reducidas = self._reducir_orden(edo, pasos, avisos)
                    if reducidas is not None:
                        if edo.condiciones:
                            particulares = []
                            for rama in reducidas:
                                inicio_condiciones = len(pasos)
                                try:
                                    valor = orden_superior.condiciones(rama.rhs, edo.condiciones)
                                except (SinExplicacion, ValueError):
                                    del pasos[inicio_condiciones:]
                                    continue
                                if all(sympy.simplify(sympy.diff(valor, x, c.orden).subs(x, c.punto) - c.valor) == 0
                                       for c in edo.condiciones):
                                    particulares.append(sympy.Eq(y, valor))
                                else:
                                    del pasos[inicio_condiciones:]
                            if not particulares:
                                raise SinExplicacion()
                            reducidas = particulares
                        self._comprobacion(edo, reducidas, pasos)
                        return reducidas, tr("reducible de orden (p = y')")
                raise SinExplicacion()
            soluciones, metodo = resultado
            if edo.condiciones and orden_superior.serie_texto is not None:
                soluciones = [sympy.Eq(y, orden_superior.condiciones_serie(soluciones[0].rhs, edo.condiciones))]
            elif edo.condiciones:
                soluciones = [sympy.Eq(y, orden_superior.condiciones(soluciones[0].rhs, edo.condiciones))]
            self._comprobacion(edo, soluciones, pasos)
            return soluciones, metodo
        yp = edo.derivadas[0]
        pasos_clairaut: List[PasoCalculo] = []
        soluciones = self._clairaut(edo, pasos_clairaut, avisos)
        if soluciones is not None:
            pasos.extend(pasos_clairaut)
            if edo.condiciones:
                soluciones = self._condicion_inicial(soluciones, edo.condiciones[0], x, y, pasos)
            self._comprobacion(edo, soluciones, pasos)
            return soluciones, tr("ecuación de Clairaut")
        despeje: List[PasoCalculo] = []
        f = self._despejar_derivada(edo, yp, despeje)

        # El primer método que reconoce la ecuación (cada uno devuelve None si no es de su tipo, antes
        # de añadir pasos). Las lineales parten de la ecuación escrita, sin despejar y'.
        exacta = (lambda *a: self._exacta(*a, edo=edo), tr("ecuación exacta"), False)
        metodos = ((lambda *a: self._riccati(*a, edo=edo), tr("ecuación de Riccati (cambio y = y1 + 1/v)"), True),
                   (self._separable, tr("ecuación separable"), True),
                   (lambda *a: self._lineal(*a, edo=edo), tr("ecuación lineal de primer orden (factor integrante)"),
                    False),
                   (self._homogenea, tr("ecuación homogénea (cambio y = u*x)"), True),
                   (lambda *a: self._bernoulli(*a, edo=edo), tr("ecuación de Bernoulli (cambio v = y^(1 - n))"),
                    False),
                   exacta,
                   (self._reducible, tr("reducible a separable (cambio u = a*x + b*y + c)"), True))
        if edo.diferencial:  # escrita como M dx + N dy = 0: primero, el método de las exactas
            metodos = (exacta,) + tuple(m for m in metodos if m is not exacta)
        for resolver, metodo, con_despeje in metodos:
            pasos_metodo = list(despeje) if con_despeje else []
            soluciones = resolver(f, x, y, pasos_metodo, avisos)
            if soluciones is not None:
                pasos.extend(pasos_metodo)
                break
        else:
            raise SinExplicacion()

        if edo.condiciones:
            soluciones = self._condicion_inicial(soluciones, edo.condiciones[0], x, y, pasos)
        self._comprobacion(edo, soluciones, pasos)
        return soluciones, metodo

    def _comprobacion(self, edo: Edo, soluciones: List[Any], pasos: List[PasoCalculo]) -> None:
        """Se deriva cada solución explícita y se sustituye en la ecuación: los dos lados valen lo mismo."""
        x, y = edo.x, edo.y
        lineas = []
        for s in soluciones:
            if s in getattr(self, "_por_tramos", set()):
                continue  # ya comprobada por su método (por tramos, o la serie hasta su orden)
            if s.lhs != y or not s.rhs.has(x):
                continue  # implícitas y constantes: las comprueba SymPy (las constantes ya se vieron)
            # log(Abs(u)) tiene la misma derivada que log(u): sin el valor absoluto no salen sign(x)
            # ni trozos; al escribir el resultado se vuelve a poner
            abs_logs = {sympy.log(e.args[0].args[0]): e for e in s.rhs.atoms(sympy.log)
                        if isinstance(e.args[0], sympy.Abs)}
            sin_abs = s.rhs.xreplace({v: k for k, v in abs_logs.items()})
            valores, calculo = {y: s.rhs}, {y: sin_abs}
            derivada = sin_abs
            for n, d in enumerate(edo.derivadas, 1):
                derivada = min((sympy.diff(derivada, x), sympy.simplify(sympy.diff(derivada, x)),
                                sympy.factor(sympy.diff(derivada, x))), key=lambda e: len(texto(e)))
                calculo[d] = derivada
                valores[d] = derivada.xreplace(abs_logs)
                lineas.append(tr("Derivamos: {d} = {valor}.", d=d, valor=texto(valores[d])))
            for lado, expr in ((tr("Lado izquierdo"), edo.izquierda), (tr("Lado derecho"), edo.derecha)):
                escrita = sustituir(expr, valores)
                valor = sympy.simplify(expr.xreplace(calculo)).xreplace(abs_logs)
                cuenta = escrita if escrita == texto(valor) else f"{escrita} = {texto(valor)}"
                lineas.append(f"{lado}: {cuenta}.")
            if s in self._condiciones:
                lineas.append(tr("Los dos lados valen lo mismo {condicion}: {solucion} cumple la ecuación.",
                                 condicion=self._condiciones[s], solucion=self._solucion_texto(s)))
                continue
            lineas.append(tr("Los dos lados valen lo mismo: {solucion} cumple la ecuación.",
                             solucion=self._solucion_texto(s)))
        if lineas:
            pasos.append(PasoCalculo(
                tr("Comprobación"),
                regla=tr("una solución tiene que cumplir la ecuación: se deriva y se sustituye en los dos lados."),
                partes=tr("la ecuación es {ecuacion}.", ecuacion=edo.enunciado),
                calculo=tuple(lineas),
                queda=tr("la solución es correcta")))

    def _despejar_derivada(self, edo: Edo, yp: Any, pasos: List[PasoCalculo]) -> Any:
        """f(x, y) en y' = f(x, y); si y' no está sola, el paso de despejarla."""
        izq, der = edo.izquierda, edo.derecha
        if izq == yp and not der.has(yp):
            return der
        if der == yp and not izq.has(yp):
            return izq
        todo = sympy.expand(izq - der)
        if not todo.is_polynomial(yp) or sympy.degree(todo, yp) != 1:
            raise SinExplicacion()
        lineas, valor = despejar(izq, der, yp)
        valor = sympy.factor_terms(sympy.together(valor)) if sympy.together(valor) != valor else valor
        pasos.append(PasoCalculo(
            tr("Despejar {yp}", yp=yp),
            regla=tr("para reconocer el tipo de ecuación se escribe {yp} = f({x}, {y}): la ecuación es de primer grado "
                     "en {yp}, y se despeja como una ecuación de primer grado.", yp=yp, x=edo.x, y=edo.y),
            partes=tr("la ecuación es {ecuacion}.", ecuacion=f"{texto(izq)} = {texto(der)}"),
            calculo=tuple(lineas),
            queda=f"{yp} = {texto(valor)}"))
        return valor

    # --- Separables ---

    def _separable(self, f: Any, x: Any, y: Any, pasos: List[PasoCalculo], avisos: List[str],
                   nombre: Optional[str] = None) -> Optional[List[Any]]:
        """Las soluciones de y' = f si f = g(x)*h(y) (None si no se separa). nombre: 'u' en un cambio."""
        if not f.has(y):
            g, h = f, sympy.S.One
        else:
            partes = sympy.separatevars(sympy.factor_terms(f), [x, y], dict=True)
            if partes is None:
                return None
            g, h = partes["coeff"] * partes[x], partes[y]
            if g.has(y) or h.has(x):
                return None
        yp = sympy.Symbol(nombre_derivada(y, 1))
        if h == 1:
            pasos.append(PasoCalculo(
                tr("Tipo de ecuación: integración directa"),
                regla=tr("si {yp} solo depende de {x}, {yp} = g({x}), la función {y} es una primitiva de g: "
                         "{y} = ∫ g({x}) d{x} + C.", yp=yp, x=x, y=y),
                partes=tr("g({x}) = {g}; no aparece {y}.", x=x, g=texto(g), y=y),
                queda=f"{y} = ∫ {entre_parentesis(g)} d{x}"))
            primitiva = self._integrar(g, x, pasos)
            solucion = _con_abs(primitiva) + C
            pasos.append(PasoCalculo(
                tr("Solución general"),
                regla=tr("se suma la constante de integración C: cada valor de C da una solución."),
                calculo=self._lineas_abs(primitiva),
                queda=f"{y} = {texto(solucion)}"))
            return [sympy.Eq(y, solucion)]

        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: separable"),
            regla=tr("una ecuación de primer orden es separable si se puede escribir {yp} = g({x})*h({y}): un factor "
                     "que solo tiene {x} por otro que solo tiene {y}.", yp=yp, x=x, y=y),
            partes=tr("{yp} = {f}, con g({x}) = {g} y h({y}) = {h}.", yp=yp, f=texto(f), x=x, y=y, g=texto(g),
                      h=texto(h)),
            queda=tr("separable")))

        izq_int = sympy.factor_terms(1 / h)
        pasos.append(PasoCalculo(
            tr("Separar las variables"),
            regla=tr("{yp} es d{y}/d{x}. Se dividen los dos lados entre h({y}) (suponiendo que no vale 0) y se "
                     "multiplican por d{x}: todo lo que tiene {y} queda con d{y}, y todo lo que tiene {x}, con d{x}.",
                     yp=yp, x=x, y=y),
            partes=tr("h({y}) = {h} y g({x}) = {g}.", y=y, h=texto(h), x=x, g=texto(g)),
            calculo=(f"d{y}/d{x} = {producto(g, h)}",),
            queda=f"{factor(izq_int)} d{y} = {factor(g)} d{x}"))

        constantes = self._soluciones_constantes(h, y, x, g, pasos)

        primitiva_y = self._integrar(izq_int, y, pasos)
        primitiva_x = self._integrar(g, x, pasos)
        izq, der = _con_abs(primitiva_y), _con_abs(primitiva_x)
        # Los logaritmos que ya estaban en la EDO conservan su dominio original.
        izq = izq.xreplace({_con_abs(log): log for log in h.atoms(sympy.log)})
        lineas = [f"∫ {factor(izq_int)} d{y} = {texto(primitiva_y)}.",
                  f"∫ {factor(g)} d{x} = {texto(primitiva_x)}."]
        lineas += self._lineas_abs(primitiva_y, primitiva_x, protegidos=h.atoms(sympy.log))
        lineas.append(tr("Las constantes de integración de los dos lados se juntan en una sola, C, en el lado de {x}.",
                         x=x))
        pasos.append(PasoCalculo(
            tr("Integrar los dos lados"),
            regla=tr("si dos expresiones son iguales, sus integrales se diferencian en una constante: ∫ d{y}/h({y}) = "
                     "∫ g({x}) d{x} + C.", x=x, y=y),
            partes=tr("se integra cada lado respecto a su variable (los pasos de cada integral están arriba)."),
            calculo=tuple(lineas),
            queda=f"{texto(izq)} = {texto(der + C)}"))

        despeje = Despeje(y, [x])
        try:
            explicitas = despeje.resolver(izq, der + C)
        except SinExplicacion:
            explicitas = None
        if explicitas:
            # Una reparametrización C -> -C debe transformar también las
            # restricciones. Aquí se conserva C si el despeje impuso alguna.
            explicitas = [self._simplificada(s, despeje.lineas, renombrar=not despeje.restricciones)
                          for s in explicitas]
            if len(explicitas) == 1 and despeje.lineas[-1] == tr("Queda {ecuacion}.",
                                                                 ecuacion=f"{y} = {texto(explicitas[0])}"):
                despeje.lineas.pop()  # lo dice el Queda: del paso
            pasos.append(PasoCalculo(
                tr("Despejar {y}", y=y),
                regla=tr("se deshace, de fuera hacia dentro, lo que envuelve a {y}: lo que suma pasa restando, lo que "
                         "multiplica pasa dividiendo, y cada función se deshace con su inversa (log con exp, una "
                         "potencia con una raíz). Una expresión que solo tiene constantes es otra constante.", y=y),
                partes=tr("la ecuación es {ecuacion}.", ecuacion=f"{texto(izq)} = {texto(der + C)}"),
                calculo=tuple(despeje.lineas),
                queda="; ".join(f"{y} = {texto(s)}" for s in explicitas)))
            soluciones = [sympy.Eq(y, s) for s in explicitas]
            for solucion in soluciones:
                restricciones = [r.subs(y, solucion.rhs) for r in despeje.restricciones]
                if restricciones:
                    self._restricciones[solucion] = restricciones
                    self._condiciones[solucion] = tr("donde {restricciones}",
                                                   restricciones="; ".join(texto(r) for r in restricciones))
            if h == sympy.sqrt(y):
                avisos.append(tr("En y = 0 puede fallar la unicidad: también pueden existir soluciones que "
                                 "empalman un tramo constante con una rama no constante. Las fórmulas "
                                 "indicadas se validan en sus propios intervalos."))
        else:
            avisos.append(tr("NOTA: la solución queda en forma implícita (sin despejar {y}).", y=y))
            soluciones = [sympy.Eq(izq, der + C)]

        for r in constantes:
            incluida = self._incluida(r, soluciones, y)
            if incluida is not None:
                pasos.append(PasoCalculo(
                    tr("La solución constante {y} = {r}", y=y, r=texto(r)),
                    regla=tr("al dividir entre h({y}) se supuso h({y}) distinto de 0; hay que ver si la solución "
                             "constante sale de la general.", y=y),
                    calculo=(tr("Con C = {c}, la solución general da {y} = {r}: está incluida.", c=texto(incluida),
                                y=y, r=texto(r)),),
                    queda=tr("incluida en la solución general")))
            else:
                pasos.append(PasoCalculo(
                    tr("La solución constante {y} = {r}", y=y, r=texto(r)),
                    regla=tr("al dividir entre h({y}) se supuso h({y}) distinto de 0; hay que ver si la solución "
                             "constante sale de la general.", y=y),
                    calculo=(tr("Ningún valor de C da {y} = {r}: se añade aparte (es una solución singular).", y=y,
                                r=texto(r)),),
                    queda=f"{y} = {texto(r)}"))
                soluciones.append(sympy.Eq(y, r))
        return soluciones

    def _soluciones_constantes(self, h: Any, y: Any, x: Any, g: Any, pasos: List[PasoCalculo]) -> List[Any]:
        """Las raíces reales de h(y): y = r cumple la ecuación (y' = 0 y h(r) = 0)."""
        raices = _raices_reales(h, y, x)
        if not raices:
            return []
        yp = sympy.Symbol(nombre_derivada(y, 1))
        lineas = [tr("{y} = {r}: {yp} = 0 y g({x})*h({r}) = {g}*{h} = 0.", y=y, r=texto(r), yp=yp, x=x,
                     g=entre_parentesis(g), h=entre_parentesis(h.subs(y, sympy.UnevaluatedExpr(r))))
                  for r in raices if not r.has(K)]
        if any(r.has(K) for r in raices):
            lineas.append(tr("{y} = {r} (con {k} cualquier número entero): {yp} = 0 y h({y}) = 0.", y=y, k=K, yp=yp,
                             r="; ".join(texto(r) for r in raices if r.has(K))))
        pasos.append(PasoCalculo(
            tr("Soluciones constantes"),
            regla=tr("si h({r}) = 0 para un número {r}, la función constante {y} = {r} es solución: su derivada es 0 "
                     "y el lado derecho también vale 0. Son las que se pierden al dividir entre h({y}).", y=y,
                     r="r"),
            partes=tr("h({y}) = {h} vale 0 en {y} = {raices}.", y=y, h=texto(h),
                      raices=", ".join(texto(r) for r in raices)),
            calculo=tuple(lineas),
            queda="; ".join(f"{y} = {texto(r)}" for r in raices)))
        return raices

    @staticmethod
    def _incluida(r: Any, soluciones: List[Any], y: Any) -> Optional[Any]:
        """El valor de C con el que la solución general da y = r (None si ninguno)."""
        for s in soluciones:
            if s.lhs != y:
                continue
            if sympy.simplify(s.rhs.subs(C, 0) - r) == 0:
                return sympy.S.Zero
            try:
                valores = sympy.solve(sympy.Eq(s.rhs, r), C)
            except Exception:
                valores = []
            if valores and not any(v.free_symbols - {C, K} for v in valores):
                return valores[0]
        return None

    def _integrar(self, f: Any, var: Any, pasos: List[PasoCalculo]) -> Any:
        """La primitiva de f, con los pasos de Integrar (sin la constante); las constantes, en una línea."""
        if not f.has(var):
            return f * var
        primitiva, _, pasos_integral, avisos = self.calculo._primitiva(f, var)
        if primitiva.has(sympy.Integral):
            raise SinExplicacion()
        pasos.extend(pasos_integral)
        destino = getattr(self, "_avisos", None)
        if destino is not None:
            destino.extend(a for a in avisos if a not in destino)
        return primitiva

    @staticmethod
    def _lineas_abs(*primitivas: Any, protegidos=()) -> Tuple[str, ...]:
        """Por qué log(y) pasa a log(Abs(y)): una línea para todos los logaritmos que cambian."""
        cambios = []
        for primitiva in primitivas:
            for log in sorted(primitiva.atoms(sympy.log), key=texto):
                if log not in protegidos and _con_abs(log) != log:
                    cambios.append(tr("{antes} se escribe {despues}", antes=texto(log), despues=texto(_con_abs(log))))
        if not cambios:
            return ()
        return (tr("La primitiva de 1/u es log(Abs(u)): con el valor absoluto vale también donde u es negativo. "
                   "Así, {cambios}.", cambios="; ".join(cambios)),)

    @staticmethod
    def _simplificada(s: Any, lineas: List[str], renombrar: bool = True) -> Any:
        simple = sympy.simplify(s)
        if len(texto(simple)) < len(texto(s)) and texto(simple) != texto(s):
            lineas.append(tr("Simplificamos: {antes} = {despues}.", antes=texto(s), despues=texto(simple)))
            s = simple
        if renombrar and s.has(C):
            # -C*exp(x)/(1 - C*exp(x)): con -C en lugar de C (otra constante cualquiera) quedan menos signos
            signos = lambda e: texto(e).count("-") + texto(e).count("(-")
            # 1/(-x - C) se escribe -1/(x + C)
            sin_menos = lambda e: e.replace(lambda f: f.is_Pow and f.exp == -1 and f.base.could_extract_minus_sign(),
                                            lambda f: -1 / (-f.base))
            opuesta = min((s.subs(C, -C), sin_menos(s.subs(C, -C)), sympy.simplify(s.subs(C, -C))), key=signos)
            if signos(opuesta) < signos(s):
                lineas.append(tr("-C es también una constante cualquiera: cambiando C por -C, {antes} se escribe "
                                 "{despues}.", antes=texto(s), despues=texto(opuesta)))
                s = opuesta
        return s

    # --- Lineales de primer orden ---

    def _lineal(self, f: Any, x: Any, y: Any, pasos: List[PasoCalculo], avisos: List[str],
                edo: Optional[Edo] = None) -> Optional[List[Any]]:
        """y' + P(x)*y = Q(x): factor integrante m(x) = exp(∫ P dx), (m*y)' = m*Q, y se integra."""
        a = sympy.simplify(sympy.diff(f, y))
        if a.has(y) or a == 0:
            return None
        Q = sympy.simplify(f - a * y)
        if Q.has(y):
            return None
        P = -a
        yp = sympy.Symbol(nombre_derivada(y, 1))
        if P.could_extract_minus_sign():
            estandar = f"{yp} - {producto(-P, y)} = {texto(Q)}"
        else:
            estandar = f"{yp} + {producto(P, y)} = {texto(Q)}"
        lineas = self._forma_lineal(edo, x, y, yp, estandar) if edo is not None else []
        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: lineal de primer orden"),
            regla=tr("una ecuación de primer orden es lineal si se puede escribir {yp} + P({x})*{y} = Q({x}): {y} y "
                     "{yp} aparecen sin potencias ni funciones, multiplicadas solo por expresiones con {x}.",
                     yp=yp, x=x, y=y),
            partes=tr("{estandar}, con P({x}) = {P} y Q({x}) = {Q}.", estandar=estandar, x=x, P=texto(P),
                      Q=texto(Q)),
            calculo=tuple(lineas),
            queda=estandar))

        # El factor integrante
        primitiva = self._integrar(P, x, pasos)
        exponente = _con_abs(primitiva)
        lineas = [f"∫ {factor(P)} d{x} = {texto(primitiva)}."]
        lineas += self._lineas_abs(primitiva)
        factor_m = sympy.exp(exponente)
        if texto(factor_m) != f"exp({texto(exponente)})":
            lineas.append(f"m({x}) = exp({texto(exponente)}) = {texto(factor_m)}.")
        sin_abs = factor_m.replace(lambda e: isinstance(e, sympy.Abs), lambda e: e.args[0])
        if sin_abs != factor_m:
            lineas.append(tr("Basta un factor integrante: en cada intervalo en que el signo no cambia, {con} es "
                             "{sin} o su opuesto, y multiplicar por -1 no cambia la ecuación. Tomamos m({x}) = {sin}.",
                             con=texto(factor_m), sin=texto(sin_abs), x=x))
            factor_m = sin_abs
        pasos.append(PasoCalculo(
            tr("Factor integrante"),
            regla=tr("se multiplica la ecuación por m({x}) = exp(∫ P({x}) d{x}). Así m' = m*P, y el lado izquierdo "
                     "queda como la derivada de un producto. Basta uno: la constante de esta integral no hace "
                     "falta.", x=x),
            partes=tr("P({x}) = {P}.", x=x, P=texto(P)),
            calculo=tuple(lineas),
            queda=f"m({x}) = {texto(factor_m)}"))

        # Multiplicar y reconocer la derivada del producto
        derivada_m = sympy.simplify(sympy.diff(factor_m, x))
        lado_derecho = sympy.simplify(factor_m * Q)
        m_y = self._por(factor_m, y)
        m_p = sympy.simplify(factor_m * P)
        signo, m_p = ("-", -m_p) if m_p.could_extract_minus_sign() else ("+", m_p)
        lineas = [tr("Multiplicamos los dos lados por {m}: {ecuacion}.", m=texto(factor_m),
                     ecuacion=f"{self._por(factor_m, yp)} {signo} {self._por(m_p, y)} = {texto(lado_derecho)}"),
                  tr("La derivada de m es {dm}, que es m*P = {m}*{P}: el lado izquierdo es m*{yp} + m'*{y}, la "
                     "derivada de m*{y} (regla del producto).", dm=texto(derivada_m), m=factor(factor_m),
                     P=factor(P), yp=yp, y=y)]
        pasos.append(PasoCalculo(
            tr("Multiplicar por el factor integrante"),
            regla=tr("con m' = m*P, el lado izquierdo m*{yp} + m*P*{y} es m*{yp} + m'*{y} = (m*{y})': la ecuación "
                     "queda (m*{y})' = m*Q.", yp=yp, y=y),
            partes=tr("m({x}) = {m}.", x=x, m=texto(factor_m)),
            calculo=tuple(lineas),
            queda=f"({m_y})' = {texto(lado_derecho)}"))

        # Integrar
        integral = _con_abs(self._integrar(lado_derecho, x, pasos))
        pasos.append(PasoCalculo(
            tr("Integrar los dos lados"),
            regla=tr("la integral de la derivada de m*{y} es m*{y}; al otro lado, la integral de m*Q más la "
                     "constante de integración C.", y=y),
            partes=tr("se integra {f} respecto a {x} (los pasos están arriba).", f=texto(lado_derecho), x=x),
            calculo=(f"∫ {factor(lado_derecho)} d{x} = {texto(integral)}.",),
            queda=f"{m_y} = {texto(integral + C)}"))

        # Despejar y
        despeje = Despeje(y, [x])
        (valor,) = despeje.resolver(factor_m * y, integral + C)
        repartido = sympy.expand(valor)
        if repartido != valor and len(texto(repartido)) <= len(texto(valor)) + 4:
            despeje.lineas.append(tr("Repartimos la división entre cada término: {y} = {valor}.", y=y,
                                     valor=texto(repartido)))
            valor = repartido
        valor = self._simplificada(valor, despeje.lineas)
        pasos.append(PasoCalculo(
            tr("Despejar {y}", y=y),
            regla=tr("se divide entre m({x}), que no vale 0 en el intervalo en que se resuelve.", x=x),
            partes=tr("la ecuación es {ecuacion}.", ecuacion=f"{m_y} = {texto(integral + C)}"),
            calculo=tuple(despeje.lineas),
            queda=f"{y} = {texto(valor)}"))
        return [sympy.Eq(y, valor)]

    @staticmethod
    def _por(m: Any, y: Any) -> str:
        """m*y como se escribe: x^2*y, y/cos(x) (no (1/cos(x))*y)."""
        if m == 1:
            return texto(y)
        if (m.is_Mul or m.is_Pow or m.is_Rational) and sympy.fraction(m)[1] != 1:
            return texto(m * y)
        return f"{factor(m)}*{y}"

    def _forma_lineal(self, edo: Edo, x: Any, y: Any, yp: Any, estandar: str) -> List[str]:
        """Cómo se llega de la ecuación escrita a y' + P*y = Q: agrupar y dividir entre el coeficiente de y'."""
        todo = sympy.expand(edo.izquierda - edo.derecha)
        a1, a0 = todo.coeff(yp), todo.coeff(y)
        resto = sympy.expand(todo - a1 * yp - a0 * y)
        if a1.has(y) or a0.has(y) or a1.has(yp) or a0.has(yp) or resto.has(y) or resto.has(yp):
            return []
        lineas = []
        agrupada = f"{self._por(a1, yp)} {'-' if a0.could_extract_minus_sign() else '+'} " \
                   f"{self._por(-a0 if a0.could_extract_minus_sign() else a0, y)} = {texto(-resto)}"
        ya_agrupada = sympy.expand(edo.izquierda - a1 * yp - a0 * y) == 0 and sympy.expand(edo.derecha + resto) == 0
        if not ya_agrupada:
            lineas.append(tr("Dejamos a la izquierda los términos con {yp} y con {y}, y a la derecha los demás: "
                             "{ecuacion}.", yp=yp, y=y, ecuacion=agrupada))
        if a1 != 1:
            lineas.append(tr("Dividimos los dos lados entre {a}, lo que multiplica a {yp}: {ecuacion}.",
                             a=texto(a1), yp=yp, ecuacion=estandar))
        return lineas

    # --- Bernoulli ---

    def _bernoulli(self, f: Any, x: Any, y: Any, pasos: List[PasoCalculo], avisos: List[str],
                   edo: Optional[Edo] = None) -> Optional[List[Any]]:
        """
        y' + P(x)*y = Q(x)*y^n (n distinto de 0 y 1): con v = y^(1 - n), v' = (1 - n)*y^(-n)*y', y al
        dividir entre y^n queda la lineal v' + (1 - n)*P*v = (1 - n)*Q.
        """
        grupos: Dict[Any, Any] = {}
        for t in sympy.Add.make_args(sympy.expand(f)):
            coef, parte = t.as_independent(y, as_Add=False)
            if parte == 1:
                return None  # un término sin y: no es de Bernoulli
            base, exponente = parte.as_base_exp()
            if base != y or not exponente.is_Rational:
                return None
            grupos[exponente] = grupos.get(exponente, 0) + coef
        otras = [e for e in grupos if e != 1]
        if 1 not in grupos or len(otras) != 1 or len(grupos) != 2:
            return None
        n = otras[0]
        P, Q = sympy.factor_terms(-grupos[1]), sympy.factor_terms(grupos[n])
        if P == 0 or Q == 0:
            return None
        yp = sympy.Symbol(nombre_derivada(y, 1))
        v = sympy.Symbol("v", real=True)
        vp = sympy.Symbol(nombre_derivada(v, 1))
        k = 1 - n  # el exponente del cambio
        y_n = sympy.Pow(y, n, evaluate=False)
        estandar = f"{yp}{_mas(P, y)} = {texto(Q * y_n)}"
        lineas = []
        if edo is not None:
            todo = sympy.expand(edo.izquierda - edo.derecha)
            a1 = sympy.factor_terms(todo.coeff(yp))
            if not a1.has(y) and not a1.has(yp):
                izq_bien = sympy.expand(edo.izquierda - a1 * yp - a1 * P * y) == 0
                der_bien = sympy.expand(edo.derecha - a1 * Q * y ** n) == 0
                if not (izq_bien and der_bien):
                    lineas.append(tr("Dejamos a la izquierda los términos con {yp} y con {y}, y a la derecha el de "
                                     "{yn}: {ecuacion}.", yp=yp, y=y, yn=texto(y_n),
                                     ecuacion=f"{MotorEdo._por(a1, yp)}{_mas(sympy.expand(a1 * P), y)} = "
                                              f"{texto(sympy.expand(a1 * Q) * y_n)}"))
                if a1 != 1:
                    lineas.append(tr("Dividimos los dos lados entre {a}, lo que multiplica a {yp}: {ecuacion}.",
                                     a=texto(a1), yp=yp, ecuacion=estandar))
        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: de Bernoulli"),
            regla=tr("una ecuación es de Bernoulli si se puede escribir {yp} + P({x})*{y} = Q({x})*{y}^n, con n "
                     "distinto de 0 y de 1 (con n = 0 o n = 1 sería lineal).", yp=yp, x=x, y=y),
            partes=tr("{estandar}: P({x}) = {P}, Q({x}) = {Q} y n = {n}.", estandar=estandar, x=x, P=texto(P),
                      Q=texto(Q), n=texto(n)),
            calculo=tuple(lineas),
            queda=estandar))

        P_v, Q_v = sympy.factor_terms(k * P), sympy.factor_terms(k * Q)
        y_menos_n = sympy.Pow(y, -n, evaluate=False)
        y_k = sympy.Pow(y, k, evaluate=False) if k != 1 else y
        dividida = f"{texto(y_menos_n * yp)}{_mas(P, y_k)} = {texto(Q)}"
        lineas = [tr("Dividimos los dos lados entre {yn}: {ecuacion}.", yn=texto(y_n), ecuacion=dividida),
                  tr("Con v = {yk}, la regla de la cadena da v' = {dv}; así {ymn} = {vk}.", yk=texto(y_k),
                     dv=texto(k * y_menos_n * yp), ymn=texto(y_menos_n * yp), vk=texto(vp / k)),
                  tr("Sustituimos: {ecuacion}.", ecuacion=f"{texto(vp / k)}{_mas(P, v)} = {texto(Q)}")]
        lineal = f"{vp}{_mas(P_v, v)} = {texto(Q_v)}"
        if k != 1:
            lineas.append(tr("Multiplicamos los dos lados por {k}: {ecuacion}.", k=texto(k), ecuacion=lineal))
        pasos.append(PasoCalculo(
            tr("Cambio de variable"),
            regla=tr("con v = {y}^(1 - n) la ecuación se vuelve lineal en v: se divide entre {y}^n, y {y}^(-n)*{yp} "
                     "es v'/(1 - n).", y=y, yp=yp),
            partes=tr("n = {n}, así que 1 - n = {k} y v = {yk}.", n=texto(n), k=texto(k), yk=texto(y_k)),
            calculo=tuple(lineas),
            queda=lineal))

        soluciones_v = self._lineal(sympy.expand(Q_v - P_v * v), x, v, pasos, avisos)
        if soluciones_v is None:
            return None
        lineas, soluciones = [], []
        V = sympy.Function("v", real=True)(x)
        lineal_v = sympy.Eq(V.diff(x) + P_v * V, Q_v)
        for s in soluciones_v:
            lineas.append(f"{texto(y_k)} = {texto(s.rhs)}.")
            despeje = Despeje(y, [x], constantes=False)
            for valor in despeje.resolver(y_k, s.rhs):
                solucion = sympy.Eq(y, valor)
                if not k.is_Integer:
                    # y = v^(1/k) con k fraccionario: vale donde v >= 0 (v es una raíz de y); se comprueba la
                    # lineal en v, que es la que se resolvió
                    if not sympy.checkodesol(lineal_v, sympy.Eq(V, s.rhs), solve_for_func=False)[0]:
                        return None
                    self._condiciones[solucion] = tr("donde {v} >= 0 (v = {yk} no puede ser negativa)",
                                                     v=texto(s.rhs), yk=texto(y_k))
                    if k == sympy.Rational(1, 2):
                        self._restricciones[solucion] = [sympy.Ge(s.rhs, 0)]
                soluciones.append(solucion)
            lineas.extend(despeje.lineas)
        pasos.append(PasoCalculo(
            tr("Deshacer el cambio"),
            regla=tr("se vuelve a la variable {y}: v = {yk}, y se despeja {y}.", y=y, yk=texto(y_k)),
            partes=tr("v = {yk}.", yk=texto(y_k)),
            calculo=tuple(lineas),
            queda="; ".join(self._solucion_texto(s) for s in soluciones)))

        if n > 0:  # al dividir entre y^n se pierde y = 0, que es solución
            incluida = self._incluida(sympy.S.Zero, soluciones, y)
            regla = tr("al dividir entre {y}^n se supuso {y} distinto de 0; {y} = 0 cumple la ecuación ({yp} = 0 y los "
                       "dos términos con {y} valen 0).", y=y, yp=yp)
            if incluida is not None:
                pasos.append(PasoCalculo(
                    tr("La solución constante {y} = {r}", y=y, r=0), regla=regla,
                    calculo=(tr("Con C = {c}, la solución general da {y} = {r}: está incluida.", c=texto(incluida),
                                y=y, r=0),),
                    queda=tr("incluida en la solución general")))
            else:
                pasos.append(PasoCalculo(
                    tr("La solución constante {y} = {r}", y=y, r=0), regla=regla,
                    calculo=(tr("Ningún valor de C da {y} = {r}: se añade aparte (es una solución singular).", y=y,
                                r=0),),
                    queda=f"{y} = 0"))
                soluciones.append(sympy.Eq(y, 0))
        return soluciones

    # --- Homogéneas ---

    def _homogenea(self, f: Any, x: Any, y: Any, pasos: List[PasoCalculo], avisos: List[str]) -> Optional[List[Any]]:
        """y' = F(y/x): f(t*x, t*y) = f(x, y). Con y = u*x, y' = u + x*u' y queda x*u' = F(u) - u, separable."""
        if not f.has(y) or not f.has(x):
            return None
        nombre_t = "s" if "t" in (x.name, y.name) else "t"
        t = sympy.Symbol(nombre_t, positive=True)
        con_t = f.subs({x: t * x, y: t * y}, simultaneous=True)
        if sympy.simplify(con_t - f) != 0:
            return None
        u = sympy.Symbol("u", real=True)
        F = sympy.simplify(f.subs(y, u * x))
        if F.has(x):
            return None
        yp, up = sympy.Symbol(nombre_derivada(y, 1)), sympy.Symbol(nombre_derivada(u, 1))
        t_texto = sympy.Symbol(nombre_t)
        lineas = [tr("Cambiamos {x} por {t}*{x} e {y} por {t}*{y}: f({t}*{x}, {t}*{y}) = {sustituida} = {f}.",
                     x=x, y=y, t=t_texto, f=texto(f),
                     sustituida=sustituir(f, {x: t_texto * x, y: t_texto * y}))]
        lineas.append(tr("{t} se simplifica: f no cambia, así que solo depende del cociente {y}/{x}.", t=t_texto,
                         y=y, x=x))
        lineas.append(tr("Con {y} = u*{x} (es decir, u = {y}/{x}): f = {sustituida} = {F}.", y=y, x=x,
                         sustituida=sustituir(f, {y: u * x}), F=texto(F)))
        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: homogénea"),
            regla=tr("una ecuación {yp} = f({x}, {y}) es homogénea si f({t}*{x}, {t}*{y}) = f({x}, {y}) para todo {t}: "
                     "entonces f solo depende de {y}/{x}, y el cambio {y} = u*{x} la convierte en separable.",
                     yp=yp, x=x, y=y, t=t_texto),
            partes=tr("f({x}, {y}) = {f}.", x=x, y=y, f=texto(f)),
            calculo=tuple(lineas),
            queda=tr("{yp} = {F}, con u = {y}/{x}", yp=yp, F=texto(F), y=y, x=x)))

        resta = sympy.simplify(F - u)
        nueva = sympy.factor_terms(sympy.together(resta / x))
        lineas = [tr("{y} = u*{x}; derivamos con la regla del producto (u también depende de {x}): {yp} = u + {x}*{up}.",
                     y=y, x=x, yp=yp, up=up),
                  tr("Sustituimos en la ecuación: u + {x}*{up} = {F}.", x=x, up=up, F=texto(F)),
                  tr("Pasamos u a la derecha cambiando de signo: {x}*{up} = {cuenta} = {resta}.", x=x, up=up,
                     cuenta=f"{texto(F)} - u", resta=texto(resta)),
                  tr("Dividimos los dos lados entre {x}: {up} = {nueva}.", x=x, up=up, nueva=texto(nueva))]
        pasos.append(PasoCalculo(
            tr("Cambio de variable"),
            regla=tr("con {y} = u*{x}, la derivada es {yp} = u + {x}*{up}; al sustituir, la ecuación queda con u y "
                     "{x} separables.", y=y, x=x, yp=yp, up=up),
            partes=tr("u = {y}/{x}.", y=y, x=x),
            calculo=tuple(lineas),
            queda=f"{up} = {texto(nueva)}"))

        soluciones_u = self._separable(nueva, x, u, pasos, avisos)
        if soluciones_u is None:
            return None
        self._nota_en_y(avisos, u, y)
        soluciones, lineas = [], []
        for s in soluciones_u:
            if s.lhs == u:
                lineas.append(tr("u = {y}/{x}: {ecuacion}.", y=y, x=x, ecuacion=f"{y}/{x} = {texto(s.rhs)}"))
                valor = sympy.expand(x * s.rhs) if s.rhs.is_Add else x * s.rhs
                lineas.append(tr("Multiplicamos los dos lados por {x}: {y} = {valor}.", x=x, y=y,
                                 valor=texto(valor)))
                valor = self._simplificada(valor, lineas)
                soluciones.append(sympy.Eq(y, valor))
            else:
                implicita = sympy.Eq(s.lhs.subs(u, y / x), s.rhs.subs(u, y / x))
                lineas.append(tr("Cambiamos u por {cambio}: {ecuacion}.", cambio=f"{y}/{x}",
                                 ecuacion=f"{texto(implicita.lhs)} = {texto(implicita.rhs)}"))
                soluciones.append(self._juntar_implicita(implicita, lineas))
        pasos.append(PasoCalculo(
            tr("Deshacer el cambio"),
            regla=tr("se vuelve a la variable {y}: se cambia u por {y}/{x} y se despeja {y}.", y=y, x=x),
            partes=tr("u = {y}/{x}.", y=y, x=x),
            calculo=tuple(lineas),
            queda="; ".join(self._solucion_texto(s) for s in soluciones)))
        return soluciones

    @staticmethod
    def _nota_en_y(avisos: List[str], u: Any, y: Any) -> None:
        """Tras un cambio de variable, la nota de forma implícita se refiere a y, no a u."""
        en_u = tr("NOTA: la solución queda en forma implícita (sin despejar {y}).", y=u)
        avisos[:] = [tr("NOTA: la solución queda en forma implícita (sin despejar {y}).", y=y) if a == en_u else a
                     for a in avisos]

    def _juntar_implicita(self, implicita: Any, lineas: List[str]) -> Any:
        """
        L = R + C con logaritmos a los dos lados: se pasan a la izquierda y se juntan
        (log(sqrt(1 + y^2/x^2)) + log(Abs(x)) = log(sqrt(x^2 + y^2))), si así queda más corta.
        """
        sin_c = sympy.expand(implicita.rhs - C)
        if not sin_c.has(sympy.log) or not implicita.lhs.has(sympy.log):
            return implicita
        juntos = sympy.logcombine(implicita.lhs - sin_c, force=True)
        juntos = juntos.replace(lambda e: isinstance(e, sympy.log), lambda e: sympy.log(sympy.simplify(e.args[0])))
        if len(texto(juntos)) >= len(texto(implicita.lhs)) + len(texto(sin_c)):
            return implicita
        lineas.append(tr("Pasamos {termino} a la izquierda y juntamos los logaritmos (log(a) + log(b) = log(a*b), "
                         "k*log(a) = log(a^k)): {ecuacion}.", termino=texto(sin_c),
                         ecuacion=f"{texto(juntos)} = C"))
        return sympy.Eq(juntos, C)

    # --- Exactas ---

    def _exacta(self, f: Any, x: Any, y: Any, pasos: List[PasoCalculo], avisos: List[str],
                edo: Optional[Edo] = None) -> Optional[List[Any]]:
        """
        M dx + N dy = 0 con M_y = N_x (o tras multiplicar por un factor integrante que solo depende
        de x o de y): existe F con F_x = M y F_y = N, y la solución es F(x, y) = C.
        """
        yp = sympy.Symbol(nombre_derivada(y, 1))
        if edo is not None:
            todo = sympy.expand(edo.izquierda - edo.derecha)
            if not todo.is_polynomial(yp) or sympy.degree(todo, yp) != 1:
                return None
            N = sympy.factor_terms(todo.coeff(yp))
            M = sympy.factor_terms(sympy.expand(todo - todo.coeff(yp) * yp))
        else:
            M, N = -f, sympy.S.One
        if M == 0 or N == 0 or not M.has(y) and not N.has(x):
            return None
        M_y, N_x = sympy.simplify(sympy.diff(M, y)), sympy.simplify(sympy.diff(N, x))
        exacta = sympy.simplify(M_y - N_x) == 0
        factor_int, variable_m, pasos_m = None, None, []
        if not exacta:
            r = sympy.simplify((M_y - N_x) / N)
            if not r.has(y):
                variable_m = x
            else:
                r = sympy.simplify((N_x - M_y) / M)
                if not r.has(x):
                    variable_m = y
            if variable_m is None:
                return None
            primitiva = self._integrar(r, variable_m, pasos_m)
            factor_int = sympy.exp(_con_abs(primitiva)).replace(lambda e: isinstance(e, sympy.Abs),
                                                                lambda e: e.args[0])
            M2, N2 = sympy.simplify(factor_int * M), sympy.simplify(factor_int * N)
            if sympy.simplify(sympy.diff(M2, y) - sympy.diff(N2, x)) != 0:
                return None

        # Forma diferencial
        lineas = []
        if not (edo is not None and edo.diferencial):
            lineas.append(tr("{yp} es d{y}/d{x}: multiplicando por d{x} y pasando todo a la izquierda, "
                             "{ecuacion}.", yp=yp, y=y, x=x, ecuacion=self._forma_diferencial(M, N, x, y)))
        pasos.append(PasoCalculo(
            tr("Forma diferencial"),
            regla=tr("se escribe la ecuación como M d{x} + N d{y} = 0, con M y N funciones de {x} y de {y}.", x=x, y=y),
            partes=tr("M = {M} y N = {N}.", M=texto(M), N=texto(N)),
            calculo=tuple(lineas),
            queda=self._forma_diferencial(M, N, x, y)))

        lineas = [tr("M_{y} es la derivada de M respecto a {y}, con {x} como constante: M_{y} = {My}.", y=y, x=x,
                     My=texto(M_y)),
                  tr("N_{x} es la derivada de N respecto a {x}, con {y} como constante: N_{x} = {Nx}.", y=y, x=x,
                     Nx=texto(N_x))]
        lineas.append(tr("Son iguales: la ecuación es exacta.") if exacta else
                      tr("No son iguales: la ecuación no es exacta."))
        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: ¿exacta?"),
            regla=tr("M d{x} + N d{y} = 0 es exacta si M_{y} = N_{x}: entonces es la diferencial de una función "
                     "F({x}, {y}), con F_{x} = M y F_{y} = N, y la solución es F({x}, {y}) = C.", x=x, y=y),
            partes=tr("M = {M} y N = {N}.", M=texto(M), N=texto(N)),
            calculo=tuple(lineas),
            queda=tr("exacta") if exacta else tr("no exacta")))

        if not exacta:
            pasos.extend(pasos_m)
            divisor = lambda e: f"({texto(e)})" if e.is_Add or e.is_Mul or e.is_Pow else texto(e)
            cociente = (f"(M_{y} - N_{x})/N = ({texto(M_y)} - {factor(N_x)})/{divisor(N)}" if variable_m == x
                        else f"(N_{x} - M_{y})/M = ({texto(N_x)} - {factor(M_y)})/{divisor(M)}")
            lineas = [tr("{cociente} = {r}: solo depende de {v}.", cociente=cociente, r=texto(r), v=variable_m),
                      f"∫ {factor(r)} d{variable_m} = {texto(primitiva)}.",
                      f"m({variable_m}) = exp({texto(_con_abs(primitiva))}) = {texto(factor_int)}."]
            lineas.append(tr("Multiplicamos M y N por m: M = {M} y N = {N}.", M=texto(M2), N=texto(N2)))
            lineas.append(tr("Ahora M_{y} = {My} y N_{x} = {Nx}: son iguales, la ecuación ya es exacta.", y=y, x=x,
                             My=texto(sympy.simplify(sympy.diff(M2, y))), Nx=texto(sympy.simplify(sympy.diff(N2, x)))))
            pasos.append(PasoCalculo(
                tr("Factor integrante"),
                regla=tr("si (M_{y} - N_{x})/N solo depende de {x}, m({x}) = exp(∫ (M_{y} - N_{x})/N d{x}) hace "
                         "exacta la ecuación; si (N_{x} - M_{y})/M solo depende de {y}, m({y}) = exp(∫ (N_{x} - "
                         "M_{y})/M d{y}).", x=x, y=y),
                partes=tr("M_{y} = {My} y N_{x} = {Nx}.", y=y, x=x, My=texto(M_y), Nx=texto(N_x)),
                calculo=tuple(lineas),
                queda=self._forma_diferencial(M2, N2, x, y)))
            M, N = M2, N2

        # La función F: primero con F_x = M
        primitiva_x = self._integrar(M, x, pasos)
        integral_x = _con_abs(primitiva_x)
        pasos.append(PasoCalculo(
            tr("Integrar M respecto a {x}", x=x),
            regla=tr("F_{x} = M: F es una primitiva de M respecto a {x} ({y} hace de constante). La constante de esa "
                     "integral puede depender de {y}: se llama g({y}).", x=x, y=y),
            partes=tr("M = {M}.", M=texto(M)),
            calculo=(f"∫ {factor(M)} d{x} = {texto(primitiva_x)}.",) + self._lineas_abs(primitiva_x),
            queda=f"F = {texto(integral_x)} + g({y})"))

        # g(y) con F_y = N
        derivada_y = sympy.simplify(sympy.diff(integral_x, y))
        g_prima = sympy.simplify(N - derivada_y)
        if g_prima.has(x):
            return None
        lineas = [tr("Derivamos F respecto a {y}: F_{y} = {d} + g'({y}).", y=y, d=texto(derivada_y)),
                  tr("Igualamos a N: {d} + g'({y}) = {N}.", d=texto(derivada_y), y=y, N=texto(N)),
                  tr("Despejamos: g'({y}) = {N} - {d} = {g}.", y=y, N=texto(N), d=entre_parentesis(derivada_y),
                     g=texto(g_prima))]
        pasos.append(PasoCalculo(
            tr("Hallar g({y})", y=y),
            regla=tr("F_{y} = N: se deriva F respecto a {y} y se iguala a N. Lo que queda es g'({y}), que no puede "
                     "tener {x}.", x=x, y=y),
            partes=tr("N = {N}.", N=texto(N)),
            calculo=tuple(lineas),
            queda=f"g'({y}) = {texto(g_prima)}"))
        primitiva_g = self._integrar(g_prima, y, pasos) if g_prima != 0 else sympy.S.Zero
        g_valor = _con_abs(primitiva_g)
        F = integral_x + g_valor
        if g_valor == 0:
            suma = texto(F)
        else:
            signo, resto_g = ("-", -g_valor) if g_valor.could_extract_minus_sign() else ("+", g_valor)
            suma = f"{texto(integral_x)} {signo} {f'({texto(resto_g)})' if resto_g.is_Add else texto(resto_g)}"
            if suma != texto(F):
                suma += f" = {texto(F)}"
        pasos.append(PasoCalculo(
            tr("Solución general"),
            regla=tr("la solución es F({x}, {y}) = C: la constante de g no hace falta, porque ya está C.", x=x, y=y),
            calculo=(f"g({y}) = ∫ {factor(g_prima)} d{y} = {texto(primitiva_g)}.",) + self._lineas_abs(primitiva_g)
                    + (f"F = {suma}.",),
            queda=f"{texto(F)} = C"))

        # Despejar y, si se puede
        despeje = Despeje(y, [x])
        try:
            explicitas = despeje.resolver(F, C)
        except SinExplicacion:
            explicitas = None
        if explicitas and len(explicitas) <= 2 and not any(s.has(y) for s in explicitas):
            explicitas = [self._simplificada(s, despeje.lineas) for s in explicitas]
            pasos.append(PasoCalculo(
                tr("Despejar {y}", y=y),
                regla=tr("se deshace, de fuera hacia dentro, lo que envuelve a {y}: lo que suma pasa restando, lo que "
                         "multiplica pasa dividiendo, y cada función se deshace con su inversa (log con exp, una "
                         "potencia con una raíz). Una expresión que solo tiene constantes es otra constante.", y=y),
                partes=tr("la ecuación es {ecuacion}.", ecuacion=f"{texto(F)} = C"),
                calculo=tuple(despeje.lineas),
                queda="; ".join(f"{y} = {texto(s)}" for s in explicitas)))
            return [sympy.Eq(y, s) for s in explicitas]
        avisos.append(tr("NOTA: la solución queda en forma implícita (sin despejar {y}).", y=y))
        return [sympy.Eq(F, C)]

    @staticmethod
    def _forma_diferencial(M: Any, N: Any, x: Any, y: Any) -> str:
        """'(2*x*y + 3) dx + (x^2 - 1) dy = 0'."""
        if N.could_extract_minus_sign():
            return f"{factor(M)} d{x} - {factor(-N)} d{y} = 0"
        return f"{factor(M)} d{x} + {factor(N)} d{y} = 0"

    # --- Riccati (con una solución conocida) ---

    def _riccati(self, f: Any, x: Any, y: Any, pasos: List[PasoCalculo], avisos: List[str],
                 edo: Optional[Edo] = None) -> Optional[List[Any]]:
        """y' = P + Q*y + R*y^2 con una solución y1: y = y1 + 1/v da la lineal v' + (Q + 2*R*y1)*v = -R."""
        if edo is None or edo.y1 is None:
            return None
        y1 = edo.y1
        g = sympy.expand(f)
        if not g.is_polynomial(y) or sympy.degree(g, y) != 2:
            return None
        R, Q, P = (sympy.factor_terms(g.coeff(y, k)) for k in (2, 1, 0))
        if any(c.has(y) for c in (P, Q, R)):
            return None
        yp = sympy.Symbol(nombre_derivada(y, 1))
        d1 = sympy.simplify(sympy.diff(y1, x))
        en_y1 = sympy.simplify(f.subs(y, y1))
        if sympy.simplify(d1 - en_y1) != 0:
            nota = tr("NOTA: {y1} no es solución de la ecuación ({yp} = {d}, pero el lado derecho vale {f}): no sirve "
                      "para la ecuación de Riccati.", y1=texto(y1), yp=yp, d=texto(d1), f=texto(en_y1))
            avisos.append(nota)
            self._notas_metodo.append(nota)
            return None
        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: de Riccati"),
            regla=tr("una ecuación de Riccati es {yp} = P({x}) + Q({x})*{y} + R({x})*{y}^2. Si se conoce una solución "
                     "y1, el cambio {y} = y1 + 1/v la convierte en lineal en v.", yp=yp, x=x, y=y),
            partes=tr("P = {P}, Q = {Q}, R = {R}; y1 = {y1}.", P=texto(P), Q=texto(Q), R=texto(R), y1=texto(y1)),
            calculo=(tr("Comprobamos y1: y1' = {d} y el lado derecho con {y} = y1 vale {f}: es solución.", d=texto(d1),
                        y=y, f=texto(en_y1)),),
            queda=f"{y} = {factor(y1)} + 1/v"))
        v = sympy.Symbol("v", real=True)
        coef = sympy.simplify(Q + 2 * R * y1)
        lineas = [tr("{y} = y1 + 1/v: {yp} = y1' - v'/v^2.", y=y, yp=yp),
                  tr("Al sustituir, y1' se va con P + Q*y1 + R*y1^2 (y1 es solución) y queda -v'/v^2 = "
                     "(Q + 2*R*y1)/v + R/v^2."),
                  tr("Multiplicamos por -v^2: v' + (Q + 2*R*y1)*v = -R, con Q + 2*R*y1 = {c} y -R = {menos_r}.",
                     c=texto(coef), menos_r=texto(-R))]
        pasos.append(PasoCalculo(
            tr("Cambio de variable"),
            regla=tr("con {y} = y1 + 1/v, la derivada es {yp} = y1' - v'/v^2; al sustituir se cancela lo que ya cumple "
                     "y1 y queda una lineal en v.", y=y, yp=yp),
            partes=f"y1 = {texto(y1)}.",
            calculo=tuple(lineas),
            queda=f"v'{_mas(coef, v)} = {texto(-R)}"))
        ecuacion_v = sympy.expand(-R - coef * v)
        # Si Q + 2*R*y1 = 0, v' = -R es una integración directa
        soluciones_v = (self._lineal(ecuacion_v, x, v, pasos, avisos) if coef != 0
                        else self._separable(ecuacion_v, x, v, pasos, avisos))
        if soluciones_v is None:
            return None
        lineas, soluciones = [], []
        for s in soluciones_v:
            if s.lhs != v:
                return None
            valor = _mas_corta(sympy.simplify(y1 + 1 / s.rhs), y1 + 1 / s.rhs)
            lineas.append(f"{y} = {factor(y1)} + 1/{factor(s.rhs)} = {texto(valor)}.")
            valor = self._simplificada(valor, lineas)
            soluciones.append(sympy.Eq(y, valor))
        pasos.append(PasoCalculo(
            tr("Deshacer el cambio"),
            regla=tr("se vuelve a {y} = y1 + 1/v.", y=y),
            calculo=tuple(lineas),
            queda="; ".join(self._solucion_texto(s) for s in soluciones)))
        return soluciones

    # --- Clairaut ---

    def _clairaut(self, edo: Edo, pasos: List[PasoCalculo], avisos: List[str]) -> Optional[List[Any]]:
        """y = x*y' + f(y'): derivando, p'*(x + f'(p)) = 0. p = C da y = C*x + f(C); x = -f'(p), la singular."""
        x, y, yp = edo.x, edo.y, edo.derivadas[0]
        todo = sympy.expand(edo.izquierda - edo.derecha)
        c = todo.coeff(y)
        if not c.is_number or c == 0:
            return None
        resto = sympy.expand(todo / c - y)
        fp = sympy.expand(-(resto + x * yp))
        if fp.has(x) or fp.has(y) or not fp.has(yp):
            return None
        if fp.is_polynomial(yp) and sympy.degree(fp, yp) < 2:
            return None  # f lineal en p: es una lineal, mejor por su método
        p = sympy.Symbol("p", real=True)
        f = fp.subs(yp, p)
        df = sympy.simplify(sympy.diff(f, p))
        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: de Clairaut"),
            regla=tr("una ecuación de Clairaut es {y} = {x}*{yp} + f({yp}). Se llama p = {yp} y se deriva respecto "
                     "a {x}.", y=y, x=x, yp=yp),
            partes=tr("{y} = {x}*p + f(p), con f(p) = {f}.", y=y, x=x, f=texto(f)),
            calculo=(tr("Derivamos: p = p + {x}*p' + f'(p)*p', con f'(p) = {df}.", x=x, df=texto(df)),
                     tr("La p de los dos lados se va: 0 = p'*({x} + f'(p)) = p'*({suma}).", x=x,
                        suma=f"{x}{_mas(df, 1)}")),
            queda=f"p'*({x}{_mas(df, 1)}) = 0"))
        general = C * x + f.subs(p, C)
        pasos.append(PasoCalculo(
            tr("Solución general"),
            regla=tr("si p' = 0, p es una constante C: se sustituye p = C en {y} = {x}*p + f(p), y sale una familia de "
                     "rectas.", y=y, x=x),
            queda=f"{y} = {texto(general)}"))
        soluciones = [sympy.Eq(y, general)]
        despeje = Despeje(p, [x], constantes=False)
        try:
            ramas = despeje.resolver(df, -x)
        except SinExplicacion:
            ramas = []
        lineas = [tr("Si {x} + f'(p) = 0: {ecuacion}.", x=x, ecuacion=f"{texto(df)} = {texto(-x)}")] + despeje.lineas
        for rama in ramas:
            singular = _mas_corta(sympy.simplify(x * rama + f.subs(p, rama)), sympy.expand(x * rama + f.subs(p, rama)))
            lineas.append(tr("Con p = {p}: {y} = {x}*p + f(p) = {valor}.", p=texto(rama), y=y, x=x,
                             valor=texto(singular)))
            soluciones.append(sympy.Eq(y, singular))
        if not ramas:
            # p no se despeja: la singular queda en forma paramétrica
            y_param = _mas_corta(sympy.simplify(f - p * df), f - p * df)
            pasos.append(PasoCalculo(
                tr("Solución singular"),
                regla=tr("el otro factor, {x} + f'(p) = 0, da la envolvente de las rectas; si p no se puede despejar, "
                         "se deja en forma paramétrica, con p como parámetro.", x=x),
                calculo=(tr("{x} = -f'(p) = {xp}; {y} = {x}*p + f(p) = {yp}.", x=x, xp=texto(-df), y=y,
                            yp=texto(y_param)),),
                queda=f"{x} = {texto(-df)}, {y} = {texto(y_param)}"))
            avisos.append(tr("NOTA: además está la solución singular en forma paramétrica: {x} = {xp}, {y} = {yp}.",
                             x=x, xp=texto(-df), y=y, yp=texto(y_param)))
        if ramas:
            pasos.append(PasoCalculo(
                tr("Solución singular"),
                regla=tr("el otro factor, {x} + f'(p) = 0, da p en función de {x}: al sustituirlo sale una curva que no "
                         "es de la familia (la envolvente de las rectas).", x=x),
                calculo=tuple(lineas),
                queda="; ".join(self._solucion_texto(s) for s in soluciones[1:])))
        return soluciones

    # --- Reducibles de orden ---

    def _reducir_orden(self, edo: Edo, pasos: List[PasoCalculo], avisos: List[str]) -> Optional[List[Any]]:
        """
        Orden 2 sin y: p = y', y'' = p' (primer orden en p(x)); después y = ∫ p dx + C2.
        Orden 2 sin x: p = y', y'' = p*dp/dy (primer orden en p(y)); después y' = p(y), separable.
        """
        x, y = edo.x, edo.y
        yp, ypp = edo.derivadas
        todo = edo.izquierda - edo.derecha
        p = sympy.Symbol("p", real=True)
        pp = sympy.Symbol("p'")
        C1, C2 = constantes_de(2)
        if not todo.has(y):
            ecuacion = (edo.izquierda.xreplace({yp: p, ypp: pp}), edo.derecha.xreplace({yp: p, ypp: pp}))
            pasos.append(PasoCalculo(
                tr("Tipo de ecuación: reducible de orden (sin {y})", y=y),
                regla=tr("si en la ecuación no aparece {y}, con p = {yp} queda {ypp} = p': una ecuación de primer "
                         "orden en p({x}). Después, {y} = ∫ p d{x} + C2.", y=y, yp=yp, ypp=ypp, x=x),
                partes=tr("la ecuación en p es {ecuacion}.", ecuacion=f"{texto(ecuacion[0])} = {texto(ecuacion[1])}"),
                queda=f"{texto(ecuacion[0])} = {texto(ecuacion[1])}"))
            sub = Edo(ecuacion[0], ecuacion[1], x, p, [pp], 1, escrita=f"{texto(ecuacion[0])} = {texto(ecuacion[1])}")
            soluciones_p, _ = self._explicar(sub, pasos, avisos)
            self._edo_actual = edo
            generales = [s for s in soluciones_p if s.lhs == p and s.has(C)]  # sin las constantes, p = 0...
            if len(generales) != 1:
                return None
            valor_p = generales[0].rhs.xreplace({C: C1})
            primitiva = self._integrar(valor_p, x, pasos)
            solucion = _con_abs(primitiva) + C2
            pasos.append(PasoCalculo(
                tr("Volver a {y}", y=y),
                regla=tr("p es {yp}: {y} es una primitiva de p, más otra constante.", y=y, yp=yp),
                calculo=(tr("La constante C de p pasa a llamarse C1."),
                         f"{y} = ∫ {factor(valor_p)} d{x} = {texto(primitiva)} + C2.") + self._lineas_abs(primitiva),
                queda=f"{y} = {texto(solucion)}"))
            soluciones = [sympy.Eq(y, solucion)]
            for rama in soluciones_p:
                if rama.lhs == p and not rama.has(C):
                    curva = sympy.Eq(y, sympy.integrate(rama.rhs, x) + C2)
                    if self._cumple(curva.rhs, edo) and curva not in soluciones:
                        soluciones.append(curva)
            return soluciones
        if not todo.has(x):
            cambio = {yp: p, ypp: p * pp}
            ecuacion = (edo.izquierda.xreplace(cambio), edo.derecha.xreplace(cambio))
            pasos.append(PasoCalculo(
                tr("Tipo de ecuación: reducible de orden (sin {x})", x=x),
                regla=tr("si en la ecuación no aparece {x}, con p = {yp} tomado como función de {y}, la regla de la "
                         "cadena da {ypp} = dp/d{x} = dp/d{y}*d{y}/d{x} = p*p': una ecuación de primer orden en p({y}). "
                         "Después, {yp} = p({y}) es separable.", x=x, y=y, yp=yp, ypp=ypp),
                partes=tr("la ecuación en p es {ecuacion} (p' es dp/d{y}).", y=y,
                          ecuacion=f"{texto(ecuacion[0])} = {texto(ecuacion[1])}"),
                queda=f"{texto(ecuacion[0])} = {texto(ecuacion[1])}"))
            sub = Edo(ecuacion[0], ecuacion[1], y, p, [pp], 1, escrita=f"{texto(ecuacion[0])} = {texto(ecuacion[1])}")
            soluciones_p, _ = self._explicar(sub, pasos, avisos)
            self._edo_actual = edo
            explicitas = [s for s in soluciones_p if s.lhs == p and s.has(C)]
            if not explicitas:
                return None
            soluciones = []
            for rama in explicitas:
                valor_p = rama.rhs.xreplace({C: C1})
                pasos.append(PasoCalculo(
                    tr("Volver a {y}", y=y),
                    regla=tr("p es {yp}: queda {yp} = p({y}), una ecuación separable en {x} e {y}.",
                             y=y, yp=yp, x=x),
                    calculo=(tr("La constante C de p pasa a llamarse C1."),),
                    queda=f"{yp} = {texto(valor_p)}"))
                nuevas = self._separable(valor_p, x, y, pasos, avisos)
                if nuevas is None:
                    return None
                for candidata in nuevas:
                    solucion = sympy.Eq(candidata.lhs, candidata.rhs.xreplace({C: C2}))
                    if solucion not in soluciones:
                        soluciones.append(solucion)
            # La sustitucion p*dp/dy presupone una rama no constante de y.
            equilibrio = todo.subs({yp: 0, ypp: 0})
            for raiz in _raices_reales(equilibrio, y, x):
                constante = sympy.Eq(y, raiz)
                if self._cumple(raiz, edo) and self._incluida(raiz, soluciones, y) is None:
                    soluciones.append(constante)
            return soluciones
        return None

    # --- Reducibles a separables ---

    def _reducible(self, f: Any, x: Any, y: Any, pasos: List[PasoCalculo], avisos: List[str]) -> Optional[List[Any]]:
        """y' = F(a*x + b*y + c): con u = a*x + b*y + c, u' = a + b*F(u) es separable."""
        u = sympy.Symbol("u", real=True)
        candidatos = []
        for sub in sympy.preorder_traversal(f):
            if sub.is_Add and sub.is_polynomial(x, y) and sympy.Poly(sub, x, y).total_degree() == 1:
                a, b = sub.coeff(x), sub.coeff(y)
                if a != 0 and b != 0 and a.is_number and b.is_number and sub not in candidatos:
                    candidatos.append(sub)
        for cambio in candidatos:
            a, b = cambio.coeff(x), cambio.coeff(y)
            c = cambio - a * x - b * y
            despejada = (u - a * x - c) / b
            F = sympy.simplify(f.subs(y, despejada))
            if F.has(x):
                continue
            return self._con_cambio(f, F, cambio, a, b, c, x, y, u, pasos, avisos)
        return None

    def _con_cambio(self, f, F, cambio, a, b, c, x, y, u, pasos, avisos) -> Optional[List[Any]]:
        yp, up = sympy.Symbol(nombre_derivada(y, 1)), sympy.Symbol(nombre_derivada(u, 1))
        nueva = sympy.expand(a + b * F) if (a + b * F).is_polynomial(u) else sympy.factor_terms(sympy.together(a + b * F))
        pasos.append(PasoCalculo(
            tr("Tipo de ecuación: reducible a separable"),
            regla=tr("si {yp} = F(a*{x} + b*{y} + c), el cambio u = a*{x} + b*{y} + c la convierte en separable: "
                     "u' = a + b*{yp} = a + b*F(u), que solo tiene u.", yp=yp, x=x, y=y),
            partes=tr("{yp} = {f} solo depende de {cambio}: a = {a}, b = {b}, c = {c}.", yp=yp, f=texto(f),
                      cambio=texto(cambio), a=texto(a), b=texto(b), c=texto(c)),
            queda=f"u = {texto(cambio)}"))
        lineas = [tr("Derivamos el cambio respecto a {x}: u' = {du}.", x=x, du=texto(a + b * yp))]
        lineas.append(tr("En {yp} = {f} cambiamos {cambio} por u: {yp} = {F}.", yp=yp, f=texto(f),
                         cambio=texto(cambio), F=texto(F)))
        lineas.append(tr("Sustituimos {yp} en u': u' = {cuenta}.", yp=yp,
                         cuenta=f"{texto(a)} + {entre_parentesis(b)}*{entre_parentesis(F)}" if b != 1
                         else f"{texto(a)} + {entre_parentesis(F)}"))
        if texto(nueva) != texto(a + b * F):
            lineas.append(tr("Operamos: u' = {nueva}.", nueva=texto(nueva)))
        pasos.append(PasoCalculo(
            tr("Cambio de variable"),
            regla=tr("se deriva u = a*{x} + b*{y} + c (la derivada de {y} es {yp}) y se sustituye {yp} por F(u).",
                     x=x, y=y, yp=yp),
            partes=tr("u = {cambio}.", cambio=texto(cambio)),
            calculo=tuple(lineas),
            queda=f"{up} = {texto(nueva)}"))
        soluciones_u = self._separable(nueva, x, u, pasos, avisos)
        if soluciones_u is None:
            return None
        self._nota_en_y(avisos, u, y)
        soluciones = []
        lineas = []
        for s in soluciones_u:
            if s.lhs == u:
                lineas.append(f"{texto(cambio)} = {texto(s.rhs)}.")
                despeje = Despeje(y, [x], constantes=False)
                valor, = despeje.resolver(cambio, s.rhs)
                lineas.extend(despeje.lineas)
                soluciones.append(sympy.Eq(y, valor))
            else:
                implicita = sympy.Eq(s.lhs.subs(u, cambio), s.rhs.subs(u, cambio))
                lineas.append(tr("Cambiamos u por {cambio}: {ecuacion}.", cambio=texto(cambio),
                                 ecuacion=f"{texto(implicita.lhs)} = {texto(implicita.rhs)}"))
                soluciones.append(implicita)
        pasos.append(PasoCalculo(
            tr("Deshacer el cambio"),
            regla=tr("se vuelve a la variable {y}: se cambia u por {cambio} y se despeja {y}.", y=y,
                     cambio=texto(cambio)),
            partes=tr("u = {cambio}.", cambio=texto(cambio)),
            calculo=tuple(lineas),
            queda="; ".join(self._solucion_texto(s) for s in soluciones)))
        return soluciones

    # --- Condición inicial ---

    def _condicion_inicial(self, soluciones: List[Any], cond: Condicion, x: Any, y: Any,
                           pasos: List[PasoCalculo]) -> List[Any]:
        x0, y0 = cond.punto, cond.valor
        lineas = []
        particulares = []
        for s in soluciones:
            if not s.has(C):
                if s.lhs == y and sympy.simplify(s.rhs.subs(x, x0) - y0) == 0:
                    lineas.append(tr("La solución {y} = {r} cumple {y}({x0}) = {y0}.", y=y, r=texto(s.rhs),
                                     x0=texto(x0), y0=texto(y0)))
                    particulares.append(s)
                continue
            sustituida = f"{sustituir(s.lhs, {x: x0, y: y0})} = {sustituir(s.rhs, {x: x0, y: y0})}"
            lineas.append(tr("Sustituimos {x} = {x0}, {y} = {y0} en {solucion}: {sustituida}.",
                             solucion=self._solucion_texto(s), x=x, x0=texto(x0), y=y, y0=texto(y0),
                             sustituida=sustituida))
            izq, der = sympy.simplify(s.lhs.subs({x: x0, y: y0})), sympy.simplify(s.rhs.subs({x: x0, y: y0}))
            if f"{texto(izq)} = {texto(der)}" != sustituida:
                lineas.append(tr("Operamos: {ecuacion}.", ecuacion=f"{texto(izq)} = {texto(der)}"))
            # Se despeja C del lado que la tiene (der); el otro queda como valor (izq)
            if izq.has(C) and not der.has(C):
                izq, der = der, izq
            despeje = Despeje(C, [], constantes=False)
            try:
                valores = despeje.resolver(der, izq) if der.has(C) else []
            except SinExplicacion:
                valores = [v for v in sympy.solve(sympy.Eq(izq, der), C)]
                lineas.append(tr("Despejamos C: C = {valores}.", valores=", ".join(texto(v) for v in valores)))
            else:
                lineas.extend(despeje.lineas)
            for v in valores:
                if v.has(sympy.I) or v.is_real is False:
                    continue
                particular = sympy.Eq(s.lhs.subs(C, v), sympy.simplify(s.rhs.subs(C, v)))
                comprobacion = sympy.simplify((particular.lhs - particular.rhs).subs({x: x0, y: y0}))
                if comprobacion != 0:
                    lineas.append(tr("Con C = {c}, {solucion} no cumple la condición: se descarta.", c=texto(v),
                                     solucion=self._solucion_texto(particular)))
                    continue
                restricciones = [r.subs(C, v) for r in self._restricciones.get(s, [])]
                if any(sympy.simplify(r.subs(x, x0)) != sympy.true for r in restricciones):
                    lineas.append(tr("Con C = {c} no se cumplen las restricciones de dominio: se descarta.", c=texto(v)))
                    continue
                edo = self._edo_actual
                cambios = {y: particular.rhs}
                cambios.update({d: sympy.diff(particular.rhs, x, n)
                                for n, d in enumerate(edo.derivadas, 1)})
                residuo = (edo.izquierda - edo.derecha).xreplace(cambios).subs(x, x0)
                if sympy.simplify(residuo) != 0:
                    lineas.append(tr("Con C = {c} no se cumple la EDO en el punto inicial: se descarta.", c=texto(v)))
                    continue
                if restricciones:
                    self._restricciones[particular] = restricciones
                    self._condiciones[particular] = tr("donde {restricciones}",
                                                     restricciones="; ".join(texto(r) for r in restricciones))
                lineas.append(tr("Con C = {c}: {solucion}.", c=texto(v), solucion=self._solucion_texto(particular)))
                particulares.append(particular)
        if not particulares:
            raise SinExplicacion()
        pasos.append(PasoCalculo(
            tr("Condición inicial"),
            regla=tr("la condición {y}({x0}) = {y0} elige una solución de la general: se sustituyen {x} = {x0} e "
                     "{y} = {y0} y se despeja la constante C.", y=y, x=x, x0=texto(x0), y0=texto(y0)),
            partes=tr("la condición es {condicion}.", condicion=self._condicion_texto(cond, y)),
            calculo=tuple(lineas),
            queda="; ".join(self._solucion_texto(s) for s in particulares)))
        return particulares


# ---------------------------------------------------------
# Orden superior: lineales con coeficientes constantes
# ---------------------------------------------------------

# Los coeficientes de y_p (sin C, que es la constante; ni D, el discriminante; ni E ni I)
LETRAS = ["A", "B", "F", "G", "H", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U", "V", "W"]


def es_constante(s: Any) -> bool:
    """Las constantes de la solución general: C, C1, C2..."""
    return isinstance(s, sympy.Symbol) and re.fullmatch(r"C\d*", s.name) is not None


def constantes_de(n: int) -> List[Any]:
    return [sympy.Symbol(f"C{i}", real=True) for i in range(1, n + 1)]


def _veces(m: int) -> str:
    return {1: tr("simple"), 2: tr("doble"), 3: tr("triple")}.get(m, tr("de multiplicidad {m}", m=m))


def _compleja(alfa: Any, beta: Any) -> str:
    """'1 ± 2*i', '±3*i', '-1/2 ± i'."""
    b = "i" if beta == 1 else f"{factor(beta)}*i"
    return f"±{b}" if alfa == 0 else f"{texto(alfa)} ± {b}"


def _mas_corta(*formas: Any) -> Any:
    return min(formas, key=lambda e: len(texto(e)))


def resolver_sistema(ecuaciones: List[Tuple[Any, Any]], incognitas: List[Any], lineas: List[str]) -> Dict[Any, Any]:
    """
    Sistema lineal por sustitución, con cada paso: se despeja una incógnita de la ecuación con
    menos incógnitas, se sustituye en las demás y al final se vuelve atrás. Lanza SinExplicacion
    si no tiene solución única.
    """
    pendientes = [(sympy.expand(i), sympy.expand(d)) for i, d in ecuaciones]
    despejadas: List[Tuple[Any, Any]] = []
    while pendientes:
        con = [(sum(1 for v in incognitas if (i - d).has(v)), k) for k, (i, d) in enumerate(pendientes)]
        utiles = [c for c in con if c[0] > 0]
        if not utiles:
            if any(sympy.simplify(i - d) != 0 for i, d in pendientes):
                raise SinExplicacion()
            break
        _, k = min(utiles)
        izq, der = pendientes.pop(k)
        variable = next(v for v in incognitas if (izq - der).has(v))
        # Las incógnitas a la izquierda y los números a la derecha
        todo = sympy.expand(izq - der)
        numero = todo.as_independent(*incognitas, as_Add=True)[0]
        izq, der = todo - numero, -numero
        pasos_despeje, valor = despejar(izq, der, variable)
        if pasos_despeje:
            lineas.append(tr("De {ecuacion}:", ecuacion=f"{texto(izq)} = {texto(der)}") + " " + " ".join(pasos_despeje))
        elif izq != variable:
            lineas.append(tr("De {ecuacion}: {v} = {valor}.", ecuacion=f"{texto(izq)} = {texto(der)}", v=variable,
                             valor=texto(valor)))
        despejadas.append((variable, valor))
        if pendientes:
            afectadas = any((i - d).has(variable) for i, d in pendientes)
            pendientes = [(sympy.expand(i.subs(variable, valor)), sympy.expand(d.subs(variable, valor)))
                          for i, d in pendientes]
            if afectadas:
                lineas.append(tr("Sustituimos {v} = {valor} en las demás: {ecuaciones}.", v=variable, valor=texto(valor),
                                 ecuaciones="; ".join(f"{texto(i)} = {texto(d)}" for i, d in pendientes)))
    solucion: Dict[Any, Any] = {}
    for variable, valor in reversed(despejadas):
        final = sympy.simplify(valor.subs(solucion))
        if valor.free_symbols & set(incognitas):
            conocidas = {v: s for v, s in solucion.items() if valor.has(v)}
            cadena = list(dict.fromkeys([texto(valor), sustituir(valor, conocidas), texto(final)]))
            lineas.append(tr("Volvemos atrás: {v} = {cuenta}.", v=variable, cuenta=" = ".join(cadena)))
        solucion[variable] = final
    if set(solucion) != set(incognitas):
        raise SinExplicacion()
    return solucion


class _OrdenSuperior:
    """a_n*y^(n) + ... + a_1*y' + a_0*y = g(x), con los a_k números."""

    def __init__(self, motor: "MotorEdo", edo: Edo, pasos: List[PasoCalculo], avisos: List[str]):
        self.motor, self.edo, self.pasos, self.avisos = motor, edo, pasos, avisos
        self.x, self.y = edo.x, edo.y
        self.r = sympy.Symbol("r")
        self.funciones = [self.y] + list(edo.derivadas)  # y, y', y''...

    # --- Reconocer la ecuación ---

    def coeficientes(self) -> Optional[Tuple[List[Any], Any]]:
        todo = sympy.expand(self.edo.izquierda - self.edo.derecha)
        a = [todo.coeff(f) for f in self.funciones]
        resto = sympy.expand(todo - sum(c * f for c, f in zip(a, self.funciones)))
        if any(not c.is_number for c in a) or a[-1] == 0 or any(resto.has(f) for f in self.funciones):
            return None
        return a, sympy.simplify(-resto)

    def coeficientes_euler(self) -> Optional[Tuple[List[Any], Any]]:
        """Cauchy-Euler: el coeficiente de y^(k) es a_k*x^k, con a_k un número: ([a_0, ..., a_n], g)."""
        x = self.x
        todo = sympy.expand(self.edo.izquierda - self.edo.derecha)
        c = [todo.coeff(f) for f in self.funciones]
        resto = sympy.expand(todo - sum(ck * f for ck, f in zip(c, self.funciones)))
        if any(resto.has(f) for f in self.funciones):
            return None
        a = [sympy.simplify(ck / x ** k) for k, ck in enumerate(c)]
        if any(not ak.is_number for ak in a) or a[-1] == 0 or all(ak == 0 for ak in a[1:-1]) and a[0] == 0:
            return None
        return a, sympy.simplify(-resto)

    def resolver(self) -> Optional[Tuple[List[Any], str]]:
        self.serie_texto = None
        if self.edo.serie:
            antes = len(self.pasos)
            resultado = self.serie()
            if resultado is not None:
                return resultado
            del self.pasos[antes:]
        if self.edo.y1 is not None:
            antes = len(self.pasos)
            resultado = self.reduccion()
            if resultado is not None:
                return resultado
            del self.pasos[antes:]  # y1 no sirve: se sigue con los demás métodos
        euler = False
        datos = self.coeficientes()
        if datos is None:
            datos, euler = self.coeficientes_euler(), True
            if datos is None:
                return None if self.edo.serie else self.serie()
        a, g = datos
        n, x, y = len(a) - 1, self.x, self.y
        homogenea = g == 0
        if euler:
            lado = suma_euler(a, self.funciones, x)
            self.pasos.append(PasoCalculo(
                tr("Tipo de ecuación: de Cauchy-Euler"),
                regla=tr("es de Cauchy-Euler si cada derivada {yk} va multiplicada por un número por {x}^k: "
                         "a_{n}*{x}^{n}*{yn} + ... + a_1*{x}*{yp} + a_0*{y} = g({x}). Se resuelve con {y} = {x}^r, "
                         "para {x} > 0 (para {x} < 0 se cambia {x} por -{x}).", yk=f"{y}^(k)", x=x, n=n,
                         yn=self.funciones[-1], yp=self.funciones[1], y=y),
                partes=tr("{ecuacion}; g({x}) = {g}.", ecuacion=f"{lado} = {texto(g)}", x=x, g=texto(g)),
                queda=tr("homogénea") if homogenea else tr("no homogénea: {y} = {y}_h + {y}_p", y=y)))
        else:
            lado = suma_lineal(a, self.funciones)
            self.pasos.append(PasoCalculo(
                tr("Tipo de ecuación: lineal con coeficientes constantes"),
                regla=tr("es lineal de orden {n} con coeficientes constantes si se puede escribir a_{n}*{yn} + ... + "
                         "a_1*{yp} + a_0*{y} = g({x}), con los a_k números. Si g = 0 es homogénea; si no, la solución "
                         "es {y} = {y}_h + {y}_p: la de la homogénea más una particular.", n=n, yn=self.funciones[-1],
                         yp=self.funciones[1], y=y, x=x),
                partes=tr("{ecuacion}; g({x}) = {g}.", ecuacion=f"{lado} = {texto(g)}", x=x, g=texto(g)),
                queda=tr("homogénea") if homogenea else tr("no homogénea: {y} = {y}_h + {y}_p", y=y)))

        raices = self.indicial(a) if euler else self.caracteristica(a)
        base = self.base(raices, euler)
        constantes = constantes_de(n)
        y_h = sum(c * f for c, f in zip(constantes, base))
        lineas = [self._aporta(raiz, beta, m, euler) for raiz, beta, m in raices]
        nombre_h = y if homogenea else sympy.Symbol(f"{y}_h")
        lineas.append(tr("Cada función se multiplica por su constante y se suman: {y} = {solucion}.", y=nombre_h,
                         solucion=texto(y_h)))
        if euler:
            regla = tr("cada raíz r aporta funciones: una raíz real simple, {x}^r; una raíz que se repite m veces, "
                       "{x}^r, {x}^r*log({x}), ..., {x}^r*log({x})^(m-1); un par complejo a ± b*i, "
                       "{x}^a*cos(b*log({x})) y {x}^a*sin(b*log({x})). La solución es una combinación de todas, con "
                       "{n} constantes.", x=x, n=n)
        else:
            regla = tr("cada raíz r aporta funciones: una raíz real simple, exp(r*{x}); una raíz que se repite m veces, "
                       "exp(r*{x}), {x}*exp(r*{x}), ..., {x}^(m-1)*exp(r*{x}); un par complejo a ± b*i, "
                       "exp(a*{x})*cos(b*{x}) y exp(a*{x})*sin(b*{x}). La solución es una combinación de todas, con "
                       "{n} constantes.", x=x, n=n)
        self.pasos.append(PasoCalculo(
            tr("Solución de la homogénea") if not homogenea else tr("Solución general"),
            regla=regla,
            partes=tr("las raíces son {raices}.", raices="; ".join(
                (_compleja(r_, b_) if b_ else texto(r_)) + (f" ({_veces(m)})" if m > 1 else "") for r_, b_, m in raices)),
            calculo=tuple(lineas),
            queda=f"{nombre_h} = {texto(y_h)}"))
        if homogenea:
            return [sympy.Eq(y, y_h)], (tr("ecuación de Cauchy-Euler (y = x^r)") if euler else
                                        tr("lineal con coeficientes constantes (ecuación característica)"))

        y_p = None if euler else self.particular(a, g, raices)
        if y_p is not None:
            metodo = tr("lineal con coeficientes constantes, no homogénea (coeficientes indeterminados)")
        else:
            y_p = self.variacion(a, g, base, euler)
            if y_p is None:
                return None
            metodo = (tr("ecuación de Cauchy-Euler, no homogénea (variación de parámetros)") if euler else
                      tr("lineal con coeficientes constantes, no homogénea (variación de parámetros)"))
        solucion = y_h + y_p
        self.pasos.append(PasoCalculo(
            tr("Solución general"),
            regla=tr("la solución general de la no homogénea es la de la homogénea más la particular: {y} = {y}_h + "
                     "{y}_p.", y=y),
            calculo=((f"{y} = {texto(y_h)} + {texto(y_p)}").replace("+ -", "- "),),
            queda=f"{y} = {texto(solucion)}"))
        return [sympy.Eq(y, solucion)], metodo

    # --- Ecuación característica y sus raíces ---

    def caracteristica(self, a: List[Any]) -> List[Tuple[Any, Any, int]]:
        """[(raíz real o parte real, parte imaginaria (0 si es real), multiplicidad)]."""
        r, x, y = self.r, self.x, self.y
        p = sum(c * r ** k for k, c in enumerate(a))
        derivadas = [f"{nombre_derivada(y, k)} = {texto(r ** k * sympy.exp(r * x))}" for k in range(1, len(a))]
        lineas = [tr("Probamos {y} = exp(r*{x}): {derivadas}.", y=y, x=x, derivadas="; ".join(derivadas)),
                  tr("Sustituimos y dividimos entre exp(r*{x}), que nunca vale 0: cada {yk} se cambia por r^k.",
                     x=x, yk=f"{y}^(k)"),
                  f"{texto(p)} = 0."]
        self.pasos.append(PasoCalculo(
            tr("Ecuación característica"),
            regla=tr("las soluciones de la homogénea son de la forma exp(r*{x}): cada derivada multiplica por r, así "
                     "que r tiene que cumplir un polinomio, el de la ecuación característica.", x=x),
            partes=tr("la parte homogénea es {ecuacion}.", ecuacion=f"{suma_lineal(a, self.funciones)} = 0"),
            calculo=tuple(lineas),
            queda=f"{texto(p)} = 0"))
        return self._raices(p, tr("Raíces de la ecuación característica"))

    def indicial(self, a: List[Any]) -> List[Tuple[Any, Any, int]]:
        """Cauchy-Euler: con y = x^r, x^k*y^(k) = r*(r - 1)*...*(r - k + 1)*x^r."""
        r, x, y = self.r, self.x, self.y

        def caida(k: int) -> str:  # r*(r - 1)*...*(r - k + 1)
            return "*".join(entre_parentesis(r - j) for j in range(k))
        derivadas = [f"{nombre_derivada(y, k)} = {caida(k)}*{x}^{entre_parentesis(r - k)}" for k in range(1, len(a))]
        terminos = []
        for k, ak in enumerate(a):
            if ak == 0:
                continue
            cuerpo = caida(k) if k else "1"
            valor = ak if not ak.could_extract_minus_sign() else -ak
            termino = cuerpo if valor == 1 and k else (f"{texto(valor)}*{cuerpo}" if k else texto(valor))
            signo = "-" if ak.could_extract_minus_sign() else "+"
            terminos.append((signo, termino))
        sin_operar = ("-" if terminos[-1][0] == "-" else "") + terminos[-1][1] + "".join(
            f" {s} {t}" for s, t in reversed(terminos[:-1]))
        p = sympy.expand(sum(ak * sympy.ff(r, k) for k, ak in enumerate(a)))
        lineas = [tr("Probamos {y} = {x}^r: {derivadas}.", y=y, x=x, derivadas="; ".join(derivadas)),
                  tr("Cada {x}^k*{yk} queda r*(r - 1)*...*{x}^r: al sustituir, todos los términos llevan {x}^r, y "
                     "se divide entre {x}^r (no vale 0 para {x} > 0).", x=x, yk=f"{y}^(k)"),
                  f"{sin_operar} = 0.",
                  tr("Operamos: {p} = 0.", p=texto(p))]
        self.pasos.append(PasoCalculo(
            tr("Ecuación indicial"),
            regla=tr("las soluciones de la homogénea son de la forma {x}^r: cada {x}^k*{yk} da un polinomio en r por "
                     "{x}^r, y r tiene que cumplir la ecuación indicial.", x=x, yk=f"{y}^(k)"),
            partes=tr("la parte homogénea es {ecuacion}.", ecuacion=f"{suma_euler(a, self.funciones, x)} = 0"),
            calculo=tuple(lineas),
            queda=f"{texto(p)} = 0"))
        return self._raices(p, tr("Raíces de la ecuación indicial"))

    def _raices(self, p: Any, titulo: str) -> List[Tuple[Any, Any, int]]:
        r = self.r
        lineas: List[str] = []
        raices: List[Tuple[Any, Any, int]] = []
        grado = sympy.degree(p, r)
        if grado <= 2:
            raices = self._grado_menor(sympy.Poly(p, r), 1, lineas)
            raices.sort(key=lambda t: (t[1] != 0, t[0]))  # las reales, de menor a mayor
        else:
            lc, factores = sympy.factor_list(p, r)
            if any(sympy.degree(f, r) > 2 for f, _ in factores):
                raise SinExplicacion()
            explicador = ExplicadorFactorizar()
            try:
                explicador.explicar(p)
                self.pasos.extend(explicador.pasos)
            except SinFactorizacion:
                lineas.append(tr("Factorizamos: {p} = {f}.", p=texto(p), f=texto(sympy.factor(p))))
            lineas.append(tr("Cada factor igualado a 0 (producto nulo):"))
            for f, m in factores:
                raices += self._grado_menor(sympy.Poly(f, r), m, lineas)
            raices.sort(key=lambda t: (t[1] != 0, t[0]))  # las reales, de menor a mayor
        self.pasos.append(PasoCalculo(
            titulo,
            regla=tr("de primer grado, se despeja r; de segundo grado, la fórmula r = (-b ± sqrt(D))/(2*a) con el "
                     "discriminante D = b^2 - 4*a*c: si D > 0, dos raíces reales; si D = 0, una doble; si D < 0, dos "
                     "complejas conjugadas (sqrt(D) = sqrt(-D)*i). De grado mayor, se factoriza antes."),
            partes=tr("la ecuación es {p} = 0.", p=texto(p)),
            calculo=tuple(lineas),
            queda="; ".join(f"r = {_compleja(r_, b_) if b_ else texto(r_)}" + (f" ({_veces(m)})" if m > 1 else "")
                            for r_, b_, m in raices)))
        return raices

    def _grado_menor(self, poli: Any, veces: int, lineas: List[str]) -> List[Tuple[Any, Any, int]]:
        r = self.r
        coef = poli.all_coeffs()
        if len(coef) == 2:
            a1, a0 = coef
            raiz = -a0 / a1
            lineas.append(tr("{p} = 0: r = {raiz}.", p=texto(poli.as_expr()), raiz=texto(raiz)))
            return [(raiz, 0, veces)]
        a, b, c = coef
        D = b ** 2 - 4 * a * c
        lineas.append(tr("{p} = 0: a = {a}, b = {b}, c = {c}; D = b^2 - 4*a*c = {cuenta} = {D}.", p=texto(poli.as_expr()),
                         a=texto(a), b=texto(b), c=texto(c), D=texto(D),
                         cuenta=f"{entre_parentesis(b)}^2 - 4*{entre_parentesis(a)}*{entre_parentesis(c)}"))
        if D == 0:
            raiz = -b / (2 * a)
            lineas.append(tr("D = 0: una raíz doble, r = -b/(2*a) = {cuenta} = {raiz}.",
                             cuenta=f"{texto(-b)}/{entre_parentesis(2 * a)}", raiz=texto(raiz)))
            return [(raiz, 0, 2 * veces)]
        raiz_d = sympy.sqrt(abs(D))
        if D > 0:
            r1, r2 = (-b + raiz_d) / (2 * a), (-b - raiz_d) / (2 * a)
            lineas.append(tr("D > 0: dos raíces reales, r = ({menos_b} ± sqrt({D}))/{dos_a} = ({menos_b} ± {raiz})/{dos_a}: "
                             "r = {r1} y r = {r2}.", menos_b=texto(-b), D=texto(D), dos_a=entre_parentesis(2 * a),
                             raiz=texto(raiz_d), r1=texto(sympy.simplify(r1)), r2=texto(sympy.simplify(r2))))
            return [(sympy.simplify(r1), 0, veces), (sympy.simplify(r2), 0, veces)]
        alfa, beta = sympy.simplify(-b / (2 * a)), sympy.simplify(raiz_d / (2 * a))
        lineas.append(tr("D < 0: no hay raíces reales; sqrt({D}) = sqrt({menos_D})*i = {raiz}*i, y r = ({menos_b} ± "
                         "{raiz}*i)/{dos_a} = {raices}.", D=texto(D), menos_D=texto(-D), raiz=factor(raiz_d),
                         menos_b=texto(-b), dos_a=entre_parentesis(2 * a), raices=_compleja(alfa, beta)))
        return [(alfa, beta, veces)]

    def _funciones(self, raiz: Any, beta: Any, m: int, euler: bool) -> List[Any]:
        """Lo que aporta una raíz: exp(r*x)... o, en Cauchy-Euler, x^r, x^r*log(x)..."""
        x = self.x
        if euler:
            potencia, angulo, repite = x ** raiz, beta * sympy.log(x), sympy.log(x)
        else:
            potencia, angulo, repite = sympy.exp(raiz * x), beta * x, x
        funciones = []
        for k in range(m):
            if beta:
                funciones += [repite ** k * potencia * sympy.cos(angulo), repite ** k * potencia * sympy.sin(angulo)]
            else:
                funciones.append(repite ** k * potencia)
        return funciones

    def base(self, raices: List[Tuple[Any, Any, int]], euler: bool = False) -> List[Any]:
        return [f for raiz, beta, m in raices for f in self._funciones(raiz, beta, m, euler)]

    def _aporta(self, raiz: Any, beta: Any, m: int, euler: bool = False) -> str:
        return tr("r = {r} ({veces}): aporta {funciones}.", r=_compleja(raiz, beta) if beta else texto(raiz),
                  veces=_veces(m), funciones=", ".join(texto(f) for f in self._funciones(raiz, beta, m, euler)))

    # --- Reducción de orden ---

    def reduccion(self) -> Optional[Tuple[List[Any], str]]:
        """y'' + P*y' + Q*y = g con una solución conocida y1 de la homogénea: y2 = u*y1, u' = exp(-∫P dx)/y1^2."""
        x, y, y1 = self.x, self.y, self.edo.y1
        todo = sympy.expand(self.edo.izquierda - self.edo.derecha)
        a = [sympy.factor_terms(todo.coeff(f)) for f in self.funciones]
        resto = sympy.expand(todo - sum(c * f for c, f in zip(a, self.funciones)))
        if len(a) != 3 or any(c.has(y) or any(c.has(f) for f in self.funciones) for c in a) or a[2] == 0 \
                or any(resto.has(f) for f in self.funciones):
            return None
        g = sympy.simplify(-resto)
        d1 = sympy.simplify(sympy.diff(y1, x))
        d2 = sympy.simplify(sympy.diff(d1, x))
        homogenea = sympy.simplify(a[2] * d2 + a[1] * d1 + a[0] * y1)
        if homogenea != 0:
            nota = tr("NOTA: {y1} no es solución de la parte homogénea (al sustituirla queda {resto}, no 0): no sirve "
                      "para reducir el orden.", y1=texto(y1), resto=texto(homogenea))
            self.avisos.append(nota)
            self.motor._notas_metodo.append(nota)
            return None
        P = sympy.simplify(a[1] / a[2])
        lado = suma_lineal(a, self.funciones)
        self.pasos.append(PasoCalculo(
            tr("Tipo de ecuación: reducción de orden"),
            regla=tr("si se conoce una solución y1 de la homogénea {ypp} + P({x})*{yp} + Q({x})*{y} = 0, otra "
                     "independiente es y2 = u*y1: al sustituir, u' cumple una ecuación de primer orden, y "
                     "u' = exp(-∫ P d{x})/y1^2.", ypp=self.funciones[2], yp=self.funciones[1], y=y, x=x),
            partes=tr("{ecuacion}; y1 = {y1}.", ecuacion=f"{lado} = {texto(g)}", y1=texto(y1)),
            calculo=(tr("y1' = {d1}; y1'' = {d2}.", d1=texto(d1), d2=texto(d2)),
                     tr("Comprobamos y1 en la homogénea: {sustituida} = 0.", sustituida=sustituir(
                         sympy.Add(*[c * f for c, f in zip(a, self.funciones)]),
                         {y: y1, self.funciones[1]: d1, self.funciones[2]: d2})),
                     tr("Dividimos entre {a2}, lo que multiplica a {ypp}: P({x}) = {P}.", a2=texto(a[2]),
                        ypp=self.funciones[2], x=x, P=texto(P)) if a[2] != 1 else f"P({x}) = {texto(P)}."),
            queda=f"y1 = {texto(y1)}; P({x}) = {texto(P)}"))

        coef_u = sympy.simplify(2 * d1 + P * y1)
        lineas = [tr("{y} = u*y1: {yp} = u'*y1 + u*y1'; {ypp} = u''*y1 + 2*u'*y1' + u*y1''.", y=y,
                     yp=self.funciones[1], ypp=self.funciones[2]),
                  tr("Al sustituir, los términos con u se anulan (y1 es solución) y queda y1*u'' + (2*y1' + P*y1)*u' "
                     "= 0: {ecuacion}.", ecuacion=f"{factor(y1)}*u'' + {factor(coef_u)}*u' = 0"),
                  tr("Con w = u' es de primer orden y separable: w'/w = -(2*y1'/y1 + P); integrando, "
                     "log(w) = -2*log(y1) - ∫ P d{x}, y w = exp(-∫ P d{x})/y1^2.", x=x)]
        self.pasos.append(PasoCalculo(
            tr("Cambio y2 = u*y1"),
            regla=tr("se deriva y = u*y1 con la regla del producto y se sustituye: como y1 ya es solución, solo "
                     "quedan u'' y u', y la ecuación baja de orden."),
            partes=f"y1 = {texto(y1)}.",
            calculo=tuple(lineas),
            queda="u' = exp(-∫ P dx)/y1^2"))
        primitiva = self.motor._integrar(P, x, self.pasos) if P != 0 else sympy.S.Zero
        exponencial = sympy.exp(-_con_abs(primitiva)).replace(lambda e: isinstance(e, sympy.Abs), lambda e: e.args[0])
        w = sympy.simplify(exponencial / y1 ** 2)
        u = _con_abs(self.motor._integrar(w, x, self.pasos))
        y2 = _mas_corta(sympy.simplify(u * y1), sympy.expand(u * y1))
        lineas = [f"∫ {factor(P)} d{x} = {texto(primitiva)}; exp(-({texto(primitiva)})) = {texto(exponencial)}.",
                  tr("u' = {e}/{y1c} = {w}.", e=factor(exponencial), y1c=factor(y1 ** 2), w=texto(w)),
                  f"u = ∫ {factor(w)} d{x} = {texto(u)}.",
                  tr("y2 = u*y1 = {cuenta} = {y2} (sin constantes: basta una solución más).",
                     cuenta=f"{factor(u)}*{factor(y1)}", y2=texto(y2))]
        self.pasos.append(PasoCalculo(
            tr("Hallar y2"),
            regla=tr("se integra P, se calcula u' = exp(-∫ P d{x})/y1^2, se integra u' (los pasos están arriba) y "
                     "y2 = u*y1.", x=x),
            calculo=tuple(lineas),
            queda=f"y2 = {texto(y2)}"))
        base = [y1, y2]
        C1, C2 = constantes_de(2)
        y_h = C1 * y1 + C2 * y2
        homogenea = g == 0
        nombre_h = y if homogenea else sympy.Symbol(f"{y}_h")
        self.pasos.append(PasoCalculo(
            tr("Solución general") if homogenea else tr("Solución de la homogénea"),
            regla=tr("con dos soluciones independientes, la general es su combinación: C1*y1 + C2*y2."),
            queda=f"{nombre_h} = {texto(y_h)}"))
        if homogenea:
            return [sympy.Eq(y, y_h)], tr("reducción de orden (y2 = u*y1)")
        y_p = self.variacion(a, g, base, False)
        if y_p is None:
            return None
        solucion = y_h + y_p
        self.pasos.append(PasoCalculo(
            tr("Solución general"),
            regla=tr("la solución general de la no homogénea es la de la homogénea más la particular: {y} = {y}_h + "
                     "{y}_p.", y=y),
            calculo=((f"{y} = {texto(y_h)} + {texto(y_p)}").replace("+ -", "- "),),
            queda=f"{y} = {texto(solucion)}"))
        return [sympy.Eq(y, solucion)], tr("reducción de orden y variación de parámetros")

    # --- Series de potencias ---

    TERMINOS_SERIE = 6  # hasta x^6

    def serie(self) -> Optional[Tuple[List[Any], str]]:
        """
        y'' + P*y' + Q*y = 0 con coeficientes polinómicos y x = 0 punto ordinario: y = Σ c_n*x^n.
        Se sustituye, se igualan a 0 los coeficientes de x^m y sale la recurrencia de c_(m+2).
        """
        x, y = self.x, self.y
        todo = sympy.expand(self.edo.izquierda - self.edo.derecha)
        a = [todo.coeff(f) for f in self.funciones]
        resto = sympy.expand(todo - sum(c * f for c, f in zip(a, self.funciones)))
        if len(a) != 3 or resto != 0 or any(not c.is_polynomial(x) or any(c.has(f) for f in self.funciones)
                                             for c in a):
            return None
        a2_0 = a[2].subs(x, 0)
        if a2_0 == 0:
            return None
        N = self.TERMINOS_SERIE
        c = sympy.IndexedBase("c")
        m = sympy.Symbol("m", integer=True, nonnegative=True)
        n = sympy.Symbol("n", integer=True, nonnegative=True)
        lado = suma_lineal(a, self.funciones)
        self.pasos.append(PasoCalculo(
            tr("Tipo de ecuación: solución en serie de potencias"),
            regla=tr("si los coeficientes son polinomios y el de {ypp} no vale 0 en {x} = 0 ({x} = 0 es un punto "
                     "ordinario), la solución es una serie de potencias {y} = Σ c[n]*{x}^n: se sustituye y se "
                     "hallan los coeficientes c[n] uno a uno.", ypp=self.funciones[2], x=x, y=y),
            partes=tr("{ecuacion}; el coeficiente de {ypp} en {x} = 0 vale {a}.", ecuacion=f"{lado} = 0",
                      ypp=self.funciones[2], x=x, a=texto(a2_0)),
            queda=f"{y} = Σ c[n]*{x}^n"))

        # Cada término a_(k,j)*x^j*y^(k), con el índice desplazado para que quede x^m
        lineas = [tr("{y} = Σ c[n]*{x}^n; {yp} = Σ n*c[n]*{x}^(n - 1); {ypp} = Σ n*(n - 1)*c[n]*{x}^(n - 2).",
                     y=y, x=x, yp=self.funciones[1], ypp=self.funciones[2])]
        recurrencia = sympy.S.Zero
        for k in range(3):
            poli = sympy.Poly(a[k], x)
            for (j,), coef in zip(poli.monoms(), poli.coeffs()):
                if coef == 0:
                    continue
                desplazado = m + k - j
                termino = coef * sympy.ff(desplazado, k) * c[desplazado]
                recurrencia += termino
                potencia = n - k + j
                original = texto(sympy.factor(coef * sympy.ff(n, k)) * c[n]) + (
                    f"*{x}^{entre_parentesis(potencia)}" if potencia != 0 else "")
                nombre = texto(coef * x ** j) + "*" + str(self.funciones[k]) if (coef * x ** j) != 1 \
                    else str(self.funciones[k])
                lineas.append(tr("{termino}: Σ {original}; con n = {desplazado} queda Σ {nuevo}*{x}^m.",
                                 termino=nombre.replace("-1*", "-"), original=original, desplazado=texto(desplazado),
                                 nuevo=entre_parentesis(sympy.factor(termino)), x=x))
        lineas.append(tr("El coeficiente de {x}^m tiene que valer 0: {recurrencia} = 0.", x=x,
                         recurrencia=texto(recurrencia)))
        principal = sympy.expand(recurrencia).coeff(c[m + 2])
        despejado = sympy.factor(sympy.expand(-(recurrencia - principal * c[m + 2]) / principal))
        self.pasos.append(PasoCalculo(
            tr("Sustituir la serie"),
            regla=tr("se sustituye cada derivada y se cambia el índice de cada suma para que todas lleven {x}^m; una "
                     "serie vale 0 solo si cada coeficiente vale 0. Los c con índice negativo valen 0.", x=x),
            partes=tr("los coeficientes son polinomios: {coefs}.", coefs="; ".join(
                f"{self.funciones[k]}: {texto(a[k])}" for k in range(3))),
            calculo=tuple(lineas),
            queda=f"c[m + 2] = {texto(despejado)}"))

        # Los coeficientes: c0 y c1 libres (C1 y C2); los demás, con la recurrencia
        C1, C2 = constantes_de(2)
        valores = {0: C1, 1: C2}
        lineas = [tr("c[0] = {y}(0) y c[1] = {yp}(0) quedan libres: c[0] = C1, c[1] = C2.", y=y,
                     yp=self.funciones[1])]
        for mm in range(N - 1):
            cuenta = despejado.subs(m, mm)
            sustituida = cuenta.replace(lambda e: isinstance(e, sympy.Indexed),
                                        lambda e: valores.get(int(e.indices[0]), 0) if e.indices[0] >= 0 else 0)
            valor = sympy.expand(sustituida)
            valores[mm + 2] = valor
            lineas.append(f"m = {mm}: c[{mm + 2}] = {texto(cuenta)} = {texto(valor)}.")
        serie = sum(valores[k] * x ** k for k in range(N + 1))
        agrupada = sympy.collect(sympy.expand(serie), [C1, C2], evaluate=False)
        orden = sympy.Order(x ** (N + 1))
        agrupados = [sympy.Mul(constante, agrupada[constante], evaluate=False) for constante in (C1, C2)
                     if agrupada.get(constante, 0) != 0]
        partes_c = [texto(sympy.Add(g, orden, evaluate=False)).rsplit(" + O(", 1)[0] for g in agrupados]
        self.pasos.append(PasoCalculo(
            tr("Coeficientes de la serie"),
            regla=tr("con la recurrencia, cada coeficiente sale de los anteriores: se dan valores a m = 0, 1, 2..."),
            calculo=tuple(lineas),
            queda=" + ".join(partes_c) + f" + O({x}^{N + 1})"))

        # Comprobación: hasta x^(N - 2), los coeficientes del lado izquierdo se anulan
        derivadas = [serie, sympy.diff(serie, x), sympy.diff(serie, x, 2)]
        residuo = sympy.expand(sum(ak * d for ak, d in zip(a, derivadas)))
        coeficientes = [residuo.coeff(x, k) for k in range(N - 1)]
        if any(sympy.simplify(co) != 0 for co in coeficientes):
            raise SinExplicacion()
        self.pasos.append(PasoCalculo(
            tr("Comprobación"),
            regla=tr("al sustituir la serie cortada en {x}^{N}, los coeficientes de {x}^0 a {x}^{M} del lado izquierdo "
                     "valen 0; los de grado mayor dependen de los términos que se dejan fuera.", x=x, N=N, M=N - 2),
            calculo=(tr("Los coeficientes de {x}^0, ..., {x}^{M} valen 0.", x=x, M=N - 2),),
            queda=tr("la solución es correcta hasta {x}^{N}", x=x, N=N)))
        solucion = sympy.Add(*agrupados, orden, evaluate=False)
        self.motor._por_tramos.add(sympy.Eq(y, solucion))
        self.serie_texto = " + ".join(partes_c) + f" + O({x}^{N + 1})"
        return [sympy.Eq(y, solucion)], tr("serie de potencias alrededor de x = 0")

    # --- Variación de parámetros ---

    def variacion(self, a: List[Any], g: Any, base: List[Any], euler: bool) -> Optional[Any]:
        """
        y_p = u1*y1 + u2*y2 con u1' = -y2*f/W y u2' = y1*f/W, donde f es g dividida entre el coeficiente
        de y'' y W = y1*y2' - y2*y1' es el wronskiano (orden 2).
        """
        if len(base) != 2:
            return None
        x, y = self.x, self.y
        y1, y2 = base
        principal = a[2] * x ** 2 if euler else a[2]
        f = sympy.simplify(g / principal)
        d1 = _mas_corta(sympy.diff(y1, x), sympy.simplify(sympy.diff(y1, x)))
        d2 = _mas_corta(sympy.diff(y2, x), sympy.simplify(sympy.diff(y2, x)))
        crudo = sympy.expand(y1 * d2 - y2 * d1)
        W = sympy.simplify(crudo)
        if W == 0:
            return None
        u1p = sympy.simplify(-y2 * f / W)
        u2p = sympy.simplify(y1 * f / W)
        lineas = [f"y1 = {texto(y1)}; y1' = {texto(d1)}.", f"y2 = {texto(y2)}; y2' = {texto(d2)}."]
        if principal != 1:
            lineas.append(tr("La ecuación se divide entre {p}, lo que multiplica a {ypp}: f = {g}/{pp} = {f}.",
                             p=texto(principal), ypp=self.funciones[2], g=factor(g), pp=factor(principal), f=texto(f)))
        else:
            lineas.append(f"f = {texto(f)}.")
        cuenta_w = f"{factor(y1)}*{factor(d2)} - {factor(y2)}*{factor(d1)}"
        cadena = list(dict.fromkeys([cuenta_w, texto(crudo), texto(W)]))
        lineas.append(tr("El wronskiano: W = y1*y2' - y2*y1' = {cuenta}.", cuenta=" = ".join(cadena)))
        if crudo.has(sympy.sin) and crudo.has(sympy.cos) and not W.has(sympy.sin, sympy.cos):
            lineas.append(tr("(sin(u)^2 + cos(u)^2 = 1.)"))
        entre_w = f"/{factor(W)}" if W != 1 else ""
        lineas.append(tr("u1' = -y2*f/W = {cuenta} = {valor}.", cuenta=f"-{factor(y2)}*{factor(f)}{entre_w}",
                         valor=texto(u1p)))
        lineas.append(tr("u2' = y1*f/W = {cuenta} = {valor}.", cuenta=f"{factor(y1)}*{factor(f)}{entre_w}",
                         valor=texto(u2p)))
        self.pasos.append(PasoCalculo(
            tr("Variación de parámetros"),
            regla=tr("se busca {y}_p = u1*y1 + u2*y2, con y1 e y2 las funciones de {y}_h y u1, u2 funciones por "
                     "hallar. Las condiciones de clase dan u1' = -y2*f/W y u2' = y1*f/W, donde f es g dividida entre "
                     "lo que multiplica a {ypp} y W = y1*y2' - y2*y1' es el wronskiano (no vale 0).", y=y,
                     ypp=self.funciones[2]),
            partes=tr("g({x}) = {g}.", x=x, g=texto(g)),
            calculo=tuple(lineas),
            queda=f"u1' = {texto(u1p)}; u2' = {texto(u2p)}"))
        primitiva1 = self.motor._integrar(u1p, x, self.pasos)
        primitiva2 = self.motor._integrar(u2p, x, self.pasos)
        u1, u2 = _con_abs(primitiva1), _con_abs(primitiva2)
        y_p = _mas_corta(sympy.simplify(u1 * y1 + u2 * y2), sympy.expand(u1 * y1 + u2 * y2), u1 * y1 + u2 * y2)
        lineas = [f"u1 = ∫ {factor(u1p)} d{x} = {texto(primitiva1)}.", f"u2 = ∫ {factor(u2p)} d{x} = {texto(primitiva2)}."]
        lineas += list(MotorEdo._lineas_abs(primitiva1, primitiva2))
        lineas += [tr("No hace falta sumar constantes: darían términos que ya están en {y}_h.", y=y),
                  f"{y}_p = u1*y1 + u2*y2 = {factor(u1)}*{factor(y1)} + {factor(u2)}*{factor(y2)} = {texto(y_p)}."
                  .replace("+ -", "- ")]
        self.pasos.append(PasoCalculo(
            tr("Integrar u1' y u2'"),
            regla=tr("u1 y u2 son las primitivas de u1' y u2' (los pasos de cada integral están arriba); con ellas, "
                     "{y}_p = u1*y1 + u2*y2.", y=y),
            calculo=tuple(lineas),
            queda=f"{y}_p = {texto(y_p)}"))
        return y_p

    # --- Coeficientes indeterminados ---

    def particular(self, a: List[Any], g: Any, raices: List[Tuple[Any, Any, int]]) -> Optional[Any]:
        x, y = self.x, self.y
        grupos: Dict[Tuple[Any, Any], int] = {}
        terminos: Dict[Tuple[Any, Any], List[Any]] = {}
        for t in sympy.Add.make_args(sympy.expand(g)):
            forma = self._forma(t)
            if forma is None:
                return None
            k, alfa, beta = forma
            grupos[(alfa, beta)] = max(grupos.get((alfa, beta), 0), k)
            terminos.setdefault((alfa, beta), []).append(t)
        letras = iter(LETRAS)
        incognitas: List[Any] = []
        prueba = sympy.S.Zero
        lineas = []
        for (alfa, beta), grado in grupos.items():
            s = next((m for r_, b_, m in raices if sympy.simplify(r_ - alfa) == 0 and sympy.simplify(b_ - beta) == 0),
                     0)
            polinomios = []
            for _ in range(2 if beta else 1):
                coefs = [sympy.Symbol(next(letras)) for _ in range(grado + 1)]
                incognitas += coefs
                polinomios.append(sum(c * x ** j for j, c in enumerate(reversed(coefs))))
            exponencial = sympy.exp(alfa * x) if alfa != 0 else sympy.S.One
            if beta:
                forma = exponencial * (polinomios[0] * sympy.cos(beta * x) + polinomios[1] * sympy.sin(beta * x))
            else:
                forma = exponencial * polinomios[0]
            descripcion = self._describe(grado, alfa, beta)
            linea = tr("{terminos}: {descripcion}; se prueba {forma}.",
                       terminos=" + ".join(texto(t) for t in terminos[(alfa, beta)]).replace("+ -", "- "),
                       descripcion=descripcion, forma=texto(forma))
            if s:
                raiz = _compleja(alfa, beta) if beta else texto(alfa)
                linea += " " + tr("Pero {raiz} es raíz ({veces}) de la ecuación característica: esas funciones ya están "
                                  "en {y}_h, y se multiplica por {xs}.", raiz=raiz, veces=_veces(s), y=y,
                                  xs=texto(x ** s))
                forma = x ** s * forma
            lineas.append(linea)
            prueba += forma
        self.pasos.append(PasoCalculo(
            tr("Forma de la solución particular"),
            regla=tr("{y}_p se prueba con la forma de g: un polinomio de grado d, un polinomio general de grado d; "
                     "exp(a*{x}), A*exp(a*{x}); cos(b*{x}) o sin(b*{x}), A*cos(b*{x}) + B*sin(b*{x}) (siempre los "
                     "dos); un producto, el producto de las formas. Si a + b*i es raíz de la ecuación característica "
                     "(m veces), la forma se multiplica por {x}^m. Las letras mayúsculas son los coeficientes por "
                     "hallar.", y=y, x=x),
            partes=tr("g({x}) = {g}.", x=x, g=texto(g)),
            calculo=tuple(lineas),
            queda=f"{y}_p = {texto(prueba)}"))

        # Derivar y sustituir
        lineas = []
        derivadas = [prueba]
        for k in range(1, len(a)):
            d = sympy.diff(derivadas[-1], x)
            d = _mas_corta(sympy.expand(d), sympy.factor_terms(sympy.expand(d)), sympy.simplify(d))
            derivadas.append(d)
            lineas.append(f"{nombre_derivada(sympy.Symbol(f'{y}_p'), k)} = {texto(d)}.")
        lado = sympy.expand(sum(c * d for c, d in zip(a, derivadas)))
        agrupado, bases = self._agrupar(lado, incognitas)
        lineas.append(tr("Sustituimos en el lado izquierdo, {lado}, y agrupamos: {agrupado} = {g}.",
                         lado=suma_lineal(a, self.funciones), agrupado=agrupado, g=texto(g)))
        self.pasos.append(PasoCalculo(
            tr("Sustituir {y}_p en la ecuación", y=y),
            regla=tr("se deriva {y}_p las veces que haga falta y se sustituye en el lado izquierdo; después se juntan "
                     "los términos de cada función.", y=y),
            partes=f"{y}_p = {texto(prueba)}.",
            calculo=tuple(lineas),
            queda=f"{agrupado} = {texto(g)}"))

        # Igualar coeficientes
        _, bases_g = self._agrupar(sympy.expand(g), incognitas)
        claves = list(dict.fromkeys(list(bases) + list(bases_g)))
        ecuaciones = [(bases.get(b, sympy.S.Zero), bases_g.get(b, sympy.S.Zero)) for b in claves]
        lineas = [tr("De {funcion}: {ecuacion}.", funcion=texto(b), ecuacion=f"{texto(i)} = {texto(d)}") if b != 1
                  else tr("De los términos constantes: {ecuacion}.", ecuacion=f"{texto(i)} = {texto(d)}")
                  for b, (i, d) in zip(claves, ecuaciones)]
        solucion = resolver_sistema(ecuaciones, incognitas, lineas)
        y_p = prueba.subs(solucion)
        y_p = _mas_corta(sympy.expand(y_p), sympy.factor_terms(y_p), sympy.simplify(y_p), y_p)
        self.pasos.append(PasoCalculo(
            tr("Igualar coeficientes"),
            regla=tr("los dos lados son iguales para todo {x} solo si coinciden los coeficientes de cada función: "
                     "sale un sistema de ecuaciones para los coeficientes.", x=x),
            partes=tr("las incógnitas son {letras}.", letras=", ".join(str(v) for v in incognitas)),
            calculo=tuple(lineas) + (tr("Sustituimos en {y}_p: {y}_p = {valor}.", y=y, valor=texto(y_p)),),
            queda=f"{y}_p = {texto(y_p)}"))
        return y_p

    def _forma(self, t: Any) -> Optional[Tuple[int, Any, Any]]:
        """c*x^k*exp(a*x)*cos(b*x) (o sin): (k, a, b); None si el término no es de esa forma."""
        x = self.x
        k, alfa, beta = 0, sympy.S.Zero, sympy.S.Zero
        for f in sympy.Mul.make_args(t):
            if not f.has(x):
                continue
            if f == x:
                k += 1
            elif f.is_Pow and f.base == x and f.exp.is_Integer and f.exp > 0:
                k += int(f.exp)
            elif isinstance(f, sympy.exp) and sympy.Poly(f.args[0], x).degree() == 1 and \
                    sympy.Poly(f.args[0], x).coeffs()[-1:] and f.args[0].subs(x, 0) == 0:
                alfa += f.args[0].coeff(x)
            elif isinstance(f, (sympy.sin, sympy.cos)) and f.args[0].is_polynomial(x) and \
                    sympy.degree(f.args[0], x) == 1 and f.args[0].subs(x, 0) == 0 and beta == 0:
                beta = abs(f.args[0].coeff(x))
            else:
                return None
        return k, alfa, beta

    def _describe(self, grado: int, alfa: Any, beta: Any) -> str:
        x = self.x
        partes = [tr("un polinomio de grado {d}", d=grado)] if grado or (not alfa and not beta) else []
        if alfa:
            partes.append(texto(sympy.exp(alfa * x)))
        if beta:
            partes.append(tr("cos o sin de {b}", b=texto(beta * x)))
        return tr("es {partes}", partes=tr(" por ").join(partes))

    def _agrupar(self, expr: Any, incognitas: List[Any]) -> Tuple[str, Dict[Any, Any]]:
        """expr como suma de coeficiente*función (x^k*exp(a*x)*cos(b*x)...): (texto, {función: coeficiente})."""
        x = self.x
        bases: Dict[Any, Any] = {}
        for t in sympy.Add.make_args(sympy.expand(sympy.powsimp(expr))):
            coef, funcion = t.as_independent(x, as_Add=False)
            bases[funcion] = bases.get(funcion, 0) + coef
        bases = {f: sympy.expand(c) for f, c in bases.items() if sympy.expand(c) != 0}
        partes = []
        for f, c in bases.items():
            if c.is_Add:
                termino = f"({texto(c)})*{texto(f)}" if f != 1 else f"({texto(c)})"
                partes.append((" + ", termino))
            else:
                signo, c = (" - ", -c) if c.could_extract_minus_sign() else (" + ", c)
                partes.append((signo, texto(c * f)))
        if not partes:
            return "0", bases
        suma = ("-" if partes[0][0] == " - " else "") + partes[0][1] + "".join(s + t for s, t in partes[1:])
        return suma, bases

    # --- Condiciones iniciales ---

    def condiciones_serie(self, solucion: Any, condiciones: List[Condicion]) -> Any:
        """En la serie alrededor de 0, c[0] = y(0) y c[1] = y'(0): C1 y C2 son esos valores."""
        y = self.y
        C1, C2 = constantes_de(2)
        valores = {}
        for cond in condiciones:
            if cond.punto != 0 or cond.orden > 1:
                raise SinExplicacion()
            valores[C1 if cond.orden == 0 else C2] = cond.valor
        particular = sympy.Add(*[a.subs(valores) for a in solucion.args if a.subs(valores) != 0], evaluate=False)
        self.motor._por_tramos.add(sympy.Eq(y, particular))
        self.pasos.append(PasoCalculo(
            tr("Condiciones iniciales"),
            regla=tr("en la serie, c[0] = {y}(0) y c[1] = {yp}(0): las constantes son directamente las condiciones.",
                     y=y, yp=self.funciones[1]),
            calculo=tuple(f"{c} = {texto(v)}" for c, v in valores.items()),
            queda=f"{y} = {texto(particular)}"))
        return particular

    def condiciones(self, solucion: Any, condiciones: List[Condicion]) -> Any:
        x, y = self.x, self.y
        constantes = sorted({s for s in solucion.free_symbols if es_constante(s)}, key=lambda s: s.name)
        lineas, ecuaciones = [], []
        derivada = solucion
        derivadas = {0: solucion}
        for k in range(1, max(c.orden for c in condiciones) + 1):
            derivada = _mas_corta(sympy.diff(derivada, x), sympy.expand(sympy.diff(derivada, x)),
                                  sympy.simplify(sympy.diff(derivada, x)))
            derivadas[k] = derivada
            lineas.append(tr("Derivamos: {d} = {valor}.", d=nombre_derivada(y, k), valor=texto(derivada)))
        for cond in condiciones:
            expr = derivadas[cond.orden]
            valor = sympy.expand(sympy.simplify(expr.subs(x, cond.punto)))
            lineas.append(tr("{condicion}: {sustituida} = {valor}, es decir {ecuacion}.",
                             condicion=MotorEdo._condicion_texto(cond, y), sustituida=sustituir(expr, {x: cond.punto}),
                             valor=texto(cond.valor), ecuacion=f"{texto(valor)} = {texto(cond.valor)}"))
            ecuaciones.append((valor, cond.valor))
        valores = resolver_sistema(ecuaciones, constantes, lineas)
        particular = solucion.subs(valores)
        particular = _mas_corta(particular, sympy.expand(particular), sympy.simplify(particular))
        self.pasos.append(PasoCalculo(
            tr("Condiciones iniciales"),
            regla=tr("cada condición da una ecuación para las constantes: se deriva la solución general las veces que "
                     "haga falta, se sustituye el punto y se resuelve el sistema."),
            partes=tr("las condiciones son {condiciones}.", condiciones="; ".join(
                MotorEdo._condicion_texto(c, y) for c in condiciones)),
            calculo=tuple(lineas) + (tr("Con {valores}: {y} = {solucion}.", valores=", ".join(
                f"{c} = {texto(v)}" for c, v in sorted(valores.items(), key=lambda cv: cv[0].name)), y=y,
                solucion=texto(particular)),),
            queda=f"{y} = {texto(particular)}"))
        return particular


def suma_euler(a: List[Any], funciones: List[Any], x: Any) -> str:
    """'x^2*y'' - 3*x*y' + 4*y': los coeficientes a_k*x^k de Cauchy-Euler."""
    return suma_lineal([ak * x ** k for k, ak in enumerate(a)], funciones)


def suma_lineal(a: List[Any], funciones: List[Any]) -> str:
    """'y'' - 3*y' + 2*y', desde la derivada más alta."""
    texto_suma = ""
    for c, f in reversed(list(zip(a, funciones))):
        if c == 0:
            continue
        if not texto_suma:
            texto_suma = producto(c, f) if c != -1 else f"-{f}"
        else:
            texto_suma += _mas(c, f)
    return texto_suma or "0"


# ---------------------------------------------------------
# Transformada de Laplace (problemas de valor inicial)
# ---------------------------------------------------------

def _con_saltos(expr: Any) -> bool:
    return expr.has(sympy.Heaviside) or expr.has(sympy.DiracDelta)


class _Laplace:
    """a_n*y^(n) + ... + a_0*y = g(t), con y(0), y'(0)...: se transforma, se despeja Y(s) y se invierte."""

    def __init__(self, motor: "MotorEdo", edo: Edo, pasos: List[PasoCalculo], avisos: List[str]):
        self.motor, self.edo, self.pasos, self.avisos = motor, edo, pasos, avisos
        self.t, self.y = edo.x, edo.y
        self.s = sympy.Symbol("s")
        self.Y = sympy.Symbol("Y")

    def resolver(self) -> Optional[Tuple[List[Any], str]]:
        datos = _OrdenSuperior(self.motor, self.edo, [], []).coeficientes()
        if datos is None:
            return None
        a, g = datos
        n, t, s, y, Y = len(a) - 1, self.t, self.s, self.y, self.Y
        valores = {c.orden: c.valor for c in self.edo.condiciones if c.punto == 0}
        if any(k not in valores for k in range(n)):
            nota = tr("NOTA: la transformada de Laplace necesita las condiciones en 0: {lista}.",
                      lista=", ".join(f"{nombre_derivada(y, k)}(0)" for k in range(n)))
            self.avisos.append(nota)
            self.motor._notas_metodo.append(nota)
            return None
        funciones = [y] + list(self.edo.derivadas)

        # 1. Transformar el lado izquierdo
        lineas, transformadas = [], []
        for k in range(n + 1):
            if k == 0:
                transformadas.append(Y)
                continue
            simbolica = " - ".join([f"{texto(s ** k)}*Y"] + [
                f"{texto(s ** (k - 1 - j)) + '*' if k - 1 - j else ''}{nombre_derivada(y, j)}(0)" for j in range(k)])
            iniciales_k = sympy.expand(sum(s ** (k - 1 - j) * valores[j] for j in range(k)))
            valor = s ** k * Y - iniciales_k
            con_valores = f"{texto(s ** k)}*Y{_mas(-iniciales_k, 1)}"
            lineas.append(f"L{{{nombre_derivada(y, k)}}} = {simbolica} = {con_valores}.")
            transformadas.append(valor)
        lineas.insert(0, tr("L{{{y}}} = Y (la transformada de la incógnita).", y=y))
        self.pasos.append(PasoCalculo(
            tr("Transformada de Laplace"),
            regla=tr("la transformada convierte las derivadas en productos por s: L{{{yp}}} = s*Y - {y}(0), "
                     "L{{{ypp}}} = s^2*Y - s*{y}(0) - {yp}(0), y así sucesivamente. Las condiciones iniciales entran "
                     "en la cuenta, y la ecuación diferencial pasa a ser una ecuación algebraica en Y.", y=y,
                     yp=funciones[1], ypp=nombre_derivada(y, 2)),
            partes=tr("las condiciones son {condiciones}.", condiciones="; ".join(
                f"{nombre_derivada(y, k)}(0) = {texto(valores[k])}" for k in range(n))),
            calculo=tuple(lineas),
            queda=tr("cada derivada transformada")))

        # 2. Transformar g
        G = sympy.S.Zero
        lineas = []
        for termino in sympy.Add.make_args(sympy.expand(g)) if g != 0 else ():
            Tg = sympy.simplify(sympy.laplace_transform(termino, t, s, noconds=True))
            if Tg.has(sympy.LaplaceTransform):
                return None
            lineas.append(f"L{{{texto(termino)}}} = {texto(Tg)}: {self._regla(termino)}.")
            G += Tg
        if g != 0:
            self.pasos.append(PasoCalculo(
                tr("Transformada de g({t})", t=t),
                regla=tr("la transformada de una suma es la suma de las transformadas; cada término sale de la "
                         "tabla: L{exp(a*t)} = 1/(s - a), L{t^n} = n!/s^(n+1), L{sin(b*t)} = b/(s^2 + b^2), "
                         "L{cos(b*t)} = s/(s^2 + b^2), L{u(t - c)} = exp(-c*s)/s (u es el escalón, Heaviside), "
                         "L{delta(t - c)} = exp(-c*s) (la delta, DiracDelta)."),
                partes=tr("g({t}) = {g}.", t=t, g=texto(g)),
                calculo=tuple(lineas),
                queda=f"G(s) = {texto(G)}"))

        # 3. La ecuación en Y y su despeje
        izquierda = sympy.expand(sum(c * T for c, T in zip(a, transformadas)))
        p = izquierda.coeff(Y)
        iniciales = sympy.expand(izquierda - p * Y)
        p_factor = sympy.factor(p)
        # Y por partes, con y sin exp(-c*s): se separa desde G (al juntarlo todo, SymPy pasa exp(-c*s) al
        # denominador y ya no se reconoce la traslación)
        partes: Dict[Any, Any] = {sympy.S.One: -iniciales / p}
        for termino in sympy.Add.make_args(G):
            exponencial = sympy.Mul(*[f for f in sympy.Mul.make_args(termino) if isinstance(f, sympy.exp)])
            partes[exponencial] = partes.get(exponencial, 0) + termino / exponencial / p
        partes = {e: sympy.factor(r) for e, r in partes.items() if r != 0}
        Y_texto = " + ".join(texto(e * r) for e, r in partes.items()).replace("+ -", "- ") or "0"
        lineas = [tr("Sustituimos en la ecuación: {ecuacion}.",
                     ecuacion=f"{factor(p_factor)}*Y{_mas(iniciales, 1)} = {texto(G)}")]
        if iniciales != 0:
            lineas.append(tr("Pasamos a la derecha lo que no tiene Y: {ecuacion}.",
                             ecuacion=f"{factor(p_factor)}*Y = {texto(G - iniciales)}"))
        lineas.append(tr("Dividimos entre {p}: Y = {valor}.", p=texto(p_factor), valor=Y_texto))
        self.pasos.append(PasoCalculo(
            tr("Despejar Y(s)"),
            regla=tr("la ecuación transformada es de primer grado en Y: se agrupan los términos con Y y se divide."),
            calculo=tuple(lineas),
            queda=f"Y = {Y_texto}"))
        solucion = sympy.S.Zero
        for exponencial, racional in partes.items():
            racional = sympy.together(racional)
            if not racional.is_rational_function(s):
                return None
            f_t = self._inversa(racional)
            if f_t is None:
                return None
            if exponencial == 1:
                solucion += f_t
                continue
            c = -exponencial.args[0].coeff(s)
            trasladada = sympy.Heaviside(t - c) * f_t.subs(t, t - c)
            self.pasos.append(PasoCalculo(
                tr("Traslación por {e}", e=texto(exponencial)),
                regla=tr("segundo teorema de traslación: si L^-1{F(s)} = f(t), L^-1{exp(-c*s)*F(s)} = "
                         "u(t - c)*f(t - c): la misma función, retrasada c y encendida en t = c (u es el escalón, "
                         "Heaviside)."),
                partes=tr("c = {c} y f({t}) = {f}.", c=texto(c), t=t, f=texto(f_t)),
                queda=texto(trasladada)))
            solucion += trasladada
        solucion = _mas_corta(solucion, sympy.expand(solucion))
        self.pasos.append(PasoCalculo(
            tr("Solución"),
            regla=tr("{y}({t}) es la transformada inversa de Y(s): la suma de las inversas de cada parte.", y=y, t=t),
            queda=f"{y} = {texto(solucion)}"))
        if _con_saltos(solucion) or _con_saltos(g):
            self._por_tramos(a, g, solucion)
        return [sympy.Eq(y, solucion)], tr("transformada de Laplace")

    def _regla(self, termino: Any) -> str:
        t = self.t
        if termino.has(sympy.DiracDelta):
            return tr("la delta en t = c da exp(-c*s)")
        if termino.has(sympy.Heaviside):
            return tr("el escalón u(t - c) da exp(-c*s)/s; si multiplica a f(t - c), exp(-c*s)*F(s)")
        if termino.has(sympy.exp) and (termino.has(sympy.sin) or termino.has(sympy.cos) or termino.has(t ** 2)
                                       or termino / sympy.exp(t) != termino and termino.has(t)):
            return tr("primer teorema de traslación: exp(a*t)*f(t) da F(s - a)")
        if termino.has(sympy.exp):
            return "L{exp(a*t)} = 1/(s - a)"
        if termino.has(sympy.sin):
            return "L{sin(b*t)} = b/(s^2 + b^2)"
        if termino.has(sympy.cos):
            return "L{cos(b*t)} = s/(s^2 + b^2)"
        return "L{t^n} = n!/s^(n+1)"

    def _inversa(self, R: Any) -> Optional[Any]:
        """L^-1 de una función racional de s: fracciones simples (con sus pasos) y la tabla, término a término."""
        s, t = self.s, self.t
        simples = sympy.apart(R, s)
        if simples != R and len(sympy.Add.make_args(simples)) > 1:
            explicador = ExplicadorFracciones(s)
            try:
                explicador.explicar(R)
                for paso in explicador.pasos:
                    if paso.titulo == tr("Descomposición en fracciones simples"):
                        break
                    self.pasos.append(paso)
            except Exception:
                pass
            self.pasos.append(PasoCalculo(
                tr("Fracciones simples"),
                regla=tr("para invertir, Y(s) se escribe como suma de fracciones simples, cada una de la tabla."),
                calculo=(f"{texto(R)} = {texto(simples)}.",),
                queda=texto(simples)))
        lineas, total = [], sympy.S.Zero
        for termino in sympy.Add.make_args(simples):
            f_t = sympy.inverse_laplace_transform(termino, s, t).subs(sympy.Heaviside(t), 1)
            if f_t.has(sympy.InverseLaplaceTransform):
                return None
            f_t = _mas_corta(f_t, sympy.simplify(f_t))
            lineas.append(f"L^-1{{{texto(termino)}}} = {texto(f_t)}: {self._regla_inversa(termino)}.")
            total += f_t
        self.pasos.append(PasoCalculo(
            tr("Transformada inversa"),
            regla=tr("cada fracción simple es la transformada de una función de la tabla: 1/(s - a) viene de "
                     "exp(a*t); 1/(s - a)^k, de t^(k-1)*exp(a*t)/(k-1)!; (s - a)/((s - a)^2 + b^2), de "
                     "exp(a*t)*cos(b*t); b/((s - a)^2 + b^2), de exp(a*t)*sin(b*t)."),
            partes=tr("la función es {F}.", F=texto(simples)),
            calculo=tuple(lineas),
            queda=texto(total)))
        return total

    def _regla_inversa(self, termino: Any) -> str:
        s = self.s
        _, den = sympy.fraction(sympy.together(termino))
        lc, factores = sympy.factor_list(den, s)
        if len(factores) == 1 and sympy.degree(factores[0][0], s) == 1:
            raiz = sympy.solve(factores[0][0], s)[0]
            k = factores[0][1]
            if k == 1:
                return tr("1/(s - a) viene de exp(a*t), con a = {a}", a=texto(raiz))
            return tr("1/(s - a)^k viene de t^(k-1)*exp(a*t)/(k-1)!, con a = {a} y k = {k}", a=texto(raiz), k=k)
        if len(factores) == 1 and sympy.degree(factores[0][0], s) == 2:
            q = sympy.Poly(factores[0][0], s).monic().all_coeffs()
            a_ = -q[1] / 2
            b2 = q[2] - a_ ** 2
            b = sympy.sqrt(b2)
            if a_ == 0:
                return tr("{d} = s^2 + {b}^2: s/(s^2 + b^2) viene de cos(b*t) y b/(s^2 + b^2) de sin(b*t), con b = {b}",
                          d=texto(factores[0][0]), b=texto(b))
            # (A*s + B)/((s - a)^2 + b^2): A*(s - a) + (B + A*a), coseno y seno por exp(a*t)
            numerador = sympy.expand(termino * factores[0][0] ** factores[0][1])
            A, B = numerador.coeff(s), numerador.subs(s, 0)
            resto = sympy.simplify(B + A * a_)
            t = self.t
            funcion = A * sympy.exp(a_ * t) * sympy.cos(b * t) + resto / b * sympy.exp(a_ * t) * sympy.sin(b * t)
            return tr("completando el cuadrado, {d} = ({sa})^2 + {b}^2; el numerador, {num} = {A}*({sa}) + {resto}; "
                      "(s - a)/((s - a)^2 + b^2) viene de exp(a*t)*cos(b*t) y b/((s - a)^2 + b^2) de exp(a*t)*sin(b*t), "
                      "con a = {a} y b = {b}: queda {f}", d=texto(factores[0][0]), sa=texto(s - a_), b=texto(b),
                      num=texto(numerador), A=texto(A), resto=texto(resto), a=texto(a_), f=texto(funcion))
        return tr("por la tabla")

    def _por_tramos(self, a: List[Any], g: Any, solucion: Any) -> None:
        """Con escalones o deltas, la solución se comprueba en cada tramo entre los saltos."""
        t, y = self.t, self.y
        cortes = sorted({sympy.solve(f.args[0], t)[0] for f in (g + solucion).atoms(sympy.Heaviside, sympy.DiracDelta)})
        puntos = [cortes[0] - 1] + [(c1 + c2) / 2 for c1, c2 in zip(cortes, cortes[1:])] + [cortes[-1] + 1]
        lineas = []
        for i, punto in enumerate(puntos):
            def en_tramo(e):
                return e.replace(lambda f: isinstance(f, sympy.Heaviside),
                                 lambda f: sympy.S.One if f.args[0].subs(t, punto) > 0 else sympy.S.Zero) \
                    .replace(lambda f: isinstance(f, sympy.DiracDelta), lambda f: sympy.S.Zero)
            tramo_y, tramo_g = sympy.simplify(en_tramo(solucion)), sympy.simplify(en_tramo(g))
            derivadas = [tramo_y]
            for _ in range(len(a) - 1):
                derivadas.append(sympy.diff(derivadas[-1], t))
            resto = sympy.simplify(sum(c * d for c, d in zip(a, derivadas)) - tramo_g)
            if resto != 0:
                raise SinExplicacion()
            if i == 0:
                tramo = f"{t} < {texto(cortes[0])}"
            elif i == len(puntos) - 1:
                tramo = f"{t} > {texto(cortes[-1])}"
            else:
                tramo = f"{texto(cortes[i - 1])} < {t} < {texto(cortes[i])}"
            lineas.append(tr("Para {tramo}: {y} = {valor} y g = {g}; al sustituir, los dos lados valen lo mismo.",
                             tramo=tramo, y=y, valor=texto(tramo_y), g=texto(tramo_g)))
        self.motor._por_tramos.add(sympy.Eq(y, solucion))
        self.pasos.append(PasoCalculo(
            tr("Comprobación por tramos"),
            regla=tr("con escalones o deltas, la ecuación se comprueba en cada tramo entre los saltos, donde todo es "
                     "derivable: el escalón vale 0 antes del salto y 1 después, y la delta vale 0 fuera del punto."),
            partes=tr("los saltos están en {t} = {cortes}.", t=t, cortes=", ".join(texto(c) for c in cortes)),
            calculo=tuple(lineas),
            queda=tr("la solución es correcta")))


# ---------------------------------------------------------
# Sistemas lineales X' = A*X con coeficientes constantes
# ---------------------------------------------------------

class _Raices(_OrdenSuperior):
    """Solo las raíces de un polinomio en r, con los pasos de la ecuación característica."""

    def __init__(self, motor: "MotorEdo", pasos: List[PasoCalculo]):
        self.motor, self.pasos = motor, pasos
        self.r = sympy.Symbol("r")


def _vector(v: Any) -> str:
    return "(" + ", ".join(texto(e) for e in v) + ")"


def _entero(v: Any) -> Any:
    """El vector con los números más sencillos: sin fracciones."""
    partes = [p for e in v for p in (sympy.re(e), sympy.im(e)) if p != 0]
    denominadores = [sympy.fraction(sympy.nsimplify(p))[1] for p in partes]
    factor_comun = sympy.ilcm(1, 1, *[int(d) for d in denominadores if d.is_Integer])
    return sympy.Matrix([sympy.expand(e * factor_comun) for e in v])


class _Sistema:
    def __init__(self, motor: "MotorEdo", t: Any, funciones: List[Any], A: Any, pasos: List[PasoCalculo]):
        self.motor, self.t, self.funciones, self.A, self.pasos = motor, t, funciones, A, pasos

    def resolver(self) -> List[Any]:
        A, t, n = self.A, self.t, len(self.funciones)
        r = sympy.Symbol("r")
        filas = "; ".join("[" + ", ".join(texto(e) for e in A.row(i)) + "]" for i in range(n))
        X = _vector(self.funciones)
        self.pasos.append(PasoCalculo(
            tr("Planteamiento"),
            regla=tr("un sistema lineal con coeficientes constantes se escribe X' = A*X, con X el vector de las "
                     "funciones y A la matriz de los coeficientes. Las soluciones son de la forma exp(r*{t})*v, con r "
                     "un valor propio de A y v un vector propio: A*v = r*v.", t=t),
            partes=tr("X = {X}; A = [{filas}] (una fila por ecuación).", X=X, filas=filas),
            queda=tr("X' = A*X")))

        M = A - r * sympy.eye(n)
        p = sympy.expand(M.det())
        if n == 2:
            cuenta = (f"{factor(M[0, 0])}*{factor(M[1, 1])} - {factor(M[0, 1])}*{factor(M[1, 0])}")
            lineas = [tr("A - r*I = [{filas}].", filas="; ".join(
                "[" + ", ".join(texto(e) for e in M.row(i)) + "]" for i in range(n))),
                      tr("det(A - r*I) = {cuenta} = {p}.", cuenta=cuenta, p=texto(p))]
        else:
            lineas = [tr("A - r*I = [{filas}].", filas="; ".join(
                "[" + ", ".join(texto(e) for e in M.row(i)) + "]" for i in range(n))),
                      tr("Desarrollando el determinante por la primera fila: det(A - r*I) = {p}.", p=texto(p))]
        self.pasos.append(PasoCalculo(
            tr("Ecuación característica del sistema"),
            regla=tr("A*v = r*v tiene un vector v distinto de 0 solo si det(A - r*I) = 0, con I la matriz "
                     "identidad: es un polinomio en r, y sus raíces son los valores propios."),
            partes=tr("A = [{filas}].", filas=filas),
            calculo=tuple(lineas),
            queda=f"{texto(p)} = 0"))
        raices = _Raices(self.motor, self.pasos)._raices(p, tr("Valores propios"))

        constantes = constantes_de(n)
        vectores: List[Any] = []  # cada solución independiente, como vector de funciones de t
        lineas = []
        for raiz, beta, m in raices:
            valor = raiz + sympy.I * beta
            N = A - valor * sympy.eye(n)
            base = N.nullspace()
            if not base:
                raise SinExplicacion()
            v = _entero(base[0])
            filas_n = "; ".join("[" + ", ".join(texto(e) for e in N.row(i)) + "]" for i in range(n))
            lineas.append(tr("r = {r}: (A - r*I)*v = 0 con A - r*I = [{filas}]; un vector que lo cumple es v = {v}.",
                             r=_compleja(raiz, beta) if beta else texto(raiz), filas=filas_n, v=_vector(v)))
            fila = next((N.row(i) for i in range(n) if any(e != 0 for e in N.row(i))), None)
            if n == 2 and fila is not None and not beta:
                ecuacion = " + ".join(f"{factor(c)}*v{j + 1}" for j, c in enumerate(fila) if c != 0) \
                    .replace("+ -", "- ")
                lineas.append(tr("De la primera fila: {ecuacion} = 0; con v = {v} se cumple: {cuenta} = 0.",
                                 ecuacion=ecuacion, v=_vector(v), cuenta=" + ".join(
                                     f"{factor(c)}*{factor(e)}" for c, e in zip(fila, v) if c != 0)))
            if beta:
                a_, b_ = v.applyfunc(sympy.re), v.applyfunc(sympy.im)
                c, s_ = sympy.cos(beta * t), sympy.sin(beta * t)
                e = sympy.exp(raiz * t) if raiz != 0 else 1
                v1 = (a_ * c - b_ * s_) * e
                v2 = (a_ * s_ + b_ * c) * e
                lineas.append(tr("Es complejo: v = {a} + {b}*i. La parte real y la imaginaria de exp(r*{t})*v son "
                                 "dos soluciones reales: {v1} y {v2}.", a=_vector(a_), b=_vector(b_), t=t,
                                 v1=_vector(v1.applyfunc(sympy.expand)), v2=_vector(v2.applyfunc(sympy.expand))))
                vectores += [v1, v2]
                continue
            e = sympy.exp(raiz * t)
            if len(base) >= m:
                for k in range(m):
                    vk = _entero(base[k])
                    if k:
                        lineas.append(tr("Otro vector independiente para r = {r}: {v}.", r=texto(raiz), v=_vector(vk)))
                    vectores.append(vk * e)
                continue
            if m == 2 and len(base) == 1:
                # Valor propio doble con un solo vector: el vector generalizado w, con (A - r*I)*w = v
                w_sim = sympy.Matrix(sympy.symbols(f"w1:{n + 1}"))
                ecuaciones = (N * w_sim - v)
                sol = sympy.solve(list(ecuaciones), list(w_sim), dict=True)
                if not sol:
                    raise SinExplicacion()
                w = w_sim.subs(sol[0]).subs({s_: 0 for s_ in w_sim})
                lineas.append(tr("r = {r} es doble pero solo tiene un vector propio: se busca w con (A - r*I)*w = v; "
                                 "w = {w}. Las soluciones son exp(r*{t})*v y exp(r*{t})*({t}*v + w).", r=texto(raiz),
                                 w=_vector(w), t=t))
                vectores += [v * e, (t * v + w) * e]
                continue
            raise SinExplicacion()
        self.pasos.append(PasoCalculo(
            tr("Vectores propios"),
            regla=tr("para cada valor propio r se resuelve (A - r*I)*v = 0: las filas son proporcionales, y basta "
                     "una para elegir v. Un valor propio complejo a ± b*i da dos soluciones reales (la parte real y "
                     "la imaginaria); uno doble con un solo vector, un vector generalizado w."),
            partes=tr("los valores propios son {raices}.", raices="; ".join(
                (_compleja(r_, b_) if b_ else texto(r_)) + (f" ({_veces(m)})" if m > 1 else "") for r_, b_, m in raices)),
            calculo=tuple(lineas),
            queda=tr("{n} soluciones independientes", n=len(vectores))))
        if len(vectores) != n:
            raise SinExplicacion()
        X_sol = sum((c * v for c, v in zip(constantes, vectores)), sympy.zeros(n, 1))
        X_sol = X_sol.applyfunc(lambda e: sympy.collect(sympy.expand(e), constantes))
        self.pasos.append(PasoCalculo(
            tr("Solución general"),
            regla=tr("la solución general es la combinación de las soluciones independientes: X = C1*X1 + C2*X2 + ..."),
            calculo=(tr("X = {suma}.", suma=" + ".join(f"{c}*{_vector(v.applyfunc(sympy.factor))}"
                                                       for c, v in zip(constantes, vectores))),)
                    + tuple(f"{f} = {texto(e)}" for f, e in zip(self.funciones, X_sol)),
            queda="; ".join(f"{f} = {texto(e)}" for f, e in zip(self.funciones, X_sol))))
        return list(X_sol)

    def condiciones(self, X_sol: List[Any], valores: Dict[Any, Any]) -> List[Any]:
        t = self.t
        constantes = sorted({s for e in X_sol for s in e.free_symbols if es_constante(s)}, key=lambda s: s.name)
        lineas, ecuaciones = [], []
        for f, e in zip(self.funciones, X_sol):
            if f in valores:
                valor = sympy.expand(sympy.simplify(e.subs(t, 0)))
                lineas.append(tr("{condicion}: {sustituida} = {valor}, es decir {ecuacion}.",
                                 condicion=f"{f}(0) = {texto(valores[f])}", sustituida=sustituir(e, {t: 0}),
                                 valor=texto(valores[f]), ecuacion=f"{texto(valor)} = {texto(valores[f])}"))
                ecuaciones.append((valor, valores[f]))
        solucion = resolver_sistema(ecuaciones, constantes, lineas)
        particular = [sympy.expand(e.subs(solucion)) for e in X_sol]
        self.pasos.append(PasoCalculo(
            tr("Condiciones iniciales"),
            regla=tr("cada condición da una ecuación para las constantes: se sustituye {t} = 0 en cada función y se "
                     "resuelve el sistema.", t=t),
            calculo=tuple(lineas),
            queda="; ".join(f"{f} = {texto(e)}" for f, e in zip(self.funciones, particular))))
        return particular

    def comprobar(self, X_sol: List[Any]) -> bool:
        t, A = self.t, self.A
        lineas = []
        cambios = dict(zip(self.funciones, X_sol))
        for i, (f, e) in enumerate(zip(self.funciones, X_sol)):
            derivada = _mas_corta(sympy.diff(e, t), sympy.simplify(sympy.diff(e, t)))
            lado = sum(A[i, j] * g for j, g in enumerate(self.funciones))
            valor = sympy.expand(lado.xreplace(cambios))
            if sympy.simplify(derivada - valor) != 0:
                return False
            lineas.append(tr("{f}' = {d}; {lado} = {valor}: valen lo mismo.", f=f, d=texto(derivada), lado=texto(lado),
                             valor=texto(valor)))
        self.pasos.append(PasoCalculo(
            tr("Comprobación"),
            regla=tr("se deriva cada función y se compara con el lado derecho de su ecuación."),
            calculo=tuple(lineas),
            queda=tr("la solución es correcta")))
        return True
