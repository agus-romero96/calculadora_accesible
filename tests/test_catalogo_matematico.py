"""Compatibilidad real con el parser y controles wx; no certifica NVDA/JAWS."""
from constructores_matematicos import construir_funcion
import pytest
import sympy
import wx
from catalogo_matematico import FUNCIONES, CATEGORIAS, funciones_categoria
from constructores_matematicos import ErrorCampoConstructor
from parser_matematico import ParserMatematico
import herramientas_matematicas as h
import dialogos_constructores as gui
from test_dialogos_constructores import aplicacion_wx, editor, modal

@pytest.mark.parametrize('funcion', FUNCIONES, ids=lambda f: f.canonica)
def test_catalogo_compatible_con_parser(funcion):
    texto = construir_funcion(funcion.canonica, ' x^2 + 1 ')
    assert texto == funcion.canonica + '(x^2 + 1)'
    expresion = ParserMatematico().parsear(texto)
    assert isinstance(expresion, sympy.Expr)
    simple = ParserMatematico().parsear(construir_funcion(funcion.canonica, 'x'))
    esperado = {'abs': sympy.Abs, 'heaviside': sympy.Heaviside, 'dirac': sympy.DiracDelta, 'log10': sympy.log}.get(funcion.canonica, getattr(sympy, funcion.canonica, None))
    if funcion.canonica == "log10":
        assert simple == sympy.log(ParserMatematico.simbolo("x"), 10)
    else:
        assert simple.func == esperado
    assert simple.free_symbols == {ParserMatematico.simbolo('x')}
    assert funcion.nombre and funcion.descripcion

@pytest.mark.parametrize('argumento', ['', ' ', 'x+', '(x', '[1,2]', 'matrix([[1]])', 'x<1', 'xsin(x)', 'x,y'])
def test_argumentos_invalidos(argumento):
    with pytest.raises(ErrorCampoConstructor) as error:
        construir_funcion('sin', argumento)
    assert error.value.campo == 'argumento'

def test_no_evalua_funcion_y_no_agrega_nombres():
    assert construir_funcion('sin', 'pi') == 'sin(pi)'
    assert construir_funcion('abs', 'x/x') == 'abs(x/x)'
    with pytest.raises(ValueError):
        construir_funcion('asec', 'x')

@pytest.mark.parametrize('categoria', CATEGORIAS)
def test_categorias(categoria):
    assert funciones_categoria(categoria)
    assert all(f.categoria == categoria for f in funciones_categoria(categoria))
    assert len({f.canonica for f in FUNCIONES}) == len(FUNCIONES)

@pytest.mark.parametrize('nombre', [f.canonica for f in FUNCIONES])
def test_dialogo_funcion_preseleccion_y_aceptar(aplicacion_wx, nombre):
    dialogo = h.DialogoFuncion(None, nombre, 'x+1')
    try:
        assert dialogo.disponibles[dialogo.lista.GetSelection()].canonica == nombre
        assert dialogo.GetEscapeId() == wx.ID_CANCEL
        assert dialogo.GetDefaultItem() == dialogo.aceptar
        assert dialogo.campos['argumento'].GetValue() == 'x+1'
        assert modal(dialogo, lambda: dialogo._aceptar(None)) == wx.ID_OK
        assert dialogo.expresion == nombre + '(x+1)'
    finally:
        dialogo.Destroy()

def test_cambiar_categoria(aplicacion_wx):
    dialogo = h.DialogoFuncion(None, 'sin')
    try:
        for indice, categoria in enumerate(CATEGORIAS):
            dialogo.categoria.SetSelection(indice)
            evento = wx.CommandEvent(wx.EVT_CHOICE.typeId, dialogo.categoria.GetId())
            dialogo.categoria.GetEventHandler().ProcessEvent(evento)
            assert dialogo.disponibles == funciones_categoria(categoria)
            assert dialogo.lista.GetSelection() == 0
            assert dialogo.descripcion.GetLabel()
    finally:
        dialogo.Destroy()

@pytest.mark.parametrize('posicion', [wx.DefaultPosition, wx.Point(10, 10)])
def test_contexto_teclado_y_raton_no_cambia_seleccion(editor, monkeypatch, posicion):
    ventana, campo = editor
    campo.SetSelection(2, 5)
    antes = campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()
    menus = []
    def abrir(menu, *args):
        menus.append([item.GetItemLabelText() for item in menu.GetMenuItems()])
    monkeypatch.setattr(campo, 'PopupMenu', abrir)
    h.instalar_menu(ventana, campo)
    evento = wx.ContextMenuEvent(wx.EVT_CONTEXT_MENU.typeId, campo.GetId(), posicion)
    campo.GetEventHandler().ProcessEvent(evento)
    assert menus and len(menus[0]) == 15
    assert (campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()) == antes


