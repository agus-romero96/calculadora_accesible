"""
puente.py (La Fachada / Controller)
===================================
Punto de conexión entre la Interfaz Gráfica (main.py) y los Motores Matemáticos.

Dos formas de uso:
  - API de objetos (la que usa la interfaz): evaluar(), derivar(), limite()...
    devuelven un ResultadoOperacion con el texto, el valor SymPy y si hubo error.
    Es lo que permite copiar el resultado y exportarlo (LaTeX, JSON...).
  - API de texto (compatibilidad): Evaluar(), Derivar(), CalcularLimite()...
    devuelven solo el texto accesible.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import sympy

from i18n import N_, idioma_actual

# --- 1. IMPORTACIONES DE HERRAMIENTAS COMUNES ---
from parser_matematico import ParserMatematico

# --- 2. IMPORTACIONES DE LOS ESPECIALISTAS ---
from aritmetica import Aritmetica

# Módulos de ÁLGEBRA
from algebra.matrix_logic import MotorMatrices
from algebra.gauss_logic import MotorGauss
from algebra.classic_systems import MotorSistemasClasicos

# Módulos de CÁLCULO
from calculo.limite import GestorLimites
from calculo.router import RouterMatematico
from calculo.calculo import Calculo

# Nombre visible de cada operación (se traduce con tr al mostrarlo)
OPERACIONES = {
    "evaluar": N_("Evaluación"),
    "simplificar": N_("Simplificación"),
    "factorizar": N_("Factorización"),
    "derivar": N_("Derivada"),
    "derivada_n": N_("Derivada de orden N"),
    "integrar": N_("Integral indefinida"),
    "limite": N_("Límite"),
    "gauss": N_("Sistema de ecuaciones (Gauss-Jordan)"),
    "sistema_clasico": N_("Sistema 2x2 (método clásico)"),
    "inversa": N_("Matriz inversa (cofactores)"),
}


def _normal(expr: Any) -> Any:
    """Forma normal de una expresión del parser (que no evalúa): 1/x en lugar de 1*1/x."""
    try:
        return expr.doit()
    except Exception:
        return expr


def _legible(expr: Any) -> Any:
    """
    La expresión tal como se escribió, pero presentable en LaTeX/MathML: el parser deja
    "1/3" como 1·3⁻¹ (se imprimiría "1 · 1/3"). Convierte entero/entero en fracción y
    quita los factores 1, sin evaluar el resto (2+2 sigue siendo 2+2).
    """
    def es_fraccion(e):
        return (e.is_Mul and len(e.args) == 2 and e.args[0].is_Integer
                and e.args[1].is_Pow and e.args[1].base.is_Integer and e.args[1].exp == -1)

    try:
        with sympy.evaluate(False):
            expr = expr.replace(es_fraccion, lambda e: sympy.Rational(e.args[0], e.args[1].base))
            return expr.replace(lambda e: e.is_Mul and len(e.args) == 2 and e.args[0] == 1,
                                lambda e: e.args[1])
    except Exception:
        return expr


@dataclass
class ResultadoOperacion:
    operacion: str                      # clave de OPERACIONES
    entrada: str                        # lo que escribió el usuario
    texto: str                          # informe accesible, en el idioma actual
    valor: Any = None                   # resultado como objeto SymPy (None si no aplica)
    es_error: bool = False
    parametros: Dict[str, Any] = field(default_factory=dict)  # variable, tendencia, orden, método
    expresion: Any = None               # entrada interpretada por el parser (si se pudo)
    # El problema como objeto SymPy sin evaluar (Derivative, Integral, Limit, lista de Eq...),
    # para exportarlo como en un libro: "planteamiento = resultado"
    planteamiento: Any = None
    # Integral indefinida: el valor no incluye "+ C"; se añade al mostrarlo (así queda al final)
    mas_constante: bool = False
    idioma: str = field(default_factory=idioma_actual)
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


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

    def _expresion(self, texto: str) -> Optional[Any]:
        """La entrada interpretada (para exportarla en LaTeX/MathML), o None si no se puede."""
        try:
            return self.parser_comun.parsear(texto)
        except Exception:
            return None

    def _ecuaciones(self, lineas: List[str]) -> Optional[List[Any]]:
        """Las líneas de un sistema como ecuaciones SymPy sin evaluar (para exportar)."""
        try:
            ecuaciones = []
            for linea in lineas:
                if not linea.strip():
                    continue
                izq, der = linea.split("=") if "=" in linea else (linea, "0")
                ecuaciones.append(sympy.Eq(_normal(self.parser_comun.parsear(izq)),
                                           _normal(self.parser_comun.parsear(der)), evaluate=False))
            return ecuaciones or None
        except Exception:
            return None

    # ==========================================
    # 1. API DE OBJETOS (usada por la interfaz)
    # ==========================================

    def _aritmetica(self, operacion: str, dto, entrada: str) -> ResultadoOperacion:
        return ResultadoOperacion(
            operacion=operacion, entrada=entrada, texto=self.aritmetica.renderizar(dto),
            valor=dto.resultado if dto.es_exitoso else None, es_error=not dto.es_exitoso,
            expresion=dto.expresion_original if dto.es_exitoso else None,
            planteamiento=_legible(dto.expresion_original) if dto.es_exitoso else None,
        )

    def evaluar(self, expresion: str) -> ResultadoOperacion:
        return self._aritmetica("evaluar", self.aritmetica.evaluar(expresion), expresion)

    def simplificar(self, expresion: str) -> ResultadoOperacion:
        return self._aritmetica("simplificar", self.aritmetica.simplificar(expresion), expresion)

    def factorizar(self, expresion: str) -> ResultadoOperacion:
        return self._aritmetica("factorizar", self.aritmetica.factorizar(expresion), expresion)

    def _calculo(self, operacion: str, res, entrada: str, parametros: Dict[str, Any]) -> ResultadoOperacion:
        valor = planteamiento = None
        if res.es_exitoso:
            var = res.variable
            if operacion == "integrar":
                planteamiento = sympy.Integral(_normal(res.expr_sympy), var)
            elif operacion == "derivada_n":
                planteamiento = sympy.Derivative(_normal(res.expr_sympy), (var, parametros["orden"]))
            else:
                planteamiento = sympy.Derivative(_normal(res.expr_sympy), var)
            valor = res.resultado
            if res.variable is not None:
                parametros = {**parametros, "variable": str(res.variable)}
        return ResultadoOperacion(
            operacion=operacion, entrada=entrada, texto=self.calculo.RenderizarTexto(res),
            valor=valor, es_error=not res.es_exitoso, parametros=parametros, expresion=res.expr_sympy,
            planteamiento=planteamiento, mas_constante=res.es_exitoso and res.requiere_constante,
        )

    def derivar(self, expresion: str, variable: Optional[str] = None) -> ResultadoOperacion:
        res = self.calculo.CalcularDerivada(expresion, variable=variable)
        return self._calculo("derivar", res, expresion, {"variable": variable})

    def derivada_enecima(self, expresion: str, variable: str, orden: int) -> ResultadoOperacion:
        res = self.calculo.DerivadaEnecima(expresion, variable, orden)
        return self._calculo("derivada_n", res, expresion, {"variable": variable, "orden": orden})

    def integrar(self, expresion: str, variable: Optional[str] = None) -> ResultadoOperacion:
        res = self.calculo.CalcularIntegral(expresion, variable=variable)
        return self._calculo("integrar", res, expresion, {"variable": variable})

    def limite(self, expresion: str, variable: Optional[str], tendencia: str) -> ResultadoOperacion:
        res = self.router.calcular(expresion, variable, tendencia)
        expr = self._expresion(expresion)
        planteamiento = None
        if not res.es_error and expr is not None:
            try:
                var = self.router._resolver_var(expr, variable)
                punto, direccion = self.router._parsear_tendencia(tendencia)
                lado = direccion or ("+-" if punto.is_finite else "+")
                planteamiento = sympy.Limit(_normal(expr), var, punto, dir=lado)
            except Exception:
                planteamiento = None
        return ResultadoOperacion(
            operacion="limite", entrada=expresion, texto=res.texto, valor=res.valor, es_error=res.es_error,
            parametros={"variable": variable, "tendencia": tendencia}, expresion=expr,
            planteamiento=planteamiento,
        )

    def sistema_gauss(self, lineas: List[str]) -> ResultadoOperacion:
        texto, valor, es_error = self.gauss.resolver(lineas)
        return ResultadoOperacion(operacion="gauss", entrada="\n".join(lineas), texto=texto,
                                  valor=valor, es_error=es_error, planteamiento=self._ecuaciones(lineas))

    def sistema_clasico(self, lineas: List[str], metodo: str) -> ResultadoOperacion:
        texto, valor, es_error = self.clasicos.resolver(lineas, metodo)
        return ResultadoOperacion(operacion="sistema_clasico", entrada="\n".join(lineas), texto=texto,
                                  valor=valor, es_error=es_error, parametros={"metodo": metodo},
                                  planteamiento=self._ecuaciones(lineas))

    def inversa(self, expresion_matriz: str) -> ResultadoOperacion:
        res = self.matrices.CalcularInversaCofactores(expresion_matriz)
        return ResultadoOperacion(
            operacion="inversa", entrada=expresion_matriz, texto=self.matrices.RenderizarInformeInversa(res),
            valor=res.matriz_inversa if res.es_posible else None, es_error=not res.es_posible,
            expresion=res.matriz_original,
            planteamiento=(sympy.Inverse(res.matriz_original)
                           if res.es_posible and res.matriz_original is not None and res.matriz_original.shape[0] > 1
                           else None),
        )

    # ==========================================
    # 2. API DE TEXTO (compatibilidad)
    # ==========================================

    def Evaluar(self, expresion):
        return self.evaluar(expresion).texto

    def Simplificar(self, expresion):
        return self.simplificar(expresion).texto

    def Factorizar(self, expresion):
        return self.factorizar(expresion).texto

    def ResolverSistemaGauss(self, lista_ecuaciones):
        return self.sistema_gauss(lista_ecuaciones).texto

    def ResolverSistemaEducativo(self, lista_ecuaciones, metodo):
        return self.sistema_clasico(lista_ecuaciones, metodo).texto

    def MatrizInversaCofactores(self, expresion_matriz):
        return self.inversa(expresion_matriz).texto

    def Derivar(self, expresion, variable=None):
        return self.derivar(expresion, variable).texto

    def DerivadaEnecima(self, expresion, variable, orden):
        return self.derivada_enecima(expresion, variable, orden).texto

    def Integrar(self, expresion, variable=None):
        return self.integrar(expresion, variable).texto

    def CalcularLimite(self, expresion, variable, tendencia):
        return self.limite(expresion, variable, tendencia).texto

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
