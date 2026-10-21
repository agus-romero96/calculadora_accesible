"""Catálogo explícito de funciones aceptadas por ParserMatematico, sin wx."""
from dataclasses import dataclass
from i18n import N_


@dataclass(frozen=True)
class Funcion:
    canonica: str
    nombre: str
    categoria: str
    descripcion: str


CATEGORIAS = {
    'trig': N_('Funciones trigonométricas'),
    'inversas': N_('Funciones trigonométricas inversas'),
    'hiper': N_('Funciones hiperbólicas'),
    'logs': N_('Logaritmos y exponenciales'),
    'otras': N_('Otras funciones'),
}
FUNCIONES = (
    Funcion('sin', N_('Seno'), 'trig', N_('Ángulo en radianes.')),
    Funcion('cos', N_('Coseno'), 'trig', N_('Ángulo en radianes.')),
    Funcion('tan', N_('Tangente'), 'trig', N_('Ángulo en radianes.')),
    Funcion('cot', N_('Cotangente'), 'trig', N_('Ángulo en radianes.')),
    Funcion('sec', N_('Secante'), 'trig', N_('Ángulo en radianes.')),
    Funcion('csc', N_('Cosecante'), 'trig', N_('Ángulo en radianes.')),
    Funcion('asin', N_('Arcoseno'), 'inversas', N_('Devuelve un ángulo en radianes.')),
    Funcion('acos', N_('Arcocoseno'), 'inversas', N_('Devuelve un ángulo en radianes.')),
    Funcion('atan', N_('Arcotangente'), 'inversas', N_('Devuelve un ángulo en radianes.')),
    Funcion('acot', N_('Arcocotangente'), 'inversas', N_('Devuelve un ángulo en radianes.')),
    Funcion('sinh', N_('Seno hiperbólico'), 'hiper', N_('Función hiperbólica del argumento.')),
    Funcion('cosh', N_('Coseno hiperbólico'), 'hiper', N_('Función hiperbólica del argumento.')),
    Funcion('tanh', N_('Tangente hiperbólica'), 'hiper', N_('Función hiperbólica del argumento.')),
    Funcion('coth', N_('Cotangente hiperbólica'), 'hiper', N_('Función hiperbólica del argumento.')),
    Funcion('asinh', N_('Seno hiperbólico inverso'), 'hiper', N_('Función hiperbólica del argumento.')),
    Funcion('acosh', N_('Coseno hiperbólico inverso'), 'hiper', N_('Función hiperbólica del argumento.')),
    Funcion('atanh', N_('Tangente hiperbólica inversa'), 'hiper', N_('Función hiperbólica del argumento.')),
    Funcion('log', N_('Logaritmo natural'), 'logs', N_('Logaritmo de base e del argumento.')),
    Funcion('log10', N_('Logaritmo base 10'), 'logs', N_('Logaritmo de base 10 del argumento.')),
    Funcion('exp', N_('Exponencial'), 'logs', N_('Número e elevado al argumento.')),
    Funcion('abs', N_('Valor absoluto'), 'otras', N_('Distancia del argumento al cero.')),
    Funcion('heaviside', N_('Escalón unitario'), 'otras', N_('Escalón unitario: cero para negativos y uno para positivos; un medio en cero.')),
    Funcion('dirac', N_('Delta de Dirac'), 'otras', N_('Distribución delta de Dirac, utilizada en transformadas de Laplace.')),
)
POR_NOMBRE = {f.canonica: f for f in FUNCIONES}

def funciones_categoria(categoria):
    return tuple(f for f in FUNCIONES if f.categoria == categoria)
