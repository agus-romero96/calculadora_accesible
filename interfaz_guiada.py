"""Formularios nativos; solo recogen datos, el cálculo pertenece al proceso existente."""
from dataclasses import dataclass

import wx

from i18n import N_, tr
from puente import OPERACION, Operacion
from dialogos_constructores import insertar_constructor
from formularios_guiados import FORMULARIOS, OPCIONES, CampoObligatorio, construir_argumentos


PLANTILLAS = (
    (N_("Fracción"), "(1)/(2)", 1, 2),
    (N_("Raíz cuadrada"), "sqrt(1)", 5, 6),
    (N_("Potencia"), "(x)^(2)", 1, 2),
    (N_("Paréntesis"), "(x)", 1, 2),
)


def insertar_plantilla(texto, seleccion, indice):
    """Devuelve texto y selección editable, conservando el resto de la entrada."""
    _, plantilla, inicio, fin = PLANTILLAS[indice]
    a, b = seleccion
    if a != b:
        elegido = texto[a:b]
        plantilla = plantilla[:inicio] + elegido + plantilla[fin:]
        fin = inicio + len(elegido)
    return texto[:a] + plantilla + texto[b:], (a + inicio, a + fin)


@dataclass(frozen=True)
class SolicitudGuiada:
    operacion: Operacion
    argumentos: tuple
    valores: dict

    def __iter__(self):
        # Conserva el desempaquetado (operación, argumentos) del prototipo.
        yield self.operacion
        yield self.argumentos


class DialogoCalculo(wx.Dialog):
    def __init__(self, parent, clave, valores=None):
        formulario = FORMULARIOS[clave]
        super().__init__(parent, title=tr(formulario.nombre))
        self.clave = clave
        self.argumentos = None
        self.campos = {}
        self.selectores = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        ayuda = wx.StaticText(self, label=tr(formulario.ejemplo))
        ayuda.Wrap(560)
        sizer.Add(ayuda, 0, wx.ALL, 10)
        for campo in formulario.campos:
            self._campo(sizer, campo)
            if campo.clave == "expresion":
                self._herramientas(sizer)
        botones = wx.StdDialogButtonSizer()
        calcular = wx.Button(self, wx.ID_OK, label=tr("Calcular"), name=tr("Calcular"))
        cancelar = wx.Button(self, wx.ID_CANCEL, label=tr("Cancelar"), name=tr("Cancelar"))
        botones.AddButton(calcular)
        botones.AddButton(cancelar)
        botones.Realize()
        calcular.SetDefault()
        calcular.Bind(wx.EVT_BUTTON, self._aceptar)
        sizer.Add(botones, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        if valores is not None:
            for nombre, campo in self.campos.items():
                campo.SetValue(valores[nombre])
            for nombre, selector in self.selectores.items():
                selector.SetSelection(valores[nombre])
        self.campos["expresion"].SetFocus()

    @property
    def direccion(self):
        try:
            return self.selectores["direccion"]
        except KeyError:
            raise AttributeError("direccion") from None

    def _campo(self, sizer, definicion):
        etiqueta = tr(definicion.etiqueta)
        sizer.Add(wx.StaticText(self, label=etiqueta), 0, wx.LEFT, 10)
        if definicion.opciones:
            campo = wx.Choice(self, choices=[tr(opcion) for opcion in definicion.opciones], name=etiqueta)
            campo.SetSelection(definicion.inicial)
            self.selectores[definicion.clave] = campo
        else:
            campo = wx.TextCtrl(self, value=definicion.inicial, name=etiqueta)
            self.campos[definicion.clave] = campo
        sizer.Add(campo, 0, wx.EXPAND | wx.ALL, 10)

    def _herramientas(self, sizer):
        ayuda = wx.StaticText(self, label=tr("Fracción, Raíz cuadrada y Potencia abren formularios. El texto seleccionado se usa como primer dato. Paréntesis agrupa la selección."))
        ayuda.Wrap(560)
        sizer.Add(ayuda, 0, wx.ALL, 10)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        for indice, (nombre, *_) in enumerate(PLANTILLAS):
            boton = wx.Button(self, label=tr(nombre), name=tr(nombre))
            boton.Bind(wx.EVT_BUTTON, lambda e, i=indice: self._insertar(i))
            fila.Add(boton, 0, wx.RIGHT, 5)
        sizer.Add(fila, 0, wx.ALL, 10)

    def _insertar(self, indice):
        campo = self.campos["expresion"]
        if indice < 3:
            insertar_constructor(self, campo, ("fraccion", "raiz", "potencia")[indice])
            return
        texto, seleccion = insertar_plantilla(campo.GetValue(), campo.GetSelection(), indice)
        # Replace conserva la edición nativa y el historial de deshacer.
        campo.Replace(0, campo.GetLastPosition(), texto)
        campo.SetFocus()
        campo.SetSelection(*seleccion)

    def obtener_valores(self):
        """Copia literal del formulario, independiente de los argumentos normalizados."""
        datos = {clave: campo.GetValue() for clave, campo in self.campos.items()}
        datos.update({clave: selector.GetSelection() for clave, selector in self.selectores.items()})
        return datos

    def _aceptar(self, event):
        try:
            self.argumentos = construir_argumentos(self.clave, **self.obtener_valores())
        except CampoObligatorio as error:
            wx.MessageBox(str(error), tr("Datos del cálculo"), wx.OK | wx.ICON_INFORMATION, parent=self)
            self.campos[error.campo].SetFocus()
            return
        self.EndModal(wx.ID_OK)


def solicitar_calculo(parent, anterior=None):
    """Al recuperar un envío, restaura su formulario sin repetir la selección de operación."""
    if anterior is None:
        selector = wx.SingleChoiceDialog(parent, tr("Elija qué desea calcular:"),
            tr("Nuevo cálculo guiado"), [tr(nombre) + ": " + tr(descripcion) for _, nombre, descripcion in OPCIONES])
        try:
            if selector.ShowModal() != wx.ID_OK:
                return None
            clave = OPCIONES[selector.GetSelection()][0]
        finally:
            selector.Destroy()
        dialogo = DialogoCalculo(parent, clave)
    else:
        clave = anterior.operacion.clave
        dialogo = DialogoCalculo(parent, clave, anterior.valores)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return SolicitudGuiada(FORMULARIOS[clave].operacion, dialogo.argumentos, dialogo.obtener_valores())
        return None
    finally:
        dialogo.Destroy()


def iniciar_calculo_guiado(parent, anterior=None):
    """Controla la recuperación en el hilo de wx; solo Calcular inicia otro envío."""
    foco = wx.Window.FindFocus()
    try:
        solicitud = solicitar_calculo(parent, anterior)
    finally:
        (foco or parent.input_text).SetFocus()
    if solicitud is None:
        return

    def terminado(resultado):
        if resultado.es_error:
            wx.MessageBox(resultado.texto, tr("Error Matemático"), wx.OK | wx.ICON_ERROR, parent=parent)
            iniciar_calculo_guiado(parent, solicitud)
        else:
            parent.presentar_resultado(resultado)

    op, args = solicitud
    parent._ejecutar(op.metodo, args, tr(op.descripcion), al_finalizar=terminado)
