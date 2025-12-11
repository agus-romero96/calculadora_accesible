"""
Módulo de operaciones matemáticas (Versión Híbrida Definitiva).
Combina la robustez de SymPy unificado con la pedagogía detallada original.
"""
import random
from sympy.polys.polyerrors import PolynomialError 
import sympy
from sympy import Symbol, Matrix, S
# Importaciones para el parser seguro y flexible
from sympy.parsing.sympy_parser import (
    parse_expr, 
    standard_transformations, 
    implicit_multiplication_application,
    convert_xor
)
# Importamos TODAS las reglas de integración manual para explicaciones
from sympy.integrals.manualintegrate import (
    integral_steps,
    ConstantRule, PowerRule, AddRule, URule,
    PartsRule, TrigRule, ExpRule, ReciprocalRule,
    AlternativeRule, DontKnowRule, ConstantTimesRule
)

class Algebra:
    """
    Motor matemático accesible.
    Mantiene explicaciones pedagógicas detalladas sobre un motor SymPy robusto.
    """

    def __init__(self):
        # Configuración para permitir "2x", "x^2", etc.
        self.transformations = (standard_transformations + 
                                (implicit_multiplication_application, convert_xor))

    def _parsear_seguro(self, expresion: str):
        """
        Convierte texto a objeto matemático corrigiendo errores comunes.
        """
        if not expresion or not expresion.strip():
            raise ValueError("La expresión está vacía.")
            
        # 1. Chequeo de paréntesis
        if expresion.count('(') != expresion.count(')'):
             raise ValueError("Error de sintaxis: Paréntesis desbalanceados.")

        # 2. Ajustes de texto para accesibilidad
        # Mapeos: ln -> log natural, log -> base 10
        txt = expresion.replace("log", "log_placeholder")
        txt = txt.replace("ln", "log") 
        txt = txt.replace("log_placeholder", "log/log(10)")
        
        try:
            # --- LA GRAN MEJORA AQUÍ ---
            # Usamos 'local_dict' para decirle a SymPy: 
            # "Si ves la letra 'e', significa el número E de Euler (sympy.E)"
            diccionario_simbolos = {'e': sympy.E}
            
            return parse_expr(txt, 
                              transformations=self.transformations,
                              local_dict=diccionario_simbolos)
                              
        except SyntaxError:
            raise ValueError("Error de escritura: Revise operadores.")
        except Exception as ex:
            raise ValueError(f"No se pudo interpretar la fórmula: {str(ex)}")

    def ResolverSistemaCramer(self, lista_ecuaciones: list) -> str:
        """
        Resuelve un sistema de ecuaciones lineales usando la Regla de Cramer.
        Ideal para pedagogía porque explica paso a paso usando determinantes.
        """
        try:
            # 1. Preparación (Igual que en Gauss)
            ecus_sympy = []
            todas_vars = set()
            
            for ecu in lista_ecuaciones:
                if not ecu.strip(): continue
                if "=" in ecu:
                    parts = ecu.split("=")
                    izq = self._parsear_seguro(parts[0])
                    der = self._parsear_seguro(parts[1])
                    eq = sympy.Eq(izq, der)
                else:
                    eq = sympy.Eq(self._parsear_seguro(ecu), 0)
                ecus_sympy.append(eq)
                todas_vars.update(eq.free_symbols)
            
            variables = sorted(list(todas_vars), key=lambda s: s.name)
            
            if len(ecus_sympy) != len(variables):
                return (f"Error: La Regla de Cramer solo funciona si el número de ecuaciones ({len(ecus_sympy)}) "
                        f"es igual al número de variables ({len(variables)}).")

            # 2. Obtener matrices A (coeficientes) y B (resultados)
            A, B = sympy.linear_eq_to_matrix(ecus_sympy, variables)
            det_sistema = sympy.simplify(A.det())
            
            pasos = [f"Sistema analizado para variables: {variables}"]
            pasos.append(f"1. Calculamos el Determinante del Sistema (Delta):\n   Det = {det_sistema}")
            
            if det_sistema == 0:
                return ("El determinante del sistema es 0. \n"
                        "La Regla de Cramer no se puede aplicar porque implicaría dividir por cero.\n"
                        "Use el método de Gauss-Jordan para ver si tiene infinitas soluciones o ninguna.")

            # 3. Iterar por cada variable calculando su determinante asociado
            soluciones = []
            pasos.append("\n2. Calculamos los determinantes individuales reemplazando columnas:")
            
            for i, var in enumerate(variables):
                # Crear matriz temporal reemplazando la columna i por el vector B
                # .col_insert inserta, así que primero borramos la columna vieja
                M_temp = A.copy()
                M_temp.col_del(i)
                M_temp.col_insert(i, B)
                
                det_var = sympy.simplify(M_temp.det())
                valor = sympy.simplify(det_var / det_sistema)
                
                pasos.append(f"   - Para {var}: Reemplazamos columna {i+1} por los resultados.")
                pasos.append(f"     Det({var}) = {det_var}")
                pasos.append(f"     {var} = Det({var}) / Delta = {det_var} / {det_sistema} = {valor}")
                
                soluciones.append(f"{var} = {valor}")

            return (f"Resolución por Regla de Cramer:\n"
                    f"Solución Única:\n" + "\n".join(soluciones) + "\n"
                    f"----------------------------------------\n"
                    f"Explicación Paso a Paso:\n" + "\n".join(pasos))

        except Exception as e:
            return f"Error en Cramer: {str(e)}"

    def ResolverSistemaEducativo2x2(self, lista_ecuaciones: list, metodo: str) -> str:
        """
        Resuelve sistemas 2x2 usando métodos de secundaria.
        Versión EDUCATIVA PREMIUM:
        - Corrige extracción de coeficientes (usa coeff correctamente).
        - Maneja constantes desordenadas (ej: x + 3 = y).
        - Explicaciones pedagógicas coherentes (no trucos).
        - Diagnóstico robusto de casos infinitos/imposibles.
        """
        try:
            # 1. Validación inicial
            if len(lista_ecuaciones) != 2:
                return "Error: Se requieren exactamente 2 ecuaciones."

            ecus = []
            vars_set = set()
            
            # --- PARSEO Y NORMALIZACIÓN ROBUSTA ---
            for txt in lista_ecuaciones:
                if not txt.strip(): continue
                
                # Parseo seguro con expansión
                if "=" in txt:
                    parts = txt.split("=")
                    izq = self._parsear_seguro(parts[0])
                    der = self._parsear_seguro(parts[1])
                    # Pasamos todo a la izquierda: lhs - rhs = 0
                    expr_raw = izq - der
                else:
                    expr_raw = self._parsear_seguro(txt)
                
                # Normalización crítica: expandir y simplificar
                expr = sympy.expand(expr_raw)
                
                # Validación de linealidad (Poly total degree)
                try:
                    poly = sympy.Poly(expr)
                    if not poly.is_zero and poly.total_degree() > 1:
                        return f"Error: La ecuación contiene términos no lineales (grado {poly.total_degree()})."
                except sympy.PolificationFailed:
                     return "Error: La ecuación contiene funciones no polinómicas (seno, log, etc)."
                
                # Reconstruimos la ecuación como Eq(expr, 0) para uso interno
                ecus.append(sympy.Eq(expr, 0))
                vars_set.update(expr.free_symbols)
            
            variables = sorted(list(vars_set), key=lambda s: s.name)
            
            # Caso degenerado: menos de 2 variables
            if len(variables) < 2:
                 sol = sympy.solve(ecus, dict=True)
                 if not sol: return "Sistema Incompatible (Sin solución)."
                 return f"Sistema simple resuelto (no requiere método 2x2):\n{sol}"
            
            # Si hay más de 2 variables, error
            if len(variables) > 2:
                return f"Error: El sistema tiene {len(variables)} variables. Solo se soportan 2 para métodos escolares."

            x, y = variables[0], variables[1]
            eq1, eq2 = ecus[0], ecus[1]

            # --- DIAGNÓSTICO ROUCHÉ-FROBENIUS CORREGIDO ---
            # Para linear_eq_to_matrix funcione bien, las ecuaciones deben ser lineales puras
            # Usamos las expresiones lhs directamente que ya son (ax + by + c)
            try:
                # Extraemos matriz A y B manualmente para evitar errores de constantes
                # Forma: ax + by + c = 0  ->  ax + by = -c
                coeffs = []
                consts = []
                for eq in [eq1, eq2]:
                    expr = eq.lhs
                    p = sympy.Poly(expr, x, y)
                    # coeff de x, coeff de y
                    # Nota: nth(1,0) es x^1 y^0, nth(0,1) es x^0 y^1
                    a = p.coeff_monomial(x)
                    b = p.coeff_monomial(y)
                    # Constante: todo lo que no tiene x ni y (término independiente)
                    # Restamos la parte con variables a la expresión original y simplificamos
                    c = expr.subs({x:0, y:0})
                    coeffs.append([a, b])
                    consts.append([-c]) # Al otro lado del igual
                
                A_mat = sympy.Matrix(coeffs)
                B_mat = sympy.Matrix(consts)
                
                rango_A = A_mat.rank()
                M_aumentada = A_mat.row_join(B_mat)
                rango_M = M_aumentada.rank()
                
                tipo_sistema = "UNICA"
                if rango_A < rango_M:
                    tipo_sistema = "INCOMPATIBLE"
                elif rango_A == rango_M:
                    if rango_A < 2:
                        tipo_sistema = "INDETERMINADO"
            except Exception:
                # Fallback seguro si falla el análisis matricial
                tipo_sistema = "UNICA"

            if tipo_sistema == "INCOMPATIBLE":
                return "El sistema es INCOMPATIBLE (No tiene solución).\nLas rectas son paralelas distintas."
            
            if tipo_sistema == "INDETERMINADO":
                return "El sistema es INDETERMINADO (Infinitas soluciones).\nLas ecuaciones son equivalentes (misma recta) o una es 0=0."

            # Solución final real para comprobación
            sol_final = sympy.solve((eq1, eq2), (x, y))
            val_x_final = sol_final[x]
            val_y_final = sol_final[y]

            # --- INICIO DE EXPLICACIÓN ---
            pasos = [f"Sistema Lineal 2x2. Variables: {x}, {y}"]
            # Mostramos las ecuaciones en forma bonita (ax + by = -c)
            # Reconstruimos visualmente
            def fmt_eq(eq_obj):
                expr = eq_obj.lhs
                const = expr.subs({x:0, y:0})
                vars_part = expr - const
                return f"{vars_part} = {-const}"
            
            pasos.append(f"Ec 1: {fmt_eq(eq1)}")
            pasos.append(f"Ec 2: {fmt_eq(eq2)}\n")

            # --- LÓGICA POR MÉTODO ---
            
            if metodo == "sustitucion":
                pasos.append("MÉTODO DE SUSTITUCIÓN:\n")
                
                # 1. Búsqueda inteligente de variable con coeficiente 1 o -1
                # Usamos Poly para extracción segura
                mejor_candidato = None
                
                candidatos = [(eq1, x, 1), (eq1, y, 1), (eq2, x, 2), (eq2, y, 2)]
                
                for ecu, var, idx in candidatos:
                    try:
                        p = sympy.Poly(ecu.lhs, var)
                        # coeff_monomial requiere monomio exacto, pero Poly(expr, var) lo trata como polinomio en var
                        # El coeficiente de var^1 es lo que buscamos
                        c = p.coeff_monomial(var)
                        if abs(c) == 1:
                            mejor_candidato = (ecu, var, idx)
                            break
                    except: continue
                
                if not mejor_candidato: mejor_candidato = (eq1, x, 1) # Default
                
                ecu_origen, var_despejada, idx_origen = mejor_candidato
                
                # Despeje simbólico
                res_despeje = sympy.solve(ecu_origen, var_despejada)[0]
                
                nom_origen = "primera" if idx_origen == 1 else "segunda"
                nom_destino = "segunda" if idx_origen == 1 else "primera"
                ecu_destino = eq2 if idx_origen == 1 else eq1
                var_otra = y if var_despejada == x else x

                pasos.append(f"1. Despejamos '{var_despejada}' de la {nom_origen} ecuación:")
                pasos.append(f"   {var_despejada} = {res_despeje}")
                
                pasos.append(f"\n2. Sustituimos en la {nom_destino} ecuación:")
                # Sustitución explicita
                eq_sust = ecu_destino.subs(var_despejada, res_despeje)
                pasos.append(f"   {eq_sust}") # Debería mostrar algo con una sola variable = 0
                
                pasos.append(f"\n3. Resolvemos la ecuación resultante para '{var_otra}':")
                # Aquí resolvemos la ecuación del paso intermedio, no usamos la final mágica
                val_otra_calc = sympy.solve(eq_sust, var_otra)[0]
                pasos.append(f"   {var_otra} = {val_otra_calc}")
                
                pasos.append(f"\n4. Reemplazamos en el despeje del paso 1:")
                val_desp_calc = res_despeje.subs(var_otra, val_otra_calc)
                pasos.append(f"   {var_despejada} = {val_desp_calc}")

            elif metodo == "igualacion":
                pasos.append("MÉTODO DE IGUALACIÓN:\n")
                
                # Intentamos despejar x en ambas
                var_objetivo = x
                try:
                    d1 = sympy.solve(eq1, x)[0]
                    d2 = sympy.solve(eq2, x)[0]
                except:
                    var_objetivo = y
                    try:
                        d1 = sympy.solve(eq1, y)[0]
                        d2 = sympy.solve(eq2, y)[0]
                    except:
                        return "Error: No se pudo despejar la misma variable en ambas ecuaciones."
                
                var_restante = y if var_objetivo == x else x
                
                pasos.append(f"1. Despejamos '{var_objetivo}' en ambas ecuaciones:")
                pasos.append(f"   De Ec 1: {var_objetivo} = {d1}")
                pasos.append(f"   De Ec 2: {var_objetivo} = {d2}")
                
                pasos.append(f"\n2. Igualamos las expresiones:")
                eq_igual = sympy.Eq(d1, d2)
                pasos.append(f"   {d1} = {d2}")
                
                pasos.append(f"\n3. Resolvemos para '{var_restante}':")
                val_res_calc = sympy.solve(eq_igual, var_restante)[0]
                pasos.append(f"   {var_restante} = {val_res_calc}")
                
                pasos.append(f"\n4. Reemplazamos para hallar '{var_objetivo}':")
                val_obj_calc = d1.subs(var_restante, val_res_calc)
                pasos.append(f"   {var_objetivo} = {val_obj_calc}")

            elif metodo == "reduccion":
                pasos.append("MÉTODO DE REDUCCIÓN (SUMA Y RESTA):\n")
                
                # Extracción robusta de coeficientes para X
                p1 = sympy.Poly(eq1.lhs, x, y)
                p2 = sympy.Poly(eq2.lhs, x, y)
                c1 = p1.coeff_monomial(x)
                c2 = p2.coeff_monomial(x)
                
                target_var = x
                other_var = y
                
                # Caso degenerado: Si coeficientes de x son 0, cambiamos a y
                if c1 == 0 and c2 == 0:
                    target_var = y
                    other_var = x
                    c1 = p1.coeff_monomial(y)
                    c2 = p2.coeff_monomial(y)
                    pasos.append("Nota: Como no hay 'x', eliminaremos 'y'.")
                
                # Caso mixto: Si uno es cero, reducción es trivial (es sustitución directa)
                if c1 == 0 or c2 == 0:
                    pasos.append(f"Nota: El coeficiente de {target_var} es cero en una ecuación.")
                    pasos.append("Esto simplifica el proceso a un despeje directo.")
                    # Fallback a lógica genérica de solve para este caso raro
                    val_t = val_x_final if target_var == x else val_y_final
                    val_o = val_y_final if target_var == x else val_x_final
                else:
                    # CASO ESTÁNDAR DE REDUCCIÓN
                    pasos.append(f"1. Coeficientes de '{target_var}': {c1} y {c2}.")
                    m1 = c2
                    m2 = -c1
                    
                    # Optimización visual: simplificar signos (si m1 y m2 tienen divisor común)
                    # gcd = sympy.gcd(m1, m2) ... (opcional, dejamos así por seguridad)

                    pasos.append(f"2. Multiplicamos Ec 1 por ({m1}) y Ec 2 por ({m2}):")
                    
                    # Ecuaciones transformadas (lhs)
                    e1_new = sympy.expand(eq1.lhs * m1)
                    e2_new = sympy.expand(eq2.lhs * m2)
                    
                    # Formato bonito = const
                    def fmt_poly(p):
                        c = p.subs({x:0, y:0})
                        return f"{p-c} = {-c}"

                    pasos.append(f"   {fmt_poly(e1_new)}")
                    pasos.append(f"   {fmt_poly(e2_new)}")
                    
                    pasos.append(f"\n3. Sumamos las ecuaciones (se elimina '{target_var}'):")
                    suma = sympy.simplify(e1_new + e2_new)
                    # Al sumar, debería quedar: term_other + const = 0
                    
                    pasos.append(f"   {fmt_poly(suma)}") # ej: 5y = 10
                    
                    # Resolver paso intermedio
                    val_o = sympy.solve(suma, other_var)[0]
                    pasos.append(f"   {other_var} = {val_o}")
                    
                    pasos.append(f"\n4. Reemplazamos en la Ec 1 original:")
                    eq_final = eq1.subs(other_var, val_o)
                    pasos.append(f"   {fmt_eq(eq_final)}")
                    val_t = sympy.solve(eq_final, target_var)[0]
                    pasos.append(f"   {target_var} = {val_t}")

            else:
                return "Método desconocido."

            return (f"Resultado por {metodo.capitalize()}:\n"
                    f"{x} = {val_x_final}\n{y} = {val_y_final}\n"
                    f"--------------------------------\n"
                    f"{chr(10).join(pasos)}")

        except Exception as e:
            return f"Error en método educativo: {str(e)}"

    def ResolverSistemaPasos(self, lista_ecuaciones: list) -> str:
        """
        Resuelve sistemas lineales por Gauss-Jordan.
        Versión V8 FINAL (Producción):
        - Verificación probabilística robusta para soluciones infinitas.
        - Arquitectura híbrida: Pasos pedagógicos + Verdad matemática (RREF).
        - Detección de errores simbólicos mejorada.
        """
        
        # --- Helper: Cero robusto ---
        def _es_cero_seguro(expr, tries=5):
            try:
                e = sympy.simplify(expr)
                if e.is_Number: return e == 0
                check = e.equals(0)
                if check is not None: return check
                
                # Semilla local para consistencia entre ejecuciones del mismo paso
                rng = random.Random(42) 
                syms = list(e.free_symbols)
                if not syms: return abs(float(sympy.N(e))) < 1e-10
                
                for _ in range(tries):
                    # Probamos enteros aleatorios
                    subs = {s: rng.randint(-10, 10) for s in syms}
                    val = e.evalf(subs=subs)
                    # Si al evaluar da un número real distinto de cero, es seguro que no es cero
                    if val.is_Number and abs(val) > 1e-9: 
                        return False
                return True # Si pasa todas las pruebas, asumimos cero
            except Exception: 
                return False # Ante error de evaluación, asumimos no-cero para evitar divisiones fatales

        try:
            # --- FASE 1: PLANTEAMIENTO ---
            pasos = ["=== FASE 1: PLANTEAMIENTO DEL SISTEMA ==="]
            
            ecus_sympy = []
            todas_vars = set()
            ecus_originales_para_verificar = [] 
            
            for txt in lista_ecuaciones:
                if not txt.strip(): continue
                try:
                    if "=" in txt:
                        parts = txt.split("=")
                        izq = self._parsear_seguro(parts[0])
                        der = self._parsear_seguro(parts[1])
                        ecus_originales_para_verificar.append(sympy.Eq(izq, der))
                        eq = sympy.Eq(sympy.expand(izq), sympy.expand(der))
                    else:
                        orig = self._parsear_seguro(txt)
                        ecus_originales_para_verificar.append(sympy.Eq(orig, 0))
                        eq = sympy.Eq(sympy.expand(orig), 0)
                    
                    # Validación Linealidad
                    expr = eq.lhs - eq.rhs
                    poly = sympy.Poly(expr)
                    if poly.total_degree() > 1:
                        return f"Error: Ecuación no lineal detectada: {eq}"
                
                except PolynomialError:
                     return "Error: Ecuación con funciones no polinómicas."
                except Exception as e_parse:
                     return f"Error de sintaxis en la ecuación '{txt}': {str(e_parse)}"

                ecus_sympy.append(eq)
                todas_vars.update(eq.free_symbols)
            
            variables = sorted(list(todas_vars), key=lambda s: s.name)
            if not variables: return "Error: No se detectaron variables."

            pasos.append(f"Variables identificadas: {variables}")
            
            # Construcción Matrices
            try:
                A_orig, B_orig = sympy.linear_eq_to_matrix(ecus_sympy, variables)
                # Forzar racionales para evitar errores de punto flotante (0.333 vs 1/3)
                convertir_rat = lambda e: sympy.nsimplify(e, rational=True) if e.is_Float else e
                A_orig = A_orig.applyfunc(convertir_rat)
                B_orig = B_orig.applyfunc(convertir_rat)
                
                M_truth = A_orig.row_join(B_orig).as_mutable()
                M = M_truth.copy() 
            except Exception as e_matriz:
                return f"Error construyendo la matriz del sistema: {str(e_matriz)}"

            filas, columnas = M.shape
            pasos.append(f"\nMatriz Aumentada Inicial:\n{self._matriz_a_texto(M)}")
            
            # --- FASE 2: TRANSFORMACIONES (GAUSS-JORDAN) ---
            pasos.append("\n=== FASE 2: REDUCCIÓN (MÉTODO GAUSS-JORDAN) ===")
            
            pivot_row = 0
            MAX_PASOS = 200
            contador_pasos = 0
            
            for col in range(len(variables)):
                if pivot_row >= filas: break
                if contador_pasos > MAX_PASOS: 
                    pasos.append("... (Se omiten pasos restantes por seguridad) ...")
                    break

                # Buscar Pivote
                pivot_found_row = None
                for r in range(pivot_row, filas):
                    if not _es_cero_seguro(M[r, col]):
                        pivot_found_row = r
                        break
                
                if pivot_found_row is None: continue 
                
                # Swap
                if pivot_found_row != pivot_row:
                    M.row_swap(pivot_row, pivot_found_row)
                    pasos.append(f"Paso: Intercambio Fila {pivot_row+1} <-> Fila {pivot_found_row+1}.")
                    pasos.append(self._matriz_a_texto(M))
                    contador_pasos += 1
                
                # Normalizar
                pivot_val = sympy.simplify(M[pivot_row, col])
                if pivot_val != 1:
                    M.row_op(pivot_row, lambda v, j: sympy.expand(v / pivot_val))
                    pasos.append(f"Paso: Normalizar Fila {pivot_row+1} (Dividir entre {pivot_val}).")
                    pasos.append(self._matriz_a_texto(M))
                    contador_pasos += 1
                
                # Eliminación
                hay_cambios = False
                for r in range(filas):
                    if r != pivot_row:
                        factor = M[r, col]
                        if not _es_cero_seguro(factor):
                            factor_simp = sympy.simplify(factor)
                            M.row_op(r, lambda v, j: sympy.expand(v - factor_simp * M[pivot_row, j]))
                            pasos.append(f"Paso: Fila {r+1} - ({factor_simp}) * Fila {pivot_row+1}.")
                            hay_cambios = True
                            contador_pasos += 1
                
                if hay_cambios:
                    pasos.append(self._matriz_a_texto(M))
                
                pivot_row += 1

            # --- FASE 3: INTERPRETACIÓN Y RESULTADO (Fuente: RREF) ---
            M_rref, pivots_indices = M_truth.rref()
            col_b = columnas - 1
            indices_basicas = [c for c in pivots_indices if c < len(variables)]
            indices_libres = [c for c in range(len(variables)) if c not in indices_basicas]
            
            inconsistente = False
            if col_b in pivots_indices:
                fila_inc = pivots_indices.index(col_b)
                parte_A_ceros = all(_es_cero_seguro(M_rref[fila_inc, j]) for j in range(len(variables)))
                if parte_A_ceros and not _es_cero_seguro(M_rref[fila_inc, col_b]):
                    inconsistente = True

            msg_resultado = ""
            # Diccionario para verificación: mapea Variable -> Valor (o Expresión evaluada)
            diccionario_prueba = {} 
            es_infinita = False

            if inconsistente:
                msg_resultado = "RESULTADO: ¡Sistema Inconsistente!\nNo existe solución común para todas las ecuaciones."
            
            elif len(indices_libres) == 0:
                # Solución Única
                msg_resultado = "RESULTADO: Solución Única.\n"
                lista_sol = []
                for i, var_idx in enumerate(indices_basicas):
                    var_name = variables[var_idx]
                    valor = M_rref[i, col_b]
                    lista_sol.append(f"{var_name} = {valor}")
                    diccionario_prueba[var_name] = valor 
                msg_resultado += "\n".join(lista_sol)
                
            else:
                # Infinitas Soluciones
                es_infinita = True
                msg_resultado = "RESULTADO: Sistema Compatible Indeterminado (Infinitas Soluciones).\n"
                msg_resultado += f"Variables libres: {[variables[i] for i in indices_libres]}\n"
                
                # Parámetros t0, t1...
                params = sympy.symbols(f"t0:{len(indices_libres)}")
                if len(indices_libres) == 1: params = [sympy.Symbol('t')]
                
                # Vectores P y v
                vec_P = [sympy.Integer(0)] * len(variables)
                vectores_v = [[sympy.Integer(0)] * len(variables) for _ in range(len(indices_libres))]
                mapa_filas = {col: row for row, col in enumerate(pivots_indices) if col < len(variables)}
                
                for var_idx in indices_basicas:
                    if var_idx in mapa_filas:
                        fila = mapa_filas[var_idx]
                        vec_P[var_idx] = M_rref[fila, col_b]
                
                for i_param, idx_libre in enumerate(indices_libres):
                    vectores_v[i_param][idx_libre] = sympy.Integer(1)
                    for var_idx in indices_basicas:
                        if var_idx in mapa_filas:
                            fila = mapa_filas[var_idx]
                            coef = M_rref[fila, idx_libre]
                            if not _es_cero_seguro(coef):
                                vectores_v[i_param][var_idx] = -coef

                # Texto Paramétrico
                txt_vec = f"{list(sympy.Matrix(vec_P))}"
                for i, v_list in enumerate(vectores_v):
                    txt_vec += f" + {params[i]}*{list(sympy.Matrix(v_list))}"
                
                msg_resultado += "\nEcuaciones Paramétricas:\n"
                for i, var in enumerate(variables):
                    expr = vec_P[i]
                    for j, v_vec in enumerate(vectores_v):
                        expr += params[j] * v_vec[i]
                    msg_resultado += f"{var} = {expr}\n"
                
                msg_resultado += f"\nForma Vectorial:\nX = {txt_vec}\n(Donde t son números reales)."

                # Generamos valores de prueba aleatorios para verificar
                # No usamos t=1 fijo, sino valores al azar para evitar falsos positivos
                rng_verif = random.Random() # Sin semilla fija para variar prueba si se repite
                vals_params = [rng_verif.randint(-5, 5) for _ in params]
                
                msg_resultado += f"\n[Nota interna: Verificando con parámetros {dict(zip(params, vals_params))}...]"
                
                # Construimos el punto de prueba sustituyendo los parámetros
                for i, var in enumerate(variables):
                    val_prueba = vec_P[i]
                    for j, v_vec in enumerate(vectores_v):
                        val_prueba += v_vec[i] * vals_params[j]
                    diccionario_prueba[var] = val_prueba

            # --- FASE 4: VERIFICACIÓN AUTOMÁTICA ---
            msg_verificacion = ""
            if diccionario_prueba and not inconsistente:
                msg_verificacion = "\n\n=== FASE 4: VERIFICACIÓN ==="
                if es_infinita:
                    msg_verificacion += "\nProbamos con un punto aleatorio de la solución (sustituyendo t):\n"
                    msg_verificacion += f"Valores usados: {diccionario_prueba}\n"
                else:
                    msg_verificacion += "\nSustituimos los valores encontrados en las ecuaciones originales:\n"
                
                todas_correctas = True
                for i, eq_orig in enumerate(ecus_originales_para_verificar):
                    try:
                        izq_val = eq_orig.lhs.subs(diccionario_prueba)
                        der_val = eq_orig.rhs.subs(diccionario_prueba)
                        
                        # Usamos simplify para comparar simbólicamente si es necesario
                        diff = sympy.simplify(izq_val - der_val)
                        es_correcto = _es_cero_seguro(diff)
                        
                        estado = "CORRECTO" if es_correcto else "FALLO"
                        if not es_correcto: todas_correctas = False
                        
                        msg_verificacion += f"Ec {i+1}: {izq_val} = {der_val} -> {estado}\n"
                    except Exception as e_verif:
                        msg_verificacion += f"Ec {i+1}: Error verificando ({str(e_verif)})\n"
                        todas_correctas = False
                
                if todas_correctas:
                    msg_verificacion += ">>> Conclusión: La solución satisface el sistema perfectamente."
                else:
                    msg_verificacion += ">>> Advertencia: Alguna ecuación no verificó (posible error numérico)."

            texto_final = (f"{msg_resultado}"
                           f"{msg_verificacion}\n"
                           f"----------------------------------------\n"
                           f"HISTORIAL DETALLADO:\n{chr(10).join(pasos)}")
            
            return texto_final

        except Exception as e:
            return f"Error crítico resolviendo sistema: {str(e)}"

    def _matriz_a_texto(self, Matriz) -> str:
        """Helper para convertir matriz a texto legible por NVDA fila por fila"""
        filas_str = []
        rows, cols = Matriz.shape
        for i in range(rows):
            fila_vals = [str(Matriz[i, j]) for j in range(cols)]
            # Formato: [ 1, 0, 5 ]
            filas_str.append(f"  [ {', '.join(fila_vals)} ]")
        return "\n".join(filas_str)

    def EvaluarExpresion(self, expresion: str) -> str:
        try:
            expr = self._parsear_seguro(expresion)
            
            # Cálculo exacto y decimal
            res_exacto = sympy.simplify(expr)
            res_decimal = res_exacto.evalf()

            # Formato de salida
            if res_exacto == res_decimal:
                texto = f"{res_exacto}"
            else:
                texto = f"Exacto: {res_exacto}\nDecimal: {res_decimal:.6f}"
                
            return f"Resultado:\n{texto}"
        except Exception as e:
            return f"Error: {str(e)}"

    def ResolverEcuacion(self, ecuacion: str, variable: str = 'x') -> str:
        try:
            # Manejo de igualdades (lado izquierdo - lado derecho)
            parts = ecuacion.split('=')
            if len(parts) == 2:
                expr = self._parsear_seguro(parts[0]) - self._parsear_seguro(parts[1])
            else:
                expr = self._parsear_seguro(ecuacion)
            
            # Detectar variable automáticamente si el usuario no la especifica bien
            var_symbol = Symbol(variable)
            if variable == 'x' and var_symbol not in expr.free_symbols:
                libres = list(expr.free_symbols)
                if len(libres) == 1:
                    var_symbol = libres[0]

            soluciones = sympy.solve(expr, var_symbol)
            
            if not soluciones:
                return "No se encontraron soluciones reales exactas."
            
            # Formateo detallado como en tu original
            texto_salida = f"Soluciones para {var_symbol}:\n"
            for i, sol in enumerate(soluciones, 1):
                val_approx = sol.evalf(4)
                texto_salida += f"Solución {i}: {sol}  (Aprox: {val_approx})\n"
                
            return texto_salida

        except Exception as e:
            return f"Error al resolver: {str(e)}"

    def CalcularLimite(self, expresion: str, variable: str, tendencia: str) -> str:
        try:
            expr = self._parsear_seguro(expresion)
            var_symbol = sympy.Symbol(variable)
            
            # 1. Normalización de la tendencia (infinito)
            t_str = tendencia.lower().strip()
            if t_str in ['inf', 'oo', 'infinito', '+inf']:
                punto = sympy.oo
            elif t_str in ['-inf', '-oo', '-infinito']:
                punto = -sympy.oo
            else:
                punto = self._parsear_seguro(tendencia)
                
            # 2. Cálculo de límites laterales (Izquierda y Derecha) para diagnóstico
            # Esto ayuda a saber si el límite realmente existe
            lim_derecha = sympy.limit(expr, var_symbol, punto, dir='+')
            lim_izquierda = sympy.limit(expr, var_symbol, punto, dir='-')
            
            # 3. Límite general (bidireccional)
            limite = sympy.limit(expr, var_symbol, punto)
            
            # 4. Construcción de la explicación pedagógica
            explicacion = ""
            if lim_derecha != lim_izquierda:
                explicacion = (f"¡Atención! El límite no existe porque los laterales son distintos.\n"
                               f"Por la derecha tiende a: {lim_derecha}\n"
                               f"Por la izquierda tiende a: {lim_izquierda}")
            else:
                try:
                    eval_directa = expr.subs(var_symbol, punto)
                    # Comparamos si la evaluación directa dio el mismo resultado
                    if eval_directa == limite:
                        explicacion = "El límite se obtuvo por evaluación directa (la función es continua en ese punto)."
                    else:
                        explicacion = "Hubo una indeterminación (como 0/0) que fue resuelta algebraicamente."
                except:
                    explicacion = "Límite calculado simbólicamente."

            return (f"Límite de {expresion} cuando {variable} -> {tendencia}:\n"
                    f"Resultado General: {limite}\n"
                    f"-----------------------------\n"
                    f"Análisis:\n{explicacion}")
        except Exception as e:
            return f"Error calculando límite: {str(e)}"

    def Determinante(self, matriz_input_str: str) -> str:
        """
        Calcula determinante mostrando pasos reales (2x2 y Sarrus para 3x3).
        Versión Corregida: Ahora sí muestra el paso final de la resta.
        """
        try:
            # Parser flexible para leer la matriz
            filas_str = matriz_input_str.split(';')
            matriz_datos = []
            for f in filas_str:
                elementos = f.replace(',', ' ').split()
                # Usamos parsear_seguro para admitir fracciones o variables
                fila = [self._parsear_seguro(e) for e in elementos]
                if fila: matriz_datos.append(fila)
            
            if not matriz_datos: return "Error: Matriz vacía."

            M = sympy.Matrix(matriz_datos)
            if not M.is_square: return "Error: La matriz debe ser cuadrada."
            
            det = sympy.simplify(M.det())
            pasos = ""

            # CASO 2x2
            if M.shape == (2, 2):
                a, b = M[0, 0], M[0, 1]
                c, d = M[1, 0], M[1, 1]
                pasos = (f"Regla 2x2 (Multiplicación cruzada):\n"
                         f"({a} * {d}) - ({b} * {c})\n"
                         f"= {sympy.simplify(a*d)} - {sympy.simplify(b*c)}")

            # CASO 3x3 (Regla de Sarrus Explícita)
            elif M.shape == (3, 3):
                # Asignamos variables a posiciones a11..a33 para claridad
                a, b, c = M[0,0], M[0,1], M[0,2]
                d, e, f = M[1,0], M[1,1], M[1,2]
                g, h, i = M[2,0], M[2,1], M[2,2]
                
                # Diagonales Principales (Positivas)
                p1 = a * e * i
                p2 = b * f * g
                p3 = c * d * h
                sum_p = sympy.simplify(p1 + p2 + p3)
                
                # Diagonales Secundarias (Negativas)
                s1 = c * e * g
                s2 = a * f * h
                s3 = b * d * i
                sum_s = sympy.simplify(s1 + s2 + s3)
                
                pasos = "Regla de Sarrus (3x3):\n"
                pasos += "1. Diagonales Principales (+):\n"
                pasos += f"   ({a}*{e}*{i}) + ({b}*{f}*{g}) + ({c}*{d}*{h})\n"
                pasos += f"   = {p1} + {p2} + {p3} = {sum_p}\n\n"
                
                pasos += "2. Diagonales Secundarias (-):\n"
                pasos += f"   ({c}*{e}*{g}) + ({a}*{f}*{h}) + ({b}*{d}*{i})\n"
                pasos += f"   = {s1} + {s2} + {s3} = {sum_s}\n\n"
                
                # --- AQUÍ FALTABA EL CÓDIGO ---
                pasos += "3. Resta Final (Principales - Secundarias):\n"
                pasos += f"   ({sum_p}) - ({sum_s})\n"
                pasos += f"   = {det}"
                # ------------------------------

            else:
                pasos = f"Cálculo directo para matriz de orden {M.shape[0]}."

            return (f"Resultado del determinante:\n"
                    f"Valor Final: {det}\n"
                    f"-----------------------------\n"
                    f"Detalle del cálculo:\n{pasos}")

        except Exception as e:
            return f"Error en matriz: {str(e)}"

    # --- DERIVADAS CON EXPLICACIÓN ---

    def Derivada(self, expresion: str, variable: str = None) -> str:
        try:
            expr = self._parsear_seguro(expresion)
            sym_vars = expr.free_symbols
            
            if variable and variable.strip():
                var_symbol = Symbol(variable)
            elif len(sym_vars) == 1:
                var_symbol = list(sym_vars)[0]
            else:
                var_symbol = Symbol('x')

            # --- RESTAURACIÓN: Detección de regla pedagógica ---
            explicacion = self._detectar_regla_derivada(expr, var_symbol)
            
            # Cálculo
            resultado = sympy.diff(expr, var_symbol)
            
            return (f"Resultado: {resultado}\n"
                    f"-----------------------\n"
                    f"Lógica probable: {explicacion}")
        except Exception as e:
            return f"Error derivando: {str(e)}"

    def _detectar_regla_derivada(self, expr, var) -> str:
        """ Método original restaurado para explicar reglas """
        if not expr.has(var):
            return "Regla de la Constante (la derivada es cero)."
        
        if expr.is_Add:
            return "Regla de la Suma: Se deriva cada término por separado."
        
        if expr.is_Mul:
            args_con_var = [arg for arg in expr.args if arg.has(var)]
            if len(args_con_var) > 1:
                return "Regla del Producto: (f'g + fg')."
            return "Regla del Múltiplo Constante: Se mantiene el número y se deriva la función."
        
        if expr.is_Pow:
            base, exp = expr.as_base_exp()
            if base == var and exp.is_constant():
                return "Regla de la Potencia: Se baja el exponente y se resta 1."
            if base.has(var) and exp.is_constant():
                return "Regla de la Cadena (Generalizada de Potencia)."
            if base.is_constant() and exp.has(var):
                return "Regla Exponencial: a^u * ln(a) * u'."
        
        if isinstance(expr, sympy.exp):
            return "Regla de la Exponencial natural (e^x se mantiene)."
            
        if isinstance(expr, (sympy.sin, sympy.cos, sympy.tan)):
            return "Regla Trigonométrica básica."
            
        return "Derivación directa o Regla de la Cadena compuesta."

    def Enecima(self, expresion: str, variable: str, orden: int) -> str:
        """
        Calcula derivadas sucesivas (Blindada contra errores de formato).
        """
        try:
            # 1. Parseo seguro
            expr = self._parsear_seguro(expresion)
            var_symbol = sympy.Symbol(variable)
            
            if orden < 1:
                return "El orden debe ser mayor a 0."
            
            pasos = []
            derivada_actual = expr
            
            # 2. Bucle de derivación
            for i in range(1, orden + 1):
                derivada_actual = sympy.diff(derivada_actual, var_symbol)
                
                # --- CORRECCIÓN CRÍTICA AQUÍ ---
                # Forzamos la conversión a texto (str) INMEDIATAMENTE.
                # Esto evita que la f-string intente formatear el objeto matemático 'Add'.
                resultado_texto = str(derivada_actual) 
                
                nombre = f"{i}ª Derivada"
                pasos.append(f"{nombre}: {resultado_texto}")

            pasos_str = "\n".join(pasos)

            # Convertimos también el resultado final a string explícitamente
            final_str = str(derivada_actual)

            return (f"Resultado Final (Orden {orden}):\n{final_str}\n"
                    f"--------------------------------\n"
                    f"Secuencia de derivadas:\n{pasos_str}")
            
        except Exception as e:
            return f"Error matemático: {str(e)}"

    # --- INTEGRALES CON PASOS (ManualIntegrate) ---

    def Integral(self, expresion: str, variable: str = None) -> str:
        try:
            expr = self._parsear_seguro(expresion)
            sym_vars = expr.free_symbols
            if variable and variable.strip():
                var_symbol = Symbol(variable)
            elif len(sym_vars) == 1:
                var_symbol = list(sym_vars)[0]
            else:
                var_symbol = Symbol('x')

            # --- RESTAURACIÓN: Pasos explicativos completos ---
            explicacion = ""
            try:
                pasos_obj = integral_steps(expr, var_symbol)
                explicacion = self._pasos_a_texto(pasos_obj)
            except Exception:
                explicacion = "No se pudieron simplificar los pasos para esta integral compleja."

            resultado = sympy.integrate(expr, var_symbol)

            return (f"Resultado Final: {resultado} + C\n"
                    f"----------------------------------------\n"
                    f"Explicación Paso a Paso:\n{explicacion}")
        except Exception as e:
            return f"Error integrando: {str(e)}"

    def _pasos_a_texto(self, rule, nivel=0) -> str:
        """ 
        Convierte reglas de integración de SymPy a texto plano explicativo.
        Versión corregida para evitar errores en reglas sin nombre.
        """
        if not rule:
            return ""
        indent = "  " * nivel
        texto = ""

        # 1. Reglas de Suma
        if isinstance(rule, AddRule):
            texto += f"{indent}- Estrategia: Suma de términos (se integra cada uno por separado).\n"
            for substep in rule.substeps:
                texto += self._pasos_a_texto(substep, nivel + 1)

        # 2. Reglas de Constantes
        elif isinstance(rule, ConstantRule):
            texto += f"{indent}- Regla de la Constante: La integral de {rule.constant} es {rule.constant} * {rule.symbol}\n"
        
        elif isinstance(rule, ConstantTimesRule):
            texto += f"{indent}- Regla del Múltiplo Constante: Se saca el número {rule.constant} fuera de la integral.\n"
            texto += self._pasos_a_texto(rule.substep, nivel + 1)

        # 3. Potencias y Raíces
        elif isinstance(rule, PowerRule):
            base, exp = rule.base, rule.exp
            texto += (f"{indent}- Regla de la Potencia: Se suma 1 al exponente y se divide por el nuevo exponente.\n"
                      f"{indent}  (Integral de {base}^{exp} es {base}^{exp + 1} / {exp + 1})\n")

        # 4. Sustitución (Cambio de variable)
        elif isinstance(rule, URule):
            texto += (f"{indent}- Método de Sustitución: Se elige u = {rule.u_func}.\n")
            texto += self._pasos_a_texto(rule.substep, nivel + 1)

        # 5. Integración por Partes
        elif isinstance(rule, PartsRule):
            texto += (f"{indent}- Integración por Partes: Fórmula u*v - Integral(v*du).\n"
                      f"{indent}  Se elige u={rule.u} y dv={rule.dv}\n")
            texto += self._pasos_a_texto(rule.second_step, nivel + 1)

        # 6. Reglas Trigonométricas y Exponenciales (CORREGIDO)
        elif isinstance(rule, TrigRule):
            # Protegemos el acceso al nombre por si acaso
            nombre = getattr(rule, 'func_name', 'función trigonométrica')
            texto += f"{indent}- Regla Trigonométrica directa para {nombre}.\n"

        elif isinstance(rule, ExpRule):
            # La regla exponencial a veces no tiene func_name, ponemos texto fijo
            texto += f"{indent}- Regla Exponencial: La integral de e^x es ella misma (e^x).\n"

        elif isinstance(rule, ReciprocalRule):
            texto += f"{indent}- Regla del Logaritmo: Integral de 1/x es logaritmo natural de x.\n"

        # 7. Reglas Alternativas y Default
        elif isinstance(rule, AlternativeRule):
            texto += f"{indent}- Probando estrategia alternativa:\n"
            for substep in rule.alternatives:
                texto += self._pasos_a_texto(substep, nivel + 1)

        else:
            # Captura cualquier otra regla no específica
            nombre_regla = type(rule).__name__.replace("Rule", "")
            texto += f"{indent}- Paso aplicado: {nombre_regla}\n"

        return texto

    def SimplificarEcuacion(self, expresion: str) -> str:
        try:
            expr = self._parsear_seguro(expresion)
            result = sympy.simplify(expr)
            return f"Simplificación: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

class DifFactorizaciones:
    def __init__(self, op):
        self.op = op # Referencia a la clase Algebra
    def IntentarFactorizar(self, expresion: str) -> str:
        try:
            expr = self.op._parsear_seguro(expresion)
            return f"Factorización:\n{sympy.factor(expr)}"
        except Exception as e:
            return f"Error: {str(e)}"