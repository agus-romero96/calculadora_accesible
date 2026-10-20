"""
Paso a paso de Evaluar, Simplificar y Factorizar, con el formato de calculo/pasos.py
(Regla, En este caso, las cuentas, Queda). En los tres, el resultado que se muestra es el de
SymPy, y los pasos solo se muestran si llegan a él.

  - ExplicadorEvaluar: la cuenta tal como se escribió (módulo ast, que conserva el orden y los
    paréntesis; el parser de SymPy reordena los términos), operación a operación según la
    jerarquía: paréntesis y funciones, potencias, multiplicaciones y divisiones, sumas y restas.
  - ExplicadorSimplificar: desarrollar, agrupar términos semejantes, denominador común,
    factorizar y cancelar, e identidades.
  - ExplicadorFactorizar: factor común, productos notables, trinomios, cubos, agrupación y
    Ruffini; cada factor se intenta factorizar de nuevo y al final se comprueba multiplicando.
"""
from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from functools import reduce
from typing import Any, List, Optional, Tuple

import sympy

from calculo.pasos import PasoCalculo, agrupa_semejantes, entre_parentesis, suma_texto, texto
from i18n import N_, tr


class SinExplicacion(Exception):
    """La expresión no se puede explicar paso a paso (se da el resultado de SymPy)."""


# =============================================================
# EVALUAR
# =============================================================

FUNCIONES = {
    "sqrt": sympy.sqrt, "abs": sympy.Abs, "exp": sympy.exp, "log": sympy.log, "ln": sympy.log,
    "log10": lambda v: sympy.log(v, 10), "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "cot": sympy.cot, "sec": sympy.sec, "csc": sympy.csc, "asin": sympy.asin, "acos": sympy.acos,
    "atan": sympy.atan, "sinh": sympy.sinh, "cosh": sympy.cosh, "tanh": sympy.tanh,
}
CONSTANTES = {"pi": sympy.pi, "e": sympy.E}
PRECEDENCIA = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}
MAX_OPERACIONES = 25


@dataclass
class Valor:
    valor: Any
    escrito: Optional[str] = None  # cómo se escribió ("0.5", "1/3", "pi")


@dataclass
class Op:
    op: str
    izq: Any
    der: Any


@dataclass
class Neg:
    arg: Any


@dataclass
class Fun:
    nombre: str
    arg: Any


def _a_nodo(n: ast.AST) -> Any:
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        if isinstance(n.value, int):
            return Valor(sympy.Integer(n.value))
        return Valor(sympy.Float(repr(n.value)), repr(n.value))
    if isinstance(n, ast.Name) and n.id in CONSTANTES:
        return Valor(CONSTANTES[n.id], n.id)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.UAdd):
        return _a_nodo(n.operand)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        dentro = _a_nodo(n.operand)
        if isinstance(dentro, Valor) and dentro.valor.is_number:
            return Valor(-dentro.valor, f"-{dentro.escrito}" if dentro.escrito else None)
        return Neg(dentro)
    if isinstance(n, ast.BinOp):
        ops = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "^"}
        op = ops.get(type(n.op))
        if op is None:
            raise SinExplicacion()
        izq, der = _a_nodo(n.left), _a_nodo(n.right)
        # 1/3 o 7/2 (enteros sin factor común) es un número, una fracción, no una división pendiente
        if (op == "/" and isinstance(izq, Valor) and isinstance(der, Valor) and izq.valor.is_Integer
                and der.valor.is_Integer and der.valor > 1 and sympy.igcd(izq.valor, der.valor) == 1):
            return Valor(sympy.Rational(izq.valor, der.valor))
        return Op(op, izq, der)
    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCIONES
            and len(n.args) == 1 and not n.keywords):
        return Fun(n.func.id, _a_nodo(n.args[0]))
    raise SinExplicacion()


def leer_cuenta(entrada: str) -> Any:
    """El árbol de la cuenta tal como se escribió (SinExplicacion si no es una cuenta numérica)."""
    t = entrada.strip().lower().replace("^", "**").replace("√", "sqrt").replace("π", "pi").replace("×", "*")
    try:
        # Los tokens distinguen el número 10 del nombre log10 y conservan 1e-3.
        tokens = []
        anterior = None
        for token in tokenize.generate_tokens(io.StringIO(t).readline):
            if anterior is not None and (
                (anterior.type == tokenize.NUMBER and (token.type == tokenize.NAME or token.string == "("))
                or (anterior.string == ")" and (token.type in (tokenize.NUMBER, tokenize.NAME) or token.string == "("))
            ):
                tokens.append((tokenize.OP, "*"))
            tokens.append((token.type, token.string))
            anterior = token
        t = tokenize.untokenize(tokens)
        return _a_nodo(ast.parse(t, mode="eval").body)
    except (SyntaxError, ValueError, RecursionError, tokenize.TokenError) as e:
        raise SinExplicacion() from e


def _prec_valor(v: Valor) -> float:
    """Precedencia de cómo se escribe un valor: para saber si necesita paréntesis."""
    x = v.valor
    if v.escrito and not v.escrito.startswith("-"):
        return 4
    if x.could_extract_minus_sign():
        return 1.5
    if x.is_Rational and not x.is_Integer:
        return 2
    if x.is_Add:
        return 1
    if x.is_Mul:
        return 2
    if x.is_Pow and texto(x).startswith(("sqrt", "1/")) is False:
        return 3
    return 4


def _prec(n: Any) -> float:
    if isinstance(n, Valor):
        return _prec_valor(n)
    if isinstance(n, Op):
        return PRECEDENCIA[n.op]
    if isinstance(n, Neg):
        return 1.5
    return 4  # función


def escribir(n: Any, padre: float = 0, derecha: bool = False, op_padre: str = "") -> str:
    """La cuenta con los paréntesis justos: 2 + 3*4, (2 + 3)*4, 2 - (-3)."""
    p = _prec(n)
    if isinstance(n, Valor):
        s = n.escrito or texto(n.valor)
    elif isinstance(n, Op):
        izq = escribir(n.izq, p, False, n.op)
        der = escribir(n.der, p, True, n.op)
        s = f"{izq} {n.op} {der}" if n.op in "+-" else f"{izq}{n.op}{der}"
    elif isinstance(n, Neg):
        s = f"-{escribir(n.arg, 2.5)}"
    else:
        s = f"{n.nombre}({escribir(n.arg)})"
    fraccion = isinstance(n, Valor) and n.valor.is_Rational and not n.valor.is_Integer and not n.escrito
    necesita = ((fraccion and padre >= 2) or p < padre
                or (p == padre and derecha and op_padre in "-/^")
                or (p == padre and not derecha and op_padre == "^")
                or (p == 1.5 and padre >= 1 and (derecha or padre > 1.5)))
    return f"({s})" if necesita and padre else s


def _operaciones(n: Any) -> int:
    if isinstance(n, Op):
        return 1 + _operaciones(n.izq) + _operaciones(n.der)
    if isinstance(n, Fun):
        return 1 + _operaciones(n.arg)
    if isinstance(n, Neg):
        return _operaciones(n.arg)
    return 0


