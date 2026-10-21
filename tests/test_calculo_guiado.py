"""Contratos de cálculo avanzado; controles reales, sin certificar lectores de pantalla."""
import pytest
import wx
import i18n
from catalogos import leer
import interfaz_guiada as gui
import herramientas_matematicas as herramientas
from formularios_guiados import construir_argumentos, CampoObligatorio
from test_dialogos_constructores import aplicacion_wx, modal

DATOS = {
    'derivada_n': dict(expresion=' x^4 ', variable=' x ', orden=' 3 '),
    'tangente': dict(expresion='x^2', variable='x', punto='1/2'),
    'extremos': dict(expresion='x^3-3*x', variable='x'),
    'taylor': dict(expresion='exp(x)', variable='x', orden='3', punto='pi/2'),
    'implicita': dict(expresion=' x^2+y^2=25 '),
}

@pytest.mark.parametrize('clave,esperado', [
    ('derivada_n', ('x^4', 'x', 3)), ('tangente', ('x^2', 'x', '1/2')),
    ('extremos', ('x^3-3*x', 'x')), ('taylor', ('exp(x)', 'x', 3, 'pi/2')),
    ('implicita', ('x^2+y^2=25',)),
])
def test_argumentos(clave, esperado):
    assert construir_argumentos(clave, **DATOS[clave]) == esperado

@pytest.mark.parametrize('clave', ['derivada_n', 'taylor'])
@pytest.mark.parametrize('orden', ['', ' ', '1.5', '3.0', 'x', '1/2', '-1'])
def test_orden_invalido(clave, orden):
    with pytest.raises(CampoObligatorio) as error:
        construir_argumentos(clave, **dict(DATOS[clave], orden=orden))
    assert error.value.campo == 'orden'

@pytest.mark.parametrize('clave,orden', [('derivada_n', '1'), ('derivada_n', '16'), ('taylor', '0'), ('taylor', '15')])
def test_fronteras_del_motor(clave, orden):
    assert construir_argumentos(clave, **dict(DATOS[clave], orden=orden))[2] == int(orden)

@pytest.mark.parametrize('clave', DATOS)
def test_resultado_e_historial_compartidos(core, tmp_path, clave):
    from historial import Historial, cargar
    import sympy
    datos = dict(DATOS[clave])
    if clave == 'tangente':
        datos['punto'] = '1'
    if clave == 'taylor':
        datos['punto'] = '0'
    operacion = gui.OPERACION[clave]
    resultado = getattr(core, operacion.metodo)(*construir_argumentos(clave, **datos))
    assert not resultado.es_error
    assert resultado.operacion == clave
    x = core.parser_comun.simbolo('x')
    y = core.parser_comun.simbolo('y')
    if clave == 'derivada_n':
        assert resultado.valor == 24*x
    elif clave == 'taylor':
        assert sympy.expand(resultado.valor - (1+x+x**2/2+x**3/6)) == 0
    elif clave == 'implicita':
        assert sympy.simplify(resultado.valor + x/y) == 0
    elif clave == 'tangente':
        assert resultado.valor == [sympy.Eq(y, 2*x-1), sympy.Eq(y, (3-x)/2)]
    else:
        assert resultado.valor and '-1' in resultado.texto and '1' in resultado.texto
    ruta = str(tmp_path / 'historial.json')
    historial = Historial(ruta)
    historial.agregar(resultado)
    recuperado, = cargar(ruta)
    assert recuperado.operacion == clave
    assert recuperado.texto == resultado.texto
    assert recuperado.parametros == resultado.parametros

@pytest.mark.parametrize('clave', DATOS)
def test_progreso_y_envio_unico(monkeypatch, clave):
    from types import SimpleNamespace
    solicitud = gui.SolicitudGuiada(gui.OPERACION[clave], construir_argumentos(clave, **DATOS[clave]), DATOS[clave])
    llamadas = []
    foco = SimpleNamespace(SetFocus=lambda: None)
    padre = SimpleNamespace(input_text=foco, _ejecutar=lambda *a, **kw: llamadas.append(a))
    monkeypatch.setattr(wx.Window, 'FindFocus', lambda: foco)
    monkeypatch.setattr(gui, 'solicitar_calculo', lambda *a: solicitud)
    gui.iniciar_calculo_guiado(padre)
    assert len(llamadas) == 1
    assert llamadas[0][:2] == (solicitud.operacion.metodo, solicitud.argumentos)
    assert '{' not in llamadas[0][2]
    if 'orden' in DATOS[clave]:
        assert '3' in llamadas[0][2]

@pytest.mark.parametrize('idioma', ['es', 'en'])
@pytest.mark.parametrize('clave', DATOS)
@pytest.mark.parametrize('cancelar', [False, True])
def test_catalogo_foco_navegacion_y_traducciones(aplicacion_wx, monkeypatch, idioma, clave, cancelar):
    anterior = i18n.idioma_actual()
    i18n.establecer_idioma(idioma)
    dialogo = gui.DialogoCalculo(None, clave, DATOS[clave])
    fabrica = herramientas.DialogoCatalogo
    def crear(*args):
        catalogo = fabrica(*args)
        def actuar():
            if cancelar:
                catalogo._cancelar(None)
            else:
                catalogo.categoria.SetSelection(1)
                catalogo._categoria(None)
                catalogo._aceptar(None)
        wx.CallAfter(actuar)
        return catalogo
    monkeypatch.setattr(herramientas, 'DialogoCatalogo', crear)
    try:
        for campo in gui.FORMULARIOS[clave].campos:
            assert dialogo.campos[campo.clave].GetName() == i18n.tr(campo.etiqueta)
            assert campo.etiqueta in leer(idioma)
        def comprobar():
            campo = dialogo.campos['expresion']
            assert wx.Window.FindFocus() == campo
            assert dialogo.GetEscapeId() == wx.ID_CANCEL
            controles = [c for c in dialogo.GetChildren() if c.AcceptsFocus()]
            for previo, siguiente in zip(controles, controles[1:]):
                previo.SetFocus()
                previo.Navigate(wx.NavigationKeyEvent.IsForward)
                assert wx.Window.FindFocus() == siguiente
                siguiente.Navigate(wx.NavigationKeyEvent.IsBackward)
                assert wx.Window.FindFocus() == previo
            campo.SetValue('x+1')
            campo.SetSelection(0, 3)
            gui.insertar_constructor(dialogo, campo, 'catalogo')
            assert campo.GetValue() == ('x+1' if cancelar else 'sin(x+1)')
            assert campo.GetSelection() == ((0, 3) if cancelar else (8, 8))
            assert wx.Window.FindFocus() == campo
            dialogo.EndModal(wx.ID_CANCEL)
        assert modal(dialogo, comprobar) == wx.ID_CANCEL
    finally:
        dialogo.Destroy()
        i18n.establecer_idioma(anterior)
