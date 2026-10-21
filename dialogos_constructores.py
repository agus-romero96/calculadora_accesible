"""Diálogo reutilizable y adaptación de los constructores a un wx.TextCtrl."""
import threading

import wx

from constructores_matematicos import CONSTRUCTORES, ErrorCampoConstructor, construir_expresion
from i18n import tr


class DialogoConstructor(wx.Dialog):
    def __init__(self, parent, tipo, inicial=""):
        constructor = CONSTRUCTORES[tipo]
        super().__init__(parent, title=tr(constructor.titulo))
        self.tipo = tipo
        self.expresion = None
        self.campos = {}
        self._token = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        for indice, campo in enumerate(constructor.campos):
            etiqueta = tr(campo.etiqueta)
            # En MSW la etiqueta nativa inmediatamente anterior identifica el campo.
            sizer.Add(wx.StaticText(self, label=etiqueta), 0, wx.LEFT | wx.TOP, 10)
            control = wx.TextCtrl(self, value=inicial if indice == 0 else campo.sugerencia,
                                  name=etiqueta, size=(360, -1))
            self.campos[campo.clave] = control
            from herramientas_matematicas import instalar_menu
            instalar_menu(self, control)
            sizer.Add(control, 0, wx.EXPAND | wx.ALL, 10)
        botones = wx.StdDialogButtonSizer()
        self.aceptar = wx.Button(self, wx.ID_OK, label=tr("Aceptar"), name=tr("Aceptar"))
        cancelar = wx.Button(self, wx.ID_CANCEL, label=tr("Cancelar"), name=tr("Cancelar"))
        botones.AddButton(self.aceptar)
        botones.AddButton(cancelar)
        botones.Realize()
        self.aceptar.SetDefault()
        self.SetEscapeId(wx.ID_CANCEL)
        self.aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        cancelar.Bind(wx.EVT_BUTTON, self._cancelar)
        self.Bind(wx.EVT_CLOSE, self._cancelar)
        sizer.Add(botones, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        next(iter(self.campos.values())).SetFocus()

    def _aceptar(self, event):
        if self._token is not None:
            return
        valores = {clave: campo.GetValue() for clave, campo in self.campos.items()}
        token = self._token = object()
        self._habilitar_edicion(False)

        def validar():
            try:
                expresion = self._construir(valores)
                error = None
            except Exception as fallo:
                expresion, error = None, fallo
            # El parser y la comprobación simbólica no se ejecutan en el hilo de wx.
            wx.CallAfter(self._validado, token, expresion, error)

        threading.Thread(target=validar, daemon=True).start()

    def _construir(self, valores):
        return construir_expresion(self.tipo, valores)

    def _habilitar_edicion(self, habilitar):
        self.aceptar.Enable(habilitar)
        for campo in self.campos.values():
            campo.Enable(habilitar)

    def _validado(self, token, expresion, error):
        if not self or self._token is not token:
            return  # Se canceló o destruyó el diálogo mientras se validaba.
        self._token = None
        if error is not None:
            self._habilitar_edicion(True)
            wx.MessageBox(str(error), tr("Revise los datos de la expresión"),
                          wx.OK | wx.ICON_INFORMATION, parent=self)
            clave = error.campo if isinstance(error, ErrorCampoConstructor) else next(iter(self.campos))
            self.campos[clave].SetFocus()
            return
        self.expresion = expresion
        self.EndModal(wx.ID_OK)

    def _cancelar(self, event):
        self._token = None
        self.EndModal(wx.ID_CANCEL)


def solicitar_expresion(parent, tipo, inicial=""):
    if tipo == "catalogo":
        from herramientas_matematicas import solicitar_catalogo
        return solicitar_catalogo(parent, inicial)
    if tipo.startswith("constante:"):
        from herramientas_matematicas import CONSTANTES
        return next(v for v, _ in CONSTANTES if v == tipo.split(":", 1)[1])
    if tipo.startswith("funcion:"):
        from herramientas_matematicas import DialogoFuncion
        dialogo = DialogoFuncion(parent, tipo.split(":", 1)[1], inicial)
    else:
        dialogo = DialogoConstructor(parent, tipo, inicial)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.expresion
        return None
    finally:
        dialogo.Destroy()


def insertar_constructor(parent, campo, tipo):
    """Guarda el rango nativo antes de abrir el modal y reemplaza solo ese rango.

    Se restaura primero el foco y después el cursor: en MSW recibir el foco
    por primera vez puede seleccionar automáticamente todo el contenido.
    """
    inicio, fin = campo.GetSelection()
    cursor = campo.GetInsertionPoint()
    if inicio == fin:
        inicio = fin = cursor
    seleccionado = campo.GetRange(inicio, fin)
    longitud_original = campo.GetLastPosition()
    posicion_final = None
    try:
        expresion = solicitar_expresion(parent, tipo, seleccionado)
        if expresion is not None:
            campo.Replace(inicio, fin, expresion)
            # Usa posiciones nativas, también cuando el texto contiene Unicode.
            insertados = campo.GetLastPosition() - (longitud_original - (fin - inicio))
            posicion_final = inicio + insertados
    finally:
        campo.SetFocus()
        if posicion_final is not None:
            campo.SetInsertionPoint(posicion_final)
        elif inicio == fin:
            campo.SetInsertionPoint(cursor)
        elif campo.GetSelection() != (inicio, fin):
            # Si el foco no cambió la selección, se deja intacta su orientación.
            campo.SetSelection(inicio, fin)
