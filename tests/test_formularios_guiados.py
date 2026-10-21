"""Esquema declarativo, argumentos y valores del núcleo sin crear controles wx."""
import inspect

import pytest
import sympy

from formularios_guiados import FORMULARIOS, OPCIONES, CampoObligatorio, construir_argumentos
from parser_matematico import ParserMatematico
from puente import OPERACION, REGISTRO, CoreMatematico, ResultadoOperacion


DATOS = {
    'evaluar': {'expresion': ' 2+3*4 '},
    'simplificar': {'expresion': ' (x^2-1)/(x-1) '},
    'factorizar': {'expresion': ' x^2-9 '},
    'integrar': {'expresion': ' 2*t ', 'variable': ' t '},
    'integral_definida': {'expresion': ' t ', 'variable': ' t ', 'inferior': ' -1 ', 'superior': ' 2 '},
}


def test_operaciones_del_registro_sin_cambiar_claves_ni_metodos():
    assert [clave for clave, _, _ in OPCIONES] == [
        'ecuacion', 'derivar', 'limite', 'evaluar', 'simplificar', 'factorizar', 'integrar', 'integral_definida']
    assert len(OPCIONES) == len(FORMULARIOS) == 8
    for clave, formulario in FORMULARIOS.items():
        assert formulario.operacion is OPERACION[clave]
        assert formulario.operacion in REGISTRO
        firma = inspect.signature(getattr(CoreMatematico, formulario.operacion.metodo))
        assert len(formulario.argumentos) == len(firma.parameters) - 1
        assert formulario.nombre and formulario.ejemplo
        assert len({c.clave for c in formulario.campos}) == len(formulario.campos)


@pytest.mark.parametrize('clave,esperado', [
    ('evaluar', ('2+3*4',)),
    ('simplificar', ('(x^2-1)/(x-1)',)),
    ('factorizar', ('x^2-9',)),
    ('integrar', ('2*t', 't')),
    ('integral_definida', ('t', 't', '-1', '2')),
])
def test_argumentos_en_orden_y_sin_modificar_datos_originales(clave, esperado):
    antes = dict(DATOS[clave])
    assert construir_argumentos(clave, **DATOS[clave]) == esperado
    assert DATOS[clave] == antes


@pytest.mark.parametrize('clave,campo', [(clave, campo) for clave, datos in DATOS.items() for campo in datos])
@pytest.mark.parametrize('vacio', ['', '   '])
def test_todos_los_campos_son_obligatorios(clave, campo, vacio):
    valores = dict(DATOS[clave], **{campo: vacio})
    with pytest.raises(CampoObligatorio) as error:
        construir_argumentos(clave, **valores)
    assert error.value.campo == campo


@pytest.mark.parametrize('inferior,superior', [('2', '0'), ('0', '0'), ('-oo', 'oo'), ('0', 'k'), ('1/2', 'sqrt(2)')])
def test_no_reordena_limites_ni_reinterpreta_su_matematica(inferior, superior):
    assert construir_argumentos('integral_definida', 't', 't', inferior=inferior, superior=superior) == (
        't', 't', inferior, superior)


def test_armar_argumentos_no_invoca_parser_ni_calculo(monkeypatch):
    def prohibido(*args, **kwargs):
        pytest.fail('La preparación de argumentos no debe interpretar ni calcular expresiones')

    monkeypatch.setattr(ParserMatematico, 'parsear', prohibido)
    for clave, datos in DATOS.items():
        monkeypatch.setattr(CoreMatematico, OPERACION[clave].metodo, prohibido)
        assert construir_argumentos(clave, **datos)


@pytest.mark.parametrize('clave,esperado', [
    ('evaluar', '14'), ('simplificar', 'x+1'), ('factorizar', '(x-3)*(x+3)'),
    ('integrar', 't^2'), ('integral_definida', '3/2'),
])
def test_nuevos_formularios_se_integran_con_el_nucleo(core, clave, esperado):
    resultado = getattr(core, FORMULARIOS[clave].operacion.metodo)(*construir_argumentos(clave, **DATOS[clave]))
    assert isinstance(resultado, ResultadoOperacion)
    assert not resultado.es_error
    assert resultado.operacion == clave
    assert resultado.entrada == DATOS[clave]['expresion'].strip()
    assert sympy.simplify(resultado.valor - ParserMatematico().parsear(esperado)) == 0
    if clave == 'integrar':
        assert resultado.mas_constante
        assert resultado.parametros['variable'] == 't'
    if clave == 'integral_definida':
        assert not resultado.mas_constante
        assert resultado.parametros == {'variable': 't', 'inferior': '-1', 'superior': '2'}


def test_integral_de_una_constante_recibe_la_variable(core):
    resultado = core.integrar(*construir_argumentos('integrar', '5', 't'))
    assert not resultado.es_error
    assert str(resultado.valor) == '5*t'
    assert resultado.mas_constante