def _candidatos(n: Any, padre: float = 0, profundidad: int = 0, salida: Optional[list] = None, ruta=()) -> list:
    """(prioridad, orden, ruta) de cada operación que ya se puede hacer (sus datos son números)."""
    if salida is None:
        salida = []
    p = _prec(n)
    # Entre paréntesis (precedencia menor que la del padre) o dentro de una función: va antes
    dentro = profundidad + (1 if (padre and p < padre) or padre == 5 else 0)
    if isinstance(n, Op):
        _candidatos(n.izq, p, dentro, salida, ruta + ("izq",))
        _candidatos(n.der, p, dentro, salida, ruta + ("der",))
        if isinstance(n.izq, Valor) and isinstance(n.der, Valor):
            salida.append(((dentro, p), len(salida), ruta))
    elif isinstance(n, Neg):
        _candidatos(n.arg, 2.5, dentro, salida, ruta + ("arg",))
        if isinstance(n.arg, Valor):
            salida.append(((dentro + 100, 5), len(salida), ruta))  # cambiar el signo: inmediato, sin paso
    elif isinstance(n, Fun):
        _candidatos(n.arg, 5, dentro, salida, ruta + ("arg",))
        if isinstance(n.arg, Valor):
            salida.append(((dentro, 4), len(salida), ruta))
    return salida


def _obtener(n: Any, ruta) -> Any:
    for paso in ruta:
        n = getattr(n, paso)
    return n


def _reemplazar(n: Any, ruta, nuevo: Any) -> Any:
    if not ruta:
        return nuevo
    if isinstance(n, Op):
        izq = _reemplazar(n.izq, ruta[1:], nuevo) if ruta[0] == "izq" else n.izq
        der = _reemplazar(n.der, ruta[1:], nuevo) if ruta[0] == "der" else n.der
        return Op(n.op, izq, der)
    if isinstance(n, Fun):
        return Fun(n.nombre, _reemplazar(n.arg, ruta[1:], nuevo))
    return Neg(_reemplazar(n.arg, ruta[1:], nuevo))


def _escrito(x: Any) -> Optional[str]:
    """Cómo se escribe un decimal: 0.75, no 0.750000000000000."""
    if isinstance(x, sympy.Float):
        return repr(float(x))
    return None


def _fraccion(x: Any) -> Tuple[Any, Any]:
    x = sympy.Rational(x)
    return sympy.Integer(x.p), sympy.Integer(x.q)


def _signo(a: Any, b: Any, resultado: Any, dividiendo: bool = False) -> Optional[str]:
    """La regla de los signos, si hay algún negativo: 'menos por más da menos'."""
    if not (a.is_negative or b.is_negative) or not (a.is_real and b.is_real):
        return None
    if a.is_zero or b.is_zero:
        return None  # 0 por (o entre) cualquier número da 0: el 0 no tiene signo

    nombre = {True: tr("menos"), False: tr("más")}
    if dividiendo:
        return tr("Signos: {a} entre {b} da {c}.", a=nombre[bool(a.is_negative)], b=nombre[bool(b.is_negative)],
                  c=nombre[bool(resultado.is_negative)])
    return tr("Signos: {a} por {b} da {c}.", a=nombre[bool(a.is_negative)], b=nombre[bool(b.is_negative)],
              c=nombre[bool(resultado.is_negative)])


