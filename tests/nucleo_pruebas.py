"""
Núcleo matemático para las pruebas del proceso de cálculo y de la interfaz.

Se pasa a ProcesoCalculo(fabrica=NucleoPruebas) o a CalculadoraAccesible(nucleo=...):
como se ejecuta en el proceso hijo, no se puede sustituir un método desde la
prueba; por eso sus casos especiales se eligen con la entrada.

  - evaluar("dormir N"): tarda N segundos y devuelve "RESULTADO: lento".
  - factorizar("fallar"): lanza una excepción.
  - morir("..."): termina el proceso de golpe (como si se quedara sin memoria).
  - pid(): el identificador del proceso que calcula.
El resto se comporta como CoreMatematico.
"""
import os
import time

from puente import CoreMatematico, ResultadoOperacion


class NucleoPruebas(CoreMatematico):
    def evaluar(self, expresion):
        if expresion.startswith("dormir "):
            time.sleep(float(expresion.split()[1]))
            return ResultadoOperacion(operacion="evaluar", entrada=expresion, texto="RESULTADO: lento")
        return super().evaluar(expresion)

    def factorizar(self, expresion):
        if expresion == "fallar":
            return 1 / 0
        return super().factorizar(expresion)

    def morir(self, expresion):
        os._exit(3)

    def pid(self):
        return os.getpid()
