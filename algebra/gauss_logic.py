"""
Sistemas de ecuaciones por Gauss-Jordan, explicados con el formato de calculo/pasos.py
(Regla, En este caso, las cuentas, Queda).

Cada operación de fila muestra la cuenta de cada elemento ("F2 → F2 - (-3)*F1:
[-3 - (-3)*1, ...] = [0, ...]"), para que no haya que reconstruirla de cabeza. Al final se
lee la solución en la forma escalonada reducida y se comprueba en las ecuaciones originales.
El resultado (la verdad matemática) es el de SymPy: rref() y el rango (Rouché-Frobenius).
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import sympy

from algebra.ecuaciones import comprobar, ecuacion_texto
from calculo.pasos import PasoCalculo, entre_parentesis, texto, texto_paso
from i18n import N_, tr

# Tipos de solución
UNICA = N_("UNICA")
INFINITA = N_("INFINITA")
INCONSISTENTE = N_("INCONSISTENTE")


@dataclass(frozen=True)
class ResultadoGauss:
    tipo_solucion: str       # UNICA, INFINITA o INCONSISTENTE
    variables: List[str]
    matriz_aumentada_inicial: sympy.Matrix
    matriz_rref_final: sympy.Matrix  # La verdad matemática (SymPy .rref())
    pasos: List[PasoCalculo] = field(default_factory=list)
    resultado: List[str] = field(default_factory=list)  # líneas del RESULTADO
    advertencias: List[str] = field(default_factory=list)
    # Solución como objetos SymPy (para exportar): lista de Eq(variable, valor) o EmptySet
    solucion: Any = None


def fila_texto(fila: List[Any]) -> str:
    """[ 2, 1, -1 | 8 ]: coeficientes, barra y término independiente."""
    valores = [texto(v) for v in fila]
    return f"[ {', '.join(valores[:-1])} | {valores[-1]} ]"


def matriz_lineas(M: sympy.Matrix) -> List[str]:
    return [tr("Fila {i}: {fila}", i=i + 1, fila=fila_texto(list(M.row(i)))) for i in range(M.rows)]


class MotorGauss:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    def _es_cero(self, valor) -> bool:
        return sympy.simplify(valor).equals(0)

    # --- Lectura ---

    def _parsear_sistema_mixto(self, lista_entradas: List[str]) -> Tuple[sympy.Matrix, List[str], Optional[List]]:
        """
        (matriz aumentada, nombres de las incógnitas, ecuaciones (izquierda, derecha) o None).
        Acepta ecuaciones ("2x + y = 10") o una matriz aumentada directa ("[[1,2,10]]").
        """
        if len(lista_entradas) == 1 and ("[[" in lista_entradas[0] or "matrix" in lista_entradas[0].lower()):
            try:
                expr = self.parser.parsear(lista_entradas[0])
                if isinstance(expr, list) or isinstance(expr, sympy.Matrix):
                    M = sympy.Matrix(expr)
                    cols = M.shape[1]
                    nombres = ["x", "y", "z"][:cols - 1] if cols - 1 <= 3 else [f"x{i + 1}" for i in range(cols - 1)]
                    return M, nombres, None
            except Exception:
                pass  # no era una matriz: se intenta como ecuaciones

        try:
            ecuaciones = []
            todas = set()
            for txt in lista_entradas:
                if not txt.strip():
                    continue
                if "=" in txt:
                    partes = txt.split("=")
                    if len(partes) != 2:
                        raise ValueError(tr("La ecuación '{strip}' debe tener exactamente un signo '='.", strip=txt.strip()))
                    izquierda, derecha = self.parser.parsear(partes[0]).doit(), self.parser.parsear(partes[1]).doit()
                else:
                    izquierda, derecha = self.parser.parsear(txt).doit(), sympy.S.Zero  # "= 0" si no hay igual
                ecuaciones.append((izquierda, derecha))
                todas.update((izquierda - derecha).free_symbols)
            if not ecuaciones:
                raise ValueError(tr("No se detectaron ecuaciones válidas."))
            variables = sorted(todas, key=lambda s: s.name)
            A, B = sympy.linear_eq_to_matrix([sympy.Eq(i, d) for i, d in ecuaciones], variables)
            return A.row_join(B), [v.name for v in variables], ecuaciones
        except Exception as e:
            raise ValueError(tr("No se pudo interpretar el sistema: {e}", e=str(e)))

    # --- Pasos ---

    def _paso_matriz(self, M: sympy.Matrix, variables: List[str], ecuaciones: Optional[List]) -> PasoCalculo:
        if ecuaciones:
            calculo = [tr("Ecuación {i}: {ecuacion} → fila {fila}.", i=i, ecuacion=ecuacion_texto(*e),
                          fila=fila_texto(list(M.row(i - 1)))) for i, e in enumerate(ecuaciones, 1)]
        else:
            calculo = matriz_lineas(M)
        return PasoCalculo(
            tr("Matriz aumentada"),
            regla=tr("cada ecuación es una fila: los coeficientes de las incógnitas, siempre en el mismo orden (0 si "
                     "una incógnita no aparece), y tras la barra el término independiente, el número de la derecha. "
                     "El objetivo es conseguir, con operaciones de fila, unos en la diagonal y ceros en el resto."),
            partes=tr("{filas} ecuaciones con {n} incógnitas, en este orden: {variables}.", filas=M.rows, n=M.cols - 1,
                      variables=", ".join(variables)),
            calculo=tuple(calculo),
            queda="; ".join(fila_texto(list(M.row(i))) for i in range(M.rows)))

    def _paso_intercambio(self, M: sympy.Matrix, col: int, fila: int, candidata: int, anterior: Any) -> PasoCalculo:
        motivo = (tr("en la fila {f} hay un 0 en la columna {c}: no sirve de pivote, y la fila {otra} tiene {valor}.",
                     f=fila + 1, c=col + 1, otra=candidata + 1, valor=texto(M[fila, col]))
                  if self._es_cero(anterior) else
                  tr("en la columna {c}, la fila {otra} tiene {valor}, un pivote más cómodo que {anterior}: con 1 o -1 "
                     "no aparecen fracciones.", c=col + 1, otra=candidata + 1, valor=texto(M[fila, col]),
                     anterior=texto(anterior)))
        return PasoCalculo(
            tr("Intercambiar las filas {a} y {b}", a=fila + 1, b=candidata + 1),
            regla=tr("intercambiar dos filas no cambia las soluciones: es escribir las ecuaciones en otro orden."),
            partes=motivo,
            calculo=(tr("F{a} ↔ F{b}.", a=fila + 1, b=candidata + 1),) + tuple(matriz_lineas(M)),
            queda="; ".join(fila_texto(list(M.row(i))) for i in range(M.rows)))

    def _paso_normalizar(self, antes: List[Any], despues: List[Any], fila: int, col: int, pivote: Any) -> PasoCalculo:
        if pivote == -1:
            cuenta = tr("F{f} → (-1)*F{f}: {cuentas} = {fila}.", f=fila + 1,
                        cuentas=self._lista([f"(-1)*{entre_parentesis(v)}" for v in antes]),
                        fila=fila_texto(despues))
        else:
            divisiones = [f"{entre_parentesis(v)}/{entre_parentesis(pivote)}" for v in antes]
            cuenta = tr("F{f} → F{f}/{p}: {cuentas} = {fila}.", f=fila + 1, p=entre_parentesis(pivote),
                        cuentas=self._lista(divisiones), fila=fila_texto(despues))
        return PasoCalculo(
            tr("Hacer 1 el pivote de la fila {f}", f=fila + 1),
            regla=tr("multiplicar o dividir una fila entre un número distinto de 0 no cambia las soluciones: se divide "
                     "la fila del pivote entre el propio pivote para que valga 1."),
            partes=tr("el pivote de la columna {c} está en la fila {f} y vale {p}.", c=col + 1, f=fila + 1,
                      p=texto(pivote)),
            calculo=(cuenta,),
            queda=tr("F{f} = {fila}", f=fila + 1, fila=fila_texto(despues)))

    def _paso_eliminar(self, M: sympy.Matrix, cuentas: List[str], fila: int, col: int, filas: List[int]) -> PasoCalculo:
        return PasoCalculo(
            tr("Hacer ceros en la columna {c}", c=col + 1),
            regla=tr("restar a una fila un múltiplo de otra no cambia las soluciones. Con F_i → F_i - a*F_p, donde a es "
                     "el número de la fila i en la columna del pivote (que vale 1), ese número pasa a ser 0."),
            partes=tr("el pivote está en la fila {f}; hay que hacer 0 la columna {c} en {filas}.", f=fila + 1,
                      c=col + 1, filas=self._enumerar([tr("la fila {i}", i=i + 1) for i in filas])),
            calculo=tuple(cuentas) + (tr("La matriz queda:"),) + tuple(matriz_lineas(M)),
            queda="; ".join(fila_texto(list(M.row(i))) for i in range(M.rows)))

    @staticmethod
    def _enumerar(partes: List[str]) -> str:
        """'la fila 2', 'la fila 2 y la fila 3', 'la fila 1, la fila 2 y la fila 4'."""
        return partes[0] if len(partes) == 1 else tr("{lista} y {ultimo}", lista=", ".join(partes[:-1]), ultimo=partes[-1])

    @staticmethod
    def _lista(cuentas: List[str]) -> str:
        """[c1, c2 | c3]: las cuentas de cada elemento de una fila."""
        return f"[{', '.join(cuentas[:-1])} | {cuentas[-1]}]"

    @staticmethod
    def _cuenta_eliminacion(antes: List[Any], pivote: List[Any], factor: Any, despues: List[Any], fila: int, fila_p: int) -> str:
        restas = [f"{texto(e)} - {entre_parentesis(factor)}*{entre_parentesis(p)}" for e, p in zip(antes, pivote)]
        return tr("F{i} → F{i} - {a}*F{p}: {cuentas} = {fila}.", i=fila + 1, a=entre_parentesis(factor), p=fila_p + 1,
                  cuentas=MotorGauss._lista(restas), fila=fila_texto(despues))

    # --- Motor ---

    def _resolver_core_gauss(self, matriz_inicial: sympy.Matrix, variables: List[str],
                             ecuaciones: Optional[List] = None) -> ResultadoGauss:
        M = matriz_inicial.copy()
        rows, cols = M.shape
        num_vars = cols - 1
        pasos = [self._paso_matriz(M, variables, ecuaciones)]
        advertencias = []
        if rows > 5:
            advertencias.append(tr("Sistema grande ({rows} ecuaciones). La explicación detallada puede ser extensa.", rows=rows))

        pivot_row = 0
        for col in range(num_vars):
            if pivot_row >= rows:
                break
            candidata = self._buscar_mejor_pivote(M, col, pivot_row, rows)
            if candidata is None:
                continue  # columna sin pivote: esa incógnita será libre

            if candidata != pivot_row:
                anterior = M[pivot_row, col]
                M.row_swap(pivot_row, candidata)
                pasos.append(self._paso_intercambio(M, col, pivot_row, candidata, anterior))

            pivote = M[pivot_row, col]
            if not self._es_cero(pivote - 1):
                antes = list(M.row(pivot_row))
                M.row_op(pivot_row, lambda v, j: sympy.simplify(v / pivote))
                pasos.append(self._paso_normalizar(antes, list(M.row(pivot_row)), pivot_row, col, pivote))

            cuentas, filas = [], []
            for r in range(rows):
                if r == pivot_row:
                    continue
                factor = M[r, col]
                if self._es_cero(factor):
                    continue
                antes = list(M.row(r))
                M.row_op(r, lambda v, j: sympy.simplify(v - factor * M[pivot_row, j]))
                cuentas.append(self._cuenta_eliminacion(antes, list(M.row(pivot_row)), factor, list(M.row(r)), r, pivot_row))
                filas.append(r)
            if cuentas:
                pasos.append(self._paso_eliminar(M, cuentas, pivot_row, col, filas))
            pivot_row += 1

        # --- Verdad matemática (SymPy) y diagnóstico de Rouché-Frobenius ---
        rref, _ = matriz_inicial.rref()
        rango_A = matriz_inicial[:, :-1].rank()
        rango_aumentada = matriz_inicial.rank()
        # Sin solución, SymPy además reduce la fila imposible (0 = 2 pasa a 0 = 1): no se compara
        if rango_A == rango_aumentada and (M - rref).applyfunc(sympy.simplify) != sympy.zeros(rows, cols):
            advertencias.append(tr("Las operaciones explicadas no llegaron a la forma escalonada de SymPy; se usa la de SymPy."))
        simbolos = [self.parser.simbolo(v) for v in variables]

        if rango_A < rango_aumentada:
            tipo = INCONSISTENTE
            solucion = sympy.EmptySet
            resultado = [tr("RESULTADO: Sin solución (SISTEMA INCOMPATIBLE).")]
            lectura = [tr("Fila {i}: {fila} significa {ecuacion}, que es imposible.", i=i + 1,
                          fila=fila_texto(list(M.row(i))), ecuacion=f"0 = {texto(M[i, -1])}")
                       for i in range(rows) if all(self._es_cero(v) for v in M.row(i)[:-1]) and not self._es_cero(M[i, -1])]
            lectura.append(tr("Una ecuación imposible basta: el sistema no tiene solución."))
            pasos.append(self._paso_leer(lectura, tr("sin solución")))
        elif rango_A == num_vars:
            tipo = UNICA
            valores = {s: rref[i, -1] for i, s in enumerate(simbolos)}
            solucion = [sympy.Eq(s, valores[s]) for s in simbolos]
            resultado = [tr("RESULTADO:")] + [f"{v} = {texto(valores[s])}" for v, s in zip(variables, simbolos)]
            lectura = [tr("Fila {i}: {fila} significa {variable} = {valor}.", i=i + 1, fila=fila_texto(list(rref.row(i))),
                          variable=variables[i], valor=texto(rref[i, -1])) for i in range(num_vars)]
            pasos.append(self._paso_leer(lectura, ", ".join(f"{v} = {texto(valores[s])}" for v, s in zip(variables, simbolos))))
            if ecuaciones:
                pasos.append(PasoCalculo(
                    tr("Comprobación"),
                    regla=tr("se sustituyen los valores en las ecuaciones originales: si todas se cumplen, la solución "
                             "es correcta."),
                    partes=", ".join(f"{v} = {texto(valores[s])}" for v, s in zip(variables, simbolos)) + ".",
                    calculo=tuple(comprobar(ecuaciones, valores)),
                    queda=", ".join(f"{v} = {texto(valores[s])}" for v, s in zip(variables, simbolos))))
        else:
            tipo = INFINITA
            conjunto = sympy.linsolve((matriz_inicial[:, :-1], matriz_inicial[:, -1]), simbolos)
            tupla = list(conjunto)[0]
            solucion = [sympy.Eq(s, e, evaluate=False) for s, e in zip(simbolos, tupla)]
            libres = [s for s, e in zip(simbolos, tupla) if e == s]
            resultado = [tr("RESULTADO: Infinitas soluciones (grados de libertad: {grados}).", grados=len(libres))]
            resultado += [tr("{variable} es libre (puede valer cualquier número)", variable=s) if e == s
                          else f"{s} = {texto(e)}" for s, e in zip(simbolos, tupla)]
            lectura = []
            for i in range(rows):
                fila = list(rref.row(i))
                if all(self._es_cero(v) for v in fila):
                    lectura.append(tr("Fila {i}: todo ceros (0 = 0): no aporta nada.", i=i + 1))
                    continue
                izquierda = sympy.Add(*[c * s for c, s in zip(fila[:-1], simbolos)])
                principal = next(s for c, s in zip(fila[:-1], simbolos) if c != 0)
                valor = tupla[simbolos.index(principal)]
                lectura.append(tr("Fila {i}: {ecuacion}, así que {variable} = {valor}.", i=i + 1,
                                  ecuacion=ecuacion_texto(izquierda, fila[-1]), variable=principal, valor=texto(valor)))
            for s in libres:
                lectura.append(tr("{variable} no tiene pivote: es libre, puede valer cualquier número.", variable=s))
            pasos.append(self._paso_leer(lectura, "; ".join(f"{s} = {texto(e)}" for s, e in zip(simbolos, tupla) if e != s)))

        return ResultadoGauss(tipo_solucion=tipo, variables=variables, matriz_aumentada_inicial=matriz_inicial,
                              matriz_rref_final=rref, pasos=pasos, resultado=resultado,
                              advertencias=advertencias, solucion=solucion)

    @staticmethod
    def _paso_leer(lineas: List[str], queda: str) -> PasoCalculo:
        return PasoCalculo(
            tr("Leer la solución"),
            regla=tr("en la forma escalonada reducida, cada fila con un 1 principal da su incógnita: [1, 0, 0 | 2] es "
                     "1*x + 0*y + 0*z = 2, es decir x = 2. Una fila [0, 0, 0 | k] con k distinto de 0 dice 0 = k: no "
                     "hay solución. Una incógnita sin pivote es libre: hay infinitas soluciones."),
            partes=tr("la matriz ya está en forma escalonada reducida."),
            calculo=tuple(lineas),
            queda=queda)

    def _buscar_mejor_pivote(self, matriz: sympy.Matrix, col: int, fila_inicio: int, total_filas: int) -> Optional[int]:
        """Un 1 si lo hay; si no, un -1; si no, el primer valor distinto de 0 (None si la columna es de ceros)."""
        candidato = None
        for r in range(fila_inicio, total_filas):
            val = matriz[r, col]
            if self._es_cero(val):
                continue
            if val == 1:
                return r
            if val == -1:
                if candidato is None or matriz[candidato, col] not in [1, -1]:
                    candidato = r
            elif candidato is None:
                candidato = r
        return candidato

    # --- Fachada ---

    def ExplicarGaussJordan(self, lista_entradas: List[str]) -> str:
        """Entrada: ["2x+y=1", "x-y=2"] o ["[[2,1,1],[1,-1,2]]"]."""
        return self.resolver(lista_entradas)[0]

    def resolver(self, lista_entradas: List[str]) -> Tuple[str, Any, bool]:
        """Devuelve (texto accesible, solución SymPy o None, es_error)."""
        try:
            M, variables, ecuaciones = self._parsear_sistema_mixto(lista_entradas)
            res = self._resolver_core_gauss(M, variables, ecuaciones)
            lineas = res.resultado + ["=" * 30, tr("MÉTODO: {metodo}", metodo=tr("Gauss-Jordan (reducción por filas)")),
                                      tr("Sistema de {ecuaciones} ecuaciones con {n} incógnitas: {variables}.",
                                         ecuaciones=M.rows, n=M.cols - 1, variables=", ".join(variables))]
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(res.pasos, 1)]
            if res.advertencias:
                lineas += ["", tr("[!] AVISOS:")] + [f" - {a}" for a in res.advertencias]
            return "\n".join(lineas), res.solucion, False
        except Exception as e:
            return tr("Error procesando el sistema: {e}", e=str(e)), None, True
