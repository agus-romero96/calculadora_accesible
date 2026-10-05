"""
puente.py (La Fachada / Controller)
===================================
Punto de conexión entre la Interfaz Gráfica (main.py) y los Motores Matemáticos.
Su responsabilidad es orquestar las llamadas y asegurar que la UI reciba texto limpio.
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
# NOTA: Asegúrate de que tu archivo nuevo se llame calculo.py y esté en la carpeta calculo/
from calculo.limite import GestorLimites
from calculo.router import RouterMatematico 
from calculo.calculo import Calculo 

class CoreMatematico:
    def __init__(self):
        # A. FUENTE ÚNICA DE VERDAD (Parser)
        self.parser_comun = ParserMatematico()

        # B. INYECCIÓN DE DEPENDENCIAS
        
        # Especialista en Aritmética
        self.aritmetica = Aritmetica(self.parser_comun)
        
        # Especialistas en Álgebra Lineal
        self.matrices = MotorMatrices(self.parser_comun)
        self.gauss = MotorGauss(self.parser_comun)
        self.clasicos = MotorSistemasClasicos(self.parser_comun)
        
        # Especialistas en Cálculo
        self.calculo = Calculo(self.parser_comun)
        self.limites_backend = GestorLimites(self.parser_comun)
        self.router = RouterMatematico(self.parser_comun, self.limites_backend)

    # ==========================================
    # 1. DELEGACIÓN: ARITMÉTICA BÁSICA
    # ==========================================

    def Evaluar(self, expresion):
        # Obtenemos DTO
        dto = self.aritmetica.evaluar(expresion)
        # Renderizamos a texto accesible
        return self.aritmetica.renderizar(dto)

    def Simplificar(self, expresion):
        dto = self.aritmetica.simplificar(expresion)
        return self.aritmetica.renderizar(dto)

    def Factorizar(self, expresion):
        dto = self.aritmetica.factorizar(expresion)
        return self.aritmetica.renderizar(dto)

    # ==========================================
    # 2. DELEGACIÓN: ÁLGEBRA LINEAL
    # ==========================================

    def ResolverSistemaGauss(self, lista_ecuaciones):
        return self.gauss.ExplicarGaussJordan(lista_ecuaciones)

    def ResolverSistemaEducativo(self, lista_ecuaciones, metodo):
        return self.clasicos.ExplicarSistemaClasico(lista_ecuaciones, metodo)

    def MatrizInversaCofactores(self, expresion_matriz):
        # Nota: Aquí también podrías refactorizar para usar Renderizar, 
        # pero por ahora mantenemos compatibilidad con tu código de matrices existente.
        res = self.matrices.CalcularInversaCofactores(expresion_matriz)
        return self.matrices.RenderizarInformeInversa(res)

    # ==========================================
    # 3. DELEGACIÓN: CÁLCULO (ACTUALIZADO V4.2)
    # ==========================================

    def Derivar(self, expresion, variable=None):
        """
        Calcula la derivada y devuelve el informe accesible.
        Si variable es None, el motor la infiere (o usa 'x').
        """
        # 1. Obtenemos el objeto rico (DTO)
        resultado_dto = self.calculo.CalcularDerivada(expresion, variable=variable)
        # 2. Lo convertimos a texto para la UI
        return self.calculo.RenderizarTexto(resultado_dto)

    def DerivadaEnecima(self, expresion, variable, orden):
        """
        Calcula derivada de orden N.
        La UI sí envía variable y orden explícitos aquí.
        """
        resultado_dto = self.calculo.DerivadaEnecima(expresion, variable, orden)
        return self.calculo.RenderizarTexto(resultado_dto)

    def Integrar(self, expresion, variable=None):
        """
        Calcula integral indefinida.
        Si variable es None y la expresión es constante, el motor devuelve error (correcto).
        """
        resultado_dto = self.calculo.CalcularIntegral(expresion, variable=variable)
        return self.calculo.RenderizarTexto(resultado_dto)

    def CalcularLimite(self, expresion, variable, tendencia):
        return self.router.CalcularLimite(expresion, variable, tendencia)
    


    def DetectarVariables(self, expresion):
        """
        Método auxiliar para la UI.
        Analiza la expresión y devuelve una lista de las variables encontradas (strings).
        Ejemplo: "x + y" -> ["x", "y"]
        """
        try:
            # Usamos el parser común para ver qué hay dentro
            expr = self.parser_comun.parsear(expresion)
            # Extraemos símbolos y los ordenamos alfabéticamente
            syms = sorted([s.name for s in expr.free_symbols])
            return syms
        except Exception:
            # Si hay error de sintaxis, devolvemos lista vacía.
            # El error real saltará cuando intenten calcular.
            return []