"""
Historial de operaciones de la sesión.

Guarda los resultados correctos (ResultadoOperacion) en orden cronológico para
volver a verlos, reutilizar su entrada, copiarlos o exportarlos todos juntos.
Dura mientras la calculadora está abierta.
"""
from typing import List

from exportar import nombre_operacion, resultado_corto
from i18n import tr
from puente import ResultadoOperacion

LARGO_MAXIMO_RESUMEN = 80


class Historial:
    # Límite para que una sesión muy larga no crezca sin control (se descartan las más antiguas)
    MAXIMO = 200

    def __init__(self):
        self._entradas: List[ResultadoOperacion] = []  # de la más antigua a la más reciente

    def agregar(self, res: ResultadoOperacion) -> None:
        if res.es_error:
            return
        self._entradas.append(res)
        del self._entradas[:-self.MAXIMO]

    def entradas(self) -> List[ResultadoOperacion]:
        """Copia de las operaciones, de la más antigua a la más reciente."""
        return list(self._entradas)

    def numero(self, res: ResultadoOperacion) -> int:
        """Número de la operación (1 = la más antigua), el mismo que en el historial exportado."""
        return next(i for i, r in enumerate(self._entradas, 1) if r is res)

    def eliminar(self, res: ResultadoOperacion) -> None:
        self._entradas = [r for r in self._entradas if r is not res]

    def vaciar(self) -> None:
        self._entradas.clear()

    def __len__(self) -> int:
        return len(self._entradas)


def describir(res: ResultadoOperacion, numero: int) -> str:
    """Una línea para la lista del historial: número, operación, entrada y resultado."""
    resultado = resultado_corto(res)
    if len(resultado) > LARGO_MAXIMO_RESUMEN:
        resultado = resultado[:LARGO_MAXIMO_RESUMEN] + "…"
    return tr("{numero}. {operacion}: {entrada} → {resultado}",
              numero=numero, operacion=nombre_operacion(res),
              entrada=res.entrada.replace("\n", "; "), resultado=resultado)