def test_menu_conserva_acciones_nativas_y_no_instala_resultados(editor):
    ventana, campo = editor
    campo.SetSelection(2, 5)
    menu = h.crear_menu(ventana, campo)
    try:
        items = menu.GetMenuItems()
        assert items[0].IsEnabled() == campo.CanUndo()
        assert items[1].IsEnabled() == campo.CanRedo()
        evento = wx.CommandEvent(wx.EVT_MENU.typeId, items[6].GetId())
        menu.ProcessEvent(evento)
        assert campo.GetSelection() == (0, campo.GetLastPosition())
        campo.SetSelection(2, 5)
        menu.ProcessEvent(wx.CommandEvent(wx.EVT_MENU.typeId, items[5].GetId()))
        assert campo.GetValue() == 'a++b'
    finally:
        menu.Destroy()
    campo.SetEditable(False)
    h.instalar_menu(ventana, campo)
    assert not getattr(campo, '_menu_matematico', False)

@pytest.mark.parametrize('tipo', ['funcion:sin', 'catalogo', 'parentesis', 'constante:pi'])
@pytest.mark.parametrize('rango', [(2,5), (2,2), (5,2)])
@pytest.mark.parametrize('cancelar', [True, False])
def test_insercion_compartida_y_cancelacion(editor, monkeypatch, tipo, rango, cancelar):
    ventana, campo = editor
    campo.SetSelection(*rango)
    antes = campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()
    iniciales = []
    def solicitar(parent, elegido, inicial):
        iniciales.append((elegido, inicial))
        return None if cancelar else 'sin(x+1)'
    monkeypatch.setattr(gui, 'solicitar_expresion', solicitar)
    def insertar():
        nonlocal antes
        campo.SetSelection(*rango)
        antes = campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()
        gui.insertar_constructor(ventana, campo, tipo)
        assert wx.Window.FindFocus() == campo
        ventana.EndModal(wx.ID_CANCEL)
    modal(ventana, insertar)
    assert iniciales == [(tipo, 'x+1' if rango[0] != rango[1] else '')]
    if cancelar:
        assert (campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()) == antes
    else:
        a,b = sorted(rango)
        assert campo.GetValue() == antes[0][:a] + 'sin(x+1)' + antes[0][b:]
        assert campo.GetInsertionPoint() == a + 8


def test_error_funcion_recupera_argumento_y_foco(aplicacion_wx, monkeypatch):
    dialogo = h.DialogoFuncion(None, 'sin', 'x+')
    mensajes = []
    def mensaje(*args, **kwargs):
        mensajes.append(args[0])
        def corregir():
            assert wx.Window.FindFocus() == dialogo.campos['argumento']
            assert dialogo.campos['argumento'].GetValue() == 'x+'
            dialogo.campos['argumento'].SetValue('x')
            dialogo._aceptar(None)
        wx.CallAfter(corregir)
    monkeypatch.setattr(wx, 'MessageBox', mensaje)
    try:
        assert modal(dialogo, lambda: dialogo._aceptar(None)) == wx.ID_OK
        assert len(mensajes) == 1
        assert dialogo.expresion == 'sin(x)'
    finally:
        dialogo.Destroy()

@pytest.mark.parametrize('idioma', ['es', 'en'])
@pytest.mark.parametrize('clave', ['libre', 'ecuacion', 'derivar', 'limite', 'evaluar', 'simplificar', 'factorizar', 'integrar', 'integral_definida'])
def test_boton_catalogo_entrada_libre_y_guiada(aplicacion_wx, monkeypatch, idioma, clave):
    import i18n
    import interfaz_guiada
    anterior = i18n.idioma_actual()
    i18n.establecer_idioma(idioma)
    ventana = None
    try:
        if clave == 'libre':
            import main
            ventana = main.CalculadoraAccesible()
            campo = ventana.input_text
            boton = ventana.btn_insertar
            assert not getattr(ventana.output_text, '_menu_matematico', False)
            assert not getattr(ventana.lbl_info, '_menu_matematico', False)
        else:
            ventana = interfaz_guiada.DialogoCalculo(None, clave)
            campo = ventana.campos['expresion']
            boton = next(c for c in ventana.GetChildren() if isinstance(c, wx.Button) and c.GetLabel() == i18n.tr('Insertar expresión...'))
        assert campo._menu_matematico
        assert boton.GetName() == i18n.tr('Insertar expresión...')
        campo.SetValue('a+x+1+b')
        campo.SetSelection(2, 5)
        enviados = []
        monkeypatch.setattr(gui, 'solicitar_expresion', lambda p,t,i: enviados.append((t,i)) or 'log10(x+1)')
        boton.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId()))
        assert enviados == [('catalogo', 'x+1')]
        assert campo.GetValue() == 'a+log10(x+1)+b'
        assert campo.GetInsertionPoint() == 12
    finally:
        if ventana is not None:
            if clave == 'libre':
                ventana.proceso.cerrar()
            ventana.Destroy()
        i18n.establecer_idioma(anterior)

