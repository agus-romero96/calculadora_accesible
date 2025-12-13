"""
Módulo especializado en Cálculo Diferencial e Integral.
Nivel: Universitario / Técnico.
Enfoque: Rigor simbólico, diagnóstico previo y justificación estratégica detallada.
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Any
import sympy
from sympy import Symbol

# Reglas para manualintegrate
from sympy.integrals.manualintegrate import (
    integral_steps,
    ConstantRule, PowerRule, AddRule, URule,
    PartsRule, TrigRule, ExpRule, ReciprocalRule,
    AlternativeRule, DontKnowRule, ConstantTimesRule
)

# --- CAPA DE DATOS (DTOs) ---

@dataclass(frozen=True)
class ResultadoCalculo:
    tipo_operacion: str      # "Derivada" o "Integral"
    funcion_original: Any
    variable: Symbol
    resultado: Any
    diagnostico_inicial: str # Análisis previo
    estrategia_nombre: str   # Nombre de la regla principal
    estrategia_razon: str    # Por qué se eligió esa regla
    pasos_detallados: str    # El desarrollo paso a paso
    advertencias: List[str] = field(default_factory=list) # Hipótesis

# --- MOTOR DE CÁLCULO ---

class Calculo:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    def _determinar_variable(self, expr, variable_sugerida: str):
        if variable_sugerida and variable_sugerida.strip():
            return Symbol(variable_sugerida)
        sym_vars = expr.free_symbols
        if len(sym_vars) == 1:
            return list(sym_vars)[0]
        else:
            return Symbol('x') 

    def _diagnosticar_funcion(self, expr, var) -> str:
        """
        ANÁLISIS PREVIO: Clasifica la función con mayor precisión.
        """
        caracteristicas = []
        
        # 1. Clasificación Algebraica
        if expr.is_polynomial(var):
            grado = sympy.degree(expr, gen=var)
            caracteristicas.append(f"Polinómica (Grado {grado})")
        elif expr.is_rational_function(var):
            caracteristicas.append("Racional (Cociente de polinomios)")
        
        # 2. Detección de Trascendentes
        if expr.has(sympy.sin, sympy.cos, sympy.tan, sympy.sec, sympy.csc, sympy.cot):
            caracteristicas.append("Trigonométrica")
        if expr.has(sympy.exp):
            caracteristicas.append("Exponencial")
        if expr.has(sympy.log):
            caracteristicas.append("Logarítmica")
        
        # 3. Estructura (Mejorado: Evita falsos positivos de Add/Mul)
        # Buscamos funciones aplicadas a otras funciones (e.g. sin(x^2))
        es_compuesta = False
        for atom in expr.atoms(sympy.Function):
            # Si el argumento de la función no es solo la variable (ej: sin(2x) o sin(x^2))
            if not any(arg == var for arg in atom.args):
                es_compuesta = True
                break
        
        if es_compuesta:
            caracteristicas.append("Estructura Compuesta (Regla de la Cadena)")

        if not caracteristicas:
            return "Función Algebraica General"
            
        return ", ".join(caracteristicas) + "."

    def _analizar_dominio_advertencias(self, expr, var) -> List[str]:
        """Detecta posibles problemas de dominio."""
        advertencias = []
        
        # Logaritmos
        if expr.has(sympy.log):
            advertencias.append("Hipótesis: El argumento del logaritmo debe ser positivo.")
        
        # Denominadores (Detectando potencias negativas reales)
        if any(p.is_Pow and p.exp.is_negative for p in expr.atoms(sympy.Pow)):
            advertencias.append(f"Hipótesis: El denominador debe ser distinto de cero ({var} ≠ 0).")
            
        return advertencias

    # ==========================================
    # SECCIÓN: DERIVADAS
    # ==========================================

    def derivar(self, expresion: str, variable: str = None) -> str:
        try:
            expr = self.parser.parsear(expresion)
            var_symbol = self._determinar_variable(expr, variable)

            # 1. Diagnóstico
            diagnostico = self._diagnosticar_funcion(expr, var_symbol)

            # 2. Análisis de Regla (Estrategia)
            regla_nom, regla_razon = self._justificar_regla_derivada(expr, var_symbol)
            
            # 3. Pasos Detallados (Simulados para mayor pedagogía)
            pasos_texto = self._generar_pasos_derivada(expr, var_symbol, regla_nom)

            # 4. Cálculo Exacto
            resultado = sympy.diff(expr, var_symbol)
            
            # 5. Advertencias
            advertencias = self._analizar_dominio_advertencias(expr, var_symbol)

            res_obj = ResultadoCalculo(
                tipo_operacion="Derivada",
                funcion_original=expr,
                variable=var_symbol,
                resultado=resultado,
                diagnostico_inicial=diagnostico,
                estrategia_nombre=regla_nom,
                estrategia_razon=regla_razon,
                pasos_detallados=pasos_texto,
                advertencias=advertencias
            )

            return self._formatear_salida(res_obj)

        except Exception as e:
            return f"Error al derivar: {str(e)}"

    def _justificar_regla_derivada(self, expr, var) -> Tuple[str, str]:
        """Devuelve (Nombre, Razón)."""
        if not expr.has(var):
            return "Regla de la Constante", "La expresión no varía con respecto a la variable."
        
        if expr.is_Add:
            return "Linealidad (Suma)", "La derivada se distribuye en cada término."
        
        if expr.is_Mul:
            # Check si es constante * funcion
            args_var = [a for a in expr.args if a.has(var)]
            if len(args_var) == 1:
                return "Múltiplo Constante", "Se extrae el factor constante y se deriva la función."
            return "Regla del Producto (Leibniz)", "Multiplicación de funciones variables: (uv)' = u'v + uv'."
        
        if expr.is_Pow:
            base, exp = expr.as_base_exp()
            if base == var and exp.is_constant():
                return "Regla de la Potencia", "Variable elevada a constante: n·x^(n-1)."
            if base.has(var) and exp.is_constant():
                return "Regla de la Cadena (Potencia)", "Función elevada a constante: n·u^(n-1) · u'."
            if base.is_constant() and exp.has(var):
                return "Regla Exponencial General", "Base constante elevada a función: a^u · ln(a) · u'."
        
        if isinstance(expr, sympy.exp):
            return "Exponencial Natural", "La derivada de e^x es ella misma."
            
        # Detección de composición
        if any(arg.has(var) for arg in expr.args):
             return "Regla de la Cadena", "Composición de funciones f(g(x)): f'(g(x)) · g'(x)."

        return "Derivación Directa", "Regla elemental de tabla."

    def _generar_pasos_derivada(self, expr, var, regla_detectada) -> str:
        """
        Genera una explicación estructurada del primer paso lógico.
        No hace toda la derivada paso a paso recursiva (muy complejo), 
        pero explica el desglose inicial.
        """
        pasos = []
        
        if "Suma" in regla_detectada:
            terminos = expr.args
            pasos.append("Desglosamos la suma:")
            for t in terminos:
                der_t = sympy.diff(t, var)
                pasos.append(f"  d/d{var}({t}) = {der_t}")
                
        elif "Producto" in regla_detectada:
            # Intentamos identificar u y v (simplificado a 2 términos principales)
            args_var = [a for a in expr.args if a.has(var)]
            if len(args_var) >= 2:
                u = args_var[0]
                v = sympy.Mul(*args_var[1:]) # El resto es v
                pasos.append("Aplicando (u·v)' = u'·v + u·v':")
                pasos.append(f"  u = {u}  =>  u' = {sympy.diff(u, var)}")
                pasos.append(f"  v = {v}  =>  v' = {sympy.diff(v, var)}")
        
        elif "Cociente" in regla_detectada or (expr.is_Mul and any(p.is_Pow and p.exp.is_negative for p in expr.atoms(sympy.Pow))):
             # SymPy ve cocientes como multiplicaciones con potencia negativa, es difícil de detectar "Cociente" puro a veces
             pass 

        elif "Cadena" in regla_detectada:
            # Intento heurístico de identificar externa e interna
            if expr.is_Pow:
                base, exp = expr.as_base_exp()
                pasos.append("Aplicando regla de potencia generalizada:")
                pasos.append(f"  1. Bajar exponente: {exp} * ({base})^({exp-1})")
                pasos.append(f"  2. Multiplicar por derivada interna: d/d{var}({base})")
            elif isinstance(expr, sympy.Function):
                func = type(expr)
                arg = expr.args[0]
                pasos.append(f"Derivada de función externa {func.__name__} multiplicada por interna:")
                pasos.append(f"  d/d{var}({arg}) = {sympy.diff(arg, var)}")

        if not pasos:
            pasos.append("Aplicación directa de la fórmula correspondiente.")
            
        return "\n".join(pasos)

    # ==========================================
    # SECCIÓN: INTEGRALES
    # ==========================================

    def integrar(self, expresion: str, variable: str = None) -> str:
        try:
            expr = self.parser.parsear(expresion)
            var_symbol = self._determinar_variable(expr, variable)
            
            diagnostico = self._diagnosticar_funcion(expr, var_symbol)
            advertencias = self._analizar_dominio_advertencias(expr, var_symbol)

            estrategia_nom = "Integración Directa"
            estrategia_razon = "Primitiva inmediata."
            pasos_texto = ""
            
            try:
                pasos_obj = integral_steps(expr, var_symbol)
                if pasos_obj:
                    estrategia_nom, estrategia_razon = self._analizar_estrategia_integral(pasos_obj)
                    pasos_texto = self._pasos_a_texto(pasos_obj)
                    
                    # Detectar DontKnow
                    if "Método Numérico" in estrategia_nom:
                        advertencias.append("Aviso: No se encontró un método analítico estándar (DontKnowRule).")
                else:
                    pasos_texto = "Aplicación de tablas estándar."
            except Exception:
                pasos_texto = "Método algorítmico avanzado (Risch)."

            resultado = sympy.integrate(expr, var_symbol)
            
            # Post-análisis del resultado
            if "Integral" in str(resultado):
                advertencias.append("Resultado no elemental: La integral no tiene solución cerrada simple.")

            res_obj = ResultadoCalculo(
                tipo_operacion="Integral Indefinida",
                funcion_original=expr,
                variable=var_symbol,
                resultado=f"{resultado} + C",
                diagnostico_inicial=diagnostico,
                estrategia_nombre=estrategia_nom,
                estrategia_razon=estrategia_razon,
                pasos_detallados=pasos_texto,
                advertencias=advertencias
            )
            
            return self._formatear_salida(res_obj)

        except Exception as e:
            return f"Error al integrar: {str(e)}"

    def _analizar_estrategia_integral(self, rule) -> Tuple[str, str]:
        """Determina la estrategia dominante y el porqué."""
        if isinstance(rule, URule):
            return "Sustitución (Cambio de Variable)", \
                   f"Se identifica la derivada interna. Cambio: u = {rule.u_func}."
        
        if isinstance(rule, PartsRule):
            return "Integración por Partes", \
                   "Producto de funciones de distinta naturaleza (ej: x*e^x)."
        
        if isinstance(rule, TrigRule):
            return "Identidades Trigonométricas", "Simplificación necesaria mediante identidades."

        if isinstance(rule, AddRule):
            return "Linealidad", "Separación en sumas más sencillas."
            
        if isinstance(rule, ReciprocalRule):
            return "Regla del Logaritmo", "Forma 1/x -> ln|x|."
            
        if isinstance(rule, ExpRule):
            return "Exponencial", "Forma e^x."

        if isinstance(rule, DontKnowRule):
            return "Método Numérico / Aproximado", "No se detecta patrón elemental."

        return "Reglas Básicas", "Ajuste a tabla de integración."

    def _pasos_a_texto(self, rule, nivel=0) -> str:
        """Renderiza los pasos recursivos."""
        if not rule: return ""
        indent = "  " * nivel
        texto = ""

        if isinstance(rule, URule):
            texto += f"{indent}► SUSTITUCIÓN: u = {rule.u_func}  ->  du = {rule.constant} dx\n"
            texto += self._pasos_a_texto(rule.substep, nivel + 1)
        
        elif isinstance(rule, PartsRule):
            texto += f"{indent}► POR PARTES: u = {rule.u}, dv = {rule.dv}\n"
            texto += f"{indent}  Formula: uv - ∫v du\n"
            texto += self._pasos_a_texto(rule.second_step, nivel + 1)
            
        elif isinstance(rule, AddRule):
            texto += f"{indent}• Linealidad (separar términos):\n"
            for substep in rule.substeps:
                texto += self._pasos_a_texto(substep, nivel + 1)
        
        elif isinstance(rule, PowerRule):
            texto += f"{indent}• Potencia: ∫ x^{rule.exp} dx = x^{rule.exp+1}/{rule.exp+1}\n"
        
        elif isinstance(rule, ConstantTimesRule):
            texto += f"{indent}• Extraer constante {rule.constant}\n"
            texto += self._pasos_a_texto(rule.substep, nivel + 1)
            
        elif isinstance(rule, ReciprocalRule):
            texto += f"{indent}• Logaritmo: ∫ 1/{rule.base} dx = ln|{rule.base}|\n"
            
        elif isinstance(rule, ExpRule):
            texto += f"{indent}• Exponencial: ∫ {rule.base}^{rule.exp} dx\n"

        elif isinstance(rule, DontKnowRule):
            texto += f"{indent}• [!] Paso no elemental detectado.\n"

        else:
            nombre = type(rule).__name__.replace("Rule", "")
            texto += f"{indent}• Regla: {nombre}\n"
            
        return texto

    def _formatear_salida(self, res: ResultadoCalculo) -> str:
        """Renderizador de texto accesible."""
        txt = []
        txt.append(f"CÁLCULO: {res.tipo_operacion.upper()}")
        txt.append(f"Función: {res.funcion_original}")
        txt.append(f"Variable: {res.variable}\n")
        
        txt.append("1. ANÁLISIS PREVIO")
        txt.append(f"   Tipo: {res.diagnostico_inicial}")
        if res.advertencias:
            for adv in res.advertencias:
                txt.append(f"   [!] {adv}")
        
        txt.append("\n2. ESTRATEGIA")
        txt.append(f"   Método: {res.estrategia_nombre}")
        txt.append(f"   Por qué: {res.estrategia_razon}")
        
        txt.append("\n3. DESARROLLO")
        if res.pasos_detallados:
            txt.append(res.pasos_detallados)
        
        txt.append("\n" + "="*30)
        txt.append(f"RESULTADO FINAL: {res.resultado}")
        
        return "\n".join(txt)

    # --- Derivada N-ésima ---
    def derivada_enecima(self, expresion: str, variable: str, orden: int) -> str:
        try:
            if orden < 1: return "El orden debe ser mayor a 0."
            expr = self.parser.parsear(expresion)
            var_sym = self._determinar_variable(expr, variable)
            
            txt = [f"DERIVADAS SUCESIVAS (Orden {orden})", f"f(x) = {expr}"]
            curr = expr
            for i in range(1, orden+1):
                curr = sympy.diff(curr, var_sym)
                txt.append(f"Derivada {i}: {curr}")
            return "\n".join(txt)
        except Exception as e: return str(e)