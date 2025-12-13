"""
operations.py (El Backend / Fachada)
====================================
Este archivo es el ÚNICO punto de contacto para la interfaz gráfica (ui.py).
Su responsabilidad es:
1. Inicializar la herramienta compartida (Parser).
2. "Contratar" (instanciar) a los módulos especialistas.
3. Delegar las peticiones de la UI al especialista correcto.
"""

# --- 1. IMPORTACIONES DE HERRAMIENTAS COMUNES ---
from parser import ParserMatematico

# --- 2. IMPORTACIONES DE LOS ESPECIALISTAS ---
from aritmetica import Aritmetica

# Módulos de ÁLGEBRA
from algebra.matrix_logic import MotorMatrices
from algebra.gauss_logic import MotorGauss
from algebra.classic_systems import MotorSistemasClasicos

# Módulos de CÁLCULO
from calculo.limite import GestorLimites
from calculo.calculo import Calculo  # Tu nuevo archivo

class CoreMatematico:
    def __init__(self):
        # A. CREAMOS LA FUENTE ÚNICA DE VERDAD (El Parser)
        # Esto ahorra memoria y asegura que todos entiendan "ln(x)" igual.
        self.parser_comun = ParserMatematico()

        # B. INYECCIÓN DE DEPENDENCIAS (Contratamos a los especialistas)
        # Les pasamos el parser común para que no creen uno propio cada vez.
        
        # Especialista en Aritmética
        self.aritmetica = Aritmetica(self.parser_comun)
        
        # Especialistas en Álgebra Lineal
        self.matrices = MotorMatrices(self.parser_comun)
        self.gauss = MotorGauss(self.parser_comun)
        self.clasicos = MotorSistemasClasicos(self.parser_comun)
        
        # Especialistas en Cálculo
        # Nota: Tu archivo calculo.py actual crea su propio parser en __init__.
        # Idealmente, modifícalo para aceptar (self.parser_comun).
        # Por ahora lo instanciamos directo:
        self.calculo = Calculo(self.parser_comun)
        
        # Especialista en Límites
        self.limites = GestorLimites(self.parser_comun)

    # ==========================================
    # 1. DELEGACIÓN: ARITMÉTICA BÁSICA
    # ==========================================

    def Evaluar(self, expresion):
        """Calcula valor exacto y decimal."""
        return self.aritmetica.evaluar(expresion)

    def Simplificar(self, expresion):
        """Reduce términos algebraicos."""
        return self.aritmetica.simplificar(expresion)

    def Factorizar(self, expresion):
        """Convierte sumas en productos."""
        return self.aritmetica.factorizar(expresion)

    # ==========================================
    # 2. DELEGACIÓN: ÁLGEBRA LINEAL (Sistemas y Matrices)
    # ==========================================

    def ResolverSistemaGauss(self, lista_ecuaciones):
        """Método universal para sistemas NxN (Gauss-Jordan)."""
        return self.gauss.ExplicarGaussJordan(lista_ecuaciones)

    def ResolverSistemaEducativo(self, lista_ecuaciones, metodo):
        """Métodos de colegio (Sustitución, Igualación) para 2x2."""
        return self.clasicos.ExplicarSistemaClasico(lista_ecuaciones, metodo)

    def MatrizInversaCofactores(self, expresion_matriz):
        """Explicación paso a paso de la Inversa por Adjunta."""
        return self.matrices.ExplicarInversaCofactores(expresion_matriz)

    # ==========================================
    # 3. DELEGACIÓN: CÁLCULO (Derivadas, Integrales, Límites)
    # ==========================================

    def Derivar(self, expresion):
        """Derivada simple con explicación de regla."""
        return self.calculo.derivar(expresion)

    def DerivadaEnecima(self, expresion, variable, orden):
        """Muestra la secuencia de derivadas hasta orden N."""
        # La UI debe asegurar que 'orden' sea un entero (int)
        return self.calculo.derivada_enecima(expresion, variable, orden)

    def Integrar(self, expresion):
        """Integral indefinida con pasos (ManualIntegrate)."""
        return self.calculo.integrar(expresion)

    def CalcularLimite(self, expresion, variable, tendencia):
        """Límites con análisis de continuidad y asíntotas."""
        return self.limites.calcular_limite(expresion, variable, tendencia)