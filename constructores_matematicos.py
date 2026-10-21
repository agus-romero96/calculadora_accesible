"""Construcción y validación de expresiones, sin dependencia de wxPython."""
from dataclasses import dataclass

import sympy

from i18n import N_, tr
from parser_matematico import ParserMatematico


@dataclass(frozen=True)
class CampoConstructor:
    clave: str
    etiqueta: str
    mensaje_vacio: str
    sugerencia: str = ""


@dataclass(frozen=True)
class Constructor:
    titulo: str
    campos: tuple


CONSTRUCTORES = {
    "parentesis": Constructor(N_("Insertar paréntesis"), (
        CampoConstructor("argumento", N_("Argumento:"), N_("Escriba el argumento de la función.")),
    )),
    "fraccion": Constructor(N_("Insertar fracción"), (
        CampoConstructor("numerador", N_("Numerador:"), N_("Escriba el numerador de la fracción.")),
        CampoConstructor("denominador", N_("Denominador:"), N_("Escriba el denominador de la fracción.")),
    )),
    "potencia": Constructor(N_("Insertar potencia"), (
        CampoConstructor("base", N_("Base:"), N_("Escriba la base de la potencia.")),
        CampoConstructor("exponente", N_("Exponente:"), N_("Escriba el exponente de la potencia."), "2"),
    )),
    "raiz": Constructor(N_("Insertar raíz cuadrada"), (
        CampoConstructor("radicando", N_("Expresión dentro de la raíz:"), N_("Escriba la expresión dentro de la raíz.")),
    )),
}


class ErrorCampoConstructor(ValueError):
    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo


def validar_campos(tipo, valores):
    """Reutiliza el parser y exige expresiones escalares; no valida dominios.

    Solo el denominador se simplifica en una copia para detectar cero exacto.
    No se emplean tolerancias ni pruebas numéricas de posibles raíces.
    """
    parser = ParserMatematico()
    textos = {}
    for campo in CONSTRUCTORES[tipo].campos:
        texto = valores.get(campo.clave, "").strip()
        if not texto:
            raise ErrorCampoConstructor(campo.clave, tr(campo.mensaje_vacio))
        try:
            expresion = parser.parsear(texto)
            if not isinstance(expresion, sympy.Expr):
                raise ValueError(tr("Escriba una expresión matemática, sin ecuaciones, listas ni matrices."))
            if campo.clave == "denominador" and sympy.simplify(expresion).is_zero is True:
                raise ErrorCampoConstructor(campo.clave, tr("El denominador es cero. Escriba un denominador distinto de cero."))
        except ErrorCampoConstructor:
            raise
        except Exception as error:
            raise ErrorCampoConstructor(campo.clave, tr("Revise {campo}: {error}",
                campo=tr(campo.etiqueta).rstrip(":"), error=error)) from error
        textos[campo.clave] = texto
    return textos


def construir_expresion(tipo, valores):
    """Conserva el texto del usuario y agrupa cada operando sin evaluarlo."""
    datos = validar_campos(tipo, valores)
    if tipo == "fraccion":
        return f"({datos['numerador']})/({datos['denominador']})"
    if tipo == "potencia":
        return f"({datos['base']})^({datos['exponente']})"
    if tipo == "parentesis":
        return f"({datos['argumento']})"
    return f"sqrt({datos['radicando']})"


def construir_fraccion(numerador, denominador):
    return construir_expresion("fraccion", dict(numerador=numerador, denominador=denominador))


def construir_potencia(base, exponente):
    return construir_expresion("potencia", dict(base=base, exponente=exponente))


def construir_raiz(radicando):
    return construir_expresion("raiz", dict(radicando=radicando))

def construir_funcion(nombre, argumento):
    from catalogo_matematico import POR_NOMBRE

    if nombre not in POR_NOMBRE:
        raise ValueError(tr("Función fuera del catálogo."))
    texto = argumento.strip()
    try:
        if not texto:
            raise ValueError(tr("Escriba el argumento de la función."))
        valor = ParserMatematico().parsear(texto)
        if not isinstance(valor, sympy.Expr):
            raise ValueError(tr("Escriba una expresión matemática, sin ecuaciones, listas ni matrices."))
    except Exception as error:
        raise ErrorCampoConstructor("argumento", str(error)) from error
    # Solo valida el argumento. No aplica ni evalúa la función elegida.
    return f"{nombre}({texto})"
