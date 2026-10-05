import sympy
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

class ParserMatematico:
    """
    Parser matemático seguro y estable.
    - NO reescribe expresiones
    - NO aplica identidades
    - SOLO define símbolos y alias estándar
    """

    def __init__(self):
        self.transformations = (
            standard_transformations
            + (implicit_multiplication_application, convert_xor)
        )

        self.contexto = {
            # Constantes
            "e": sympy.E,
            "pi": sympy.pi,

            # Infinito
            "oo": sympy.oo,
            "inf": sympy.oo,
            "infinito": sympy.oo,

            # Logaritmos
            "log": sympy.log,      # natural
            "ln": sympy.log,       # alias natural
            "log10": lambda x: sympy.log(x, 10),

            # Trigonometría (explícito por claridad)
            "sin": sympy.sin,
            "cos": sympy.cos,
            "tan": sympy.tan,
            "sqrt": sympy.sqrt,
            "abs": sympy.Abs,
        }

    def parsear(self, expresion: str):
        if not expresion or not expresion.strip():
            raise ValueError("La expresión está vacía.")

        if expresion.count("(") != expresion.count(")"):
            raise ValueError("Paréntesis desbalanceados.")

        txt = expresion.lower().strip()

        try:
            return parse_expr(
                txt,
                transformations=self.transformations,
                local_dict=self.contexto,
                evaluate=False,  # 🔴 CLAVE: no reescribas nada
            )
        except Exception as e:
            raise ValueError(f"No se pudo interpretar la expresión: {e}")
