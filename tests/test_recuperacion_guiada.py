"""Recuperación por es_error, con controles nativos y cálculo real en otro proceso."""
from types import SimpleNamespace

import pytest
import wx

import interfaz_guiada as gui
from main import CalculadoraAccesible
from proceso_calculo import ProcesoCalculo
from puente import OPERACION, ResultadoOperacion
from test_dialogos_constructores import modal
from test_interfaz_guiada import handlers


@pytest.fixture(scope='module')
def aplicacion_wx():
    app = wx.App.Get() or wx.App(False)
    yield app


@pytest.mark.parametrize('clave,valores,campo', [
    ('derivada_n', {'expresion': 'x^4', 'variable': 'x', 'orden': '0'}, 'orden'),
    ('taylor', {'expresion': 'exp(x)', 'variable': 'x', 'orden': '16', 'punto': '0'}, 'orden'),
    ('tangente', {'expresion': 'x^2', 'variable': 'x', 'punto': ' '}, 'punto'),
    ('extremos', {'expresion': 'x^3', 'variable': ' '}, 'variable'),
    ('implicita', {'expresion': ' '}, 'expresion'),
    ('ecuacion', {'expresion': ' 2*x+1 '}, 'expresion'),
    ('derivar', {'expresion': ' x^2 ', 'variable': ' '}, 'variable'),
    ('limite', {'expresion': ' t^2 ', 'variable': 't', 'tendencia': ' ', 'direccion': 2}, 'tendencia'),
    ('limite', {'expresion': ' t^2 ', 'variable': 't', 'tendencia': '0+', 'direccion': 1}, 'tendencia'),
    ('evaluar', {'expresion': ' '}, 'expresion'),
    ('simplificar', {'expresion': ' '}, 'expresion'),
    ('factorizar', {'expresion': ' '}, 'expresion'),
    ('integrar', {'expresion': ' ', 'variable': 't'}, 'expresion'),
    ('integrar', {'expresion': ' t ', 'variable': ' '}, 'variable'),
    ('integral_definida', {'expresion': ' ', 'variable': 't', 'inferior': '0', 'superior': '2'}, 'expresion'),
    ('integral_definida', {'expresion': ' t ', 'variable': ' ', 'inferior': '0', 'superior': '2'}, 'variable'),
    ('integral_definida', {'expresion': ' t ', 'variable': 't', 'inferior': ' ', 'superior': '2'}, 'inferior'),
    ('integral_definida', {'expresion': ' t ', 'variable': 't', 'inferior': '0', 'superior': ' '}, 'superior'),
])
def test_error_local_mantiene_formulario_y_foco(aplicacion_wx, monkeypatch, clave, valores, campo):
    dialogo = gui.DialogoCalculo(None, clave, valores)
    mensajes, estados = [], []

    def mensaje(texto, *args, **kwargs):
        mensajes.append((texto, dialogo.IsModal()))

        def cancelar():
            estados.append((dialogo.obtener_valores(), wx.Window.FindFocus()))
            dialogo.EndModal(wx.ID_CANCEL)

        wx.CallAfter(cancelar)

    monkeypatch.setattr(wx, 'MessageBox', mensaje)
    try:
        assert modal(dialogo, lambda: dialogo._aceptar(None)) == wx.ID_CANCEL
        assert len(mensajes) == 1 and mensajes[0][1]
        assert estados == [(valores, dialogo.campos[campo])]
        assert dialogo.argumentos is None
    finally:
        dialogo.Destroy()


