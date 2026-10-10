"""
El proceso de cálculo: resultados completos desde el proceso hijo y cancelación real
(el proceso que calculaba deja de existir, no solo se ignora su resultado).
"""
import threading
import time

import pytest

import i18n
from nucleo_pruebas import NucleoPruebas
from proceso_calculo import ErrorCalculo, ProcesoCalculo


@pytest.fixture(scope="module")
def proceso():
    p = ProcesoCalculo(fabrica=NucleoPruebas)
    yield p
    p.cerrar()


def test_resultado_completo(proceso):
    res = proceso.calcular("limite", "sin(x)/x", "x", "0")
    assert res.operacion == "limite" and not res.es_error
    assert res.texto.startswith("RESULTADO: 1")
    assert res.valor == 1
    assert res.planteamiento is not None  # el Limit sin evaluar también llega


def test_planteamiento_sin_evaluar(proceso):
    # Con el pickle normal de SymPy llegaría 1/2
    res = proceso.calcular("evaluar", "1/6 + 1/3")
    assert str(res.planteamiento) == "1/6 + 1/3"


def test_idioma_del_proceso_principal(proceso):
    i18n.establecer_idioma("en")
    try:
        assert proceso.calcular("derivar", "x^3").texto.startswith("RESULT: 3*x**2")
    finally:
        i18n.establecer_idioma("es")
    assert proceso.calcular("derivar", "x^3").texto.startswith("RESULTADO: 3*x**2")


def test_excepcion_del_motor(proceso):
    with pytest.raises(ErrorCalculo, match="division by zero"):
        proceso.calcular("factorizar", "fallar")
    # el proceso sigue sirviendo
    assert proceso.calcular("evaluar", "2+2").texto.splitlines()[0] == "RESULTADO: 4"


def test_cancelar_detiene_el_proceso(proceso):
    pid_anterior = proceso.calcular("pid")
    resultado = {}
    hilo = threading.Thread(target=lambda: resultado.setdefault("res", proceso.calcular("evaluar", "dormir 30")))
    hilo.start()
    time.sleep(1)
    inicio = time.monotonic()
    proceso.cancelar()
    hilo.join(10)
    assert not hilo.is_alive() and resultado["res"] is None
    assert time.monotonic() - inicio < 10  # no esperó los 30 segundos
    # el cálculo cancelado ya no existe y hay otro proceso listo
    assert proceso.esta_vivo() and proceso.pid != pid_anterior
    assert proceso.calcular("pid") != pid_anterior
    assert proceso.calcular("evaluar", "2+2").texto.splitlines()[0] == "RESULTADO: 4"


def test_cancelar_sin_calculo_en_curso(proceso):
    proceso.cancelar()
    assert proceso.calcular("evaluar", "3+3").texto.splitlines()[0] == "RESULTADO: 6"


def test_proceso_que_termina_solo(proceso):
    with pytest.raises(ErrorCalculo, match="terminó de forma inesperada"):
        proceso.calcular("morir", "x")
    # el siguiente cálculo arranca otro proceso
    assert proceso.calcular("evaluar", "2+2").texto.splitlines()[0] == "RESULTADO: 4"


def test_cerrar():
    p = ProcesoCalculo(fabrica=NucleoPruebas)
    assert p.calcular("evaluar", "1+1").texto.splitlines()[0] == "RESULTADO: 2"
    p.cerrar()
    assert not p.esta_vivo()
