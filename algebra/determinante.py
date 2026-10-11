"""
Determinante de una matriz cuadrada por cofactores (desarrollo de Laplace), explicado con el
formato de calculo/pasos.py (Regla, En este caso, las cuentas y Queda):

  - 1x1: el propio elemento. 2x2: a*d - b*c, con las cuentas.
  - 3x3 y 4x4: se desarrolla por la fila o columna con más ceros (un elemento 0 anula su
    término y su menor no hace falta). Cada menor 2x2 se calcula en la misma línea; cada menor
    3x3 (en una 4x4) se desarrolla en sus propios pasos, sin dar su valor de golpe. Después,
    cada cofactor C_ij = (-1)^(i+j)*M_ij con su signo, y la suma de los productos.

Las piezas comunes (leer la matriz, escribir filas, a*d - b*c, sumas de productos) son las de
la inversa (algebra/matrix_logic.py). El valor se compara con el de SymPy; matrices de más de
4x4 se calculan sin pasos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import sympy

from algebra.matrix_logic import MotorMatrices
from calculo.pasos import PasoCalculo, entre_parentesis, texto, texto_paso
from i18n import tr

# Más allá, el desarrollo por cofactores es demasiado largo para leerlo
TAMANO_MAXIMO = 4


@dataclass
class ResultadoDeterminante:
    texto: str
    es_error: bool = False
    valor: Any = None
    matriz: Any = None
    avisos: List[str] = field(default_factory=list)


def _nombre_linea(tipo: str, k: int) -> str:
    return tr("la fila {k}", k=k + 1) if tipo == "fila" else tr("la columna {k}", k=k + 1)


class MotorDeterminante:
    def __init__(self, parser_compartido):
        self.matrices = MotorMatrices(parser_compartido)

    # --- Fachada ---

    def resolver(self, entrada: str) -> ResultadoDeterminante:
        try:
            matriz = self.matrices._parsear_matriz_seguro(entrada)
            if matriz.rows != matriz.cols:
                raise ValueError(tr("La matriz no es cuadrada ({filas}x{columnas}): el determinante solo existe para "
                                    "matrices cuadradas.", filas=matriz.rows, columnas=matriz.cols))
            if matriz.rows == 0:
                raise ValueError(tr("La matriz está vacía."))
        except ValueError as e:
            return ResultadoDeterminante(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except Exception as e:
            return ResultadoDeterminante(tr("Error del Sistema: {error}", error=str(e)), es_error=True)

        verdad = sympy.simplify(matriz.det())
        avisos: List[str] = []
        pasos: List[PasoCalculo] = []
        if matriz.rows > TAMANO_MAXIMO:
            avisos.append(tr("NOTA: el desarrollo por cofactores se explica hasta matrices 4x4; para {n}x{n} serían "
                             "demasiados pasos. El valor lo calcula SymPy.", n=matriz.rows))
        else:
            try:
                pasos, valor = self._explicar(matriz, "A")
                if sympy.simplify(valor - verdad) != 0:
                    avisos.append(tr("AVISO: la explicación no llegó al resultado de SymPy; se muestra el resultado "
                                     "sin pasos."))
                    pasos = []
            except Exception:
                avisos.append(tr("AVISO: no se pudo explicar paso a paso; el resultado es el que calcula SymPy."))
                pasos = []

        lineas = [tr("RESULTADO: {valor}", valor=f"det(A) = {texto(verdad)}")] + avisos + ["=" * 30,
                  tr("MÉTODO: {metodo}", metodo=tr("desarrollo por cofactores")),
                  tr("Matriz {filas}x{columnas}:", filas=matriz.rows, columnas=matriz.cols)]
        lineas += self.matrices._filas(matriz)
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoDeterminante("\n".join(lineas), valor=verdad, matriz=matriz, avisos=avisos)

    # --- La explicación ---

    @staticmethod
    def _mejor_linea(matriz: sympy.Matrix) -> Tuple[str, int, int]:
        """(tipo, índice, ceros) de la fila o columna con más ceros; a igualdad, la fila 1."""
        mejor = ("fila", 0, sum(1 for v in matriz.row(0) if v == 0))
        for tipo, total in (("fila", matriz.rows), ("columna", matriz.cols)):
            for k in range(total):
                linea = matriz.row(k) if tipo == "fila" else matriz.col(k)
                ceros = sum(1 for v in linea if v == 0)
                if ceros > mejor[2]:
                    mejor = (tipo, k, ceros)
        return mejor

    def _explicar(self, matriz: sympy.Matrix, nombre: str) -> Tuple[List[PasoCalculo], Any]:
        """(pasos, valor) del determinante de matriz; nombre: 'A' o el del menor ('M12')."""
        n = matriz.rows
        de = tr("de {nombre}", nombre=nombre)
        # Dentro de un menor, otras letras: su elemento (2, 2) no debe sonar igual que a22 de A
        principal = nombre == "A"
        a, c, m = ("a", "C", "M") if principal else ("b", "D", "N")
        if n == 1:
            valor = matriz[0, 0]
            return [PasoCalculo(
                tr("Determinante {de}", de=de),
                regla=tr("el determinante de una matriz 1x1 es su único elemento."),
                partes=tr("el elemento es {elemento}.", elemento=texto(valor)),
                queda=f"det({nombre}) = {texto(valor)}")], valor
        if n == 2:
            valor = sympy.simplify(matriz.det())
            return [PasoCalculo(
                tr("Determinante {de}", de=de),
                regla=tr("el determinante de una matriz 2x2 [a, b; c, d] es a*d - b*c: el producto de la diagonal "
                         "principal menos el de la otra diagonal."),
                partes=tr("a = {a}, b = {b}, c = {c} y d = {d}.", a=texto(matriz[0, 0]), b=texto(matriz[0, 1]),
                          c=texto(matriz[1, 0]), d=texto(matriz[1, 1])),
                calculo=(f"det({nombre}) = {self.matrices._det_2x2(matriz)}.",),
                queda=f"det({nombre}) = {texto(valor)}")], valor

        tipo, k, ceros = self._mejor_linea(matriz)
        linea = _nombre_linea(tipo, k)
        posiciones = [(k, j) for j in range(n)] if tipo == "fila" else [(i, k) for i in range(n)]
        no_nulos = [(i, j) for i, j in posiciones if matriz[i, j] != 0]
        valores = [matriz[i, j] for i, j in posiciones]
        if ceros:
            partes = tr("{linea} es {elementos}: tiene {ceros} ceros, y ninguna otra tiene más (se desarrolla por ella).",
                        linea=linea, elementos=self.matrices._fila(valores), ceros=ceros) if ceros > 1 else \
                tr("{linea} es {elementos}: tiene un cero, y ninguna otra tiene más (se desarrolla por ella).",
                   linea=linea, elementos=self.matrices._fila(valores))
        else:
            partes = tr("ninguna fila ni columna tiene ceros: se desarrolla por la fila 1, {elementos}.",
                        elementos=self.matrices._fila(valores))
        calculo = [] if principal else [
            tr("Para no confundirlos con los de A, en {nombre} los elementos se llaman b_ij, sus menores N_ij y sus "
               "cofactores D_ij.", nombre=nombre)]
        calculo += [tr("{a}{i}{j} = 0: su término vale 0 y no hace falta su menor.", a=a, i=i + 1, j=j + 1)
                    for i, j in posiciones if matriz[i, j] == 0]
        plan = " + ".join(f"{a}{i + 1}{j + 1}*{c}{i + 1}{j + 1}" for i, j in no_nulos) or "0"
        pasos = [PasoCalculo(
            tr("Desarrollo por cofactores {de}", de=de),
            regla=tr("el determinante se puede desarrollar por cualquier fila o columna: es la suma de cada elemento "
                     "por su cofactor, C_ij = (-1)^(i+j)*M_ij, donde M_ij es el determinante de la matriz que queda al "
                     "quitar la fila i y la columna j. Conviene la línea con más ceros: un elemento 0 anula su término.")
            if principal else tr("el mismo desarrollo por cofactores, ahora para el menor {nombre}.", nombre=nombre),
            partes=partes,
            calculo=tuple(calculo),
            queda=f"det({nombre}) = {plan}")]
        if not no_nulos:
            pasos.append(PasoCalculo(
                tr("Línea de ceros"),
                regla=tr("si toda una fila o columna es 0, todos los términos valen 0: el determinante es 0."),
                partes=tr("{linea} solo tiene ceros.", linea=linea),
                queda=f"det({nombre}) = 0"))
            return pasos, sympy.Integer(0)

        # Menores 3x3 (en una 4x4): cada uno en sus propios pasos
        menores = {}
        for i, j in no_nulos:
            sub = matriz.minor_submatrix(i, j)
            if sub.rows >= 3:
                sub_pasos, valor_menor = self._explicar(sub, f"{m}{i + 1}{j + 1}")
                pasos.extend(sub_pasos)
                menores[(i, j)] = valor_menor

        # Cofactores y suma
        lineas, terminos = [], []
        for i, j in no_nulos:
            sub = matriz.minor_submatrix(i, j)
            filas = "; ".join(self.matrices._fila(list(sub.row(r))) for r in range(sub.rows))
            menor_nombre = f"{m}{i + 1}{j + 1}"
            if sub.rows == 1:
                menor = sub[0, 0]
                cuenta = tr("queda {submatriz}, así que {menor} = {valor}", submatriz=filas, menor=menor_nombre,
                            valor=texto(menor))
            elif sub.rows == 2:
                menor = sympy.simplify(sub.det())
                cuenta = tr("queda {submatriz}, así que {menor} = {cuenta}", submatriz=filas, menor=menor_nombre,
                            cuenta=self.matrices._det_2x2(sub))
            else:
                menor = menores[(i, j)]
                cuenta = tr("queda {submatriz}, y {menor} = {valor} (calculado en los pasos anteriores)",
                            submatriz=filas, menor=menor_nombre, valor=texto(menor))
            signo = (-1) ** (i + j)
            cofactor = signo * menor
            lineas.append(tr("{a}{i}{j} = {elemento}: quitamos la fila {i} y la columna {j}, {cuenta}. Signo: "
                             "(-1)^({i}+{j}) = {signo}, así que {c}{i}{j} = {signo}*{menor} = {cofactor}.",
                             a=a, c=c, i=i + 1, j=j + 1, elemento=texto(matriz[i, j]), cuenta=cuenta, signo=signo,
                             menor=entre_parentesis(menor), cofactor=texto(cofactor)))
            terminos.append((matriz[i, j], cofactor))
        valor = sympy.simplify(sum(a * c for a, c in terminos))
        lineas.append(f"det({nombre}) = {plan} = {self.matrices._suma_productos(terminos)}.")
        pasos.append(PasoCalculo(
            tr("Cofactores y suma {de}", de=de),
            regla=tr("cada término es el elemento por su cofactor; el signo (-1)^(i+j) alterna como un tablero de "
                     "ajedrez: + en la esquina de arriba a la izquierda.") if principal else
            tr("cada término del menor {nombre}, como antes.", nombre=nombre),
            partes=tr("se desarrolla por {linea}.", linea=linea),
            calculo=tuple(lineas),
            queda=f"det({nombre}) = {texto(valor)}"))
        return pasos, valor
