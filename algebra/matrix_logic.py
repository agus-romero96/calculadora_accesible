"""
Módulo especializado en Álgebra Matricial Accesible.
Contiene lógica robusta, estructuras de datos inmutables y narrativa pedagógica
para operaciones complejas como la Inversa por Cofactores.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple
import sympy

from i18n import N_, tr

# --- ESTRUCTURAS DE DATOS (Contrato de Datos) ---

@dataclass(frozen=True)
class PasoCofactor:
    fila: int
    columna: int
    submatriz: sympy.Matrix
    determinante_menor: Any
    signo: int
    resultado: Any

@dataclass(frozen=True)
class ResultadoInversa:
    es_posible: bool
    mensaje_error: str = ""
    matriz_original: Optional[sympy.Matrix] = None
    determinante_total: Any = None
    # Guardamos pasos crudos: List[Tuple(signo, elemento, menor)]
    det_pasos_fila1_raw: List[Tuple[int, Any, Any]] = field(default_factory=list)
    ejemplo_cofactor: Optional[PasoCofactor] = None
    matriz_cofactores: Optional[sympy.Matrix] = None
    matriz_adjunta: Optional[sympy.Matrix] = None
    matriz_inversa: Optional[sympy.Matrix] = None

# --- CLASE PRINCIPAL ---

class MotorMatrices:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    def _parsear_matriz_seguro(self, expresion: str) -> sympy.Matrix:
        """
        Convierte texto en objeto Matrix de SymPy.
        MEJORA ACCESIBLE: Soporta entrada natural (espacios y enters).
        """
        if not expresion or not expresion.strip():
            raise ValueError(tr("La expresión está vacía."))

        texto = expresion.strip()

        # --- INTENTO 1: Entrada Natural (Tu formato: 1 2 3) ---
        # Si no empieza con corchete ni 'Matrix', asumimos que es texto plano
        if not texto.startswith("[") and "matrix" not in texto.lower():
            try:
                # Separamos por líneas (filas)
                filas_txt = texto.split('\n')
                matriz_datos = []
                for fila in filas_txt:
                    # Limpiamos espacios y separamos por espacio o coma
                    if not fila.strip():
                        continue
                    # Reemplazamos comas por espacios por si acaso
                    nums = fila.replace(',', ' ').split() 
                    fila_datos = []
                    for n in nums:
                        # Convertimos cada pedazo usando el parser para soportar fracciones/raíces
                        fila_datos.append(self.parser.parsear(n))
                    matriz_datos.append(fila_datos)
                
                return sympy.Matrix(matriz_datos)
            except Exception:
                # Si falla, no pasa nada, intentamos el método clásico
                pass

        # --- INTENTO 2: Entrada Técnica ([[1,2],[3,4]]) ---
        try:
            expr = self.parser.parsear(texto)
            if isinstance(expr, list):
                return sympy.Matrix(expr)
            elif isinstance(expr, sympy.Matrix):
                return expr
            else:
                return sympy.Matrix(expr)
        except Exception as e:
            raise ValueError(tr("No se pudo interpretar como matriz. Pruebe usando espacios entre números y Enter para nueva fila.\nDetalle técnico: {e}", e=str(e)))

    def _matriz_a_texto(self, matriz: sympy.Matrix) -> str:
        """Formatea la matriz para lectura accesible (fila por fila)."""
        if matriz is None:
            return ""
        filas_str = []
        rows, cols = matriz.shape
        for i in range(rows):
            fila_vals = [str(matriz[i, j]) for j in range(cols)]
            filas_str.append(f"  [ {', '.join(fila_vals)} ]")
        return "\n".join(filas_str)

    def _calcular_core_inversa_cofactores(self, matriz: sympy.Matrix) -> ResultadoInversa:
        """Motor matemático puro. Retorna objeto ResultadoInversa inmutable."""
        filas, cols = matriz.shape
        
        # 1. Validación: Cuadrada
        if filas != cols:
             return ResultadoInversa(False, tr("La matriz no es cuadrada (Dimensiones: {filas}x{cols}).", filas=filas, cols=cols))

        # 2. Caso Especial: 1x1 (Blindaje Simbólico)
        if filas == 1:
            elem = matriz[0,0]
            # Usamos simplify + equals(0) para evitar errores con expresiones como (sin(x)^2 + cos(x)^2 - 1)
            if sympy.simplify(elem).equals(0):
                return ResultadoInversa(False, tr("Matriz 1x1 con elemento 0 (o equivalente a 0) no tiene inversa."), matriz, 0)
            
            return ResultadoInversa(
                es_posible=True,
                matriz_original=matriz,
                determinante_total=elem,
                matriz_inversa=sympy.Matrix([[1/elem]])
            )

        # 3. Validación: Tamaño Pedagógico Máximo
        if filas > 4:
            return ResultadoInversa(
                False, 
                tr("El método de cofactores es ineficiente para matrices grandes ({filas}x{cols}). Usa Gauss-Jordan.", filas=filas, cols=cols)
            )
        
        # 4. Determinante Robusto
        det_raw = matriz.det()
        det_simp = sympy.simplify(det_raw)
        
        if det_simp.equals(0):
             return ResultadoInversa(
                es_posible=False, 
                mensaje_error=tr("La matriz es singular (su determinante es 0). No tiene inversa."),
                matriz_original=matriz,
                determinante_total=det_simp
            )

        # 5. Datos para explicación (Determinante - Fila 1)
        pasos_det_raw = []
        for j in range(cols):
            signo = 1 if (0 + j) % 2 == 0 else -1
            elem = matriz[0, j]
            # minor_submatrix es seguro aquí porque filas > 1
            menor = matriz.minor_submatrix(0, j).det()
            pasos_det_raw.append((signo, elem, menor))

        # 6. Cálculo de Cofactores
        mat_cof = sympy.zeros(filas, cols)
        ejemplo_c11 = None
        
        for i in range(filas):
            for j in range(cols):
                menor_mat = matriz.minor_submatrix(i, j)
                det_menor = menor_mat.det()
                signo = (-1)**(i + j)
                cofactor = signo * det_menor
                mat_cof[i, j] = cofactor
                
                # Capturamos el primer elemento para el ejemplo pedagógico
                if i == 0 and j == 0:
                    ejemplo_c11 = PasoCofactor(1, 1, menor_mat, det_menor, 1, cofactor)

        # 7. Finalización
        adjunta = mat_cof.transpose()
        inversa = adjunta * (1 / det_simp)

        return ResultadoInversa(
            es_posible=True,
            matriz_original=matriz,
            determinante_total=det_simp,
            det_pasos_fila1_raw=pasos_det_raw,
            ejemplo_cofactor=ejemplo_c11,
            matriz_cofactores=mat_cof,
            matriz_adjunta=adjunta,
            matriz_inversa=inversa
        )

    def CalcularInversaCofactores(self, expresion: str) -> ResultadoInversa:
        """
        NUEVO CONTRATO: Ya no devuelve texto. Devuelve DATOS PUROS.
        El UI decidirá cómo mostrar esto.
        """
        try:
            # 1. Parsing
            try:
                expr = self._parsear_matriz_seguro(expresion)
            except ValueError as e:
                # Devolvemos un objeto de error controlado
                return ResultadoInversa(False, tr("Error de lectura: {e}", e=str(e)))

            # 2. Ejecución (Delegamos al motor matemático puro)
            return self._calcular_core_inversa_cofactores(expr)

        except Exception as e:
            return ResultadoInversa(False, tr("Error inesperado: {e}", e=str(e)))

    def RenderizarInformeInversa(self, res: ResultadoInversa) -> str:
        """
        NUEVA FUNCIÓN DE PRESENTACIÓN:
        Toma los DATOS y genera el TEXTO ACCESIBLE.
        Esto antes estaba mezclado dentro de la lógica.
        """
        # 1. Manejo de Errores Lógicos
        if not res.es_posible:
            return tr("No se puede calcular la inversa:\n{mensaje_error}", mensaje_error=res.mensaje_error)

        rows, cols = res.matriz_original.shape

        # CASO A: Matriz 1x1
        if rows == 1:
            return "\n".join([
                tr("Matriz de dimensión 1x1:"),
                tr("En este caso, la inversa es simplemente el recíproco del número."),
                tr("Elemento: {elemento}", elemento=res.determinante_total),
                tr("Inversa: 1 / ({elemento}) = {inversa}", elemento=res.determinante_total, inversa=res.matriz_inversa[0, 0]),
            ])

        # CASO B: Matriz NxN (Narrativa completa)
        pasos = []
        pasos.append(tr("MÉTODO DE LA MATRIZ ADJUNTA (COFACTORES)"))
        pasos.append(tr("Análisis inicial: Matriz cuadrada de {rows} filas por {cols} columnas.", rows=rows, cols=cols))
        
        # Fase 1: Determinante
        pasos.append(tr("1. DETERMINANTE (Expandiendo Fila 1)"))
        txt_suma_parts = []
        for s, e, m in res.det_pasos_fila1_raw:
            signo_txt = "+" if s == 1 else "-" 
            txt_suma_parts.append(f"({signo_txt}1 * {e} * {m})")
        
        pasos.append("   " + tr("Operación: {operacion}", operacion=" + ".join(txt_suma_parts)))
        pasos.append(tr("   Valor Determinante = {determinante_total}", determinante_total=res.determinante_total))
        
        # Fase 2: Cofactores (Ejemplo)
        if res.ejemplo_cofactor:
            c11 = res.ejemplo_cofactor
            pasos.append(tr("\n2. MATRIZ DE COFACTORES"))
            pasos.append(tr("   [Ejemplo detallado: Fila 1, Columna 1]"))
            pasos.append("     - " + tr("Signo: {signo}", signo=tr("Positivo (+)") if c11.signo > 0 else tr("Negativo (-)")))
            pasos.append(tr("     - Menor: {determinante_menor}", determinante_menor=c11.determinante_menor))
            pasos.append(tr("     - Cofactor: {resultado}", resultado=c11.resultado))
            pasos.append(tr("   Matriz de Cofactores Completa:\n{matriz_cofactores}", matriz_cofactores=self._matriz_a_texto(res.matriz_cofactores)))

        # Fase 3: Adjunta
        pasos.append(tr("\n3. MATRIZ ADJUNTA (Transpuesta de Cofactores)"))
        pasos.append(f"   {self._matriz_a_texto(res.matriz_adjunta)}")

        # Fase 4: Resultado (SECCIÓN MODIFICADA PARA NARRATIVA EXAMEN)
        pasos.append(tr("\n4. CÁLCULO FINAL Y SIMPLIFICACIÓN"))
        pasos.append(tr("   Para obtener la matriz inversa, aplicamos la definición:"))
        pasos.append(tr("   A⁻¹ = (1 / |A|) · Adj(A)"))
        pasos.append(tr("   Sustituyendo valores: A⁻¹ = (1 / {determinante_total}) · Adj(A)", determinante_total=res.determinante_total))
        pasos.append(tr("   Esto implica dividir cada elemento de la Matriz Adjunta entre el determinante ({determinante_total}).", determinante_total=res.determinante_total))
        pasos.append(tr("   Simplificando cada fracción resultante, obtenemos la solución definitiva:"))
        pasos.append(f"\n{self._matriz_a_texto(res.matriz_inversa)}")

        return "\n".join([
            tr("Resultado Inversa ({filas}x{columnas}):", filas=rows, columnas=cols),
            self._matriz_a_texto(res.matriz_inversa),
            "-" * 40,
        ] + pasos)