@pytest.mark.parametrize('tipo', ['fraccion', 'cos', None])
def test_selector_catalogo_comparte_solicitud(aplicacion_wx, monkeypatch, tipo):
    fabrica = h.DialogoCatalogo
    def crear(*args, **kwargs):
        dialogo = fabrica(*args, **kwargs)
        def elegir():
            if tipo is None:
                dialogo._cancelar(None)
            else:
                if tipo == 'cos':
                    dialogo.categoria.SetSelection(1)
                    dialogo._categoria(None)
                    dialogo.lista.SetSelection(1)
                dialogo._aceptar(None)
        wx.CallAfter(elegir)
        return dialogo
    monkeypatch.setattr(h, 'DialogoCatalogo', crear)
    enviados = []
    monkeypatch.setattr(gui, 'solicitar_expresion', lambda p,t,i: enviados.append((t,i)) or '(x+1)/(2)')
    assert h.solicitar_catalogo(None, 'x+1') == (None if tipo is None else 'cos(x+1)' if tipo == 'cos' else '(x+1)/(2)')
    assert enviados == ([('fraccion', 'x+1')] if tipo == 'fraccion' else [])

@pytest.mark.parametrize('tipo,esperado', [('parentesis', '(x+1)'), ('constante:pi', 'pi'), ('funcion:sin', 'sin(x+1)')])
def test_despacho_real_constructores(aplicacion_wx, monkeypatch, tipo, esperado):
    fabrica = h.DialogoFuncion if tipo.startswith('funcion:') else gui.DialogoConstructor
    def crear(*args, **kwargs):
        dialogo = fabrica(*args, **kwargs)
        wx.CallAfter(dialogo._aceptar, None)
        return dialogo
    monkeypatch.setattr(h if tipo.startswith('funcion:') else gui,
                        'DialogoFuncion' if tipo.startswith('funcion:') else 'DialogoConstructor', crear)
    assert gui.solicitar_expresion(None, tipo, 'x+1') == esperado

def test_orden_tab_funcion_y_escape(aplicacion_wx):
    dialogo = h.DialogoFuncion(None, 'sin', 'x')
    try:
        def comprobar():
            controles = [dialogo.categoria, dialogo.lista, dialogo.campos['argumento'], dialogo.aceptar, dialogo.FindWindow(wx.ID_CANCEL)]
            assert wx.Window.FindFocus() == controles[0]
            for anterior, siguiente in zip(controles, controles[1:]):
                anterior.Navigate(wx.NavigationKeyEvent.IsForward)
                assert wx.Window.FindFocus() == siguiente
            for actual, anterior in zip(reversed(controles[1:]), reversed(controles[:-1])):
                actual.Navigate(wx.NavigationKeyEvent.IsBackward)
                assert wx.Window.FindFocus() == anterior
            dialogo._cancelar(None)
        assert modal(dialogo, comprobar) == wx.ID_CANCEL
        assert dialogo.expresion is None
    finally:
        dialogo.Destroy()


