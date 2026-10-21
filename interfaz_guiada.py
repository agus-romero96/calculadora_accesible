"""Formularios nativos; solo recogen datos, el cálculo pertenece al proceso existente."""
import wx

from i18n import N_, tr
from puente import OPERACION


OPCIONES = (
    ("ecuacion", N_("Resolver ecuación"), N_("Encuentre el valor de la incógnita. Ejemplo: 2*x + 3 = 7.")),
    ("derivar", N_("Calcular derivada"), N_("Obtenga la derivada de una función. Ejemplo: x^2 + 3*x.")),
    ("limite", N_("Calcular límite"), N_("Estudie una función cerca de un valor. Ejemplo: sin(x)/x, cuando x tiende a 0.")),
)
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


class CampoObligatorio(ValueError):
    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo


def construir_argumentos(clave, expresion, variable="x", tendencia="", direccion=0):
    """Sin interpretar matemáticas en el hilo gráfico; el núcleo usa su parser habitual."""
    if clave not in {op[0] for op in OPCIONES}:
        raise ValueError(clave)
    datos = {"expresion": expresion.strip(), "variable": variable.strip(), "tendencia": tendencia.strip()}
    campos = ["expresion"]
    if clave != "ecuacion":
        campos.append("variable")
    if clave == "limite":
        campos.append("tendencia")
    for campo in campos:
        if not datos[campo]:
            raise CampoObligatorio(campo, tr("Complete este campo antes de calcular."))
    if clave == "ecuacion":
        return (datos["expresion"],)
    if clave == "derivar":
        return datos["expresion"], datos["variable"]
    if direccion not in (0, 1, 2):
        raise ValueError(direccion)
    punto = datos["tendencia"]
    if punto.endswith(("+", "-")):
        raise CampoObligatorio("tendencia", tr("Escriba solo el valor de tendencia y elija la dirección en la lista."))
    infinito = punto.lower() in {"oo", "+oo", "-oo", "inf", "+inf", "-inf", "infinito", "-infinito", "infinity", "-infinity", "∞", "-∞"}
    if infinito and direccion:
        raise CampoObligatorio("tendencia", tr("Para infinito, seleccione Bilateral; el sentido lo determina el signo del infinito."))
    return datos["expresion"], datos["variable"], punto + ("", "-", "+")[direccion]


class DialogoCalculo(wx.Dialog):
    def __init__(self, parent, clave):
        _, nombre, ejemplo = next(op for op in OPCIONES if op[0] == clave)
        super().__init__(parent, title=tr(nombre))
        self.clave = clave
        self.argumentos = None
        self.campos = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        ayuda = wx.StaticText(self, label=tr(ejemplo))
        ayuda.Wrap(560)
        sizer.Add(ayuda, 0, wx.ALL, 10)
        self._campo(sizer, "expresion", tr("Ecuación:") if clave == "ecuacion" else tr("Función:"))
        ayuda = wx.StaticText(self, label=tr("Puede escribir x, +, -, *, / y =. Las plantillas insertan un ejemplo editable; seleccione texto para envolverlo."))
        ayuda.Wrap(560)
        sizer.Add(ayuda, 0, wx.ALL, 10)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        for indice, (nombre, *_) in enumerate(PLANTILLAS):
            boton = wx.Button(self, label=tr(nombre), name=tr(nombre))
            boton.Bind(wx.EVT_BUTTON, lambda e, i=indice: self._insertar(i))
            fila.Add(boton, 0, wx.RIGHT, 5)
        sizer.Add(fila, 0, wx.ALL, 10)
        if clave != "ecuacion":
            self._campo(sizer, "variable", tr("Variable:"), "x")
        if clave == "limite":
            self._campo(sizer, "tendencia", tr("Valor de tendencia (por ejemplo: 0, 2, infinito):"))
            etiqueta = tr("Dirección:")
            sizer.Add(wx.StaticText(self, label=etiqueta), 0, wx.LEFT, 10)
            self.direccion = wx.Choice(self, choices=[tr("Bilateral"), tr("Izquierda"), tr("Derecha")], name=etiqueta)
            self.direccion.SetSelection(0)
            sizer.Add(self.direccion, 0, wx.EXPAND | wx.ALL, 10)
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
        self.campos["expresion"].SetFocus()

    def _campo(self, sizer, clave, etiqueta, valor=""):
        sizer.Add(wx.StaticText(self, label=etiqueta), 0, wx.LEFT, 10)
        campo = wx.TextCtrl(self, value=valor, name=etiqueta)
        self.campos[clave] = campo
        sizer.Add(campo, 0, wx.EXPAND | wx.ALL, 10)

    def _insertar(self, indice):
        campo = self.campos["expresion"]
        texto, seleccion = insertar_plantilla(campo.GetValue(), campo.GetSelection(), indice)
        # Replace conserva la edición nativa y el historial de deshacer.
        campo.Replace(0, campo.GetLastPosition(), texto)
        campo.SetFocus()
        campo.SetSelection(*seleccion)

    def _aceptar(self, event):
        datos = {clave: campo.GetValue() for clave, campo in self.campos.items()}
        try:
            self.argumentos = construir_argumentos(self.clave, **datos,
                direccion=self.direccion.GetSelection() if self.clave == "limite" else 0)
        except CampoObligatorio as error:
            wx.MessageBox(str(error), tr("Datos del cálculo"), wx.OK | wx.ICON_INFORMATION, parent=self)
            self.campos[error.campo].SetFocus()
            return
        self.EndModal(wx.ID_OK)


def solicitar_calculo(parent):
    """None al cancelar cualquier etapa; nunca solicita otra vez los datos recogidos."""
    selector = wx.SingleChoiceDialog(parent, tr("Elija qué desea calcular:"),
        tr("Nuevo cálculo guiado"), [tr(nombre) + ": " + tr(descripcion) for _, nombre, descripcion in OPCIONES])
    try:
        if selector.ShowModal() != wx.ID_OK:
            return None
        clave = OPCIONES[selector.GetSelection()][0]
    finally:
        selector.Destroy()
    dialogo = DialogoCalculo(parent, clave)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return OPERACION[clave], dialogo.argumentos
        return None
    finally:
        dialogo.Destroy()
