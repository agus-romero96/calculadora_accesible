"""Definiciones y argumentos de los formularios, sin controles ni cálculo matemático."""
from dataclasses import dataclass

from i18n import N_, tr
from puente import OPERACION
from calculo.taylor import ORDEN_MAXIMO


@dataclass(frozen=True)
class CampoGuiado:
    clave: str
    etiqueta: str
    inicial: str | int = ""
    opciones: tuple = ()
    tipo: str = "texto"


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
    FormularioGuiado("derivada_n", N_("Derivada de orden N"),
        N_("Derive varias veces. Ejemplo: x^4, variable x, orden 3."),
        (FUNCION, VARIABLE, CampoGuiado("orden", N_("Orden de la derivada (entero, mínimo 1):"), "1", tipo="orden"))),
    FormularioGuiado("tangente", N_("Recta tangente y normal"),
        N_("Calcule las rectas en un punto. Ejemplo: x^2, variable x, punto 1."),
        (FUNCION, VARIABLE, CampoGuiado("punto", N_("Punto de tangencia (por ejemplo: 1, 1/2):"), tipo="punto"))),
    FormularioGuiado("extremos", N_("Extremos y crecimiento"),
        N_("Estudie los extremos y el crecimiento. Ejemplo: x^3 - 3*x, variable x."),
        (FUNCION, VARIABLE)),
    FormularioGuiado("taylor", N_("Polinomio de Taylor"),
        N_("Aproxime una función cerca de un punto. Ejemplo: exp(x), variable x, orden 3, punto 0."),
        (FUNCION, VARIABLE, CampoGuiado("orden", N_("Orden del polinomio (entero de 0 a 15):"), "3", tipo="orden"),
         CampoGuiado("punto", N_("Punto de expansión (por ejemplo: 0, pi/2):"), "0", tipo="punto"))),
    FormularioGuiado("implicita", N_("Derivada implícita"),
        N_("Derive una ecuación con dos variables. Ejemplo: x^2 + y^2 = 25."),
        (CampoGuiado("expresion", N_("Ecuación implícita:"), tipo="ecuacion"),)),
)

FORMULARIOS = {formulario.clave: formulario for formulario in _FORMULARIOS}
OPCIONES = tuple((f.clave, f.nombre, f.ejemplo) for f in _FORMULARIOS)


class CampoObligatorio(ValueError):
    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo


def construir_argumentos(clave, expresion, variable="x", tendencia="", direccion=0,
                        inferior="", superior="", orden="", punto=""):
    """Comprueba datos obligatorios y adapta su orden; el núcleo interpreta la matemática."""
    if clave not in FORMULARIOS:
        raise ValueError(clave)
    formulario = FORMULARIOS[clave]
    datos = dict(expresion=expresion.strip(), variable=variable.strip(), tendencia=tendencia.strip(),
                 inferior=inferior.strip(), superior=superior.strip(),
                 orden=str(orden).strip(), punto=punto.strip())
    for campo in formulario.argumentos:
        if not datos[campo]:
            raise CampoObligatorio(campo, tr("Complete este campo antes de calcular."))
    if "orden" in formulario.argumentos:
        try:
            datos["orden"] = int(datos["orden"])
        except ValueError:
            raise CampoObligatorio("orden", tr("El orden debe ser un número entero.")) from None
        if clave == "derivada_n" and datos["orden"] < 1:
            raise CampoObligatorio("orden", tr("El orden de derivación debe ser 1 o mayor."))
        if clave == "taylor" and not 0 <= datos["orden"] <= ORDEN_MAXIMO:
            raise CampoObligatorio("orden", tr("El orden debe estar entre 0 y {maximo}.", maximo=ORDEN_MAXIMO))
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
