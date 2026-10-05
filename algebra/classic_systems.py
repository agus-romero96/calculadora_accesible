"""
Módulo de Resolución de Sistemas Lineales por Métodos Clásicos.
(Sustitución, Igualación, Reducción).

Estándar: Enterprise / Educational Research.
Arquitectura: Stateless Service con DTOs inmutables.
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any, Dict
import sympy

# --- CAPA DE DATOS (DTOs Inmutables) ---

@dataclass(frozen=True)
class PasoMetodo:
    fase: int                # Número de paso secuencial
    titulo: str              # Ej: "Despeje de variable"
    descripcion: str         # Explicación pedagógica
    expresion_matematica: str # Representación visual del paso

@dataclass(frozen=True)
class ResultadoClasico:
    es_exitoso: bool
    metodo: str              # "Sustitución", "Igualación", etc.
    variables: List[str]     # ["x", "y"]
    solucion_dict: Dict[str, Any] # { "x": 5, "y": 2 }
    pasos: List[PasoMetodo] = field(default_factory=list)
    mensaje_diagnostico: str = "" # Para casos de error o sistemas indeterminados

# --- CAPA DE SERVICIO (Motor Lógico) ---

class MotorSistemasClasicos:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # --- UTILIDADES PRIVADAS ---

    def _parsear_ecuaciones(self, lista_txt: List[str]) -> Tuple[List[sympy.Eq], List[sympy.Symbol]]:
        """
        Convierte lista de strings en ecuaciones SymPy normalizadas.
        Detecta variables automáticamente.
        """
        ecus = []
        todas_vars = set()

        for txt in lista_txt:
            if not txt.strip():
                continue
            try:
                # Manejo de igualdad
                if "=" in txt:
                    parts = txt.split("=")
                    lhs = self.parser.parsear(parts[0])
                    rhs = self.parser.parsear(parts[1])
                    # Normalizamos a: Expresión = 0
                    eq = sympy.Eq(lhs - rhs, 0)
                else:
                    expr = self.parser.parsear(txt)
                    eq = sympy.Eq(expr, 0)

                # Validación de Linealidad (Crucial para métodos clásicos)
                if not sympy.Poly(eq.lhs).is_linear:
                    raise ValueError(f"La ecuación '{txt}' no es lineal.")

                ecus.append(eq)
                todas_vars.update(eq.free_symbols)
            except Exception as e:
                raise ValueError(f"Error de sintaxis en '{txt}': {str(e)}")

        # Ordenar variables alfabéticamente
        vars_sorted = sorted(list(todas_vars), key=lambda x: x.name)
        return ecus, vars_sorted

    def _fmt_eq(self, eq: sympy.Eq, vars_list: List[sympy.Symbol]) -> str:
        """
        Formateador visual: Convierte 'x + y - 5 = 0' en 'x + y = 5'.
        Mejora la legibilidad para el usuario final.
        """
        expr = eq.lhs
        # Separar términos con variables de constantes
        independent = expr.as_coeff_add(*vars_list)[0]
        dependent = expr - independent
        return f"{dependent} = {-independent}"

    # --- ALGORITMOS DE RESOLUCIÓN ---

    def _resolver_sustitucion(self, eq1: sympy.Eq, eq2: sympy.Eq, x: sympy.Symbol, y: sympy.Symbol) -> List[PasoMetodo]:
        pasos = []
        
        # 1. Estrategia de Selección (Igual que antes)
        candidatos = [
            (eq1, x, 1), (eq1, y, 1),
            (eq2, x, 2), (eq2, y, 2)
        ]
        seleccion = candidatos[0]
        for ec, var, idx in candidatos:
            try:
                coef = sympy.Poly(ec.lhs, var).coeff_monomial(var)
                if abs(coef) == 1:
                    seleccion = (ec, var, idx)
                    break
            except Exception: continue

        ec_origen, var_desp, idx_origen = seleccion
        var_restante = y if var_desp == x else x
        ec_destino = eq2 if idx_origen == 1 else eq1
        idx_destino = 2 if idx_origen == 1 else 1

        # --- SEGURIDAD AGREGADA AQUÍ ---
        # Paso 1: Despeje
        sol_despeje = sympy.solve(ec_origen, var_desp)
        if not sol_despeje:
            raise ValueError(f"Imposible despejar {var_desp}. Verifique las ecuaciones.")
        despeje = sol_despeje[0]

        pasos.append(PasoMetodo(
            1, "Despeje Inicial",
            f"Seleccionamos la Ecuación {idx_origen} y despejamos '{var_desp}'.",
            f"{var_desp} = {despeje}"
        ))

        # Paso 2: Sustitución
        sustituida = ec_destino.subs(var_desp, despeje)
        pasos.append(PasoMetodo(
            2, "Sustitución",
            f"Reemplazamos en la Ecuación {idx_destino}.",
            f"{self._fmt_eq(sustituida, [var_restante])}"
        ))

        # Paso 3: Resolución parcial
        res_parcial = sympy.solve(sustituida, var_restante)
        
        # --- VALIDACIÓN DE COHERENCIA ---
        if not res_parcial:
            # Si al sustituir desaparece la variable y queda algo falso (ej: 0=5)
            raise ValueError("SISTEMA INCOMPATIBLE: No tiene solución (Rectas paralelas).")
        
        # Si devuelve algo raro o vacío (casos infinitos malformados)
        if isinstance(res_parcial, dict) and not res_parcial:
             raise ValueError("SISTEMA INDETERMINADO: Infinitas soluciones (Misma recta).")

        val_restante = res_parcial[0]
        
        pasos.append(PasoMetodo(
            3, f"Hallar {var_restante}",
            f"Resolvemos la ecuación resultante.",
            f"{var_restante} = {val_restante}"
        ))

        # Paso 4: Back-substitution
        val_desp = despeje.subs(var_restante, val_restante)
        pasos.append(PasoMetodo(
            4, f"Hallar {var_desp}",
            f"Sustituimos el valor encontrado en el despeje del paso 1.",
            f"{var_desp} = {val_desp}"
        ))

        return pasos

    def _resolver_igualacion(self, eq1: sympy.Eq, eq2: sympy.Eq, x: sympy.Symbol, y: sympy.Symbol) -> List[PasoMetodo]:
        pasos = []
        var_obj = x 

        # --- SEGURIDAD AGREGADA AQUÍ ---
        # Paso 1: Despejes
        s1 = sympy.solve(eq1, var_obj)
        s2 = sympy.solve(eq2, var_obj)

        if not s1 or not s2:
            raise ValueError(f"No se pudo despejar {var_obj} en alguna ecuación.")

        d1 = s1[0]
        d2 = s2[0]
        
        pasos.append(PasoMetodo(
            1, "Despeje Doble",
            f"Despejamos '{var_obj}' en ambas ecuaciones.",
            f"Ec1: {var_obj} = {d1}\nEc2: {var_obj} = {d2}"
        ))

        # Paso 2: Igualación
        igualdad = sympy.Eq(d1, d2)
        var_rest = y
        pasos.append(PasoMetodo(
            2, "Igualación",
            "Igualamos ambas expresiones.",
            f"{d1} = {d2}"
        ))

        # Paso 3: Resolución
        sol_rest_list = sympy.solve(igualdad, var_rest)
        
        # --- VALIDACIÓN ---
        if not sol_rest_list:
             raise ValueError("SISTEMA INCOMPATIBLE: Al igualar se obtiene una contradicción.")
        
        sol_rest = sol_rest_list[0]
        pasos.append(PasoMetodo(
            3, f"Resolución para {var_rest}",
            "Despejamos la variable restante.",
            f"{var_rest} = {sol_rest}"
        ))

        # Paso 4: Final
        sol_obj = d1.subs(var_rest, sol_rest)
        pasos.append(PasoMetodo(
            4, f"Hallar {var_obj}",
            "Reemplazamos en el primer despeje.",
            f"{var_obj} = {sol_obj}"
        ))

        return pasos

    def _resolver_reduccion(self, eq1: sympy.Eq, eq2: sympy.Eq, x: sympy.Symbol, y: sympy.Symbol) -> List[PasoMetodo]:
        pasos = []
        # Obtener coeficientes
        c1 = sympy.Poly(eq1.lhs, x).coeff_monomial(x)
        c2 = sympy.Poly(eq2.lhs, x).coeff_monomial(x)

        target = x
        other = y
        
        if c1 == 0 and c2 == 0:
            c1 = sympy.Poly(eq1.lhs, y).coeff_monomial(y)
            c2 = sympy.Poly(eq2.lhs, y).coeff_monomial(y)
            target = y
            other = x

        pasos.append(PasoMetodo(
            1, "Análisis de Coeficientes",
            f"Elegimos eliminar '{target}'. Coeficientes: Ec1({c1}), Ec2({c2}).",
            "Buscamos coeficientes opuestos."
        ))

        m1, m2 = c2, -c1
        
        # Paso 2: Multiplicación
        eq1_new = sympy.Eq(sympy.expand(eq1.lhs * m1), 0)
        eq2_new = sympy.Eq(sympy.expand(eq2.lhs * m2), 0)
        
        pasos.append(PasoMetodo(
            2, "Transformación",
            f"Multiplicamos Ec1 por ({m1}) y Ec2 por ({m2}).",
            f"{self._fmt_eq(eq1_new, [x,y])}\n{self._fmt_eq(eq2_new, [x,y])}"
        ))

        # Paso 3: Suma
        suma_lhs = sympy.simplify(eq1_new.lhs + eq2_new.lhs)
        
        # --- SEGURIDAD: VERIFICAR SI SE ELIMINÓ TODO ---
        if suma_lhs == 0:
             # 0 = 0 -> Indeterminado
             raise ValueError("SISTEMA INDETERMINADO: Al restar las ecuaciones, todo se anula (son la misma recta).")
        if suma_lhs.is_constant() and suma_lhs != 0:
             # 5 = 0 -> Incompatible
             raise ValueError("SISTEMA INCOMPATIBLE: Al restar queda una igualdad falsa (ej: 5=0).")

        pasos.append(PasoMetodo(
            3, "Reducción (Suma)",
            f"Sumamos las ecuaciones. La variable '{target}' se elimina.",
            f"{self._fmt_eq(sympy.Eq(suma_lhs, 0), [x,y])}"
        ))

        # Paso 4: Solución Parcial
        val_other_list = sympy.solve(suma_lhs, other)
        if not val_other_list:
            raise ValueError(f"Error matemático resolviendo para {other}")
            
        val_other = val_other_list[0]
        pasos.append(PasoMetodo(
            4, f"Hallar {other}",
            "Resolvemos la ecuación simplificada.",
            f"{other} = {val_other}"
        ))

        # Paso 5: Final
        eq_final = eq1.subs(other, val_other)
        val_target_list = sympy.solve(eq_final, target)
        if not val_target_list:
             raise ValueError(f"Error resolviendo para {target}")
        
        val_target = val_target_list[0]
        pasos.append(PasoMetodo(
            5, f"Hallar {target}",
            "Sustituimos en la Ec1 original.",
            f"{target} = {val_target}"
        ))

        return pasos

    # --- MÉTODO PÚBLICO PRINCIPAL (FACADE) ---

    def ExplicarSistemaClasico(self, lista_ecuaciones: List[str], metodo_preferido: str = "sustitucion") -> str:
        """
        Orquesta la resolución de sistemas 2x2.
        Entrada: Lista de ecuaciones ["x+y=1", ...], método ("sustitucion", "igualacion", "reduccion")
        Salida: String formateado para NVDA/Lectura humana.
        """
        try:
            # 1. Parsing y Validación
            ecus, vars_list = self._parsear_ecuaciones(lista_ecuaciones)

            # --- GUARD CLAUSE: DIMENSIONES ---
            if len(vars_list) != 2 or len(ecus) != 2:
                # Derivación profesional: Si no es 2x2, sugerimos la herramienta correcta
                return (f"Nota: El sistema tiene {len(vars_list)} variables y {len(ecus)} ecuaciones.\n"
                        f"Los métodos clásicos (Sustitución, etc.) son didácticos para 2x2.\n"
                        f"Para este caso, por favor use la opción 'Gauss-Jordan' del menú, que es el método universal adecuado.")

            # 2. Diagnóstico previo (Determinante)
            # Extraemos matriz para verificar compatibilidad antes de operar
            A, B = sympy.linear_eq_to_matrix(ecus, vars_list)
            det = A.det()
            
            if det == 0:
                # Diagnóstico Rouché-Frobenius simplificado
                M_aum = A.row_join(B)
                if A.rank() < M_aum.rank():
                    return "Diagnóstico: SISTEMA INCOMPATIBLE (Sin solución). Las rectas son paralelas."
                else:
                    return "Diagnóstico: SISTEMA INDETERMINADO (Infinitas soluciones). Las ecuaciones representan la misma recta."

            # 3. Selección de Algoritmo
            x, y = vars_list[0], vars_list[1]
            eq1, eq2 = ecus[0], ecus[1]
            pasos = []

            if metodo_preferido == "sustitucion":
                pasos = self._resolver_sustitucion(eq1, eq2, x, y)
            elif metodo_preferido == "igualacion":
                pasos = self._resolver_igualacion(eq1, eq2, x, y)
            elif metodo_preferido == "reduccion":
                pasos = self._resolver_reduccion(eq1, eq2, x, y)
            else:
                return "Error: Método desconocido. Use 'sustitucion', 'igualacion' o 'reduccion'."

            # 4. Cálculo de Solución Final (Verdad Matemática)
            sol_final = sympy.solve(ecus, vars_list)
            
            # 5. Generación de Narrativa
            texto = []
            texto.append(f"RESOLUCIÓN POR {metodo_preferido.upper()}")
            texto.append(f"Sistema 2x2. Variables: {x}, {y}")
            texto.append(f"Ec 1: {self._fmt_eq(eq1, vars_list)}")
            texto.append(f"Ec 2: {self._fmt_eq(eq2, vars_list)}\n")
            
            for p in pasos:
                texto.append(f"PASO {p.fase}: {p.titulo}")
                texto.append(f"   Explicación: {p.descripcion}")
                texto.append(f"   Operación: {p.expresion_matematica}\n")

            texto.append("--------------------------------")
            texto.append("RESULTADO FINAL:")
            # Formateo agnóstico del tipo de resultado de solve
            if isinstance(sol_final, dict):
                for v in vars_list:
                    texto.append(f"{v} = {sol_final[v]}")
            else:
                # Caso raro de fallback
                texto.append(str(sol_final))

            return "\n".join(texto)

        except ValueError as ve:
            return f"Error de Validación: {str(ve)}"
        except Exception as e:
            return f"Error del Sistema: {str(e)}"