@pytest.mark.parametrize('activa', [False, True])
@pytest.mark.parametrize('guiada', [False, True])
def test_finalizacion_respeta_token_y_modo_libre(activa, guiada):
    llamadas = []
    token = object()
    falso = SimpleNamespace(_calculo_actual=token if activa else None,
        _cerrar_progreso=lambda: llamadas.append('cerrar progreso'),
        lbl_info=SimpleNamespace(SetValue=lambda texto: llamadas.append(texto)),
        presentar_resultado=lambda resultado: llamadas.append('libre'))
    callback = (lambda resultado: llamadas.append('guiada')) if guiada else None
    funcion = handlers('_finalizar_calculo', texto_info=lambda: 'listo')['_finalizar_calculo']
    funcion(falso, token, ResultadoOperacion('ecuacion', 'x=', 'error', es_error=True), callback)
    assert llamadas == (['cerrar progreso', 'listo', 'guiada' if guiada else 'libre'] if activa else [])
    assert falso._calculo_actual is None


@pytest.mark.parametrize('tipo', ['sin_solucion', 'no_existe', 'no_concluyente', 'integral_divergente'])
def test_respuestas_matematicas_legitimas_no_recuperan(core, monkeypatch, tipo):
    if tipo == 'sin_solucion':
        resultado = core.ecuacion('x^2=-1')
        assert str(resultado.valor) == 'EmptySet'
    elif tipo == 'no_existe':
        resultado = core.limite('1/x', 'x', '0')
    elif tipo == 'integral_divergente':
        resultado = core.integral_definida('1/x^2', 'x', '-1', '1')
    else:
        # El protocolo distingue el estado del texto: no se deduce por palabras.
        resultado = ResultadoOperacion('limite', 'f(x)', 'No concluyente', es_error=False)
    assert not resultado.es_error
    solicitud = gui.SolicitudGuiada(OPERACION['limite'], ('1/x', 'x', '0'),
        {'expresion': '1/x', 'variable': 'x', 'tendencia': '0', 'direccion': 0})
    solicitudes, callbacks, presentados = [], [], []
    foco = SimpleNamespace(SetFocus=lambda: None)
    padre = SimpleNamespace(input_text=foco, presentar_resultado=presentados.append,
        _ejecutar=lambda *args, **kw: callbacks.append(kw['al_finalizar']))
    monkeypatch.setattr(wx.Window, 'FindFocus', lambda: foco)
    monkeypatch.setattr(gui, 'solicitar_calculo', lambda *a: solicitudes.append(a) or solicitud)
    monkeypatch.setattr(wx, 'MessageBox', lambda *a, **kw: pytest.fail('Un resultado válido no es un error'))
    gui.iniciar_calculo_guiado(padre)
    callbacks[0](resultado)
    assert presentados == [resultado]
    assert len(solicitudes) == len(callbacks) == 1


def test_error_del_motor_sin_metadatos_recupera_su_envio_sin_recalcular(monkeypatch):
    valores = {'expresion': ' t^2 ', 'variable': ' t ', 'tendencia': ' 0 ', 'direccion': 2}
    solicitud = gui.SolicitudGuiada(OPERACION['limite'], ('t^2', 't', '0+'), valores)
    solicitudes, callbacks, mensajes = [], [], []
    foco = SimpleNamespace(SetFocus=lambda: None)
    padre = SimpleNamespace(input_text=foco,
        presentar_resultado=lambda resultado: pytest.fail('No debe presentar el fallo como resultado'),
        _ejecutar=lambda *args, **kw: callbacks.append(kw['al_finalizar']))

    def solicitar(parent, anterior):
        solicitudes.append(anterior)
        return solicitud if anterior is None else None  # Cancelación del formulario recuperado.

    monkeypatch.setattr(wx.Window, 'FindFocus', lambda: foco)
    monkeypatch.setattr(wx, 'MessageBox', lambda texto, *a, **kw: mensajes.append(texto))
    monkeypatch.setattr(gui, 'solicitar_calculo', solicitar)
    gui.iniciar_calculo_guiado(padre)
    callbacks[0](ResultadoOperacion('', '', 'Fallo del motor', es_error=True))
    assert solicitudes == [None, solicitud]
    assert solicitudes[1].valores == valores
    assert mensajes == ['Fallo del motor']
    assert len(callbacks) == 1


