"""
Proceso de cálculo: ejecuta el núcleo matemático en un proceso aparte.

SymPy puede tardar mucho (o no terminar) en simplify/limit/integrate, y Python no
permite detener un hilo: antes, al cancelar, el cálculo seguía ocupando el
procesador hasta terminar. Un proceso sí se puede detener. Por eso el núcleo vive
en un proceso hijo persistente (se crea una vez, no en cada cálculo, porque
importar SymPy tarda), y cancelar lo termina y arranca otro limpio.

Uso (calcular() bloquea: la interfaz lo llama desde un hilo):

    proceso = ProcesoCalculo()
    res = proceso.calcular("limite", "sin(x)/x", "x", "0")   # ResultadoOperacion
    proceso.cancelar()   # desde otro hilo: calcular() devuelve None
    proceso.cerrar()

El resultado vuelve serializado sin evaluar (serializacion.py), para que el
planteamiento ("1/6 + 1/3") llegue tal cual y se pueda exportar.

Con "spawn" el hijo vuelve a importar el módulo principal: el arranque del
programa debe estar bajo  if __name__ == "__main__"  y, en el ejecutable
compilado, empezar por multiprocessing.freeze_support().
"""
import multiprocessing
import threading
from dataclasses import replace

import serializacion
from i18n import idioma_actual, tr


class ErrorCalculo(Exception):
    """El cálculo lanzó una excepción en el proceso hijo, o el proceso terminó solo."""


def _servir(conexion, fabrica):
    """Bucle del proceso hijo: recibe (método, argumentos, idioma) y responde."""
    import i18n
    if fabrica is None:
        from puente import CoreMatematico as fabrica
    nucleo = fabrica()
    while True:
        try:
            metodo, args, idioma = conexion.recv()
        except (EOFError, OSError):
            return  # el proceso principal cerró la conexión
        try:
            if idioma != i18n.idioma_actual():
                i18n.establecer_idioma(idioma)
            respuesta = ("ok", getattr(nucleo, metodo)(*args))
        except Exception as e:  # cualquier fallo del motor se informa a la interfaz
            respuesta = ("error", str(e) or type(e).__name__)
        try:
            datos = serializacion.a_bytes(respuesta)
        except Exception:
            # Un objeto SymPy que no se pudo serializar: se envía el informe sin las fórmulas
            datos = serializacion.a_bytes(("ok", replace(respuesta[1], valor=None, expresion=None,
                                                         planteamiento=None)))
        conexion.send_bytes(datos)


class ProcesoCalculo:
    def __init__(self, fabrica=None):
        """
        fabrica: clase o función (importable por su nombre, porque se envía al proceso hijo)
        que crea el núcleo; por defecto CoreMatematico. Las pruebas pasan uno propio.
        """
        self._contexto = multiprocessing.get_context("spawn")
        self._fabrica = fabrica
        self._cerrojo = threading.Lock()
        self._proceso = None
        self._conexion = None
        self._en_uso = None  # conexión que está usando calcular() (en otro hilo)
        self._iniciar()

    def _iniciar(self):
        conexion, extremo_hijo = self._contexto.Pipe()
        proceso = self._contexto.Process(target=_servir, args=(extremo_hijo, self._fabrica),
                                         name="CalculadoraAccesible-calculo", daemon=True)
        proceso.start()
        extremo_hijo.close()  # si no, recv() no notaría que el hijo terminó
        self._proceso, self._conexion = proceso, conexion

    def _detener(self):
        """Termina el proceso actual (la conexión se trata aparte, en _soltar_conexion)."""
        if self._proceso is not None:
            if self._proceso.is_alive():
                self._proceso.terminate()
            self._proceso.join(5)
            self._proceso = None

    @property
    def pid(self):
        return self._proceso.pid if self._proceso is not None else None

    def esta_vivo(self) -> bool:
        return self._proceso is not None and self._proceso.is_alive()

    def calcular(self, metodo, *args):
        """
        Ejecuta nucleo.metodo(*args) en el proceso hijo y devuelve su ResultadoOperacion.
        Devuelve None si se canceló mientras tanto; lanza ErrorCalculo si el cálculo
        falló o el proceso terminó solo (por ejemplo, sin memoria).
        """
        with self._cerrojo:
            if not self.esta_vivo():  # terminó solo en un cálculo anterior
                self._soltar_conexion()
                self._iniciar()
            conexion = self._en_uso = self._conexion
        try:
            conexion.send((metodo, args, idioma_actual()))
            estado, valor = serializacion.de_bytes(conexion.recv_bytes())
        except (EOFError, OSError):
            with self._cerrojo:
                if conexion is not self._conexion:
                    return None  # cancelado: cancelar() ya arrancó otro proceso
                # Terminó solo: se arranca otro ya (is_alive() puede tardar en notarlo)
                self._detener()
                self._en_uso = None
                self._soltar_conexion()
                self._iniciar()
            raise ErrorCalculo(tr("El proceso de cálculo terminó de forma inesperada "
                                  "(por ejemplo, por falta de memoria)."))
        finally:
            with self._cerrojo:
                self._en_uso = None
                if conexion is not self._conexion:
                    conexion.close()  # la reemplazó cancelar() o cerrar()
        if estado == "error":
            raise ErrorCalculo(valor)
        return valor

    def cancelar(self):
        """Detiene el cálculo en curso (el proceso entero) y deja otro listo para el siguiente."""
        with self._cerrojo:
            self._detener()
            self._soltar_conexion()
            self._iniciar()

    def cerrar(self):
        """Al salir de la calculadora."""
        with self._cerrojo:
            self._detener()
            self._soltar_conexion()

    def _soltar_conexion(self):
        # Si calcular() la está usando en otro hilo no se cierra aquí (ese hilo puede estar
        # leyendo de ella): la cierra calcular() al ver que ya no es la actual.
        if self._conexion is not None and self._conexion is not self._en_uso:
            self._conexion.close()
        self._conexion = None
