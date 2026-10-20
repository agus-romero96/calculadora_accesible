import sympy
from sympy.core.function import AppliedUndef

from i18n import tr
from sympy.parsing.sympy_parser import (
    _token_splittable,
    convert_xor,
    function_exponentiation,
    implicit_application,
    implicit_multiplication,
    parse_expr,
    split_symbols_custom,
    standard_transformations,
)

# Funciones que el usuario puede escribir. Sirve para no "partir" nombres que las
# contienen (xsin -> x*s*i*n) y para sugerir la escritura correcta.
# Orden: de más larga a más corta, para que "asin" se detecte antes que "sin".
FUNCIONES_CONOCIDAS = (
    "log10", "asinh", "acosh", "atanh",
    "asin", "acos", "atan", "acot", "sinh", "cosh", "tanh", "coth", "sqrt",
    "heaviside", "dirac",
    "sin", "cos", "tan", "cot", "sec", "csc", "exp", "log", "abs",
    "ln",
)


# Nombres alternativos o en español -> nombre canónico de la calculadora.
# Orden: de más largo a más corto, para que "arcsin" y "cosec" se detecten antes que "sin" y "cos".
ALIAS_FUNCIONES = (
    ("arcsinh", "asinh"), ("arccosh", "acosh"), ("arctanh", "atanh"),
    ("arcsin", "asin"), ("arccos", "acos"), ("arctan", "atan"), ("arccot", "acot"),
    ("arcsen", "asin"), ("arctg", "atan"), ("cosec", "csc"),
    ("coseno", "cos"), ("tangente", "tan"), ("seno", "sin"),
    ("senh", "sinh"), ("tgh", "tanh"), ("sen", "sin"), ("tg", "tan"),
)


def _contiene_funcion(nombre: str):
    """Devuelve (antes, funcion_canonica, despues) si el nombre contiene una función conocida o alias."""
    for alias, canonica in ALIAS_FUNCIONES:
        i = nombre.find(alias)
        if i != -1:
            return nombre[:i], canonica, nombre[i + len(alias):]
    for f in FUNCIONES_CONOCIDAS:
        i = nombre.find(f)
        if i != -1:
            return nombre[:i], f, nombre[i + len(f):]
    return None


def _parentesis_balanceados(txt: str) -> bool:
    nivel = 0
    for c in txt:
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
            if nivel < 0:
                return False
    return nivel == 0


def _se_puede_partir(nombre: str) -> bool:
    """
    Decide si un nombre de varias letras se interpreta como producto (xy -> x*y).
    Los nombres que contienen una función NO se parten: así 'xsin(x)' no se convierte
    en silencio en x*s*i*n*x, sino que se detecta y se informa al usuario.
    """
    if _contiene_funcion(nombre):
        return False
    return _token_splittable(nombre)


