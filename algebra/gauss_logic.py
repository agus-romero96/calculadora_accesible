"""
Módulo especializado en Resolución de Sistemas por Gauss-Jordan.
Soporta entrada por ecuaciones y matrices.
Garantiza consistencia matemática mediante RREF canónico y diagnósticos de rango.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple
import sympy

# --- ESTRUCTURAS DE DATOS (DTOs Inmutables) ---

@dataclass(frozen=True)
class PasoGauss:
    titulo: str              # Ej: "Normalizar Fila 2"
    descripcion: str         # Ej: "Dividimos toda la fila entre 5..."
    operacion_matematica: str # Ej: "F2 -> F2 / 5"
    matriz_resultante: sympy.Matrix

@dataclass(frozen=True)
class ResultadoGauss:
    tipo_solucion: str       # "UNICA", "INFINITA", "INCONSISTENTE"
    variables: List[str]     # ["x", "y", "z"]
    matriz_aumentada_inicial: sympy.Matrix
    matriz_rref_final: sympy.Matrix # La verdad matemática (SymPy .rref())
    pasos: List[PasoGauss] = field(default_factory=list)
    solucion_texto: str = "" 
    mensaje_error: str = ""
    advertencias: List[str] = field(default_factory=list) # Avisos no bloqueantes

# --- CLASE PRINCIPAL ---

class MotorGauss:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    def _es_cero(self, valor) -> bool:
        """Helper para verificación simbólica robusta."""
        return sympy.simplify(valor).equals(0)

    def _parsear_sistema_mixto(self, lista_entradas: List[str]) -> Tuple[sympy.Matrix, List[str]]:
        """
        Inteligencia de parsing:
        1. Detecta si son ecuaciones ("2x + y = 10").
        2. Detecta si es matriz directa ("[[1,2,10]]").
        Retorna (Matriz Aumentada, Lista de Nombres de Variables).
        """
        
        # Caso 1: Entrada única que parece matriz
        if len(lista_entradas) == 1 and ("[[" in lista_entradas[0] or "Matrix" in lista_entradas[0]):
            try:
                expr = self.parser.parsear(lista_entradas[0])
                if isinstance(expr, list) or isinstance(expr, sympy.Matrix):
                    M = sympy.Matrix(expr)
                    cols = M.shape[1]
                    vars_names = ["x", "y", "z"][:cols-1] if cols-1 <= 3 else [f"x{i+1}" for i in range(cols-1)]
                    return M, vars_names
            except Exception:
                pass # Falló como matriz, intentamos como ecuación

        # Caso 2: Lista de ecuaciones lineales
        try:
            ecuaciones_sympy = []
            todas_vars = set()
            
            for txt in lista_entradas:
                if not txt.strip():
                    continue
                if "=" in txt:
                    parts = txt.split("=")
                    if len(parts) != 2:
                        raise ValueError(f"La ecuación '{txt.strip()}' debe tener exactamente un signo '='.")
                    izq = self.parser.parsear(parts[0])
                    der = self.parser.parsear(parts[1])
                    eq = sympy.Eq(izq, der)
                else:
                    # Asumimos "= 0" si no hay igual
                    expr = self.parser.parsear(txt)
                    eq = sympy.Eq(expr, 0)
                
                ecuaciones_sympy.append(eq)
                todas_vars.update(eq.free_symbols)
            
            if not ecuaciones_sympy:
                raise ValueError("No se detectaron ecuaciones válidas.")

            # Ordenar variables alfabéticamente para consistencia (x, y, z)
            variables = sorted(list(todas_vars), key=lambda s: s.name)
            
            # Convertir a Ax = B -> Matriz Aumentada [A | B]
            A, B = sympy.linear_eq_to_matrix(ecuaciones_sympy, variables)
            M_aumentada = A.row_join(B)
            
            return M_aumentada, [v.name for v in variables]

        except Exception as e:
            raise ValueError(f"No se pudo interpretar el sistema: {str(e)}")

    def _resolver_core_gauss(self, matriz_inicial: sympy.Matrix, variables: List[str]) -> ResultadoGauss:
        """Motor algorítmico con Pivoteo Inteligente (Prioridad a 1 y -1)."""
        M = matriz_inicial.copy()
        rows, cols = M.shape
        num_vars = cols - 1
        pasos_historial = []
        advertencias = []

        # --- VALIDACIÓN DE TAMAÑO (NO BLOQUEANTE) ---
        if rows > 5:
            advertencias.append(f"Sistema grande ({rows} ecuaciones). La explicación detallada puede ser extensa.")

        pivot_row = 0
        
        # --- BUCLE PEDAGÓGICO DE ELIMINACIÓN ---
        for col in range(num_vars):
            if pivot_row >= rows:
                break
            
            # 1. BUSCAR PIVOTE (MEJORADO: Usamos la inteligencia heurística)
            # Antes: Elegíamos el primero que no fuera cero.
            # Ahora: Buscamos 1, luego -1, y solo si no hay, cualquiera.
            candidato_row = self._buscar_mejor_pivote(M, col, pivot_row, rows)
            
            # Si candidato_row es None, significa que toda la columna (desde pivot_row hacia abajo) es ceros.
            # Pasamos a la siguiente columna sin avanzar de fila.
            if candidato_row is None:
                continue 

            # 2. INTERCAMBIO (SWAP)
            if candidato_row != pivot_row:
                M.row_swap(pivot_row, candidato_row)
                pasos_historial.append(PasoGauss(
                    titulo=f"Intercambio de Filas (Columna {col+1})",
                    descripcion=f"Para evitar fracciones complejas, intercambiamos Fila {pivot_row+1} con Fila {candidato_row+1} (buscando un 1 o pivote simple).",
                    operacion_matematica=f"F{pivot_row+1} <-> F{candidato_row+1}",
                    matriz_resultante=M.copy()
                ))

            # 3. NORMALIZACIÓN
            # Objetivo: Que el pivote sea exactamente 1.
            pivot_val = M[pivot_row, col]
            
            # Solo dividimos si no es ya 1.
            if not self._es_cero(pivot_val - 1): 
                M.row_op(pivot_row, lambda v, j: v / pivot_val)
                pasos_historial.append(PasoGauss(
                    titulo=f"Normalizar Fila {pivot_row+1}",
                    descripcion=f"Dividimos la fila entre {pivot_val} para obtener un 1 principal.",
                    operacion_matematica=f"F{pivot_row+1} -> F{pivot_row+1} / ({pivot_val})",
                    matriz_resultante=M.copy()
                ))

            # 4. ELIMINACIÓN
            # Objetivo: Hacer ceros arriba y abajo del pivote actual.
            cambios_realizados = False
            descripciones_elim = []
            
            for r in range(rows):
                if r != pivot_row:
                    factor = M[r, col]
                    if not self._es_cero(factor):
                        # Operación fundamental de fila: F_destino = F_destino - k * F_origen
                        M.row_op(r, lambda v, j: v - factor * M[pivot_row, j])
                        descripciones_elim.append(f"F{r+1} - ({factor})*F{pivot_row+1}")
                        cambios_realizados = True
            
            if cambios_realizados:
                pasos_historial.append(PasoGauss(
                    titulo=f"Eliminación en Columna {col+1}",
                    descripcion="Hacemos ceros arriba y abajo del pivote para limpiar la columna.",
                    operacion_matematica=", ".join(descripciones_elim),
                    matriz_resultante=M.copy()
                ))

            # Avanzamos a la siguiente fila diagonal
            pivot_row += 1

        # --- CÁLCULO DE LA VERDAD MATEMÁTICA (RREF CANÓNICA) ---
        # Usamos el motor C de SymPy para la validación final, independiente de nuestros pasos manuales.
        matriz_rref_verdadera, pivotes_cols = matriz_inicial.rref()
        
        # --- DIAGNÓSTICO RIGUROSO (Rouché-Frobenius) ---
        rank_A = matriz_inicial[:, :-1].rank()
        rank_Aumentada = matriz_inicial.rank()
        
        tipo = ""
        sol_txt = ""

        if rank_A < rank_Aumentada:
            tipo = "INCONSISTENTE"
            sol_txt = "El sistema NO tiene solución. Las ecuaciones plantean una contradicción matemática (ej: 0 = 5)."
        elif rank_A == rank_Aumentada:
            if rank_A == num_vars:
                tipo = "UNICA"
                sol_parts = []
                for i, var in enumerate(variables):
                    # En solución única, la última columna de la RREF tiene los valores
                    val = matriz_rref_verdadera[i, -1]
                    sol_parts.append(f"{var} = {val}")
                sol_txt = "Solución Única:\n" + "\n".join(sol_parts)
            else:
                tipo = "INFINITA"
                # Parametrización formal usando linsolve
                A_sys = matriz_inicial[:, :-1]
                B_sys = matriz_inicial[:, -1]
                sym_vars = [sympy.Symbol(v) for v in variables]
                sol_set = sympy.linsolve((A_sys, B_sys), sym_vars)
                
                if sol_set:
                    sol_tuple = list(sol_set)[0]
                    lines = [f"{v} = {expr}" for v, expr in zip(variables, sol_tuple)]
                    params = set().union(*(expr.free_symbols for expr in sol_tuple))
                    sol_txt = (f"Infinitas Soluciones (Grados de libertad: {len(params)}).\n"
                               f"Variables libres (parámetros): {', '.join([str(p) for p in params])}\n"
                               + "\n".join(lines))
                else:
                    sol_txt = "Infinitas soluciones (Error al generar parametrización explícita)."

        return ResultadoGauss(
            tipo_solucion=tipo,
            variables=variables,
            matriz_aumentada_inicial=matriz_inicial,
            matriz_rref_final=matriz_rref_verdadera,
            pasos=pasos_historial,
            solucion_texto=sol_txt,
            advertencias=advertencias
        )

    def _buscar_mejor_pivote(self, matriz: sympy.Matrix, col: int, fila_inicio: int, total_filas: int) -> int:
        """
        Estrategia Pedagógica:
        1. Prioridad A: Buscar un 1.
        2. Prioridad B: Buscar un -1.
        3. Prioridad C: El primer valor no nulo (fallback).
        Retorna el índice de la fila ganadora, o None si toda la columna es cero.
        """
        candidato_fallback = None

        for r in range(fila_inicio, total_filas):
            val = matriz[r, col]
            
            # Si es cero, ignoramos
            if self._es_cero(val):
                continue
            
            # Si encontramos un 1, ¡ALTO! Es el mejor posible. Retornamos ya.
            if val == 1:
                return r
            
            # Si encontramos un -1, es muy bueno, pero seguimos buscando por si aparece un 1 más abajo.
            # (A menos que ya tengamos un candidato -1 previo).
            if val == -1:
                # Guardamos este -1 solo si no teníamos uno antes
                # Pero la prioridad es el 1, así que no retornamos todavía.
                # Truco: Si ya encontramos un fallback que no es 1/-1, este le gana.
                if candidato_fallback is None or matriz[candidato_fallback, col] not in [1, -1]:
                    candidato_fallback = r
            
            # Si es un número cualquiera (ej: 5, 3) y no tenemos candidato aún, lo guardamos.
            elif candidato_fallback is None:
                candidato_fallback = r

        return candidato_fallback

    def _matriz_a_texto(self, matriz: sympy.Matrix) -> str:
        """Formateo accesible con barra separadora."""
        filas_str = []
        rows, cols = matriz.shape
        for i in range(rows):
            vals = [str(matriz[i, j]) for j in range(cols)]
            parte_A = ", ".join(vals[:-1])
            parte_B = vals[-1]
            filas_str.append(f"  [ {parte_A} | {parte_B} ]")
        return "\n".join(filas_str)

    def ExplicarGaussJordan(self, lista_entradas: List[str]) -> str:
        """
        Entrada: Lista de strings. Puede ser ["2x+y=1", "x-y=2"] o ["[[2,1,1],[1,-1,2]]"]
        """
        try:
            # 1. Parsing Inteligente
            M_inicial, variables = self._parsear_sistema_mixto(lista_entradas)
            rows, cols = M_inicial.shape
            
            # 2. Motor
            res = self._resolver_core_gauss(M_inicial, variables)
            
            # 3. Narrativa
            narrativa = []
            narrativa.append("MÉTODO DE GAUSS-JORDAN (Reducción por filas)")
            
            if res.advertencias:
                narrativa.append("AVISO: " + " ".join(res.advertencias))
                
            narrativa.append(f"Sistema de {rows} ecuaciones con {cols-1} variables: {', '.join(variables)}.")
            narrativa.append(f"Matriz Aumentada Inicial:\n{self._matriz_a_texto(res.matriz_aumentada_inicial)}\n")
            
            narrativa.append("--- PASOS DE REDUCCIÓN ---")
            if not res.pasos:
                narrativa.append("(No se requirieron pasos, la matriz ya estaba escalonada).")
            
            for i, paso in enumerate(res.pasos, 1):
                narrativa.append(f"\nPaso {i}: {paso.titulo}")
                narrativa.append(f"   {paso.descripcion}")
                narrativa.append(f"   Operación: {paso.operacion_matematica}")
                narrativa.append(f"   Estado:\n{self._matriz_a_texto(paso.matriz_resultante)}")
            
            narrativa.append("\n--- ESTADO FINAL (RREF) ---")
            narrativa.append(f"Forma Escalonada Reducida (Calculada canónicamente):\n{self._matriz_a_texto(res.matriz_rref_final)}")
            
            narrativa.append(f"\nCONCLUSIÓN: {res.tipo_solucion}")
            if res.tipo_solucion == "INCONSISTENTE":
                narrativa.append("Existe una contradicción (fila de ceros igualada a un número).")
            
            narrativa.append(f"\n{res.solucion_texto}")

            return "\n".join(narrativa)

        except Exception as e:
            return f"Error procesando el sistema: {str(e)}"