@pytest.fixture(scope='module')
def proceso():
    proceso = ProcesoCalculo()
    proceso.calcular('evaluar', '1')  # Arranque fuera del bucle de eventos de la prueba.
    yield proceso
    proceso.cerrar()


class VentanaPrueba(wx.Dialog):
    """Usa el ejecutor y el finalizador reales sin preferencias ni historial del usuario."""
    _mostrar_texto = CalculadoraAccesible._mostrar_texto
    MS_ANTES_DE_AVISAR = 60000

    def __init__(self, proceso):
        super().__init__(None, title='Prueba de recuperación')
        self.proceso = proceso
        self._calculo_actual = self._timer_aviso = None
        self.lbl_info = wx.TextCtrl(self)
        self.input_text = wx.TextCtrl(self, value='editor libre intacto')
        self.output_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.envios, self.resultados, self.focos = [], [], []

    def _ejecutar(self, metodo, args, descripcion, **kwargs):
        self.envios.append((metodo, args))
        CalculadoraAccesible._ejecutar(self, metodo, args, descripcion, **kwargs)

    def _finalizar_calculo(self, *args):
        CalculadoraAccesible._finalizar_calculo(self, *args)
        if self._calculo_actual is None and not self.resultados:
            # Cierra el contenedor de prueba después de salir del modal recuperado.
            self.EndModal(wx.ID_CANCEL)

    def _cerrar_progreso(self):
        if self._timer_aviso is not None:
            self._timer_aviso.Stop()
            self._timer_aviso = None

    def _mostrar_progreso(self, *args):
        pass

    def presentar_resultado(self, resultado):
        self.resultados.append(resultado)
        self._mostrar_texto(resultado.texto)
        self.focos.append((wx.Window.FindFocus(), self.output_text.GetInsertionPoint()))
        self.EndModal(wx.ID_OK)


