import sympy
from sympy import Symbol


class GestorLimites:
    """
    Módulo V10: Cálculo de límites con rigor matemático y narrativa accesible.
    Corrige comparaciones simbólicas y clasificación de discontinuidades.
    """
    
    def __init__(self, parser_compartido=None):
        if parser_compartido:
            self.parser = parser_compartido
        else:
            from parser import ParserMatematico
            self.parser = ParserMatematico()

    def calcular_limite(self, expresion: str, variable: str, tendencia: str) -> str:
        try:
            # 1. Preparación
            expr, var_symbol, punto, txt_tendencia, es_infinito = self._preparar_datos(expresion, variable, tendencia)
            
            # 2. Cálculo de la Verdad Matemática (El Límite Real)
            # Calculamos esto PRIMERO, porque es la autoridad.
            try:
                limite_real = sympy.limit(expr, var_symbol, punto)
            except Exception:
                limite_real = None # Puede no existir

            # 3. Diagnóstico de Situación (Comparando Realidad vs Evaluación)
            diagnostico, tipo_indet = self._diagnosticar_situacion(expr, var_symbol, punto, limite_real, es_infinito)
            
            # 4. Análisis de Laterales (Solo si hay duda o discontinuidad)
            info_laterales = None
            if not es_infinito:
                # Calculamos laterales si el límite falló, si es infinito, o si hubo indeterminación
                # para confirmar si es salto, asíntota o hueco.
                if limite_real is None or (hasattr(limite_real, 'is_infinite') and limite_real.is_infinite) or tipo_indet:
                    info_laterales = self._analizar_laterales_seguro(expr, var_symbol, punto)

            # 5. Generar Reporte Pedagógico
            return self._construir_texto_final(
                expr, variable, txt_tendencia, 
                limite_real, diagnostico, tipo_indet, info_laterales
            )

        except ValueError as ve:
            return f"Error de entrada: {str(ve)}"
        except Exception as e:
            return f"Error crítico en el motor de límites: {str(e)}"

    # --- MÉTODOS PRIVADOS ---

    def _preparar_datos(self, expresion, variable, tendencia):
        """Parsea y normaliza."""
        expr = self.parser.parsear(expresion)
        var_symbol = Symbol(variable)
        t_str = tendencia.lower().strip()
        es_infinito = False
        
        if t_str in ['inf', 'oo', 'infinito', '+inf']:
            punto = sympy.oo
            es_infinito = True
            txt = "+Infinito"
        elif t_str in ['-inf', '-oo', '-infinito']:
            punto = -sympy.oo
            es_infinito = True
            txt = "-Infinito"
        else:
            punto = self.parser.parsear(tendencia)
            txt = str(punto)
            
        return expr, var_symbol, punto, txt, es_infinito

    def _diagnosticar_situacion(self, expr, var, punto, limite_real, es_infinito):
        """
        Determina qué está pasando: Continuidad, Hueco, Asíntota, Indeterminación.
        Retorna: (Texto Diagnóstico, Bool Indeterminación)
        """
        # A. Intentamos evaluar f(a) directamente (sustitución)
        try:
            val_sust = expr.subs(var, punto)
        except Exception:
            val_sust = sympy.nan

        # B. Análisis de Indeterminaciones (Heurística mejorada)
        tipo_indet = None
        
        # Si al sustituir da NaN (ej: 0/0, inf-inf), analizamos por qué
        if val_sust is sympy.nan or (hasattr(val_sust, 'is_nan') and val_sust.is_nan):
            # Descomponemos para ver si es el clásico 0/0 o inf/inf
            n, d = expr.as_numer_denom()
            try:
                n_val = n.subs(var, punto)
                d_val = d.subs(var, punto)
                
                if n_val == 0 and d_val == 0:
                    tipo_indet = "0/0"
                elif (n_val.is_infinite if hasattr(n_val,'is_infinite') else False) and \
                     (d_val.is_infinite if hasattr(d_val,'is_infinite') else False):
                    tipo_indet = "Inf/Inf"
                else:
                    # Chequeo rápido de otras formas (0*inf, 1^inf)
                    # Si es potencia y base tiende a 1 y exp a inf...
                    if expr.is_Pow:
                        base, exp = expr.as_base_exp()
                        l_b = sympy.limit(base, var, punto)
                        l_e = sympy.limit(exp, var, punto)
                        if l_b == 1 and l_e.is_infinite:
                            tipo_indet = "1^Inf"
                        elif l_b == 0 and l_e == 0:
                            tipo_indet = "0^0"
                        elif l_b.is_infinite and l_e == 0:
                            tipo_indet = "Inf^0"
                    
                    if not tipo_indet:
                        tipo_indet = "Compleja" # 0*inf o resta de inf
            except Exception:
                tipo_indet = "Desconocida"

        # C. Clasificación Final
        if es_infinito:
            return ("Análisis Asintótico (Tendencia al infinito)", tipo_indet)
        
        # Si el límite existe y es igual a la evaluación -> CONTINUA
        # Usamos equals para comparación segura
        es_igual = False
        try:
            if limite_real is not None and val_sust is not sympy.nan:
                diff = sympy.simplify(limite_real - val_sust)
                es_igual = (diff == 0 or diff.equals(0))
        except Exception:
            pass

        if es_igual:
            return ("FUNCIÓN CONTINUA (Evaluación directa exitosa)", None)
        
        # Si hay indeterminación pero el límite existe -> HUECO
        if tipo_indet and limite_real is not None and not limite_real.is_infinite:
            return (f"DISCONTINUIDAD EVITABLE (Hueco). Forma {tipo_indet}.", tipo_indet)
        
        # Si el límite es infinito -> ASINTOTA
        if limite_real is not None and limite_real.is_infinite:
            return ("ASÍNTOTA VERTICAL (Singularidad)", tipo_indet)

        return ("DISCONTINUIDAD DE SALTO o NO EXISTE", tipo_indet)

    def _analizar_laterales_seguro(self, expr, var, punto):
        """Calcula laterales y los compara usando equals() para robustez."""
        try:
            der = sympy.limit(expr, var, punto, dir='+')
            izq = sympy.limit(expr, var, punto, dir='-')
            
            # COMPARACIÓN ROBUSTA (Fix de la auditoría)
            coinciden = False
            try:
                if der.is_infinite and izq.is_infinite:
                    coinciden = (der == izq) # Infinito con signo
                else:
                    diff = sympy.simplify(der - izq)
                    coinciden = (diff == 0 or diff.equals(0))
            except Exception:
                coinciden = False # Ante la duda, no coinciden

            return {'der': der, 'izq': izq, 'coinciden': coinciden}
        except Exception:
            return None

    def _construir_texto_final(self, expr, var, txt_tendencia, limite, diagnostico, tipo_indet, laterales):
        """Ensambla la narrativa pedagógica para NVDA."""
        # 1. Título
        txt = f"Límite de {expr} cuando {var} -> {txt_tendencia}\n"
        txt += "-----------------------------\n"
        
        # 2. Resultado Principal
        txt_res = "Indefinido"
        if limite is not None:
            txt_res = str(limite)
            if hasattr(limite, 'is_infinite') and limite.is_infinite:
                txt_res += " (Divergente)"
        
        txt += f"RESULTADO: {txt_res}\n\n"
        
        # 3. Análisis Pedagógico
        txt += f"Análisis: {diagnostico}\n"
        
        if tipo_indet:
            txt += f"Nota: Se detectó una forma indeterminada inicial tipo [{tipo_indet}], que fue resuelta matemáticamente.\n"
        
        # 4. Detalle de Laterales (Si existen)
        if laterales:
            txt += "\nEstudio de Laterales:\n"
            txt += f" - Derecha (+): {laterales['der']}\n"
            txt += f" - Izquierda (-): {laterales['izq']}\n"
            
            if laterales['coinciden']:
                txt += " >>> Los laterales COINCIDEN. El límite existe."
            else:
                txt += " >>> Los laterales son DISTINTOS. El límite no existe (Salto)."
        
        return txt