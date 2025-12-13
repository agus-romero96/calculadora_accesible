import sympy
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)

class ParserMatematico:
    """
    Encargado exclusivamente de traducir texto de usuario a expresiones SymPy.
    """

    def __init__(self):
        # Configuración estándar + multiplicación implícita (2x) + exponente con ^
        self.transformations = (standard_transformations + 
                                (implicit_multiplication_application, convert_xor))
        
        # Diccionario local: Definimos constantes matemáticas explícitas
        # 'e' siempre será el número de Euler, no una variable cualquiera.
        self.contexto_global = {'e': sympy.E, 'pi': sympy.pi}

    def parsear(self, expresion: str):
        """
        Convierte un string en una expresión SymPy.
        Lanza ValueError si la sintaxis es incorrecta.
        """
        if not expresion or not expresion.strip():
            raise ValueError("La expresión está vacía. Por favor escriba algo.")
            
        # 1. Chequeo preliminar de paréntesis (Accesibilidad Cognitiva: error claro)
        if expresion.count('(') != expresion.count(')'):
             raise ValueError("Paréntesis desbalanceados. Revise si cerró todos los paréntesis.")

        # 2. Normalización de texto (Mapeos para facilitar escritura)
        # Convertimos 'ln' a la función interna 'log' (natural)
        # Convertimos 'log' (base 10) a una forma que SymPy entienda dividiendo por log(10)
        txt = expresion.lower() # Trabajamos todo en minúsculas
        txt = txt.replace("log", "log_placeholder")
        txt = txt.replace("ln", "log") 
        txt = txt.replace("log_placeholder", "log/log(10)")
        
        try:
            # Intentamos convertir el texto a matemáticas
            expr = parse_expr(txt, 
                              transformations=self.transformations,
                              local_dict=self.contexto_global)
            
            return expr
                              
        except SyntaxError:
            raise ValueError("Error de escritura: Revise los operadores matemáticos (+, -, *, /).")
        except Exception as ex:
            # Capturamos cualquier otro error raro de SymPy y lo hacemos legible
            raise ValueError(f"No se pudo interpretar la fórmula: {str(ex)}")