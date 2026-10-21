"""Definiciones y argumentos de los formularios, sin controles ni cálculo matemático."""
from dataclasses import dataclass

from i18n import N_, tr
from puente import OPERACION


@dataclass(frozen=True)
class CampoGuiado:
    clave: str
    etiqueta: str
    inicial: str | int = ""
    opciones: tuple = ()


@dataclass(frozen=True)
class FormularioGuiado:
    clave: str
    nombre: str
    ejemplo: str
    campos: tuple

    @property
    def operacion(self):
        return OPERACION[self.clave]

    @property
    def argumentos(self):
        # El orden del formulario coincide con la firma del método del registro.
        return tuple(campo.clave for campo in self.campos if not campo.opciones)


EXPRESION = CampoGuiado("expresion", N_("Expresión matemática:"))
FUNCION = CampoGuiado("expresion", N_("Función:"))
VARIABLE = CampoGuiado("variable", N_("Variable:"), "x")
VARIABLE_INTEGRACION = CampoGuiado("variable", N_("Variable de integración:"), "x")

_FORMULARIOS = (
    FormularioGuiado("ecuacion", N_("Resolver ecuación"),
        N_("Encuentre el valor de la incógnita. Ejemplo: 2*x + 3 = 7."),
        (CampoGuiado("expresion", N_("Ecuación:")),)),
    FormularioGuiado("derivar", N_("Calcular derivada"),
        N_("Obtenga la derivada de una función. Ejemplo: x^2 + 3*x."),
        (FUNCION, VARIABLE)),
    FormularioGuiado("limite", N_("Calcular límite"),
        N_("Estudie una función cerca de un valor. Ejemplo: sin(x)/x, cuando x tiende a 0."),
        (FUNCION, VARIABLE,
         CampoGuiado("tendencia", N_("Valor de tendencia (por ejemplo: 0, 2, infinito):")),
         CampoGuiado("direccion", N_("Dirección:"), 0, (N_("Bilateral"), N_("Izquierda"), N_("Derecha"))))),
    FormularioGuiado("evaluar", N_("Evaluar"),
        N_("Calcule el valor de una expresión. Ejemplo: 2 + 3*4."), (EXPRESION,)),
    FormularioGuiado("simplificar", N_("Simplificar"),
        N_("Obtenga una forma más sencilla. Ejemplo: (x^2-1)/(x-1)."), (EXPRESION,)),
    FormularioGuiado("factorizar", N_("Factorizar"),
        N_("Descomponga una expresión en factores. Ejemplo: x^2-9."), (EXPRESION,)),
    FormularioGuiado("integrar", N_("Integral indefinida"),
        N_("Encuentre una función cuya derivada sea la dada. Ejemplo: 2*x, respecto de x."),
        (FUNCION, VARIABLE_INTEGRACION)),
    FormularioGuiado("integral_definida", N_("Integral definida"),
        N_("Calcule una integral entre dos valores. Ejemplo: x, respecto de x, desde 0 hasta 2."),
        (FUNCION, VARIABLE_INTEGRACION,
         CampoGuiado("inferior", N_("Límite inferior:")),
         CampoGuiado("superior", N_("Límite superior:")))),
)

FORMULARIOS = {formulario.clave: formulario for formulario in _FORMULARIOS}
OPCIONES = tuple((f.clave, f.nombre, f.ejemplo) for f in _FORMULARIOS)


class CampoObligatorio(ValueError):
    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo


def construir_argumentos(clave, expresion, variable="x", tendencia="", direccion=0,
                        inferior="", superior=""):
    """Comprueba datos obligatorios y adapta su orden; el núcleo interpreta la matemática."""
    if clave not in FORMULARIOS:
        raise ValueError(clave)
    formulario = FORMULARIOS[clave]
    datos = dict(expresion=expresion.strip(), variable=variable.strip(), tendencia=tendencia.strip(),
                 inferior=inferior.strip(), superior=superior.strip())
    for campo in formulario.argumentos:
        if not datos[campo]:
            raise CampoObligatorio(campo, tr("Complete este campo antes de calcular."))
    if clave == "ecuacion" and not any(signo in datos["expresion"] for signo in "=<>≤≥"):
        raise CampoObligatorio("expresion", tr("Escriba una ecuación o inecuación con un signo =, <, >, <= o >= (ej: 2*x + 1 = 7)."))
    if clave == "limite":
        if direccion not in (0, 1, 2):
            raise ValueError(direccion)
        punto = datos["tendencia"]
        if punto.endswith(("+", "-")):
            raise CampoObligatorio("tendencia", tr("Escriba solo el valor de tendencia y elija la dirección en la lista."))
        infinito = punto.lower() in {"oo", "+oo", "-oo", "inf", "+inf", "-inf", "infinito", "-infinito", "infinity", "-infinity", "∞", "-∞"}
        if infinito and direccion:
            raise CampoObligatorio("tendencia", tr("Para infinito, seleccione Bilateral; el sentido lo determina el signo del infinito."))
        datos["tendencia"] = punto + ("", "-", "+")[direccion]
    return tuple(datos[campo] for campo in formulario.argumentos)
