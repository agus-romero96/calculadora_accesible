"""Construcción y precedencia sin cargar wxPython ni arrancar la aplicación."""
import pytest
import sympy

from constructores_matematicos import (
    CONSTRUCTORES, ErrorCampoConstructor, construir_expresion,
    construir_fraccion, construir_potencia, construir_raiz,
)
from parser_matematico import ParserMatematico


def test_fraccion_agrupa_ambos_operandos():
    texto = construir_fraccion(' x+1 ', ' x-2 ')
    assert texto == '(x+1)/(x-2)'
    parser = ParserMatematico()
    assert sympy.simplify(parser.parsear(texto) - parser.parsear('(x+1)/(x-2)')) == 0


@pytest.mark.parametrize('base,exponente,esperado', [
    ('x+1', '2', '(x+1)^(2)'),
    ('-2', '2', '(-2)^(2)'),
    ('x', '1/2', '(x)^(1/2)'),
    ('x', 'a+1', '(x)^(a+1)'),
    ('x+1', '-2', '(x+1)^(-2)'),
    ('(x+1)/(x-1)', '2/3', '((x+1)/(x-1))^(2/3)'),
])
def test_potencias(base, exponente, esperado):
    texto = construir_potencia(base, exponente)
    assert texto == esperado
    parser = ParserMatematico()
    assert parser.parsear(texto).doit() == sympy.Pow(parser.parsear(base).doit(), parser.parsear(exponente).doit())


@pytest.mark.parametrize('radicando', ['x+4', '-1', '4', '(x+1)/(x-2)', 'sqrt(x)'])
def test_raiz_sin_calcular_ni_imponer_dominio(radicando):
    assert construir_raiz(' ' + radicando + ' ') == f'sqrt({radicando})'


@pytest.mark.parametrize('tipo,campo', [
    (tipo, campo.clave) for tipo, constructor in CONSTRUCTORES.items() for campo in constructor.campos
])
@pytest.mark.parametrize('vacio', ['', '   '])
def test_campos_obligatorios_especificos(tipo, campo, vacio):
    valores = {c.clave: 'x' for c in CONSTRUCTORES[tipo].campos}
    valores[campo] = vacio
    with pytest.raises(ErrorCampoConstructor) as error:
        construir_expresion(tipo, valores)
    assert error.value.campo == campo
    esperado = next(c.mensaje_vacio for c in CONSTRUCTORES[tipo].campos if c.clave == campo)
    assert str(error.value) == esperado


@pytest.mark.parametrize('denominador', [
    '0', '0.0', '2-2', 'x-x', '(x+1)-(x+1)', 'sin(pi)',
    'sin(x)^2+cos(x)^2-1', '(x+1)^2-x^2-2*x-1',
])
def test_denominadores_exactamente_nulos(denominador):
    with pytest.raises(ErrorCampoConstructor, match='denominador es cero') as error:
        construir_fraccion('1', denominador)
    assert error.value.campo == 'denominador'


@pytest.mark.parametrize('denominador', ['x', 'x-2', 'x^2-1', 'sin(x)', '1e-100', '(x^2-1)/(x-1)'])
def test_no_rechaza_denominadores_por_posibles_ceros_o_pequenez(denominador):
    assert construir_fraccion('1', denominador) == f'(1)/({denominador})'


@pytest.mark.parametrize('tipo,campo', [
    (tipo, campo.clave) for tipo, constructor in CONSTRUCTORES.items() for campo in constructor.campos
])
@pytest.mark.parametrize('invalido', ['x+', '(x', 'xsin(x)', '[1,2]', 'matrix([[1]])', 'x<1'])
def test_exige_expresiones_validas_en_cada_campo(tipo, campo, invalido):
    valores = {c.clave: 'x' for c in CONSTRUCTORES[tipo].campos}
    valores[campo] = invalido
    with pytest.raises(ErrorCampoConstructor) as error:
        construir_expresion(tipo, valores)
    assert error.value.campo == campo


def test_conserva_la_entrada_original_y_sus_restricciones():
    assert construir_fraccion('x/x', 'x-1') == '(x/x)/(x-1)'
    assert construir_potencia('x/x', '0') == '(x/x)^(0)'


@pytest.mark.parametrize('metodo,args,valor', [
    ('ecuacion', (construir_fraccion('x+1', '2') + '=3',), '{5}'),
    ('derivar', (construir_potencia('x+1', '2'), 'x'), '2*x + 2'),
    ('limite', (construir_raiz('x+4'), 'x', '0'), '2'),
])
def test_expresiones_compatibles_con_las_operaciones(core, metodo, args, valor):
    resultado = getattr(core, metodo)(*args)
    assert not resultado.es_error
    assert str(resultado.valor) == valor