@pytest.mark.parametrize('idioma', ['es', 'en'])
def test_catalogo_filtra_conserva_argumento_y_foco(aplicacion_wx, idioma):
    import i18n
    anterior = i18n.idioma_actual()
    i18n.establecer_idioma(idioma)
    dialogo = h.DialogoCatalogo(None, 'x^2+1')
    try:
        def comprobar():
            assert len(dialogo.categorias) == 6
            assert dialogo.lista.GetName() == i18n.tr('Función o estructura:')
            assert dialogo.categoria.GetName() == i18n.tr('Categoría:')
            argumento = dialogo.campos['argumento']
            argumento.SetSelection(1, 4)
            rango = argumento.GetSelection()
            dialogo.categoria.SetFocus()
            encontradas = []
            for indice, categoria in enumerate(dialogo.categorias):
                dialogo.categoria.SetSelection(indice)
                dialogo.categoria.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.EVT_CHOICE.typeId, dialogo.categoria.GetId()))
                assert wx.Window.FindFocus() == dialogo.categoria
                assert argumento.GetValue() == 'x^2+1'
                assert argumento.GetSelection() == rango
                assert dialogo.lista.GetSelection() == 0
                if categoria == 'estructuras':
                    assert [f.canonica for f in dialogo.disponibles] == [t for t,n in h.ESTRUCTURAS]
                else:
                    assert dialogo.disponibles == funciones_categoria(categoria)
                    encontradas.extend(f.canonica for f in dialogo.disponibles)
                assert dialogo.lista.GetStrings() == [i18n.tr(f.nombre) for f in dialogo.disponibles]
                dialogo.lista.SetSelection(len(dialogo.disponibles)-1)
            assert set(encontradas) == {f.canonica for f in FUNCIONES}
            assert len(encontradas) == 23
            controles = [dialogo.categoria, dialogo.lista, argumento, dialogo.aceptar, dialogo.FindWindow(wx.ID_CANCEL)]
            for previo, siguiente in zip(controles, controles[1:]):
                previo.Navigate(wx.NavigationKeyEvent.IsForward)
                assert wx.Window.FindFocus() == siguiente
            for actual, previo in zip(reversed(controles[1:]), reversed(controles[:-1])):
                actual.Navigate(wx.NavigationKeyEvent.IsBackward)
                assert wx.Window.FindFocus() == previo
            dialogo._cancelar(None)
        assert modal(dialogo, comprobar) == wx.ID_CANCEL
    finally:
        dialogo.Destroy()
        i18n.establecer_idioma(anterior)


@pytest.mark.parametrize('funcion', FUNCIONES, ids=lambda f: f.canonica)
def test_catalogo_inserta_cada_funcion(aplicacion_wx, funcion):
    dialogo = h.DialogoCatalogo(None, 'x+1')
    try:
        def aceptar():
            dialogo.categoria.SetSelection(list(dialogo.categorias).index(funcion.categoria))
            dialogo._categoria(None)
            dialogo.lista.SetSelection([f.canonica for f in dialogo.disponibles].index(funcion.canonica))
            dialogo._aceptar(None)
        assert modal(dialogo, aceptar) == wx.ID_OK
        assert dialogo.expresion == funcion.canonica + '(x+1)'
    finally:
        dialogo.Destroy()


def test_cancelar_constructor_conserva_catalogo(aplicacion_wx, monkeypatch):
    dialogo = h.DialogoCatalogo(None, 'x+1')
    monkeypatch.setattr(gui, 'solicitar_expresion', lambda *args: None)
    try:
        def cancelar():
            campo = dialogo.campos['argumento']
            campo.SetSelection(1, 3)
            dialogo._aceptar(None)
            assert dialogo.IsModal()
            assert wx.Window.FindFocus() == campo
            assert campo.GetValue() == 'x+1'
            assert campo.GetSelection() == (1, 3)
            assert dialogo.expresion is None
            dialogo._cancelar(None)
        assert modal(dialogo, cancelar) == wx.ID_CANCEL
    finally:
        dialogo.Destroy()


@pytest.mark.parametrize('cancelar', [True, False])
@pytest.mark.parametrize('rango', [(2,5), (2,2), (5,2)])
def test_catalogo_real_restaura_editor(editor, monkeypatch, cancelar, rango):
    ventana, campo = editor
    fabrica = h.DialogoCatalogo
    def crear(*args, **kwargs):
        dialogo = fabrica(*args, **kwargs)
        def elegir():
            if cancelar:
                dialogo._cancelar(None)
            else:
                dialogo.categoria.SetSelection(1)
                dialogo._categoria(None)
                if not dialogo.campos['argumento'].GetValue():
                    dialogo.campos['argumento'].SetValue('x')
                dialogo._aceptar(None)
        wx.CallAfter(elegir)
        return dialogo
    monkeypatch.setattr(h, 'DialogoCatalogo', crear)
    def insertar():
        campo.SetSelection(*rango)
        antes = campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()
        gui.insertar_constructor(ventana, campo, 'catalogo')
        assert wx.Window.FindFocus() == campo
        if cancelar:
            assert (campo.GetValue(), campo.GetSelection(), campo.GetInsertionPoint()) == antes
        else:
            a,b = sorted(rango)
            expresion = 'sin(x+1)' if a != b else 'sin(x)'
            assert campo.GetValue() == antes[0][:a] + expresion + antes[0][b:]
            assert campo.GetSelection() == (a+len(expresion),)*2
        ventana.EndModal(wx.ID_CANCEL)
    modal(ventana, insertar)
