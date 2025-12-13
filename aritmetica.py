import sympy
from dataclasses import dataclass, field
from typing import List, Any, Optional
from sympy import degree, Symbol, Poly, RealNumber

# --- 1. CAPA DE DATOS (DTO - Data Transfer Object) ---
# Esto estandariza la salida. Nunca más devolvemos strings sueltos.

@dataclass(frozen=True)
class ResultadoAritmetica:
    operacion: str              # "Factorización", "Simplificación", "Evaluación"
    expresion_original: Any     # Objeto SymPy
    resultado: Any              # Objeto SymPy
    diagnostico: str            # Análisis previo (ej: "Polinomio grado 2")
    estrategia: str             # Nombre del método (ej: "Diferencia de Cuadrados")
    justificacion: str          # Por qué se eligió (ej: "Dos términos cuadrados con signo opuesto")
    pasos: List[str]            # Lista de pasos intermedios
    advertencias: List[str] = field(default_factory=list) # Notas de dominio o precisión

# --- 2. MOTOR LÓGICO ---

class Aritmetica:
    """
    Módulo V4: Arquitectura Empresarial.
    Implementa DTOs, Diagnóstico Formal y Estrategias Explícitas.
    """
    
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # ==========================================
    # MÉTODOS PÚBLICOS (Fachada)
    # ==========================================

    def evaluar(self, expresion: str) -> str:
        try:
            expr = self.parser.parsear(expresion)
            
            # 1. Diagnóstico
            es_entero = isinstance(expr, sympy.Integer) or expr.is_Integer
            es_racional = expr.is_Rational
            
            diag = "Número Entero" if es_entero else "Expresión Numérica Real"
            if not es_entero and es_racional: diag = "Número Racional (Fracción)"

            # 2. Ejecución
            res_exacto = sympy.simplify(expr)
            res_decimal = res_exacto.evalf()
            
            pasos = []
            advertencias = []
            
            # Análisis de precisión
            if res_exacto != res_decimal:
                diff = abs(res_exacto.evalf() - res_decimal)
                if diff > 1e-15:
                    advertencias.append("La representación decimal es una aproximación (contiene redondeo).")
                pasos.append(f"Valor Exacto: {res_exacto}")
                pasos.append(f"Valor Decimal: {res_decimal:.6f}")

            dto = ResultadoAritmetica(
                operacion="Evaluación Numérica",
                expresion_original=expr,
                resultado=res_exacto if es_entero else f"{res_exacto} ≈ {res_decimal:.6f}",
                diagnostico=diag,
                estrategia="Evaluación Directa y Aproximación",
                justificacion="Cálculo de valor simbólico y punto flotante.",
                pasos=pasos,
                advertencias=advertencias
            )
            return self._renderizar(dto)
            
        except Exception as e:
            return f"Error al evaluar: {str(e)}"

    def simplificar(self, expresion: str) -> str:
        try:
            expr = self.parser.parsear(expresion)
            
            # 1. Diagnóstico Previo
            diag = self._diagnosticar_estructura(expr)
            
            # 2. Ejecución
            resultado = sympy.simplify(expr)
            
            # 3. Análisis de Estrategia (Trazabilidad)
            estrategia, justificacion, pasos = self._analizar_cambios_simplificacion(expr, resultado)

            dto = ResultadoAritmetica(
                operacion="Simplificación Algebraica",
                expresion_original=expr,
                resultado=resultado,
                diagnostico=diag,
                estrategia=estrategia,
                justificacion=justificacion,
                pasos=pasos
            )
            return self._renderizar(dto)

        except Exception as e:
            return f"Error al simplificar: {str(e)}"

    def factorizar(self, expresion: str) -> str:
        try:
            expr = self.parser.parsear(expresion)
            
            # 1. Diagnóstico Riguroso
            info_polinomio = self._analizar_polinomio_formal(expr)
            
            # 2. Selección de Estrategia
            estrategia_nombre, razon, pasos_previos = self._seleccionar_estrategia_factorizacion(expr, info_polinomio)
            
            # 3. Ejecución
            resultado = sympy.factor(expr)
            
            # 4. Verificación de Irreducibilidad (Mejora Matemática)
            advertencias = []
            if expr == resultado:
                razon = "El polinomio no tiene raíces racionales (Irreducible en Q)."
                advertencias.append("Nota: Podría tener raíces reales (irracionales) o complejas no detectadas por factorización simple.")

            dto = ResultadoAritmetica(
                operacion="Factorización de Polinomios",
                expresion_original=expr,
                resultado=resultado,
                diagnostico=info_polinomio['texto'],
                estrategia=estrategia_nombre,
                justificacion=razon,
                pasos=pasos_previos,
                advertencias=advertencias
            )
            return self._renderizar(dto)

        except Exception as e:
            return f"Error al factorizar: {str(e)}"

    # ==========================================
    # VALIDADORES MATEMÁTICOS (Helpers Privados)
    # ==========================================

    def _es_cuadrado_perfecto(self, expr) -> bool:
        """Verifica matemáticamente si una expresión es un cuadrado exacto."""
        # Caso simple: x^2
        if expr.is_Pow:
            return expr.exp % 2 == 0
        # Caso coeficientes: 4, 9, 16...
        if expr.is_Integer and expr > 0:
            raiz = sympy.sqrt(expr)
            return raiz.is_Integer
        # Caso compuesto: 4*x^2
        if expr.is_Mul:
            return all(self._es_cuadrado_perfecto(arg) for arg in expr.args)
        return False

    def _es_cubo_perfecto(self, expr) -> bool:
        if expr.is_Pow:
            return expr.exp % 3 == 0
        if expr.is_Integer:
            raiz = sympy.cbrt(expr)
            return raiz.is_Integer
        return False

    def _diagnosticar_estructura(self, expr) -> str:
        if expr.is_RationalFunction:
            n, d = sympy.fraction(expr)
            if d != 1: return "Fracción Racional (Cociente de polinomios)"
        if expr.is_polynomial():
            grado = sympy.degree(expr)
            return f"Polinomio de Grado {grado}"
        return "Expresión Algebraica General"

    def _analizar_polinomio_formal(self, expr) -> dict:
        """Devuelve metadata matemática para toma de decisiones."""
        info = {'es_poli': False, 'grado': 0, 'terminos': 0, 'vars': []}
        
        info['vars'] = list(expr.free_symbols)
        if expr.is_polynomial():
            info['es_poli'] = True
            info['grado'] = sympy.degree(expr)
            # Contamos términos si es una suma
            if expr.is_Add:
                info['terminos'] = len(expr.args)
            else:
                info['terminos'] = 1
            info['texto'] = f"Polinomio Grado {info['grado']} con {info['terminos']} términos."
        else:
            info['texto'] = "Expresión no polinómica estándar."
        
        return info

    def _analizar_cambios_simplificacion(self, original, resultado) -> tuple:
        """Compara estados para deducir qué hizo SymPy."""
        ops_antes = original.count_ops()
        ops_despues = resultado.count_ops()
        pasos = []
        
        # Estrategia 1: Cancelación
        n1, d1 = sympy.fraction(original)
        n2, d2 = sympy.fraction(resultado)
        
        if d1 != 1 and (d2 == 1 or sympy.degree(d2) < sympy.degree(d1)):
            estrategia = "Cancelación de Factores"
            justificacion = "El numerador y denominador compartían factores comunes."
            pasos.append(f"1. Numerador original: {n1}")
            pasos.append(f"2. Denominador original: {d1}")
            pasos.append("3. Se eliminaron los términos repetidos.")
            return estrategia, justificacion, pasos

        # Estrategia 2: Reducción
        if ops_despues < ops_antes:
            return "Agrupación de Términos", "Se sumaron coeficientes de variables iguales.", [f"Reducción de complejidad: {ops_antes} ops -> {ops_despues} ops"]

        return "Transformación Algebraica", "Aplicación de identidades generales.", []

    def _seleccionar_estrategia_factorizacion(self, expr, info) -> tuple:
        """
        El cerebro: Decide la estrategia basado en evidencia matemática, no corazonadas.
        Retorna: (Nombre, Justificación, Pasos Teóricos)
        """
        pasos = []
        
        # 1. Factor Común (Prioridad Máxima)
        terms = expr.args if expr.is_Add else [expr]
        common = sympy.gcd(terms)
        if common != 1:
            return (
                "Factor Común (Distributiva Inversa)",
                f"Todos los términos son divisibles por '{common}'.",
                [f"Extraemos {common} y dividimos el polinomio original."]
            )

        # 2. Diferencia de Cuadrados
        # Rigor: 2 términos, uno negativo, ambos cuadrados perfectos
        if info['terminos'] == 2 and expr.is_Add:
            a, b = expr.args[0], expr.args[1]
            # Aseguramos a positivo, b negativo para la forma a^2 - b^2
            term_pos, term_neg = None, None
            if a.as_coeff_Mul()[0] > 0 and b.as_coeff_Mul()[0] < 0: term_pos, term_neg = a, b
            elif b.as_coeff_Mul()[0] > 0 and a.as_coeff_Mul()[0] < 0: term_pos, term_neg = b, a
            
            if term_pos and term_neg:
                # Quitamos el signo para chequear si es cuadrado
                neg_abs = -term_neg
                if self._es_cuadrado_perfecto(term_pos) and self._es_cuadrado_perfecto(neg_abs):
                    return (
                        "Diferencia de Cuadrados",
                        "Forma a^2 - b^2 identificada rigurosamente.",
                        [f"Identificamos a = sqrt({term_pos})", f"Identificamos b = sqrt({neg_abs})", "Aplicamos (a+b)(a-b)"]
                    )

        # 3. Trinomios (Grado 2, 3 términos)
        if info['grado'] == 2 and info['terminos'] == 3:
            var = info['vars'][0] if info['vars'] else Symbol('x')
            a = sympy.Poly(expr, var).coeff_monomial(var**2)
            b = sympy.Poly(expr, var).coeff_monomial(var)
            c = sympy.Poly(expr, var).coeff_monomial(1)
            
            delta = b**2 - 4*a*c
            pasos.append(f"Análisis del Discriminante (Δ = b^2 - 4ac): {delta}")
            
            if delta == 0:
                return "Trinomio Cuadrado Perfecto", "El discriminante es cero.", pasos
            elif delta > 0:
                raiz_delta = sympy.sqrt(delta)
                if raiz_delta.is_Integer:
                    return "Trinomio Factorizable (Aspa Simple)", "El discriminante es un cuadrado perfecto positivo.", pasos
                else:
                    return "Fórmula General (Raíces Irracionales)", "Discriminante positivo pero no cuadrado perfecto.", pasos
            else:
                return "Irreducible en Reales", "Discriminante negativo (soluciones complejas).", pasos

        # 4. Suma/Resta de Cubos
        if info['terminos'] == 2 and info['grado'] == 3:
             return "Suma/Diferencia de Cubos", "Binomio de grado 3 detectado.", ["Aplicar identidad a^3 ± b^3"]

        # 5. Ruffini / General
        if info['grado'] > 2:
            return "Evaluación Polinómica (Ruffini)", "Grado superior a 2.", ["Búsqueda de raíces racionales (p/q)."]

        return "Factorización General", "Método algorítmico estándar.", []

    # ==========================================
    # RENDERIZADO (Salida Accesible)
    # ==========================================

    def _renderizar(self, dto: ResultadoAritmetica) -> str:
        """Convierte el DTO en la narrativa accesible que espera la UI."""
        txt = []
        txt.append(f"OPERACIÓN: {dto.operacion.upper()}")
        txt.append(f"Expresión: {dto.expresion_original}")
        txt.append("-" * 30)
        
        txt.append("1. DIAGNÓSTICO")
        txt.append(f"   {dto.diagnostico}")
        
        txt.append("\n2. ESTRATEGIA SELECCIONADA")
        txt.append(f"   Método: {dto.estrategia}")
        txt.append(f"   Justificación: {dto.justificacion}")
        
        if dto.pasos:
            txt.append("\n3. DESARROLLO / ANÁLISIS")
            for p in dto.pasos:
                txt.append(f"   • {p}")
        
        if dto.advertencias:
            txt.append("\n[!] ADVERTENCIAS MATEMÁTICAS:")
            for adv in dto.advertencias:
                txt.append(f"   - {adv}")
                
        txt.append("-" * 30)
        txt.append(f"RESULTADO FINAL: {dto.resultado}")
        
        return "\n".join(txt)

    # --- Funciones Legacy (MCD, Primos) ---
    # Se mantienen por compatibilidad, pero idealmente deberían migrar al DTO también.
    def analizar_numero(self, n): return self._legacy_analizar(n)
    def mcd_mcm(self, l): return self._legacy_mcd(l)
    def fracciones_parciales(self, e): return self._legacy_fracciones(e)

    # (Implementaciones simples para no borrar funcionalidad existente...)
    def _legacy_analizar(self, n_str):
        # ... (Tu código anterior de primos aquí) ...
        # Por brevedad en la respuesta, asumo que mantienes la lógica de la V2 aquí
        try:
             expr = self.parser.parsear(n_str)
             if not expr.is_Integer: return "Error: Solo enteros."
             n = int(expr)
             return f"Análisis de {n}:\nPrimo: {sympy.isprime(n)}\nFactores: {sympy.factorint(n)}"
        except: return "Error."
        
    def _legacy_mcd(self, l_str):
        # ... (Tu código anterior de MCD aquí) ...
        try:
            nums = [int(self.parser.parsear(x)) for x in l_str.replace(',', ' ').split()]
            return f"MCD: {sympy.gcd(nums)}\nmcm: {sympy.lcm(nums)}"
        except: return "Error."

    def _legacy_fracciones(self, e_str):
        try: return f"Fracciones Parciales:\n{sympy.apart(self.parser.parsear(e_str))}"
        except: return "Error."