"""Adaptación a controles wx reales y ciclo modal; no certifica lectores de pantalla."""
from types import SimpleNamespace
import threading

import pytest
import wx

import dialogos_constructores as gui
import interfaz_guiada
from constructores_matematicos import CONSTRUCTORES


@pytest.fixture(scope='module')
def aplicacion_wx():
    app = wx.App.Get() or wx.App(False)
    yield app


@pytest.fixture
def editor(aplicacion_wx):
    ventana = wx.Dialog(None, title='Prueba de edición')
    campo = wx.TextCtrl(ventana, value='a+x+1+b')
    yield ventana, campo
    ventana.Destroy()


@pytest.mark.parametrize('rango,insertado,esperado,cursor', [
    ((2, 5), '(x+1)/(x-2)', 'a+(x+1)/(x-2)+b', 13),
    ((2, 2), 'sqrt(x)', 'a+sqrt(x)x+1+b', 9),
    ((0, 0), '(x)^(2)', '(x)^(2)a+x+1+b', 7),
    ((7, 7), 'sqrt(4)', 'a+x+1+bsqrt(4)', 14),
])
def test_insercion_y_sustitucion(editor, monkeypatch, rango, insertado, esperado, cursor):
    ventana, campo = editor
    campo.SetSelection(*rango)
    iniciales = []
    monkeypatch.setattr(gui, 'solicitar_expresion',
                        lambda parent, tipo, inicial: iniciales.append(inicial) or insertado)
    gui.insertar_constructor(ventana, campo, 'fraccion')
    assert iniciales == ['' if rango[0] == rango[1] else 'x+1']
    assert campo.GetValue() == esperado
    assert campo.GetInsertionPoint() == cursor
    assert campo.GetSelection() == (cursor, cursor)


@pytest.mark.parametrize('rango', [(2, 5), (2, 2), (5, 2)])
def test_cancelar_no_toca_texto_seleccion_ni_cursor(editor, monkeypatch, rango):
    ventana, campo = editor
    campo.SetSelection(*rango)
    antes = campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()
    monkeypatch.setattr(gui, 'solicitar_expresion', lambda *args: None)
    gui.insertar_constructor(ventana, campo, 'potencia')
    assert (campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()) == antes


def modal(dialogo, accion):
    """Cierra siempre el modal, también si falla una aserción en la acción."""
    errores = []

    def iniciar():
        try:
            accion()
        except Exception as error:
            errores.append(error)
            dialogo.EndModal(wx.ID_CANCEL)

    def agotar_tiempo():
        errores.append(AssertionError('El diálogo no terminó en 5 segundos'))
        dialogo.EndModal(wx.ID_CANCEL)

    wx.CallAfter(iniciar)
    timer = wx.CallLater(5000, agotar_tiempo)
    try:
        resultado = dialogo.ShowModal()
    finally:
        timer.Stop()
    if errores:
        raise errores[0]
    return resultado


@pytest.mark.parametrize('tipo', CONSTRUCTORES)
def test_controles_nativos_etiquetas_foco_y_cancelar(aplicacion_wx, tipo):
    dialogo = gui.DialogoConstructor(None, tipo, 'x+1')
    try:
        controles = list(dialogo.campos.values())
        assert controles[0].GetValue() == 'x+1'
        assert all(isinstance(c, wx.TextCtrl) and c.GetName() for c in controles)
        for control in controles:
            assert isinstance(control.GetPrevSibling(), wx.StaticText)
            assert control.GetPrevSibling().GetLabel() == control.GetName()
        assert dialogo.GetDefaultItem() == dialogo.aceptar
        assert dialogo.GetEscapeId() == wx.ID_CANCEL
        if tipo == 'potencia':
            assert dialogo.campos['exponente'].GetValue() == '2'

        def cancelar():
            assert wx.Window.FindFocus() == controles[0]
            dialogo._cancelar(None)

        assert modal(dialogo, cancelar) == wx.ID_CANCEL
        assert dialogo.expresion is None
    finally:
        dialogo.Destroy()


@pytest.mark.parametrize('tipo,valores,esperado', [
    ('fraccion', ['x+1', 'x-2'], '(x+1)/(x-2)'),
    ('potencia', ['x+1', '1/2'], '(x+1)^(1/2)'),
    ('raiz', ['x+4'], 'sqrt(x+4)'),
])
def test_aceptar_modal_real_y_validacion_fuera_del_hilo_wx(aplicacion_wx, monkeypatch, tipo, valores, esperado):
    dialogo = gui.DialogoConstructor(None, tipo)
    validar = gui.construir_expresion
    hilos = []

    def comprobar_hilo(*args):
        hilos.append(wx.IsMainThread())
        return validar(*args)

    monkeypatch.setattr(gui, 'construir_expresion', comprobar_hilo)
    try:
        for campo, valor in zip(dialogo.campos.values(), valores):
            campo.SetValue(valor)
        assert modal(dialogo, lambda: dialogo._aceptar(None)) == wx.ID_OK
        assert dialogo.expresion == esperado
        assert hilos == [False]
    finally:
        dialogo.Destroy()