@pytest.mark.parametrize('clave,valores,corregida,esperado', [
    ('derivada_n', {'expresion': ' x^ ', 'variable': ' x ', 'orden': ' 3 '}, 'x^4', '24*x'),
    ('taylor', {'expresion': ' exp( ', 'variable': ' x ', 'orden': ' 3 ', 'punto': ' 0 '}, 'exp(x)', 'x**3/6 + x**2/2 + x + 1'),
    ('tangente', {'expresion': 'x^2', 'variable': 'x', 'punto': '('}, {'punto': '1'}, '[Eq(y, 2*x - 1), Eq(y, 3/2 - x/2)]'),
    ('extremos', {'expresion': ' x^ ', 'variable': ' x '}, 'x', None),
    ('implicita', {'expresion': 'x^2+y^2='}, 'x^2+y^2=25', '-x/y'),
    ('ecuacion', {'expresion': ' x+ = 1 '}, 'x+1=3', '{2}'),
    ('derivar', {'expresion': ' t^ ', 'variable': ' t '}, 't^3', '3*t**2'),
    ('limite', {'expresion': ' t+ ', 'variable': ' t ', 'tendencia': ' -2 ', 'direccion': 0}, 't+1', '-1'),
    ('limite', {'expresion': ' t+ ', 'variable': ' t ', 'tendencia': ' -2 ', 'direccion': 1}, 't+1', '-1'),
    ('limite', {'expresion': ' t+ ', 'variable': ' t ', 'tendencia': ' -2 ', 'direccion': 2}, 't+1', '-1'),
    ('evaluar', {'expresion': ' 2+ '}, '2+3*4', '14'),
    ('simplificar', {'expresion': ' t+ '}, '(t^2-1)/(t-1)', 't + 1'),
    ('factorizar', {'expresion': ' t+ '}, '2*t+2', '2*(t + 1)'),
    ('integrar', {'expresion': ' t^ ', 'variable': ' t '}, 't^2', 't**3/3'),
    ('integral_definida', {'expresion': ' t^ ', 'variable': ' t ', 'inferior': ' -1 ', 'superior': ' 2 '}, 't', '3/2'),
    ('integral_definida', {'expresion': ' t ', 'variable': ' t ', 'inferior': ' ( ', 'superior': ' 2 '}, {'inferior': '0'}, '2'),
    ('integral_definida', {'expresion': ' t ', 'variable': ' t ', 'inferior': ' 0 ', 'superior': ' ( '}, {'superior': '2'}, '2'),
])
@pytest.mark.parametrize('cancelar', [False, True])
def test_error_del_proceso_recupera_datos_y_permite_corregir_o_cancelar(
        aplicacion_wx, proceso, monkeypatch, clave, valores, corregida, esperado, cancelar):
    padre = VentanaPrueba(proceso)
    fabrica = gui.DialogoCalculo
    formularios, mensajes, errores, timers, selecciones = [], [], [], [], []
    selector = SimpleNamespace(ShowModal=lambda: wx.ID_OK,
        GetSelection=lambda: selecciones.append(True) or [op[0] for op in gui.OPCIONES].index(clave),
        Destroy=lambda: None)
    monkeypatch.setattr(wx, 'SingleChoiceDialog', lambda *a: selector)

    def mensaje(texto, *args, **kwargs):
        mensajes.append((texto, wx.IsMainThread()))

    monkeypatch.setattr(wx, 'MessageBox', mensaje)

    def crear(parent, operacion, anteriores=None):
        dialogo = fabrica(parent, operacion, anteriores)
        vuelta = len(formularios)
        formularios.append((operacion, dialogo.obtener_valores()))

        def actuar():
            try:
                assert wx.IsMainThread()
                if vuelta == 0:
                    for nombre, campo in dialogo.campos.items():
                        campo.SetValue(valores[nombre])
                    if clave == 'limite':
                        dialogo.direccion.SetSelection(valores['direccion'])
                else:
                    assert vuelta == 1  # No hay reenvíos ni reaperturas automáticos.
                    assert len(padre.envios) == 1
                    assert dialogo.obtener_valores() == valores
                    assert wx.Window.FindFocus() == dialogo.campos['expresion']
                    if cancelar:
                        dialogo.EndModal(wx.ID_CANCEL)
                        return
                    cambios = {'expresion': corregida} if isinstance(corregida, str) else corregida
                    for campo, texto in cambios.items():
                        dialogo.campos[campo].SetValue(texto)
                dialogo._aceptar(None)
            except Exception as error:
                errores.append(error)
                dialogo.EndModal(wx.ID_CANCEL)

        wx.CallAfter(actuar)
        timers.append(wx.CallLater(4000, lambda: dialogo.EndModal(wx.ID_CANCEL) if dialogo and dialogo.IsModal() else None))
        return dialogo

    monkeypatch.setattr(gui, 'DialogoCalculo', crear)
    try:
        assert modal(padre, lambda: gui.iniciar_calculo_guiado(padre)) == (wx.ID_CANCEL if cancelar else wx.ID_OK)
        assert not errores
        assert len(formularios) == 2
        assert formularios[1] == (clave, valores)
        assert selecciones == [True]
        assert len(mensajes) == 1 and mensajes[0][1]
        assert padre.input_text.GetValue() == 'editor libre intacto'
        assert len(padre.envios) == (1 if cancelar else 2)
        if cancelar:
            assert padre.resultados == []
        else:
            resultado, = padre.resultados
            assert not resultado.es_error
            if esperado is not None:
                assert str(resultado.valor) == esperado
            assert padre.focos == [(padre.output_text, 0)]
    finally:
        for timer in timers:
            timer.Stop()
        if padre._calculo_actual is not None:
            padre._calculo_actual = None
            proceso.cancelar()
        padre._cerrar_progreso()
        padre.Destroy()
