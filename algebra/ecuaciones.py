"""
Ecuaciones lineales explicadas paso a paso, para los sistemas (sustitución, igualación,
reducción, Gauss-Jordan):

  - despejar(izquierda, derecha, variable): cada transformación de una ecuación de primer
    grado hasta dejar sola la variable: quitar paréntesis, agrupar términos semejantes,
    pasar términos al otro lado (con la cuenta) y dividir entre el coeficiente.
  - comprobar(ecuaciones, solucion): sustituye la solución en cada ecuación original.

Las expresiones se escriben como en calculo/pasos.py (texto(), con ^).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

import sympy
from sympy import Symbol

from calculo.pasos import agrupa_semejantes, entre_parentesis, suma_texto, texto
from i18n import tr

Ecuacion = Tuple[Any, Any]  # (lado izquierdo, lado derecho)


def ecuacion_texto(izquierda: Any, derecha: Any) -> str:
    return f"{texto(izquierda)} = {texto(derecha)}"


def normalizada(izquierda: Any, derecha: Any, variables: Sequence[Symbol]) -> Ecuacion:
    """a*x + b*y = c: las incógnitas a la izquierda y el número a la derecha."""
    todo = sympy.expand(izquierda - derecha)
    numero = todo.as_independent(*variables, as_Add=True)[0]
    return todo - numero, -numero


def _terminos(expr: Any) -> List[Any]:
    return list(sympy.Add.make_args(expr)) if expr != 0 else []


def _quitar_parentesis(lado: Any, lineas: List[str], escrito: str = None) -> Any:
    """
    Distribuye cada término (sin agrupar todavía) y después agrupa los semejantes.
    escrito: el lado tal como se muestra (2*(y + 1) + 3*y), si no es texto(lado).
    """
    evaluado = sympy.expand(lado.doit())
    # Solo números: una cuenta. Si hay incógnitas que se cancelan (2*(x + 1) - 2*x), no: hay que ver cómo
    if evaluado.is_number and not sympy.sympify(lado).free_symbols:
        # Solo números (2*2 - 1): una cuenta, en el orden en que se escribió
        antes = escrito or texto(lado)
        if antes != texto(evaluado):
            lineas.append(tr("Operamos: {antes} = {despues}.", antes=antes, despues=texto(evaluado)))
        return evaluado
    sumandos = _terminos(lado)
    distribuidos = [s for t in sumandos for s in _terminos(sympy.expand(t.doit()))]
    # Primero los términos con incógnitas, después los números: 2*y + 3*y + 2
    distribuidos.sort(key=lambda s: s.is_number)
    cambiados = [t for t in sumandos if sympy.expand(t.doit()) != t]
    if cambiados:
        # Con una suma dentro hay paréntesis que quitar (2*(y + 1)); si no, solo números que operar (3*2)
        con_parentesis = any(isinstance(n, sympy.Add) for t in cambiados for n in sympy.preorder_traversal(t))
        plantilla = (tr("Quitamos paréntesis (propiedad distributiva): {antes} = {despues}.") if con_parentesis
                     else tr("Operamos: {antes} = {despues}."))
        lineas.append(plantilla.format(antes=escrito or texto(lado),
                                       despues=suma_texto(distribuidos) if distribuidos else "0"))
    lineas.extend(agrupa_semejantes(distribuidos))
    return sympy.expand(lado.doit())


def _pasar(termino: Any, lado: str) -> str:
    """'Pasamos 2 a la derecha cambiando de signo (es restar 2 en los dos lados).'"""
    if termino.could_extract_minus_sign():
        return tr("Pasamos {termino} a la {lado} cambiando de signo (es sumar {opuesto} en los dos lados).",
                  termino=texto(termino), lado=lado, opuesto=texto(-termino))
    return tr("Pasamos {termino} a la {lado} cambiando de signo (es restar {termino} en los dos lados).",
              termino=texto(termino), lado=lado)


def sin_evaluar(expr: Any, valores: Dict[Symbol, Any]) -> Any:
    """expr con cada incógnita cambiada por su valor entre paréntesis y sin operar: 2*(y + 1) + 3*y."""
    if sympy.sympify(expr) in valores:  # un lado que es solo la incógnita: su valor, sin paréntesis
        return sympy.sympify(valores[sympy.sympify(expr)])
    return sympy.sympify(expr).xreplace({v: sympy.UnevaluatedExpr(sympy.sympify(e)) for v, e in valores.items()})


def despejar(izquierda: Any, derecha: Any, variable: Symbol, izquierda_escrita: str = None,
             derecha_escrita: str = None) -> Tuple[List[str], Any]:
    """
    (líneas, valor) de despejar variable en izquierda = derecha (lineal en variable).
    El valor puede contener otras incógnitas (despejar x en x - y = 1 da y + 1).
    izquierda_escrita: el lado izquierdo tal como se mostró (tras una sustitución, en su orden).
    """
    lineas: List[str] = []
    izquierda = _quitar_parentesis(sympy.sympify(izquierda), lineas, izquierda_escrita)
    derecha = _quitar_parentesis(sympy.sympify(derecha), lineas, derecha_escrita)

    con_izq, sin_izq = izquierda.coeff(variable) * variable, izquierda - izquierda.coeff(variable) * variable
    con_der, sin_der = derecha.coeff(variable) * variable, derecha - derecha.coeff(variable) * variable
    lado_var = [t for t in _terminos(con_izq)] + [-t for t in _terminos(con_der)]
    lado_resto = [t for t in _terminos(sin_der)] + [-t for t in _terminos(sin_izq)]

    for termino in _terminos(con_der):
        lineas.append(_pasar(termino, tr("izquierda")))
    for termino in _terminos(sin_izq):
        lineas.append(_pasar(termino, tr("derecha")))
    coeficiente = sympy.expand(con_izq - con_der).coeff(variable)
    if coeficiente == 0:
        raise ValueError(tr("La incógnita {variable} desaparece de la ecuación.", variable=variable))
    resto = sympy.expand(sin_der - sin_izq)
    if con_der != 0 or sin_izq != 0:
        operado = ecuacion_texto(coeficiente * variable, resto)
        if len(lado_var) == len(_terminos(coeficiente * variable)) and len(lado_resto) == len(_terminos(resto)):
            lineas.append(tr("Queda {ecuacion}.", ecuacion=operado))  # solo cambia el orden: nada que operar
        else:
            izquierda_txt = suma_texto(lado_var)
            derecha_txt = suma_texto(lado_resto) if lado_resto else "0"
            lineas.append(tr("Queda {ecuacion}.", ecuacion=f"{izquierda_txt} = {derecha_txt}"))
            lineas.append(tr("Operamos cada lado: {ecuacion}.", ecuacion=operado))

    valor = sympy.expand(resto / coeficiente)
    if coeficiente == -1:
        lineas.append(tr("Cambiamos el signo de los dos lados: {variable} = {valor}.", variable=variable, valor=texto(valor)))
    elif coeficiente != 1:
        division = f"{entre_parentesis(resto)}/{entre_parentesis(coeficiente)}"
        lineas.append(tr("Dividimos los dos lados entre {coeficiente}: {variable} = {division} = {valor}.",
                         coeficiente=texto(coeficiente), variable=variable, division=division, valor=texto(valor))
                      if division != texto(valor) else
                      tr("Dividimos los dos lados entre {coeficiente}: {variable} = {valor}.",
                         coeficiente=texto(coeficiente), variable=variable, valor=texto(valor)))
    return lineas, valor


def sustituir(expr: Any, valores: Dict[Symbol, Any]) -> str:
    """
    La expresión con cada incógnita cambiada por su valor, sin calcular y en el orden en que se
    escribe: 2*x + 3*y con x = 3, y = 2 da '2*3 + 3*2' (SymPy reordenaría los términos).
    """
    if sympy.sympify(expr) in valores:  # un lado que es solo la incógnita: su valor, sin paréntesis
        return texto(sympy.sympify(valores[sympy.sympify(expr)]))
    escrita = texto(sympy.sympify(expr))
    nombres = sorted(valores, key=lambda v: -len(v.name))
    marcas = {v: f"\x00{i}\x00" for i, v in enumerate(nombres)}
    for v in nombres:  # primero marcas, para no volver a cambiar lo ya sustituido
        escrita = re.sub(rf"(?<![\w.]){re.escape(v.name)}(?![\w(])", marcas[v], escrita)
    for v in nombres:
        valor = sympy.sympify(valores[v])
        nombre = texto(valor)
        if not (valor.is_Symbol or (valor.is_Integer and valor >= 0)):
            nombre = f"({nombre})"
        escrita = escrita.replace(marcas[v], nombre)
    # -(-2) se lee bien; (( )) dobles, no
    return re.sub(r"\(\(([^()]+)\)\)", r"(\1)", escrita)


def comprobar(ecuaciones: List[Ecuacion], solucion: Dict[Symbol, Any]) -> List[str]:
    """Una línea por ecuación original: el lado izquierdo con la solución vale lo mismo que el derecho."""
    lineas = []
    for i, (izquierda, derecha) in enumerate(ecuaciones, 1):
        solucion = {v: sympy.sympify(e) for v, e in solucion.items()}
        valor_izq = sympy.simplify(sympy.sympify(izquierda).subs(solucion))
        valor_der = sympy.simplify(sympy.sympify(derecha).subs(solucion))
        cuenta_izq = sustituir(izquierda, solucion)
        cuenta_izq = cuenta_izq if cuenta_izq == texto(valor_izq) else f"{cuenta_izq} = {texto(valor_izq)}"
        cuenta_der = sustituir(derecha, solucion)
        cuenta_der = cuenta_der if cuenta_der == texto(valor_der) else f"{cuenta_der} = {texto(valor_der)}"
        se_cumple = sympy.simplify(valor_izq - valor_der) == 0
        lineas.append(tr("Ecuación {i}: {izquierda}, y el lado derecho es {derecha}: {veredicto}.", i=i,
                         izquierda=cuenta_izq, derecha=cuenta_der,
                         veredicto=tr("se cumple") if se_cumple else tr("NO se cumple")))
    return lineas
