"""
Pasos de una explicación de cálculo (derivadas, integrales) y su texto.

Un paso tiene un título y, según el motor que lo genera:
  - una descripción y una fórmula (integrales), o
  - el desglose de una regla (derivadas), una línea por parte, en este orden:
      Regla:        la regla general, antes de aplicarla
      En este caso: qué parte de la expresión es cada pieza de la regla
      (cálculo)     la sustitución y las cuentas intermedias, una por línea
      Queda:        la expresión tras el paso
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

import sympy

from i18n import tr


@dataclass(frozen=True)
class PasoCalculo:
    titulo: str
    descripcion: str = ""
    expresion_matematica: str = ""
    regla: str = ""
    partes: str = ""
    calculo: Tuple[str, ...] = ()
    queda: str = ""


def texto_paso(numero: int, paso: PasoCalculo) -> str:
    """El paso numerado; cada línea añadida va sangrada para leerla con las flechas."""
    lineas: List[str] = [f"{numero}. {tr(paso.titulo)}."]
    if paso.descripcion:
        lineas[0] += f" {tr(paso.descripcion)}"
    if paso.expresion_matematica:
        lineas.append(tr("[Fórmula]: {formula}", formula=paso.expresion_matematica))
    if paso.regla:
        lineas.append(tr("Regla: {regla}", regla=paso.regla))
    if paso.partes:
        lineas.append(tr("En este caso: {partes}", partes=paso.partes))
    lineas.extend(paso.calculo)
    if paso.queda:
        lineas.append(tr("Queda: {expresion}", expresion=paso.queda))
    return "\n   ".join(lineas)


# ---------------- Expresiones dentro de los pasos ----------------

def texto(expr: Any) -> str:
    """Expresión para leer: con ^ en lugar de ** (como se escribe en la calculadora)."""
    return sympy.sstr(expr).replace("**", "^")


def entre_parentesis(expr: Any) -> str:
    """Expresión lista para ir dentro de un producto o como exponente: entre paréntesis si hace falta."""
    simple = (expr.is_Symbol or (expr.is_Integer and expr >= 0) or expr.is_Function
              or (expr.is_Pow and expr.exp.is_Integer and expr.exp > 0 and expr.base.is_Symbol))
    return texto(expr) if simple else f"({texto(expr)})"


def suma_texto(terminos: List[Any]) -> str:
    """t1 + t2 - t3: los términos negativos se restan en lugar de sumar "(-t3)"."""
    partes = [texto(terminos[0])]
    for t in terminos[1:]:
        if t.could_extract_minus_sign():
            partes.append(f"- {texto(-t)}")
        else:
            partes.append(f"+ {texto(t)}")
    return " ".join(partes)


def como_potencia(expr: Any, forma: str) -> str:
    """Final de la frase que identifica la potencia: por qué sqrt(x), 1/x o x tienen exponente."""
    if texto(expr) == forma:
        return "."
    return tr(", porque {expresion} es lo mismo que {potencia}.", expresion=texto(expr), potencia=forma)


def forma_final(base: Any, exponente: Any) -> List[str]:
    """Cómo se escribe la potencia que queda: exponente negativo -> fracción, 1/2 -> raíz."""
    if not exponente.is_Number or exponente in (0, 1):
        return []
    cuentas = []
    if exponente.is_negative:
        cuentas.append(tr("Un exponente negativo pasa la potencia al denominador: {potencia} = 1/{positiva}.",
                          potencia=f"{entre_parentesis(base)}^{entre_parentesis(exponente)}", positiva=f"{entre_parentesis(base)}^{entre_parentesis(-exponente)}"))
    if abs(exponente) == sympy.Rational(1, 2):
        cuentas.append(tr("Elevar a 1/2 es sacar la raíz cuadrada: {potencia} = {raiz}.",
                          potencia=f"{entre_parentesis(base)}^(1/2)", raiz=texto(sympy.sqrt(base))))
    return cuentas


def agrupa_semejantes(terminos: List[Any]) -> List[str]:
    """
    Si al sumar los términos se juntan algunos semejantes (3*x^2*cos(x) + 3*x^2*cos(x)), la
    cuenta de cada grupo: '3*x^2*cos(x) + 3*x^2*cos(x) = 6*x^2*cos(x)'.
    """
    grupos = {}
    for termino in terminos:
        for sumando in sympy.Add.make_args(sympy.sympify(termino)):
            if sumando == 0:
                continue
            grupos.setdefault(sumando.as_coeff_Mul()[1], []).append(sumando)
    lineas = []
    for grupo in grupos.values():
        if len(grupo) > 1:
            lineas.append(tr("Agrupamos términos semejantes: {suma} = {resultado}.", suma=suma_texto(grupo),
                             resultado=texto(sympy.Add(*grupo))))
    return lineas


def multiplica_numeros(*factores: Any) -> List[str]:
    """Si hay varios coeficientes numéricos que multiplicar, la cuenta: 3 * 2 = 6."""
    numeros = [sympy.sympify(f).as_coeff_Mul()[0] for f in factores]
    numeros = [n for n in numeros if n != 1]
    if len(numeros) < 2:
        return []
    return [tr("Multiplicamos los números: {cuenta} = {resultado}.",
               cuenta=" * ".join(entre_parentesis(n) for n in numeros), resultado=texto(sympy.Mul(*numeros)))]
