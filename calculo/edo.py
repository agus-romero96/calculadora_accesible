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
        return [t for t in terminos if not t.has(C)] + [t for t in terminos if t.has(C)]

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
    compuesto = (expr.is_Add or (expr.is_Number and expr < 0)
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
            self.lineas.append(tr("Quitamos el valor absoluto: {dentro} = {derecha} o {dentro} = -({derecha}).",
                                  dentro=texto(dentro), derecha=texto(der)))
            if self.constantes and der.has(C):
                self.lineas.append(tr("Como C es cualquier constante, ±C también lo es: basta {ecuacion}.",
                                      ecuacion=self._igualdad(dentro, der)))
                return [(dentro, der)]
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
        if not (self.constantes and der.has(C)):
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
        # d2y/dx2 y dy/dx -> y'' e y'
        def derivada_leibniz(m):
            nonlocal independiente
            independiente = m.group(3)
            return f"{m.group(2)}" + "'" * int(m.group(1) or 1)
        ecuacion = re.sub(r"d\s*\^?\s*(\d)?\s*([a-z])\s*/\s*d\s*([a-z])\s*(?:\^?\s*\d)?", derivada_leibniz, ecuacion)
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
        for c in condiciones_txt:
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
                   diferencial=bool(diferencial))

    # --- Fachada ---

    def resolver(self, entrada: str) -> ResultadoEdo:
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
            pasos, soluciones, avisos = [], None, []
        except Exception:
            pasos, soluciones = [], None
            avisos = [tr("AVISO: no se pudo explicar paso a paso; el resultado es el que calcula SymPy.")]
        if soluciones is None:
            metodo = ""
            try:
                soluciones = self._con_sympy(ode, edo, Y, avisos)
            except Exception as e:
                return ResultadoEdo(tr("Error del Sistema: {error}", error=str(e)), es_error=True)
            if soluciones is None:
                return ResultadoEdo(tr("Error de Validación: {error}", error=tr(
                    "no se encontró una solución en forma cerrada para esta ecuación.")), es_error=True)

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
            s = s.xreplace({edo.y: Y})
            try:
                ok, _ = sympy.checkodesol(ode, s, solve_for_func=False)
            except Exception:
                ok = False
            if not ok:
                return False
        return True

    def _con_sympy(self, ode: Any, edo: Edo, Y: Any, avisos: List[str]) -> Optional[List[Any]]:
        """La solución de dsolve, sin pasos (con las condiciones, si las hay)."""
        ics = {}
        for cond in edo.condiciones:
            izq = Y.diff(edo.x, cond.orden).subs(edo.x, cond.punto) if cond.orden else Y.subs(edo.x, cond.punto)
            ics[izq] = cond.valor
        resultado = sympy.dsolve(ode, Y, ics=ics or None)
        resultado = resultado if isinstance(resultado, list) else [resultado]
        constantes = sorted({s for r in resultado for s in r.free_symbols if re.fullmatch(r"C\d+", s.name)},
                            key=lambda s: s.name)
        cambio = {Y: edo.y}
        if len(constantes) == 1:
            cambio[constantes[0]] = C
        soluciones = [sympy.Eq(r.lhs.xreplace(cambio), r.rhs.xreplace(cambio)) for r in resultado]
        avisos.append(tr("NOTA: por ahora hay explicación paso a paso para las ecuaciones de primer orden "
                         "separables, lineales, de Bernoulli, homogéneas, exactas (o con factor integrante) y reducibles a "
                         "separables, "
                         "y' = F(a*x + b*y + c). Esta "
                         "ecuación la "
                         "resuelve SymPy, sin pasos."))
        return soluciones

    # --- Textos ---

    @staticmethod
    def _solucion_texto(s: Any) -> str:
        return f"{texto(s.lhs)} = {texto(s.rhs)}"

    @staticmethod
    def _condicion_texto(cond: Condicion, y: Any) -> str:
        return f"{nombre_derivada(y, cond.orden)}({texto(cond.punto)}) = {texto(cond.valor)}"

    # --- La explicación ---

    def _explicar(self, edo: Edo, pasos: List[PasoCalculo], avisos: List[str]) -> Tuple[List[Any], str]:
        x, y = edo.x, edo.y
        # Soluciones que valen con una condición (y = v^2 con v = sqrt(y) >= 0): el método las comprueba
        # por su cuenta y la comprobación dice dónde valen
        self._condiciones: Dict[Any, str] = {}
        pasos.append(PasoCalculo(
            tr("Planteamiento"),
            regla=tr("una ecuación diferencial relaciona una función {y}({x}) con sus derivadas. Resolverla es hallar "
                     "todas las funciones que la cumplen: la solución general, con tantas constantes como el orden. "
                     "El orden es el de la derivada más alta.", x=x, y=y),
            partes=tr("la ecuación es {ecuacion}; la incógnita es la función {y}({x}); la derivada más alta es {d}, "
                      "así que es de orden {orden}.", ecuacion=edo.enunciado,
                      x=x, y=y, d=edo.derivadas[-1], orden=edo.orden),
            queda=tr("ecuación de orden {orden}", orden=edo.orden)))
        if edo.orden != 1:
            raise SinExplicacion()
        yp = edo.derivadas[0]
        despeje: List[PasoCalculo] = []
        f = self._despejar_derivada(edo, yp, despeje)

        # El primer método que reconoce la ecuación (cada uno devuelve None si no es de su tipo, antes
        # de añadir pasos). Las lineales parten de la ecuación escrita, sin despejar y'.
        exacta = (lambda *a: self._exacta(*a, edo=edo), tr("ecuación exacta"), False)
        metodos = ((self._separable, tr("ecuación separable"), True),
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
        lineas = [f"∫ {factor(izq_int)} d{y} = {texto(primitiva_y)}.",
                  f"∫ {factor(g)} d{x} = {texto(primitiva_x)}."]
        lineas += self._lineas_abs(primitiva_y, primitiva_x)
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
            explicitas = [self._simplificada(s, despeje.lineas) for s in explicitas]
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
        return primitiva

    @staticmethod
    def _lineas_abs(*primitivas: Any) -> Tuple[str, ...]:
        """Por qué log(y) pasa a log(Abs(y)): una línea para todos los logaritmos que cambian."""
        cambios = []
        for primitiva in primitivas:
            for log in sorted(primitiva.atoms(sympy.log), key=texto):
                if _con_abs(log) != log:
                    cambios.append(tr("{antes} se escribe {despues}", antes=texto(log), despues=texto(_con_abs(log))))
        if not cambios:
            return ()
        return (tr("La primitiva de 1/u es log(Abs(u)): con el valor absoluto vale también donde u es negativo. "
                   "Así, {cambios}.", cambios="; ".join(cambios)),)

    @staticmethod
    def _simplificada(s: Any, lineas: List[str]) -> Any:
        simple = sympy.simplify(s)
        if len(texto(simple)) < len(texto(s)) and texto(simple) != texto(s):
            lineas.append(tr("Simplificamos: {antes} = {despues}.", antes=texto(s), despues=texto(simple)))
            s = simple
        if s.has(C):
            # -C*exp(x)/(1 - C*exp(x)): con -C en lugar de C (otra constante cualquiera) quedan menos signos
            opuesta = sympy.simplify(s.subs(C, -C))
            signos = lambda e: texto(e).count("-") + texto(e).count("(-")
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
                if s.lhs == y and sympy.simplify(s.rhs - y0) == 0:
                    lineas.append(tr("La solución constante {y} = {r} cumple {y}({x0}) = {y0}.", y=y, r=texto(s.rhs),
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
