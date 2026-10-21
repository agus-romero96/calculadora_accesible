"""Contratos de formularios y envío al flujo existente, sin abrir ventanas."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
import wx

import interfaz_guiada as gui
import dialogos_constructores
from constructores_matematicos import construir_raiz
from puente import OPERACION
from parser_matematico import ParserMatematico


@pytest.mark.parametrize('clave,datos,esperado', [
    ('ecuacion', dict(expresion=' 2*x=4 '), ('2*x=4',)),
    ('derivar', dict(expresion='t^2', variable='t'), ('t^2', 't')),
    ('limite', dict(expresion='1/x', tendencia='0', direccion=0), ('1/x', 'x', '0')),
    ('limite', dict(expresion='1/x', tendencia='-2', direccion=1), ('1/x', 'x', '-2-')),
    ('limite', dict(expresion='1/x', tendencia='0', direccion=2), ('1/x', 'x', '0+')),
    ('limite', dict(expresion='1/x', tendencia='-infinito'), ('1/x', 'x', '-infinito')),
])
def test_argumentos(clave, datos, esperado):
    assert gui.construir_argumentos(clave, **datos) == esperado


@pytest.mark.parametrize('clave,datos,valor', [
    ('ecuacion', dict(expresion='2*x+3=7'), '{2}'),
    ('derivar', dict(expresion='x^2+3*x'), '2*x + 3'),
    ('limite', dict(expresion='sin(x)/x', tendencia='0'), '1'),
])
def test_primeras_operaciones_con_nucleo(core, clave, datos, valor):
    resultado = getattr(core, OPERACION[clave].metodo)(*gui.construir_argumentos(clave, **datos))
    assert not resultado.es_error
    assert str(resultado.valor) == valor


@pytest.mark.parametrize('clave,datos,campo', [
    ('ecuacion', dict(expresion=' '), 'expresion'),
    ('derivar', dict(expresion='x', variable=''), 'variable'),
    ('limite', dict(expresion='x', tendencia=''), 'tendencia'),
    ('limite', dict(expresion='x', tendencia='0+'), 'tendencia'),
    ('limite', dict(expresion='x', tendencia='oo', direccion=2), 'tendencia'),
])
def test_campos(clave, datos, campo):
    with pytest.raises(gui.CampoObligatorio) as error:
        gui.construir_argumentos(clave, **datos)
    assert error.value.campo == campo


@pytest.mark.parametrize('indice', range(4))
def test_plantillas_validas_y_cursor(indice):
    texto, seleccion = gui.insertar_plantilla('3+', (2, 2), indice)
    ParserMatematico().parsear(texto)
    assert texto[:2] == '3+'
    assert texto[slice(*seleccion)] in ('1', 'x')
    texto, seleccion = gui.insertar_plantilla('3+x+1', (2, 5), indice)
    assert texto[slice(*seleccion)] == 'x+1'
    ParserMatematico().parsear(texto)


@pytest.mark.parametrize('indice', range(3))
@pytest.mark.parametrize('cancelar', ['selector', 'formulario', None])
def test_seleccion_y_cancelacion(monkeypatch, indice, cancelar):
    destruidos = []
    selector = SimpleNamespace(ShowModal=lambda: wx.ID_CANCEL if cancelar == 'selector' else wx.ID_OK,
        GetSelection=lambda: indice, Destroy=lambda: destruidos.append('selector'))
    formulario = SimpleNamespace(ShowModal=lambda: wx.ID_CANCEL if cancelar == 'formulario' else wx.ID_OK,
        argumentos=('datos',), Destroy=lambda: destruidos.append('formulario'))
    monkeypatch.setattr(wx, 'SingleChoiceDialog', lambda *a: selector)
    elegidas = []
    monkeypatch.setattr(gui, 'DialogoCalculo', lambda padre, clave: elegidas.append(clave) or formulario)
    resultado = gui.solicitar_calculo(None)
    if cancelar:
        assert resultado is None
    else:
        assert resultado == (OPERACION[gui.OPCIONES[indice][0]], ('datos',))
    assert destruidos == (['selector'] if cancelar == 'selector' else ['selector', 'formulario'])
    assert elegidas == ([] if cancelar == 'selector' else [gui.OPCIONES[indice][0]])


def handlers(*nombres, **entorno):
    arbol = ast.parse(Path('main.py').read_text(encoding='utf-8'))
    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef))
    funciones = [n for n in clase.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
    exec(compile(ast.Module(body=funciones, type_ignores=[]), 'main.py', 'exec'), entorno)
    return entorno


@pytest.mark.parametrize('entrada,clave', [('2+2', 'evaluar'), ('x=2', 'ecuacion'), ('x=2\ny=3', 'gauss')])
def test_modo_libre(entrada, clave):
    llamadas = []
    falso = SimpleNamespace(obtener_texto=lambda: entrada, _calcular=lambda *a: llamadas.append(a))
    handlers('on_evaluar_inteligente', OPERACION=OPERACION)['on_evaluar_inteligente'](falso, None)
    assert llamadas == [(OPERACION[clave], entrada)]


@pytest.mark.parametrize('cancelar', [True, False])
def test_envio_asincrono_y_foco(cancelar):
    llamadas = []
    foco = SimpleNamespace(SetFocus=lambda: llamadas.append('foco'))
    falso = SimpleNamespace(_calculo_actual=None, _ejecutar=lambda *a: llamadas.append(a), input_text=foco)
    solicitud = None if cancelar else (OPERACION['derivar'], ('t^2', 't'))
    entorno = handlers('on_calculo_guiado', wx=SimpleNamespace(Window=SimpleNamespace(FindFocus=lambda: foco)),
        interfaz_guiada=SimpleNamespace(solicitar_calculo=lambda _: solicitud), tr=lambda s: s)
    entorno['on_calculo_guiado'](falso, None)
    assert llamadas == (['foco'] if cancelar else ['foco', ('derivar', ('t^2', 't'), OPERACION['derivar'].descripcion)])


def test_resultado_empieza_en_primera_linea_y_recibe_foco():
    llamadas = []
    campo = SimpleNamespace(SetValue=lambda valor: llamadas.append(('texto', valor)),
                            SetInsertionPoint=lambda punto: llamadas.append(('cursor', punto)),
                            SetFocus=lambda: llamadas.append('foco'))
    handlers('_mostrar_texto')['_mostrar_texto'](SimpleNamespace(output_text=campo), 'RESULTADO: 2\nExplicación')
    assert llamadas == [('texto', 'RESULTADO: 2\nExplicación'), ('cursor', 0), 'foco']


@pytest.fixture(scope='module')
def aplicacion_wx():
    app = wx.App.Get() or wx.App(False)
    yield app


@pytest.mark.parametrize('clave,campos', [
    ('ecuacion', ['expresion']),
    ('derivar', ['expresion', 'variable']),
    ('limite', ['expresion', 'variable', 'tendencia']),
])
def test_controles_nativos_y_edicion(aplicacion_wx, monkeypatch, clave, campos):
    monkeypatch.setattr(dialogos_constructores, 'solicitar_expresion',
                        lambda parent, tipo, inicial: construir_raiz(inicial))
    dialogo = gui.DialogoCalculo(None, clave)
    try:
        assert list(dialogo.campos) == campos
        assert all(isinstance(campo, wx.TextCtrl) and campo.GetName() for campo in dialogo.campos.values())
        assert dialogo.GetDefaultItem() == dialogo.FindWindow(wx.ID_OK)
        assert dialogo.FindWindow(wx.ID_CANCEL).GetName()
        expresion = dialogo.campos['expresion']
        expresion.SetValue('x+1')
        expresion.SetSelection(0, 3)
        dialogo._insertar(1)
        assert expresion.GetValue() == 'sqrt(x+1)'
        assert expresion.GetSelection() == (9, 9)
        if clave == 'limite':
            assert dialogo.direccion.GetSelection() == 0
            assert dialogo.direccion.GetCount() == 3
    finally:
        dialogo.Destroy()
