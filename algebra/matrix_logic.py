"""
Módulo especializado en Álgebra Matricial Accesible.
Contiene lógica robusta, estructuras de datos inmutables y narrativa pedagógica
para operaciones complejas como la Inversa por Cofactores.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple
import sympy

from calculo.pasos import PasoCalculo, entre_parentesis, texto, texto_paso
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

    # --- Explicación (formato de calculo/pasos.py) ---

    @staticmethod
    def _fila(valores: List[Any]) -> str:
        return f"[ {', '.join(texto(v) for v in valores)} ]"

    def _filas(self, matriz: sympy.Matrix) -> List[str]:
        return [tr("Fila {i}: {fila}", i=i + 1, fila=self._fila(list(matriz.row(i)))) for i in range(matriz.rows)]

    def _det_2x2(self, m: sympy.Matrix) -> str:
        """'1*4 - 2*3 = 4 - 6 = -2'."""
        a, b, c, d = m[0, 0], m[0, 1], m[1, 0], m[1, 1]
        productos = f"{entre_parentesis(a)}*{entre_parentesis(d)} - {entre_parentesis(b)}*{entre_parentesis(c)}"
        valor = texto(sympy.simplify(a * d - b * c))
        if not ((a * d).is_number and (b * c).is_number):
            # Con letras, los productos ya están hechos: a*d - b*c, sin una cuenta intermedia que lo repita
            return f"{productos} = {valor}" if productos != valor else productos
        intermedio = f"{texto(a * d)} - {entre_parentesis(b * c)}"
        return f"{productos} = {intermedio} = {valor}" if intermedio != valor else f"{productos} = {valor}"

    @staticmethod
    def _suma_productos(pares: List[Tuple[Any, Any]]) -> str:
        """'2*1 + 0*(-1) + 1*3 = 2 + 0 + 3 = 5': los productos, sus valores y la suma."""
        productos = " + ".join(f"{entre_parentesis(a)}*{entre_parentesis(b)}" for a, b in pares)
        valores = " + ".join(entre_parentesis(sympy.simplify(a * b)) if i else texto(sympy.simplify(a * b))
                             for i, (a, b) in enumerate(pares))
        total = texto(sympy.simplify(sum(a * b for a, b in pares)))
        return f"{productos} = {valores} = {total}" if valores != total else f"{productos} = {total}"

    def _menor(self, matriz: sympy.Matrix, i: int, j: int) -> Tuple[Any, str]:
        """(M_ij, cómo se calcula): la submatriz sin la fila i y la columna j, y su determinante."""
        sub = matriz.minor_submatrix(i, j)
        valor = sympy.simplify(sub.det())
        filas = "; ".join(self._fila(list(sub.row(k))) for k in range(sub.rows))
        if sub.rows == 1:
            cuenta = tr("queda {submatriz}, así que M{i}{j} = {valor}", submatriz=filas, i=i + 1, j=j + 1, valor=texto(valor))
        elif sub.rows == 2:
            cuenta = tr("queda {submatriz}, así que M{i}{j} = {cuenta}", submatriz=filas, i=i + 1, j=j + 1,
                        cuenta=self._det_2x2(sub))
        else:
            cuenta = tr("queda {submatriz}, cuyo determinante es M{i}{j} = {valor}", submatriz=filas, i=i + 1, j=j + 1,
                        valor=texto(valor))
        return valor, cuenta

    def _paso_determinante(self, matriz: sympy.Matrix, det: Any) -> PasoCalculo:
        n = matriz.rows
        if n == 2:
            return PasoCalculo(
                tr("Determinante"),
                regla=tr("el determinante de una matriz 2x2 [a, b; c, d] es a*d - b*c. Una matriz tiene inversa solo si "
                         "su determinante no es 0."),
                partes=tr("a = {a}, b = {b}, c = {c} y d = {d}.", a=texto(matriz[0, 0]), b=texto(matriz[0, 1]),
                          c=texto(matriz[1, 0]), d=texto(matriz[1, 1])),
                calculo=(tr("det(A) = {cuenta}.", cuenta=self._det_2x2(matriz)),),
                queda=tr("det(A) = {det}", det=texto(det)))
        calculo, terminos = [], []
        for j in range(n):
            menor, cuenta = self._menor(matriz, 0, j)
            signo = (-1) ** j
            cofactor = signo * menor
            calculo.append(tr("Columna {j}: quitamos la fila 1 y la columna {j}, {cuenta}; C1{j} = ({signo}1)*{menor} = {cofactor}.",
                              j=j + 1, cuenta=cuenta, signo="+" if signo > 0 else "-", menor=entre_parentesis(menor),
                              cofactor=texto(cofactor)))
            terminos.append((matriz[0, j], cofactor))
        calculo.append(tr("det(A) = a11*C11 + a12*C12 + ... = {suma}.", suma=self._suma_productos(terminos)))
        return PasoCalculo(
            tr("Determinante"),
            regla=tr("el determinante se desarrolla por la primera fila: det(A) = a11*C11 + a12*C12 + ..., donde C1j = "
                     "(-1)^(1+j)*M1j y M1j es el determinante de la matriz que queda al quitar la fila 1 y la columna j. "
                     "Una matriz tiene inversa solo si su determinante no es 0."),
            partes=tr("la primera fila es {fila}.", fila=self._fila(list(matriz.row(0)))),
            calculo=tuple(calculo),
            queda=tr("det(A) = {det}", det=texto(det)))

    def _pasos_inversa(self, res: ResultadoInversa) -> List[PasoCalculo]:
        A, det, n = res.matriz_original, res.determinante_total, res.matriz_original.rows
        pasos = [self._paso_determinante(A, det)]

        calculo = []
        for i in range(n):
            for j in range(n):
                menor, cuenta = self._menor(A, i, j)
                signo = (-1) ** (i + j)
                calculo.append(tr("C{i}{j}: quitamos la fila {i} y la columna {j}, {cuenta}; el signo es {signo}, así que "
                                  "C{i}{j} = ({signo}1)*{menor} = {cofactor}.", i=i + 1, j=j + 1, cuenta=cuenta,
                                  signo="+" if signo > 0 else "-", menor=entre_parentesis(menor),
                                  cofactor=texto(res.matriz_cofactores[i, j])))
        pasos.append(PasoCalculo(
            tr("Matriz de cofactores"),
            regla=tr("cada elemento se cambia por su cofactor: C_ij = (-1)^(i+j)*M_ij, donde M_ij es el determinante de "
                     "la matriz que queda al quitar la fila i y la columna j. El signo alterna como un tablero: + en "
                     "(1,1), - en (1,2)..."),
            partes=tr("A es una matriz {n}x{n}: hay {total} cofactores.", n=n, total=n * n),
            calculo=tuple(calculo) + (tr("La matriz de cofactores queda:"),) + tuple(self._filas(res.matriz_cofactores)),
            queda="; ".join(self._fila(list(res.matriz_cofactores.row(i))) for i in range(n))))

        pasos.append(PasoCalculo(
            tr("Matriz adjunta"),
            regla=tr("la adjunta es la traspuesta de la matriz de cofactores: la fila i pasa a ser la columna i."),
            partes=tr("se trasponen los cofactores."),
            calculo=tuple(tr("Fila {i} de los cofactores, {fila}, pasa a ser la columna {i}.", i=i + 1,
                             fila=self._fila(list(res.matriz_cofactores.row(i)))) for i in range(n))
                    + (tr("La adjunta queda:"),) + tuple(self._filas(res.matriz_adjunta)),
            queda="; ".join(self._fila(list(res.matriz_adjunta.row(i))) for i in range(n))))

        calculo = []
        for i in range(n):
            cuentas = []
            for j in range(n):
                division = f"{entre_parentesis(res.matriz_adjunta[i, j])}/{entre_parentesis(det)}"
                valor = texto(res.matriz_inversa[i, j])
                cuentas.append(f"{division} = {valor}" if division != valor else valor)
            calculo.append(tr("Fila {i}: {cuentas}.", i=i + 1, cuentas="; ".join(cuentas)))
        pasos.append(PasoCalculo(
            tr("Dividir entre el determinante"),
            regla=tr("A^(-1) = (1/det(A))*Adj(A): cada elemento de la adjunta se divide entre el determinante."),
            partes=tr("det(A) = {det}.", det=texto(det)),
            calculo=tuple(calculo),
            queda="; ".join(self._fila(list(res.matriz_inversa.row(i))) for i in range(n))))

        producto = A * res.matriz_inversa
        calculo = []
        if n <= 3:
            for i in range(n):
                for j in range(n):
                    calculo.append(tr("Fila {i} por columna {j}: {suma}.", i=i + 1, j=j + 1,
                                      suma=self._suma_productos([(A[i, k], res.matriz_inversa[k, j]) for k in range(n)])))
        calculo.append(tr("A por A^(-1) es la identidad: la inversa es correcta.")
                       if producto.applyfunc(sympy.simplify) == sympy.eye(n)
                       else tr("A por A^(-1) NO es la identidad."))
        pasos.append(PasoCalculo(
            tr("Comprobación"),
            regla=tr("una matriz por su inversa da la identidad: unos en la diagonal y ceros fuera. Cada elemento del "
                     "producto es una fila de A por una columna de A^(-1) (se multiplican elemento a elemento y se suman)."),
            partes=tr("multiplicamos A por la inversa obtenida."),
            calculo=tuple(calculo),
            queda=tr("A*A^(-1) = I")))
        return pasos

    def RenderizarInformeInversa(self, res: ResultadoInversa) -> str:
        """El texto accesible: RESULTADO primero y después el paso a paso."""
        A = res.matriz_original
        encabezado = [tr("MÉTODO: {metodo}", metodo=tr("matriz adjunta (cofactores)"))]
        if A is not None:
            encabezado.append(tr("Matriz {filas}x{columnas}:", filas=A.rows, columnas=A.cols))
            encabezado += self._filas(A)

        if not res.es_posible:
            # Singular: el determinante explica por qué no hay inversa
            if A is not None and A.rows == A.cols and A.rows > 1 and res.determinante_total is not None:
                pasos = [self._paso_determinante(A, res.determinante_total), PasoCalculo(
                    tr("Conclusión"),
                    regla=tr("A^(-1) = (1/det(A))*Adj(A): si el determinante es 0, habría que dividir entre 0, así que "
                             "la matriz no tiene inversa (es singular)."),
                    partes=tr("det(A) = 0."),
                    queda=tr("no tiene inversa"))]
                return "\n".join([tr("RESULTADO: {valor}", valor=tr("No tiene inversa (determinante 0)")), "=" * 30]
                                  + encabezado + ["", tr("PASO A PASO:")]
                                  + [texto_paso(i, p) for i, p in enumerate(pasos, 1)])
            return tr("No se puede calcular la inversa:\n{mensaje_error}", mensaje_error=res.mensaje_error)

        resultado = [tr("RESULTADO:")] + [self._fila(list(res.matriz_inversa.row(i))) for i in range(A.rows)]
        if A.rows == 1:
            pasos = [PasoCalculo(
                tr("Inversa de un número"),
                regla=tr("una matriz 1x1 es un número: su inversa es 1 entre ese número."),
                partes=tr("el elemento es {elemento}.", elemento=texto(A[0, 0])),
                calculo=(tr("La inversa es 1/{elemento}{igual}.", elemento=entre_parentesis(A[0, 0]),
                            igual="" if f"1/{entre_parentesis(A[0, 0])}" == texto(res.matriz_inversa[0, 0])
                            else f" = {texto(res.matriz_inversa[0, 0])}"),),
                queda=self._fila([res.matriz_inversa[0, 0]]))]
        else:
            pasos = self._pasos_inversa(res)
        return "\n".join(resultado + ["=" * 30] + encabezado + ["", tr("PASO A PASO:")]
                         + [texto_paso(i, p) for i, p in enumerate(pasos, 1)])