class ParserMatematico:
    """
    Parser matemático seguro y estable.
    - NO reescribe expresiones (evaluate=False)
    - NO aplica identidades
    - SOLO define símbolos y alias estándar

    Convenciones:
    - No distingue mayúsculas/minúsculas (más cómodo con lector de pantalla).
    - Las variables son REALES (Symbol(..., real=True)): así abs(x)' = sign(x) y
      sqrt(x^2) = |x|, en lugar de expresiones con re(x) e im(x).
      Para crear una variable compatible desde otro módulo, use simbolo().
    """

    def __init__(self):
        # convert_xor va primero para que function_exponentiation entienda "sin^2(x)"
        self.transformations = standard_transformations + (
            convert_xor,
            split_symbols_custom(_se_puede_partir),
            implicit_multiplication,
            implicit_application,
            function_exponentiation,
        )

        self.contexto = {
            # Todas las variables nuevas se crean como reales.
            # (La entrada se pasa a minúsculas, así que el usuario nunca escribe "Symbol".)
            "Symbol": self.simbolo,

            # Constantes
            "e": sympy.E,
            "pi": sympy.pi,

            # Infinito
            "oo": sympy.oo,
            "inf": sympy.oo,
            "infinito": sympy.oo,
            "infinity": sympy.oo,

            # Logaritmos
            "log": sympy.log,      # natural
            "ln": sympy.log,       # alias natural
            "log10": lambda x: sympy.log(x, 10),

            # Trigonometría (explícito por claridad)
            "sin": sympy.sin,
            "cos": sympy.cos,
            "tan": sympy.tan,
            "sqrt": sympy.sqrt,
            # Abs evalúa incluso argumentos sin evaluar (abs(x/x) perdería x != 0).
            "abs": lambda arg: sympy.Abs(arg, evaluate=False),

            # Escalón y delta (ecuaciones diferenciales con la transformada de Laplace)
            "heaviside": sympy.Heaviside,
            "dirac": sympy.DiracDelta,

            # Matrices: Matrix([[1,2],[3,4]]) (se escribe en minúsculas tras normalizar)
            "matrix": sympy.Matrix,
        }

    @staticmethod
    def simbolo(nombre: str) -> sympy.Symbol:
        """Variable real con el mismo criterio que el parser (minúsculas, sin espacios)."""
        return sympy.Symbol(str(nombre).strip().lower(), real=True)

    def parsear(self, expresion: str):
        if not expresion or not expresion.strip():
            raise ValueError(tr("La expresión está vacía."))

        if not _parentesis_balanceados(expresion):
            raise ValueError(tr("Paréntesis desbalanceados."))

        txt = (expresion.lower().strip()
               .replace("√", "sqrt").replace("π", "pi").replace("×", "*"))

        try:
            resultado = parse_expr(
                txt,
                transformations=self.transformations,
                local_dict=self.contexto,
                evaluate=False,  # 🔴 CLAVE: no reescribas nada
            )
        except Exception as e:
            raise ValueError(tr("No se pudo interpretar la expresión: {error}", error=e))

        self._validar_nombres(resultado, txt)
        return resultado

    # ---------------------------------------------------------
    # Validación: nombres que parecen funciones mal escritas
    # ---------------------------------------------------------

    def _validar_nombres(self, obj, txt: str) -> None:
        if isinstance(obj, (list, tuple, sympy.MatrixBase)):
            for item in obj:
                self._validar_nombres(item, txt)
            return
        if not isinstance(obj, sympy.Basic):
            return

        # xsin(x) -> función desconocida "xsin" aplicada a x
        for f in obj.atoms(AppliedUndef):
            nombre = f.func.__name__
            args = ", ".join(str(a) for a in f.args)
            raise ValueError(self._mensaje_nombre(nombre, f"{nombre}({args})", args))

        # sinx -> variable "sinx";  xsin(x) -> variable "xsin" por (x)
        for s in obj.free_symbols:
            if _contiene_funcion(s.name):
                args = self._argumento_tras(txt, s.name)
                escrito = f"{s.name}({args})" if args is not None else s.name
                raise ValueError(self._mensaje_nombre(s.name, escrito, args))

    @staticmethod
    def _argumento_tras(txt: str, nombre: str):
        """Si en el texto 'nombre' va seguido de '(...)', devuelve lo de dentro del paréntesis."""
        i = txt.find(nombre + "(")
        if i == -1:
            return None
        inicio = i + len(nombre) + 1
        nivel = 1
        for j in range(inicio, len(txt)):
            if txt[j] == "(":
                nivel += 1
            elif txt[j] == ")":
                nivel -= 1
                if nivel == 0:
                    return txt[inicio:j]
        return None

    def _mensaje_nombre(self, nombre: str, escrito: str, args) -> str:
        partes = _contiene_funcion(nombre)
        if not partes:
            return tr("No se reconoce la función '{nombre}' en '{escrito}'. Si quería multiplicar, use '*'.",
                      nombre=nombre, escrito=escrito)

        antes, funcion, despues = partes
        if args is not None and not despues:
            # xsin(x) -> x*sin(x); sen(x) -> sin(x)
            sugerencia = f"{'*'.join(antes)}*{funcion}({args})" if antes else f"{funcion}({args})"
        elif args is None and despues and not antes:
            # sinx -> sin(x)
            sugerencia = f"{funcion}({despues})"
        elif args is None and despues and antes:
            # xsinx -> x*sin(x)
            sugerencia = f"{'*'.join(antes)}*{funcion}({despues})"
        else:
            sugerencia = None

        msg = tr("No se reconoce '{escrito}'.", escrito=escrito)
        if sugerencia:
            msg += " " + tr("¿Quiso decir {sugerencia}?", sugerencia=sugerencia)
        return msg + " " + tr("Escriba '*' entre una variable y una función, "
                              "y el argumento de la función entre paréntesis.")