@pytest.mark.parametrize('tipo,clave,valores', [
    ('fraccion', 'numerador', ['', 'x']),
    ('fraccion', 'denominador', ['1', '0']),
    ('potencia', 'exponente', ['x', '']),
    ('raiz', 'radicando', ['x+']),
])
def test_validacion_devuelve_foco_al_campo(aplicacion_wx, monkeypatch, tipo, clave, valores):
    dialogo = gui.DialogoConstructor(None, tipo)
    mensajes, focos = [], []

    def mensaje(texto, *args, **kwargs):
        mensajes.append(texto)

        def comprobar_y_cancelar():
            focos.append(wx.Window.FindFocus())
            dialogo._cancelar(None)

        wx.CallAfter(comprobar_y_cancelar)

    monkeypatch.setattr(wx, 'MessageBox', mensaje)
    try:
        for campo, valor in zip(dialogo.campos.values(), valores):
            campo.SetValue(valor)
        assert modal(dialogo, lambda: dialogo._aceptar(None)) == wx.ID_CANCEL
        assert len(mensajes) == 1
        assert focos == [dialogo.campos[clave]]
        assert dialogo.expresion is None
    finally:
        dialogo.Destroy()


@pytest.mark.parametrize('cancelar', [False, True])
def test_foco_vuelve_al_editor_tras_constructor(editor, monkeypatch, cancelar):
    ventana, campo = editor
    campo.SetSelection(2, 5)
    monkeypatch.setattr(gui, 'solicitar_expresion', lambda *a: None if cancelar else 'sqrt(x+1)')
    focos = []

    def insertar():
        gui.insertar_constructor(ventana, campo, 'raiz')
        focos.append(wx.Window.FindFocus())
        ventana.EndModal(wx.ID_CANCEL)

    modal(ventana, insertar)
    assert focos == [campo]


@pytest.mark.parametrize('cancelar', [False, True])
def test_solicitar_expresa_cancelacion_y_destruye(monkeypatch, cancelar):
    destruidos = []
    falso = SimpleNamespace(ShowModal=lambda: wx.ID_CANCEL if cancelar else wx.ID_OK,
        expresion='(x)/(2)', Destroy=lambda: destruidos.append(True))
    monkeypatch.setattr(gui, 'DialogoConstructor', lambda *args: falso)
    assert gui.solicitar_expresion(None, 'fraccion', 'x') == (None if cancelar else '(x)/(2)')
    assert destruidos == [True]


def test_resultado_de_validacion_tardio_se_ignora(aplicacion_wx):
    dialogo = gui.DialogoConstructor(None, 'raiz')
    token = dialogo._token = object()
    try:
        assert modal(dialogo, lambda: dialogo._cancelar(None)) == wx.ID_CANCEL
        dialogo._validado(token, 'sqrt(4)', None)
        assert dialogo.expresion is None
    finally:
        dialogo.Destroy()
    dialogo._validado(token, 'sqrt(4)', None)


def test_cancelar_mientras_se_valida_no_bloquea_wx(aplicacion_wx, monkeypatch):
    dialogo = gui.DialogoConstructor(None, 'raiz', 'x')
    liberar = threading.Event()

    def lento(*args):
        liberar.wait(2)
        return 'sqrt(x)'

    monkeypatch.setattr(gui, 'construir_expresion', lento)
    try:
        def cancelar():
            dialogo._aceptar(None)
            assert not dialogo.aceptar.IsEnabled()
            assert not dialogo.campos['radicando'].IsEnabled()
            dialogo._cancelar(None)

        assert modal(dialogo, cancelar) == wx.ID_CANCEL
        assert dialogo.expresion is None
        assert dialogo._token is None
    finally:
        liberar.set()
        dialogo.Destroy()


@pytest.mark.parametrize('clave', ['ecuacion', 'derivar', 'limite'])
@pytest.mark.parametrize('indice,tipo,expresion', [
    (0, 'fraccion', '(x+1)/(x-2)'),
    (1, 'raiz', 'sqrt(x+1)'),
    (2, 'potencia', '(x+1)^(2)'),
])
@pytest.mark.parametrize('cancelar', [False, True])
def test_constructores_reales_en_los_tres_formularios(aplicacion_wx, monkeypatch, clave, indice, tipo, expresion, cancelar):
    padre = interfaz_guiada.DialogoCalculo(None, clave)
    fabrica = gui.DialogoConstructor
    iniciales, finales, timers = [], [], []

    def constructor(parent, elegido, inicial):
        dialogo = fabrica(parent, elegido, inicial)
        iniciales.append((elegido, next(iter(dialogo.campos.values())).GetValue()))

        def completar():
            if elegido == 'fraccion':
                dialogo.campos['denominador'].SetValue('x-2')
            boton = dialogo.FindWindow(wx.ID_CANCEL if cancelar else wx.ID_OK)
            boton.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId()))

        wx.CallAfter(completar)
        timers.append(wx.CallLater(4000, lambda: dialogo.EndModal(wx.ID_CANCEL) if dialogo and dialogo.IsModal() else None))
        return dialogo

    monkeypatch.setattr(gui, 'DialogoConstructor', constructor)
    campo = padre.campos['expresion']

    def insertar():
        campo.SetValue('a+x+1+b')
        campo.SetSelection(2, 5)
        antes = campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()
        padre._insertar(indice)
        finales.append((antes, campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint(), wx.Window.FindFocus()))
        padre.EndModal(wx.ID_CANCEL)

    try:
        modal(padre, insertar)
        assert iniciales == [(tipo, 'x+1')]
        antes, texto, seleccion, cursor, foco = finales[0]
        assert foco == campo
        if cancelar:
            assert (texto, seleccion, cursor) == antes
        else:
            assert texto == 'a+' + expresion + '+b'
            assert seleccion == (2 + len(expresion),) * 2
            assert cursor == 2 + len(expresion)
    finally:
        for timer in timers:
            timer.Stop()
        padre.Destroy()