def operar(nodo: Any) -> Tuple[Any, str, str, List[str]]:
    """(resultado, nombre de la operación, regla, cuentas) de una operación con datos numéricos."""
    if isinstance(nodo, Fun):
        return _operar_funcion(nodo)
    a, b = nodo.izq.valor, nodo.der.valor
    ta, tb = escribir(nodo.izq, PRECEDENCIA[nodo.op], False, nodo.op), escribir(nodo.der, PRECEDENCIA[nodo.op], True, nodo.op)
    racionales = a.is_Rational and b.is_Rational
    if nodo.op in "+-":
        resultado = a + b if nodo.op == "+" else a - b
        nombre = N_("Suma") if nodo.op == "+" else N_("Resta")
        if racionales and (not a.is_Integer or not b.is_Integer):
            (pa, qa), (pb, qb) = _fraccion(a), _fraccion(b)
            m = sympy.ilcm(qa, qb)
            na, nb = pa * (m // qa), pb * (m // qb)
            cuentas = [tr("Denominador común: el mínimo común múltiplo de {qa} y {qb} es {m}.", qa=qa, qb=qb, m=m)]
            for p, q, n in ((pa, qa, na), (pb, qb, nb)):
                if q != m:
                    original = f"{p}/{q}" if q != 1 else str(p)
                    cuentas.append(tr("{original} = {nuevo} (multiplicamos arriba y abajo por {k}).", original=original,
                                      nuevo=f"{n}/{m}", k=m // q))
            suma = na + nb if nodo.op == "+" else na - nb
            cuentas.append(tr("Operamos los numeradores: {a} {op} {b} = {s}, así que queda {s}/{m}.", a=na, op=nodo.op,
                              b=f"({nb})" if nb < 0 else nb, s=suma, m=m))
            g = sympy.igcd(suma, m)
            if g > 1:
                cuentas.append(tr("Simplificamos dividiendo arriba y abajo entre {g}: {s}/{m} = {r}.", g=g, s=suma, m=m,
                                  r=texto(resultado)))
            regla = tr("para sumar o restar fracciones se pasan a un denominador común (el mínimo común múltiplo de los "
                       "denominadores) y se suman o restan los numeradores; al final se simplifica.")
        elif racionales or (a.is_Float or b.is_Float):
            cuentas = [f"{ta} {nodo.op} {tb} = {_escrito(resultado) or texto(resultado)}."]
            regla = (tr("se suman los números; si tienen signos distintos, se restan y el resultado lleva el signo del "
                        "mayor (en valor absoluto).") if nodo.op == "+"
                     else tr("restar un número es sumar su opuesto: a - b = a + (-b)."))
        else:
            agrupado = sympy.expand(resultado)
            if len(sympy.Add.make_args(agrupado)) == 2 and agrupado.is_Add:
                regla = tr("solo se pueden juntar términos semejantes (los dos números, o los dos con pi, por ejemplo); "
                           "si no lo son, la suma se deja indicada.")
            else:
                regla = tr("los términos semejantes se juntan sumando sus coeficientes: 2*pi + 3*pi = (2 + 3)*pi = 5*pi.")
            resultado = agrupado
            cuentas = [f"{ta} {nodo.op} {tb} = {texto(resultado)}."]
        return resultado, nombre, regla, cuentas

    if nodo.op == "*":
        resultado = a * b
        cuentas = []
        if racionales and (not a.is_Integer or not b.is_Integer):
            (pa, qa), (pb, qb) = _fraccion(a), _fraccion(b)
            cuentas.append(tr("{a}*{b} = ({pa}*{pb})/({qa}*{qb}) = {n}/{d}.", a=ta, b=tb, pa=pa, pb=entre_parentesis(pb),
                              qa=qa, qb=qb, n=pa * pb, d=qa * qb))
            if sympy.igcd(pa * pb, qa * qb) > 1:
                cuentas.append(tr("Simplificamos dividiendo arriba y abajo entre {g}: {r}.", g=sympy.igcd(pa * pb, qa * qb),
                                  r=texto(resultado)))
            regla = tr("para multiplicar fracciones se multiplican los numeradores entre sí y los denominadores entre sí, "
                       "y se simplifica.")
        else:
            cuentas.append(f"{ta}*{tb} = {_escrito(resultado) or texto(resultado)}.")
            regla = tr("se multiplican los números; el signo es + si los dos tienen el mismo signo y - si son distintos.")
        signo = _signo(a, b, resultado) if a.is_number and b.is_number else None
        if signo:
            cuentas.append(signo)
        return resultado, N_("Multiplicación"), regla, cuentas

    if nodo.op == "/":
        if b == 0:
            raise ValueError(tr("No se puede dividir entre 0."))
        resultado = a / b
        if a.is_Integer and b.is_Integer:
            if resultado.is_Integer:
                cuentas = [f"{ta}/{tb} = {texto(resultado)}."]
            else:
                g = sympy.igcd(a, b)
                cuentas = [tr("{a}/{b} no es exacta: el resultado es la fracción {a}/{b}.", a=ta, b=tb)]
                if g > 1:
                    cuentas.append(tr("Simplificamos dividiendo arriba y abajo entre {g} (el máximo común divisor): "
                                      "{a}/{b} = {r}.", g=g, a=ta, b=tb, r=texto(resultado)))
            regla = tr("se divide; si la división no es exacta, el resultado es una fracción, que se simplifica dividiendo "
                       "numerador y denominador entre su máximo común divisor.")
        elif racionales:
            pb, qb = _fraccion(b)
            inversa = sympy.Rational(qb, pb)
            cuentas = [tr("{a}/{b} = {a}*{inversa} = {r}.", a=ta, b=tb, inversa=entre_parentesis(inversa), r=texto(resultado))]
            regla = tr("dividir entre una fracción es multiplicar por su inversa (se le da la vuelta): a/(c/d) = a*(d/c).")
        else:
            resultado = sympy.simplify(resultado)
            cuentas = [f"{ta}/{tb} = {texto(resultado)}."]
            regla = tr("se divide; si no es un número exacto, el cociente se deja indicado y se simplifica.")
        signo = _signo(a, b, resultado, dividiendo=True) if a.is_number and b.is_number else None
        if signo:
            cuentas.append(signo)
        return resultado, N_("División"), regla, cuentas

    # Potencia
    if a == 0 and b.is_negative:
        raise ValueError(tr("No se puede dividir entre 0."))
    resultado = sympy.simplify(a ** b)
    if resultado.is_real is False:
        raise SinExplicacion()  # las reglas del explicador solo describen operaciones reales
    if b.is_Integer and b == 0:
        regla = tr("cualquier número distinto de 0 elevado a 0 vale 1.")
        cuentas = [f"{ta}^{tb} = 1."]
    elif b.is_Integer and b == 1:
        regla = tr("cualquier número elevado a 1 es él mismo: a^1 = a.")
        cuentas = [f"{ta}^1 = {texto(resultado)}."]
    elif b.is_Integer and 2 <= b <= 6 and a.is_number:
        regla = tr("una potencia con exponente natural n es la base multiplicada por sí misma n veces.")
        cuentas = [f"{ta}^{tb} = {'*'.join([entre_parentesis(a)] * int(b))} = {texto(resultado)}."]
    elif b.is_Integer and b > 6:
        regla = tr("una potencia con exponente natural n es la base multiplicada por sí misma n veces.")
        cuentas = [f"{ta}^{tb} = {texto(resultado)}."]
    elif b.is_Integer and b < 0:
        regla = tr("un exponente negativo es el inverso de la potencia positiva: a^(-n) = 1/a^n.")
        inv = entre_parentesis(a) if b == -1 else f"{entre_parentesis(a)}^{-b}"
        cuentas = [f"{ta}^{tb} = 1/{inv} = {texto(resultado)}."]
    elif b.is_Rational and not b.is_Integer:
        regla = tr("un exponente fraccionario p/q es una raíz: a^(p/q) es la raíz q-ésima de a, elevada a p "
                   "(a^(1/2) es la raíz cuadrada).")
        cuentas = [f"{ta}^{tb} = {texto(resultado)}."]
    else:
        regla = tr("si el exponente es irracional, la potencia se deja indicada y al final se aproxima con decimales.")
        cuentas = [f"{ta}^{tb} = {texto(resultado)}."]
    return resultado, N_("Potencia"), regla, cuentas


def _operar_funcion(nodo: Fun) -> Tuple[Any, str, str, List[str]]:
    v = nodo.arg.valor
    resultado = sympy.simplify(FUNCIONES[nodo.nombre](v))
    escrito = f"{nodo.nombre}({escribir(nodo.arg)})"
    if resultado.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo):
        raise ValueError(tr("La función {funcion} no está definida en {valor}.",
                            funcion=nodo.nombre, valor=escribir(nodo.arg)))
    if resultado.is_real is False:
        raise SinExplicacion()  # el resultado final lo valida Aritmetica.evaluar
    if nodo.nombre == "sqrt":
        regla = tr("la raíz cuadrada de a es el número positivo cuyo cuadrado es a. Si a = c^2*k, entonces "
                   "sqrt(a) = c*sqrt(k).")
        if resultado.is_Rational:
            r_cuadrado = texto(resultado) if resultado.is_Integer else f"({texto(resultado)})"
            cuentas = [tr("{f} = {r}, porque {rc}^2 = {v}.", f=escrito, r=texto(resultado),
                          rc=r_cuadrado, v=texto(v)) if resultado >= 0 else f"{escrito} = {texto(resultado)}."]
        else:
            c, resto = resultado.as_coeff_Mul()
            if c != 1 and resto.is_Pow:
                cuentas = [tr("{v} = {c}^2*{k}, así que {f} = {r}.", v=texto(v), c=entre_parentesis(c),
                              k=texto(resto.base), f=escrito, r=texto(resultado))]
            else:
                cuentas = [tr("{f} no es exacta: se deja indicada.", f=escrito)]
        return resultado, N_("Raíz cuadrada"), regla, cuentas
    if nodo.nombre == "abs":
        regla = tr("el valor absoluto es la distancia a 0: el número sin su signo.")
        return resultado, N_("Valor absoluto"), regla, [f"{escrito} = {texto(resultado)}."]
    sin_valor = (resultado.has(sympy.log) if nodo.nombre == "log10"
                 else resultado.has(FUNCIONES[nodo.nombre](sympy.Symbol("z")).func))
    if sin_valor:
        regla = tr("algunas funciones solo tienen valor exacto sencillo en puntos concretos (sin(pi/2) = 1, log(1) = 0...); "
                   "en los demás, el valor se deja indicado y al final se aproxima con decimales.")
        cuentas = [tr("{f} no tiene un valor exacto sencillo: se deja indicado.", f=escrito)]
    else:
        regla = tr("algunas funciones tienen valores exactos conocidos en puntos concretos: sin(pi/2) = 1, cos(0) = 1, "
                   "log(1) = 0, log(e) = 1, exp(0) = 1...")
        cuentas = [tr("{f} = {r} (valor exacto conocido).", f=escrito, r=texto(resultado))]
    return resultado, N_("Función"), regla, cuentas


class ExplicadorEvaluar:
    def explicar(self, entrada: str, exacto: Any) -> List[PasoCalculo]:
        """Pasos de la cuenta hasta exacto (el valor de SymPy); SinExplicacion si no llega a él."""
        arbol = leer_cuenta(entrada)
        total = _operaciones(arbol)
        if total > MAX_OPERACIONES:
            raise SinExplicacion()
        pasos: List[PasoCalculo] = []
        if total >= 2:
            pasos.append(PasoCalculo(
                tr("Jerarquía de las operaciones"),
                regla=tr("se calcula en este orden: 1) lo que hay entre paréntesis o dentro de una función (sqrt, sin...); "
                         "2) potencias y raíces; 3) multiplicaciones y divisiones, de izquierda a derecha; 4) sumas y "
                         "restas, de izquierda a derecha."),
                partes=tr("la cuenta es {cuenta}, con {n} operaciones.", cuenta=escribir(arbol), n=total),
                queda=escribir(arbol)))
        while not isinstance(arbol, Valor):
            candidatos = _candidatos(arbol)
            if not candidatos:
                raise SinExplicacion()
            mejor = max(candidatos, key=lambda c: (c[0], -c[1]))
            (dentro, prec), _, ruta = mejor
            nodo = _obtener(arbol, ruta)
            if isinstance(nodo, Neg):
                arbol = _reemplazar(arbol, ruta, Valor(-nodo.arg.valor))
                continue
            resultado, nombre, regla, cuentas = operar(nodo)
            if texto(resultado) == escribir(nodo):
                # 2*pi: ya es un valor, no hay nada que operar
                arbol = _reemplazar(arbol, ruta, Valor(resultado))
                continue
            mismos = [c for c in candidatos if c[0] == mejor[0]]
            if dentro > 0:
                motivo = tr("está entre paréntesis o dentro de una función: va primero.")
            elif prec >= 3:
                motivo = tr("las potencias van antes que las multiplicaciones, divisiones, sumas y restas.")
            elif prec == 2:
                motivo = tr("las multiplicaciones y divisiones van antes que las sumas y restas.")
            else:
                motivo = tr("solo quedan sumas y restas.")
            if len(mismos) > 1:
                motivo += " " + tr("Entre las del mismo nivel, se empieza por la de la izquierda.")
            arbol = _reemplazar(arbol, ruta, Valor(resultado, _escrito(resultado)))
            pasos.append(PasoCalculo(
                tr("{operacion}: {cuenta}", operacion=tr(nombre), cuenta=escribir(nodo)),
                regla=regla,
                partes=tr("es la operación que toca: {motivo}", motivo=motivo),
                calculo=tuple(cuentas),
                queda=escribir(arbol)))
        if sympy.simplify(arbol.valor - exacto) != 0:
            raise SinExplicacion()
        if not pasos and total == 0:
            pasos.append(PasoCalculo(
                tr("Sin operaciones"),
                regla=tr("un número solo no tiene operaciones pendientes: su valor es él mismo."),
                partes=tr("la expresión es {cuenta}.", cuenta=escribir(arbol)),
                queda=texto(exacto)))
        return pasos


def paso_decimal(exacto: Any, decimal: Any) -> PasoCalculo:
    return PasoCalculo(
        tr("Aproximación decimal"),
        regla=tr("pi, e, las raíces no exactas y la mayoría de logaritmos y senos tienen infinitas cifras decimales sin "
                 "repetición: se da el valor exacto y una aproximación."),
        partes=tr("el valor exacto es {exacto}.", exacto=texto(exacto)),
        calculo=(tr("{exacto} ≈ {decimal}.", exacto=texto(exacto), decimal=decimal),),
        queda=f"≈ {decimal}")


# =============================================================
# SIMPLIFICAR
# =============================================================

def _terminos(expr: Any) -> List[Any]:
    return [t for t in sympy.Add.make_args(expr) if t != 0]


def limpiar(e: Any) -> Any:
    """
    El árbol sin evaluar del parser, con los productos de números ya hechos (-1*3 = -3) y lo
    demás sin tocar: 2*(x - 3) se sigue viendo con su paréntesis (evaluado sería 2*x - 6).
    """
    if not e.args:
        return e
    if (e.is_Mul or e.is_Add) and all(a.is_number for a in e.args):
        return e.func(*e.args)
    if e.is_Add or e.is_Mul or e.is_Pow:
        return e.func(*[limpiar(a) for a in e.args], evaluate=False)
    try:  # exp(log(x)) se queda así: evaluado sería ya x
        return e.func(*[limpiar(a) for a in e.args], evaluate=False)
    except TypeError:
        return e.func(*[limpiar(a) for a in e.args])


def _por_grado(terminos: List[Any]) -> List[Any]:
    """De mayor a menor grado, y los números al final: x^2 + 2*x + 1."""
    def grado(t):
        try:
            return -sympy.Poly(t).total_degree() if t.free_symbols else 1
        except Exception:
            return 0
    return sorted(terminos, key=grado)


def _desarrollo(termino: Any) -> Tuple[Any, str]:
    """(expandido, regla que lo justifica) de un término con paréntesis."""
    if termino.is_Pow and termino.base.is_Add and termino.exp == 2 and len(termino.base.args) == 2:
        a, b = termino.base.args
        if b.could_extract_minus_sign() and not a.could_extract_minus_sign():
            return sympy.expand(termino), tr("cuadrado de una resta: (a - b)^2 = a^2 - 2*a*b + b^2")
        return sympy.expand(termino), tr("cuadrado de una suma: (a + b)^2 = a^2 + 2*a*b + b^2")
    if termino.is_Pow and termino.base.is_Add and termino.exp == 3 and len(termino.base.args) == 2:
        return sympy.expand(termino), tr("cubo de un binomio: (a + b)^3 = a^3 + 3*a^2*b + 3*a*b^2 + b^3")
    factores = sympy.Mul.make_args(termino)
    sumas = [f for f in factores if f.is_Add]
    if len(sumas) == 2 and len(factores) == 2 and all(len(s.args) == 2 for s in sumas) and len(_terminos(sympy.expand(termino))) == 2:
        return sympy.expand(termino), tr("suma por diferencia: (a + b)*(a - b) = a^2 - b^2")
    return sympy.expand(termino), tr("propiedad distributiva: cada término de un paréntesis multiplica a cada término del otro")


def _agrupar(terminos: List[Any]) -> List[str]:
    """'3*x + 2*x = (3 + 2)*x = 5*x' por cada grupo de términos semejantes."""
    grupos = {}
    for t in terminos:
        coef, parte = t.as_coeff_Mul()
        grupos.setdefault(parte, []).append(coef)
    lineas = []
    for parte, coefs in grupos.items():
        if len(coefs) < 2:
            continue
        suma_coef = sum(coefs)
        escritos = suma_texto([c * parte for c in coefs])
        if parte == 1:
            lineas.append(tr("Números: {suma} = {total}.", suma=escritos, total=texto(suma_coef)))
        else:
            lineas.append(tr("{suma} = ({coeficientes})*{parte} = {total}.", suma=escritos,
                             coeficientes=suma_texto(coefs), parte=entre_parentesis(parte), total=texto(suma_coef * parte)))
    return lineas


class ExplicadorSimplificar:
    def explicar(self, crudo: Any, expr: Any, resultado: Any) -> List[PasoCalculo]:
        """Pasos de simplificar crudo (tal como lo leyó el parser) hasta resultado (el de SymPy)."""
        variables = sorted(crudo.free_symbols | expr.free_symbols, key=lambda s: s.name)
        num, den = sympy.fraction(sympy.together(expr))
        num_c, den_c = sympy.fraction(limpiar(crudo))
        es_fraccion = (
            any(den.has(v) for v in variables)
            or any(den_c.has(v) for v in variables)
            or (den_c != 1 and bool(variables) and sympy.gcd(sympy.expand(num_c.doit()), sympy.expand(den_c.doit())) != 1)
        )
        pasos: List[PasoCalculo] = []
        if es_fraccion:
            actual = self._racional(crudo, expr, num, den, pasos)
        else:
            actual = self._polinomio(crudo, expr, pasos)

        if not pasos and texto(limpiar(crudo)) != texto(actual):
            # SymPy ya lo cambió al leerlo (exp(log(x)) es x): es una identidad
            actual = limpiar(crudo)
        if texto(actual) != texto(resultado):
            if sympy.simplify(sympy.sympify(actual).doit() - resultado) != 0:
                raise SinExplicacion()
            pasos.append(PasoCalculo(
                tr("Forma más compacta"),
                regla=tr("se reescribe con factor común o con identidades (trigonométricas como sin(x)^2 + cos(x)^2 = 1, "
                         "de logaritmos o de potencias), sin cambiar el valor."),
                partes=tr("la expresión es {expresion}.", expresion=texto(actual)),
                calculo=(f"{texto(actual)} = {texto(resultado)}.",),
                queda=texto(resultado)))
        if not pasos:
            pasos.append(PasoCalculo(
                tr("Ya está simplificada"),
                regla=tr("una expresión está simplificada cuando no tiene paréntesis que desarrollar, términos semejantes "
                         "que agrupar ni factores que cancelar."),
                partes=tr("{expresion} ya cumple las tres condiciones.", expresion=texto(resultado)),
                queda=texto(resultado)))
        return pasos

    def _polinomio(self, crudo: Any, expr: Any, pasos: List[PasoCalculo]) -> Any:
        desarrollados, lineas, reglas, identidades = [], [], [], []
        for t in (limpiar(t) for t in sympy.Add.make_args(crudo)):
            tiene_parentesis = (t.is_Mul and any(a.is_Add or (a.is_Pow and a.base.is_Add) for a in t.args)) or (
                t.is_Pow and t.base.is_Add
            )
            # doit() puede distribuir antes de reconocer los paréntesis originales.
            expandido, regla = _desarrollo(t if tiene_parentesis else t.doit())
            if texto(expandido) != texto(t) and tiene_parentesis:
                lineas.append(f"{texto(t)} = {suma_texto(_por_grado(_terminos(expandido)))}.")
                if regla not in reglas:
                    reglas.append(regla)
            elif texto(expandido) != texto(t):
                identidades.append(f"{texto(t)} = {texto(expandido)}.")
            desarrollados.extend(_por_grado(_terminos(expandido)))
        if identidades:
            pasos.append(PasoCalculo(
                tr("Aplicar identidades"),
                regla=tr("hay funciones que se deshacen entre sí o valores conocidos: log(exp(u)) = u, exp(log(u)) = u, "
                         "sqrt(u^2) = |u|, sin(0) = 0..."),
                partes=tr("en {expresion} hay términos que se pueden reescribir.", expresion=texto(limpiar(crudo))),
                calculo=tuple(identidades),
                queda=suma_texto(desarrollados)))
        if lineas:
            pasos.append(PasoCalculo(
                tr("Desarrollar"),
                regla="; ".join(reglas) + ".",
                partes=tr("hay paréntesis que desarrollar en {expresion}.", expresion=texto(limpiar(crudo))),
                calculo=tuple(lineas),
                queda=suma_texto(desarrollados)))
        agrupar = _agrupar(desarrollados)
        actual = sympy.expand(expr) if (expr.is_polynomial() or lineas) else expr
        if agrupar:
            pasos.append(PasoCalculo(
                tr("Agrupar términos semejantes"),
                regla=tr("los términos semejantes (misma parte con letras: mismas variables con los mismos exponentes) se "
                         "juntan sumando sus coeficientes: a*x + b*x = (a + b)*x. Los números se suman entre sí."),
                partes=tr("los términos son {terminos}.", terminos="; ".join(texto(t) for t in desarrollados)),
                calculo=tuple(agrupar),
                queda=texto(actual)))
        return actual

    def _racional(self, crudo: Any, expr: Any, num: Any, den: Any, pasos: List[PasoCalculo]) -> Any:
        sumandos = [t.doit() for t in sympy.Add.make_args(crudo)]
        if len(sumandos) == 1:
            num_c, den_c = sympy.fraction(limpiar(crudo))
            if den_c != 1:
                num, den = num_c.doit(), den_c.doit()
        den = sympy.factor(den)
        if len(sumandos) > 1:
            # El mínimo común múltiplo de los denominadores (together los multiplicaría todos)
            den = sympy.factor(reduce(sympy.lcm, [sympy.fraction(sympy.together(s))[1] for s in sumandos]))
            num = sympy.expand(sum(sympy.fraction(sympy.together(s))[0] * sympy.cancel(den / sympy.fraction(sympy.together(s))[1])
                                   for s in sumandos))
        junta = sympy.expand(num) / den
        if len(sumandos) > 1:
            calculo = [tr("Denominador común: {d}.", d=texto(den))]
            numeradores = []
            for s in sumandos:
                n_s, d_s = sympy.fraction(sympy.together(s))
                falta = sympy.factor(sympy.cancel(den / d_s))
                nuevo = sympy.expand(n_s * falta)
                numeradores.append(nuevo)
                if falta != 1:
                    calculo.append(tr("{fraccion} = {nuevo}/{den}: multiplicamos arriba y abajo por {falta}.",
                                      fraccion=texto(s), nuevo=entre_parentesis(nuevo), den=entre_parentesis(den),
                                      falta=entre_parentesis(falta)))
            calculo.append(tr("Sumamos los numeradores: {suma} = {total}.",
                              suma=suma_texto([n for n in numeradores if n != 0]), total=texto(sympy.expand(num))))
            calculo += agrupa_semejantes(numeradores)
            pasos.append(PasoCalculo(
                tr("Denominador común"),
                regla=tr("para sumar o restar fracciones algebraicas se usa un denominador común (el mínimo común múltiplo "
                         "de los denominadores): cada fracción se multiplica arriba y abajo por lo que le falta a su "
                         "denominador, y se suman los numeradores."),
                partes=tr("los denominadores son {denominadores}.",
                          denominadores="; ".join(texto(sympy.fraction(sympy.together(s))[1]) for s in sumandos)),
                calculo=tuple(calculo),
                queda=f"{entre_parentesis(sympy.expand(num))}/{entre_parentesis(den)}"))
        num = sympy.expand(num)
        den_exp = sympy.expand(den)
        num_f, den_f = sympy.factor(num), den
        comun = sympy.gcd(num, den_exp)
        cancelada = sympy.factor(sympy.cancel(junta)) if (num != 0 and comun != 1) else junta
        if num != 0 and comun != 1:
            ceros = sympy.solve(comun, list(comun.free_symbols)[0]) if len(comun.free_symbols) == 1 else []
            calculo = []
            if texto(num_f) != texto(num):
                calculo.append(tr("Factorizamos el numerador: {antes} = {despues}.", antes=texto(num), despues=texto(num_f)))
            if len(sumandos) == 1 and texto(den_f) != texto(den_exp):
                calculo.append(tr("Factorizamos el denominador: {antes} = {despues}.", antes=texto(den_exp), despues=texto(den_f)))
            calculo.append(tr("El factor común es {factor}; lo cancelamos: {resultado}.", factor=texto(comun),
                              resultado=texto(cancelada)))
            if ceros:
                calculo.append(tr("Vale para {variable} distinto de {valores}: ahí la expresión original no está definida "
                                  "(dividiría entre 0).", variable=list(comun.free_symbols)[0],
                                  valores=", ".join(texto(c) for c in ceros)))
            pasos.append(PasoCalculo(
                tr("Factorizar y cancelar"),
                regla=tr("un factor que multiplica arriba y abajo se puede cancelar (a*c)/(b*c) = a/b, siempre que no "
                         "valga 0. Para verlo, se factorizan el numerador y el denominador."),
                partes=tr("el numerador es {num} y el denominador es {den}.", num=texto(num),
                          den=texto(den_exp if len(sumandos) == 1 else den)),
                calculo=tuple(calculo),
                queda=texto(cancelada)))
        return cancelada


# =============================================================
# FACTORIZAR
# =============================================================

# Nombres de los casos (también son la estrategia del resultado)
FACTOR_COMUN = N_("Factor común")
DIFERENCIA_CUADRADOS = N_("Diferencia de cuadrados")
TCP = N_("Trinomio cuadrado perfecto")
TRINOMIO_1 = N_("Trinomio x^2 + bx + c")
TRINOMIO_A = N_("Trinomio ax^2 + bx + c")
CUBOS = N_("Suma/diferencia de cubos")
AGRUPACION = N_("Factorización por agrupación")
RUFFINI = N_("Regla de Ruffini")
GENERAL = N_("Factorización general")
IRREDUCIBLE = N_("Irreducible")


def _raiz_exacta(t: Any, n: int) -> Optional[Any]:
    """
    b tal que b^n = t para un monomio c*x^k*y^m... (c racional positivo y exponentes múltiplos de
    n), o None. Se calcula con los exponentes: sqrt(x^2) sería Abs(x) con variables reales.
    """
    try:
        coef, resto = sympy.sympify(t).as_coeff_Mul()
        if not coef.is_Rational or coef <= 0:
            return None
        raiz_coef = sympy.root(coef, n)
        if not raiz_coef.is_Rational:
            return None
        b = raiz_coef
        for base, exp in resto.as_powers_dict().items():
            if base == 1:
                continue
            if not base.is_Symbol or not exp.is_Integer or exp % n != 0:
                return None
            b *= base ** (exp // n)
        return b
    except Exception:
        return None


def _potencia_texto(base: Any, n: int) -> str:
    """(x^2)^2, 3^2, x^2: la base entre paréntesis si es algo más que un número o una letra."""
    simple = base.is_Symbol or (base.is_Integer and base >= 0)
    return f"{texto(base)}^{n}" if simple else f"({texto(base)})^{n}"


class ExplicadorFactorizar:
    def __init__(self):
        self.pasos: List[PasoCalculo] = []
        self.casos: List[str] = []
        self._sin_seguir = set()  # factores ya explicados como irreducibles

    def explicar(self, expr: Any) -> Any:
        """Explica la factorización de expr (añade los pasos) y devuelve el producto obtenido."""
        expandida = sympy.expand(expr)
        terminos = _por_grado(_terminos(expandida))
        if len(terminos) < 2:
            raise SinExplicacion()
        # 1) Factor común
        comun = reduce(sympy.gcd, terminos)
        coef = sympy.Mul(*[f for f in sympy.Mul.make_args(comun) if f.is_number])
        if coef.is_negative:
            comun = -comun
        if comun != 1:
            nucleo = sympy.expand(expandida / comun)
            self.casos.append(FACTOR_COMUN)
            self.pasos.append(PasoCalculo(
                tr("Sacar factor común"),
                regla=tr("si todos los términos tienen un factor en común (el máximo común divisor de los números y las "
                         "letras con su menor exponente), se saca fuera: a*b + a*c = a*(b + c)."),
                partes=tr("los términos {terminos} tienen en común {comun}.", terminos="; ".join(texto(t) for t in terminos),
                          comun=texto(comun)),
                calculo=tuple(tr("{termino} entre {comun} = {cociente}.", termino=texto(t), comun=entre_parentesis(comun),
                                 cociente=texto(sympy.simplify(t / comun))) for t in terminos)
                        + (tr("Queda {comun}*({nucleo}).", comun=entre_parentesis(comun), nucleo=texto(nucleo)),),
                queda=f"{entre_parentesis(comun)}*({texto(nucleo)})"))
            # SymPy distribuye automáticamente 2*(x + 1) si se evalúa este producto.
            factores = sympy.Mul.make_args(self._factorizar(nucleo, 0))
            return sympy.Mul(comun, *factores, evaluate=False)
        return self._factorizar(expandida, 0)

    def _factorizar(self, p: Any, nivel: int) -> Any:
        """Factores de p (sin factor común), o p si no se puede."""
        if nivel > 6:
            return p
        terminos = _por_grado(_terminos(p))
        variables = sorted(p.free_symbols, key=lambda s: s.name)
        if not variables or not p.is_polynomial():
            return p
        intento = None
        if len(terminos) == 2:
            intento = self._diferencia_cuadrados(p, terminos) or self._cubos(p, terminos)
        elif len(terminos) == 3 and len(variables) == 1 and sympy.degree(p, variables[0]) == 2:
            intento = self._cuadratico(p, variables[0])
            if intento is None:
                return p  # ya explicado: el discriminante no lo permite
        elif len(terminos) == 4:
            intento = self._agrupacion(p, terminos)
        if intento is None and len(variables) == 1 and sympy.degree(p, variables[0]) >= 3:
            intento = self._ruffini(p, variables[0])
        if intento is None and len(variables) == 1 and sympy.degree(p, variables[0]) == 2 and len(terminos) != 3:
            # x^2 - 2, x^2 + 1: el discriminante dice por qué no se descompone
            intento = self._cuadratico(p, variables[0])
            if intento is None:
                return p
        if intento is None:
            factorizada = sympy.factor(p)
            if factorizada == p or not factorizada.is_Mul and not factorizada.is_Pow:
                lineal = all(sympy.degree(p, v) <= 1 for v in variables)
                if nivel > 0 and not lineal and not (len(terminos) == 3 and len(variables) == 1):  # el trinomio ya lo explicó
                    self.pasos.append(PasoCalculo(
                        tr("{expresion} no se factoriza más", expresion=texto(p)),
                        regla=tr("un factor que no encaja en ningún caso y no tiene raíces racionales no se puede "
                                 "factorizar en los racionales (por ejemplo, una suma de cuadrados como x^2 + 1)."),
                        partes=tr("el factor es {expresion}.", expresion=texto(p)),
                        queda=texto(p)))
                return p
            self.casos.append(GENERAL)
            self.pasos.append(PasoCalculo(
                tr("Factorizar {expresion}", expresion=texto(p)),
                regla=tr("cuando no encaja en ningún caso conocido, SymPy busca los factores; se comprueba multiplicándolos."),
                partes=tr("la expresión es {expresion}.", expresion=texto(p)),
                calculo=(tr("{expresion} = {factores}.", expresion=texto(p), factores=texto(factorizada)),
                         tr("Comprobación: al multiplicar, {factores} = {expresion}.", factores=texto(factorizada),
                            expresion=texto(sympy.expand(factorizada)))),
                queda=texto(factorizada)))
            return factorizada
        # Cada factor obtenido se intenta factorizar de nuevo
        resultado = sympy.Integer(1)
        for factor in intento:
            base, exp = factor.as_base_exp()
            seguir = len(_terminos(sympy.expand(base))) > 1 and sympy.expand(base) not in self._sin_seguir
            sub = self._factorizar(sympy.expand(base), nivel + 1) if seguir else base
            resultado *= sub ** exp
        return resultado

    # --- Casos ---

    def _diferencia_cuadrados(self, p: Any, terminos: List[Any]) -> Optional[List[Any]]:
        positivo = [t for t in terminos if not t.could_extract_minus_sign()]
        negativo = [t for t in terminos if t.could_extract_minus_sign()]
        if len(positivo) != 1 or len(negativo) != 1:
            return None
        a, b = _raiz_exacta(positivo[0], 2), _raiz_exacta(-negativo[0], 2)
        if a is None or b is None:
            return None
        factores = [a - b, a + b]
        self.casos.append(DIFERENCIA_CUADRADOS)
        self.pasos.append(PasoCalculo(
            tr("Diferencia de cuadrados en {expresion}", expresion=texto(p)),
            regla=tr("una resta de dos cuadrados se factoriza como suma por diferencia: a^2 - b^2 = (a - b)*(a + b)."),
            partes=tr("{t1} = {a2} y {t2} = {b2}, así que a = {ta} y b = {tb}.", t1=texto(positivo[0]),
                      a2=_potencia_texto(a, 2), t2=texto(-negativo[0]), b2=_potencia_texto(b, 2), ta=texto(a), tb=texto(b)),
            calculo=(tr("Sustituimos: ({a} - {b})*({a} + {b}).", a=texto(a), b=texto(b)),),
            queda=f"({texto(a - b)})*({texto(a + b)})"))
        return factores

    def _cubos(self, p: Any, terminos: List[Any]) -> Optional[List[Any]]:
        primero, segundo = terminos if not terminos[0].could_extract_minus_sign() else terminos[::-1]
        resta = segundo.could_extract_minus_sign()
        a, b = _raiz_exacta(primero, 3), _raiz_exacta(-segundo if resta else segundo, 3)
        if a is None or b is None or not a.free_symbols:
            return None
        if resta:
            factores = [a - b, a ** 2 + a * b + b ** 2]
            regla = tr("una diferencia de cubos se factoriza así: a^3 - b^3 = (a - b)*(a^2 + a*b + b^2).")
        else:
            factores = [a + b, a ** 2 - a * b + b ** 2]
            regla = tr("una suma de cubos se factoriza así: a^3 + b^3 = (a + b)*(a^2 - a*b + b^2).")
        es_grado_2 = len(p.free_symbols) == 1 and sympy.degree(factores[1], list(p.free_symbols)[0]) == 2
        calculo = [tr("a^2 = {a2}, a*b = {ab} y b^2 = {b2}.", a2=texto(a ** 2), ab=texto(a * b), b2=texto(b ** 2)),
                   tr("Sustituimos: ({f1})*({f2}).", f1=texto(factores[0]), f2=texto(factores[1]))]
        if es_grado_2:
            calculo.append(tr("El segundo factor no se factoriza en los racionales: su discriminante, b^2 - 4*a*c, es negativo."))
            # El factor cuadrático no se descompone: solo se sigue con el lineal
            self._sin_seguir.add(sympy.expand(factores[1]))
        self.casos.append(CUBOS)
        self.pasos.append(PasoCalculo(
            tr("Suma o diferencia de cubos en {expresion}", expresion=texto(p)),
            regla=regla,
            partes=tr("{t1} = {a3} y {t2} = {b3}, así que a = {ta} y b = {tb}.", t1=texto(primero), a3=_potencia_texto(a, 3),
                      t2=texto(-segundo if resta else segundo), b3=_potencia_texto(b, 3), ta=texto(a), tb=texto(b)),
            calculo=tuple(calculo),
            queda=f"({texto(factores[0])})*({texto(factores[1])})"))
        return factores

    def _cuadratico(self, p: Any, x: Any) -> Optional[List[Any]]:
        poli = sympy.Poly(p, x)
        a, b, c = poli.all_coeffs()
        a, b, c = sympy.Integer(a) if a.is_Integer else a, b, c
        # Trinomio cuadrado perfecto
        ra, rc = _raiz_exacta(a * x ** 2, 2), _raiz_exacta(c, 2) if c > 0 else None
        if ra is not None and rc is not None and abs(b) == 2 * sympy.sqrt(a) * rc:
            signo = "+" if b > 0 else "-"
            base = ra + rc if b > 0 else ra - rc
            self.casos.append(TCP)
            self.pasos.append(PasoCalculo(
                tr("Trinomio cuadrado perfecto en {expresion}", expresion=texto(p)),
                regla=tr("a^2 + 2*a*b + b^2 = (a + b)^2 y a^2 - 2*a*b + b^2 = (a - b)^2: si los extremos son cuadrados y "
                         "el término central es el doble de sus raíces, es el cuadrado de un binomio."),
                partes=tr("{t1} = {a2} y {t3} = {b2}, así que a = {ta} y b = {tb}.", t1=texto(a * x ** 2),
                          a2=_potencia_texto(ra, 2), t3=texto(c), b2=_potencia_texto(rc, 2), ta=texto(ra), tb=texto(rc)),
                calculo=(tr("Comprobamos el término central: 2*a*b = 2*{a}*{b} = {doble}, que coincide con {central}.",
                            a=entre_parentesis(ra), b=entre_parentesis(rc), doble=texto(2 * ra * rc),
                            central=texto(abs(b) * x)),
                         tr("El signo del término central es {signo}: ({base})^2.", signo=signo, base=texto(base))),
                queda=f"({texto(base)})^2"))
            return [base ** 2]
        delta = b ** 2 - 4 * a * c
        if a == 1:
            par = self._dos_numeros(b, c)
            if par is not None:
                m, n = par
                self.casos.append(TRINOMIO_1)
                self.pasos.append(PasoCalculo(
                    tr("Trinomio {x}^2 + b*{x} + c en {expresion}", x=x, expresion=texto(p)),
                    regla=tr("{x}^2 + b*{x} + c = ({x} + m)*({x} + n) cuando m + n = b y m*n = c: se buscan dos números "
                             "que multiplicados den c y sumados den b.", x=x),
                    partes=tr("b = {b} y c = {c}.", b=texto(b), c=texto(c)),
                    calculo=(tr("Buscamos dos números que multiplicados den {c} y sumados den {b}: {m} y {n}.", c=texto(c),
                                b=texto(b), m=texto(m), n=texto(n)),
                             tr("Comprobación: {m}*{n} = {c} y {m} + {n} = {b}.", m=entre_parentesis(m),
                                n=entre_parentesis(n), c=texto(c), b=texto(b))),
                    queda=f"({texto(x + m)})*({texto(x + n)})"))
                return [x + m, x + n]
        # Fórmula general: raíces y a*(x - x1)*(x - x2)
        lineas = [tr("Discriminante: b^2 - 4*a*c = {b}^2 - 4*{a}*{c} = {delta}.", b=entre_parentesis(b), a=entre_parentesis(a),
                     c=entre_parentesis(c), delta=texto(delta))]
        if delta < 0 or not sympy.sqrt(delta).is_Rational:
            lineas.append(tr("El discriminante es negativo: no hay raíces reales, así que no se factoriza.") if delta < 0 else
                          tr("{delta} no es un cuadrado perfecto: las raíces son irracionales, así que no se factoriza en "
                             "los racionales.", delta=texto(delta)))
            self.pasos.append(PasoCalculo(
                tr("Polinomio de grado 2 sin factores: {expresion}", expresion=texto(p)),
                regla=tr("un polinomio de grado 2 se factoriza en los racionales solo si su discriminante, b^2 - 4*a*c, es "
                         "un cuadrado perfecto (0, 1, 4, 9...)."),
                partes=tr("a = {a}, b = {b} y c = {c}.", a=texto(a), b=texto(b), c=texto(c)),
                calculo=tuple(lineas),
                queda=texto(p)))
            return None
        s = sympy.sqrt(delta)
        x1, x2 = (-b + s) / (2 * a), (-b - s) / (2 * a)
        lineas += [tr("Raíz del discriminante: sqrt({delta}) = {s}.", delta=texto(delta), s=texto(s)),
                   tr("{x}1 = (-b + {s})/(2*a) = ({nb} + {s})/{dos_a} = {x1}.", x=x, s=texto(s), nb=texto(-b), dos_a=texto(2 * a),
                      x1=texto(x1)),
                   tr("{x}2 = (-b - {s})/(2*a) = ({nb} - {s})/{dos_a} = {x2}.", x=x, s=texto(s), nb=texto(-b), dos_a=texto(2 * a),
                      x2=texto(x2))]
        factores = [a, x - x1, x - x2]
        producto = sympy.factor(p)
        lineas.append(tr("Entonces {expresion} = {a}*({f1})*({f2}).", expresion=texto(p), a=entre_parentesis(a),
                         f1=texto(x - x1), f2=texto(x - x2)))
        if a != 1:
            # El coeficiente se reparte entre los factores con fracciones: 2*(x + 1/2) = 2*x + 1
            resto_a, cuentas = a, []
            for raiz in (x1, x2):
                q = sympy.Rational(raiz).q
                if q != 1 and resto_a % q == 0:
                    cuentas.append(f"{q}*({texto(x - raiz)}) = {texto(sympy.expand(q * (x - raiz)))}")
                    resto_a = resto_a / q
            if cuentas:
                lineas.append(tr("Repartimos el {a} entre los factores para quitar las fracciones: {cuentas}.",
                                 a=entre_parentesis(a), cuentas="; ".join(cuentas)))
        self.casos.append(TRINOMIO_A if a != 1 else TRINOMIO_1)
        self.pasos.append(PasoCalculo(
            tr("Trinomio a*{x}^2 + b*{x} + c en {expresion}", x=x, expresion=texto(p)),
            regla=tr("si x1 y x2 son las raíces de a*x^2 + b*x + c, que da la fórmula x = (-b ± sqrt(b^2 - 4*a*c))/(2*a), "
                     "entonces a*x^2 + b*x + c = a*(x - x1)*(x - x2)."),
            partes=tr("a = {a}, b = {b} y c = {c}.", a=texto(a), b=texto(b), c=texto(c)),
            calculo=tuple(lineas),
            queda=texto(producto)))
        return list(sympy.Mul.make_args(producto)) if a != 1 else factores[1:]

    @staticmethod
    def _dos_numeros(b: Any, c: Any) -> Optional[Tuple[Any, Any]]:
        if not (b.is_Integer and c.is_Integer) or c == 0:
            return None
        for m in sorted(sympy.divisors(abs(c)), key=abs):
            for mm in (m, -m):
                n = c // mm
                if mm * n == c and mm + n == b:
                    return (mm, n) if mm <= n else (n, mm)
        return None

    def _agrupacion(self, p: Any, terminos: List[Any]) -> Optional[List[Any]]:
        for grupo1, grupo2 in (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))):
            g1 = [terminos[i] for i in grupo1]
            g2 = [terminos[i] for i in grupo2]
            c1, c2 = reduce(sympy.gcd, g1), reduce(sympy.gcd, g2)
            r1, r2 = sympy.expand(sum(g1) / c1), sympy.expand(sum(g2) / c2)
            if r1 == -r2:
                c2, r2 = -c2, -r2
            if r1 != r2 or len(_terminos(r1)) < 2:
                continue
            self.casos.append(AGRUPACION)
            self.pasos.append(PasoCalculo(
                tr("Factor común por grupos en {expresion}", expresion=texto(p)),
                regla=tr("se agrupan los términos de dos en dos y se saca factor común en cada grupo; si queda el mismo "
                         "paréntesis, se saca también: a*x + a*y + b*x + b*y = a*(x + y) + b*(x + y) = (a + b)*(x + y)."),
                partes=tr("grupos: {g1} y {g2}.", g1=suma_texto(g1), g2=suma_texto(g2)),
                calculo=(tr("Primer grupo: {g} = {c}*({r}).", g=suma_texto(g1), c=entre_parentesis(c1), r=texto(r1)),
                         tr("Segundo grupo: {g} = {c}*({r}).", g=suma_texto(g2), c=entre_parentesis(c2), r=texto(r2)),
                         tr("Los dos tienen ({r}): sale como factor común: ({r})*({suma}).", r=texto(r1),
                            suma=texto(c1 + c2))),
                queda=f"({texto(r1)})*({texto(c1 + c2)})"))
            return [r1, c1 + c2]
        return None

    def _ruffini(self, p: Any, x: Any) -> Optional[List[Any]]:
        poli = sympy.Poly(p, x)
        coefs = poli.all_coeffs()
        if not all(c.is_Integer for c in coefs) or coefs[-1] == 0:
            return None
        principal, independiente = abs(coefs[0]), abs(coefs[-1])
        candidatos = sorted({sympy.Rational(s * d, q) for d in sympy.divisors(independiente)
                             for q in sympy.divisors(principal) for s in (1, -1)}, key=lambda r: (abs(r), bool(r < 0)))
        descartados = []
        for r in candidatos:
            if poli.eval(r) != 0:
                if len(descartados) < 6:
                    descartados.append(tr("P({r}) = {valor}, distinto de 0: {r} no es raíz.", r=texto(r),
                                          valor=texto(poli.eval(r))))
                continue
            # División por (x - r) con Ruffini
            bajados, fila = [coefs[0]], []
            for c in coefs[1:]:
                producto = bajados[-1] * r
                bajados.append(c + producto)
                fila.append(tr("{anterior}*{r} = {producto}; {c} + {p} = {suma}.", anterior=entre_parentesis(bajados[-2]),
                               r=entre_parentesis(r), producto=texto(producto), c=texto(c), p=entre_parentesis(producto),
                               suma=texto(bajados[-1])))
            cociente = sympy.Poly(bajados[:-1], x).as_expr()
            evaluacion = " + ".join(f"{entre_parentesis(c)}*{entre_parentesis(r)}^{len(coefs) - 1 - i}"
                                    for i, c in enumerate(coefs[:-1])) + f" + {entre_parentesis(coefs[-1])}"
            valores = [c * r ** (len(coefs) - 1 - i) for i, c in enumerate(coefs)]
            evaluacion += f" = {suma_texto([v for v in valores if v != 0])}"
            factor_lin = x - r
            extra = ()
            if r.q != 1 and all((b % r.q) == 0 for b in bajados[:-1]):
                factor_lin = sympy.expand(r.q * (x - r))
                cociente = sympy.expand(cociente / r.q)
                extra = (tr("Pasamos el factor {q} a ({f_frac}) para quitar las fracciones: ({f_lin})*({coc}).",
                            q=r.q, f_frac=texto(x - r), f_lin=texto(factor_lin), coc=texto(cociente)),)
            self.casos.append(RUFFINI)
            self.pasos.append(PasoCalculo(
                tr("Raíz y Ruffini en {expresion}", expresion=texto(p)),
                regla=tr("si P(r) = 0, entonces (x - r) es factor de P (teorema del factor). Las raíces racionales posibles "
                         "son los divisores del término independiente entre los del coeficiente principal. Al dividir "
                         "por (x - r) con la regla de Ruffini, se baja el primer coeficiente y, en cada columna, se "
                         "multiplica por r y se suma al siguiente."),
                partes=tr("coeficientes: {coeficientes}; probamos los divisores de {independiente}.",
                          coeficientes=", ".join(texto(c) for c in coefs), independiente=texto(coefs[-1])),
                calculo=tuple(descartados) + (tr("P({r}) = {cuenta} = 0, así que ({factor}) es un factor.", r=texto(r),
                                                 cuenta=evaluacion, factor=texto(x - r)),
                         tr("Ruffini con {r}: bajamos {primero}.", r=texto(r), primero=texto(coefs[0])))
                        + tuple(fila)
                        + (tr("El resto es {resto} y el cociente es {cociente}.", resto=texto(bajados[-1]),
                              cociente=texto(sympy.Poly(bajados[:-1], x).as_expr())),)
                        + extra,
                queda=f"({texto(factor_lin)})*({texto(cociente)})"))
            return [factor_lin, cociente]
        return None
