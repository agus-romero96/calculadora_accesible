"""
Autoprueba del núcleo matemático, pensada para el ejecutable compilado.

    CalculadoraAccesible.exe --autoprueba informe.txt

Ejecuta un cálculo representativo de cada motor sin abrir la ventana, escribe un
informe y devuelve el código de salida 0 si todo es correcto (1 si algo falla).

Sirve para comprobar que el empaquetado (cx_Freeze) incluyó todo lo necesario:
el ejecutable usa Win32GUI y no tiene consola, así que el informe va a un archivo.
"""
import os
from typing import Callable, List, Optional, Tuple

import i18n
from puente import CoreMatematico


def _casos(core: CoreMatematico) -> List[Tuple[str, Callable[[], str], str]]:
    # (nombre, llamada, texto que debe aparecer en la salida)
    return [
        ("Evaluar", lambda: core.Evaluar("2+2"), "RESULTADO: 4"),
        ("Evaluar irracional", lambda: core.Evaluar("2*pi"), "6.2831853"),
        ("Simplificar", lambda: core.Simplificar("(x^2-1)/(x-1)"), "RESULTADO FINAL: x + 1"),
        ("Factorizar", lambda: core.Factorizar("x^3-8"), "Suma/diferencia de cubos"),
        ("Derivar", lambda: core.Derivar("abs(x)"), "RESULTADO: sign(x)"),
        ("Derivada N", lambda: core.DerivadaEnecima("x^5", "x", 3), "RESULTADO: 60*x**2"),
        ("Integrar (pasos)", lambda: core.Integrar("x*exp(x)"), "Integración por Partes"),
        ("Límite trigonométrico", lambda: core.CalcularLimite("sin(x)/x", "x", "0"), "RESULTADO: 1"),
        ("Límite bilateral", lambda: core.CalcularLimite("abs(x)/x", "x", "0"), "No existe"),
        ("Límite en infinito", lambda: core.CalcularLimite("(3*x^2+1)/(5*x^2-7)", "x", "oo"), "RESULTADO: 3/5"),
        ("Gauss-Jordan", lambda: core.ResolverSistemaGauss(["x + y = 10", "x - y = 2"]), "x = 6"),
        ("Sistema clásico", lambda: core.ResolverSistemaEducativo(["x + y = 10", "x - y = 2"], "reduccion"), "y = 4"),
        ("Matriz inversa", lambda: core.MatrizInversaCofactores("1 2\n3 4"), "3/2"),
        # Traducción: comprueba que locales/en.json está junto al ejecutable
        ("Inglés", lambda: _en_ingles(lambda: core.Derivar("x^3")), "RESULT: 3*x**2"),
        # Proceso de cálculo: en el ejecutable es otra copia del .exe (freeze_support)
        ("Proceso de cálculo", _en_proceso, "RESULTADO: 4"),
    ]


def _en_proceso():
    from proceso_calculo import ProcesoCalculo
    proceso = ProcesoCalculo()
    try:
        return proceso.calcular("evaluar", "2+2").texto
    finally:
        proceso.cerrar()


def _en_ingles(llamada):
    i18n.establecer_idioma("en")
    try:
        return llamada()
    finally:
        i18n.establecer_idioma(i18n.IDIOMA_ORIGEN)


def ejecutar(ruta_informe: Optional[str] = None) -> int:
    lineas: List[str] = []
    fallos = 0
    # Los textos esperados son los del código, en español: sin locales/es.json, que el
    # usuario puede haber editado (la variable la hereda también el proceso de cálculo)
    os.environ[i18n.TEXTOS_ORIGEN] = "1"
    i18n.establecer_idioma(i18n.IDIOMA_ORIGEN)
    try:
        core = CoreMatematico()
        for nombre, llamada, esperado in _casos(core):
            try:
                salida = llamada()
                ok = esperado in salida
                detalle = "" if ok else f" | salida: {salida[:200]!r}"
            except Exception as e:  # el informe debe registrar cualquier fallo
                ok, detalle = False, f" | excepción: {type(e).__name__}: {e}"
            fallos += not ok
            lineas.append(f"{'OK  ' if ok else 'FAIL'} {nombre}{detalle}")
    except Exception as e:
        fallos += 1
        lineas.append(f"FAIL inicialización del núcleo: {type(e).__name__}: {e}")

    total = len(lineas)
    lineas.append(f"{total - fallos}/{total} correctas")
    informe = "\n".join(lineas)

    if ruta_informe:
        with open(ruta_informe, "w", encoding="utf-8") as f:
            f.write(informe + "\n")
    else:
        try:
            print(informe)
        except Exception:
            pass  # sin consola (ejecutable Win32GUI)
    return 1 if fallos else 0
