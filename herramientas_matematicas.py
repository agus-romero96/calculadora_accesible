"""Catálogo, diálogo de funciones y menú nativo compartidos por ambos editores."""
from dataclasses import dataclass

import wx
from i18n import N_, tr
from catalogo_matematico import CATEGORIAS, FUNCIONES, POR_NOMBRE, funciones_categoria
from constructores_matematicos import construir_funcion
from dialogos_constructores import DialogoConstructor, insertar_constructor

ESTRUCTURAS = (("fraccion", N_("Fracción")), ("potencia", N_("Potencia")),
               ("raiz", N_("Raíz cuadrada")), ("parentesis", N_("Paréntesis")))
CONSTANTES = (("pi", N_("Pi")), ("e", N_("Número e")), ("oo", N_("Infinito")))

class DialogoFuncion(DialogoConstructor):
    categorias = CATEGORIAS
    etiqueta_lista = N_("Función:")

    def _opciones_categoria(self, categoria):
        return funciones_categoria(categoria)

    def _categoria_nombre(self, nombre):
        return POR_NOMBRE[nombre].categoria

    def __init__(self, parent, nombre="", inicial=""):
        # Reutiliza botones, validación asíncrona, errores y cancelación del constructor.
        self.funcion = nombre or FUNCIONES[0].canonica
        super().__init__(parent, "parentesis", inicial)
        self.SetTitle(tr("Insertar función matemática"))
        sizer = self.GetSizer()
        bloque = wx.BoxSizer(wx.VERTICAL)
        bloque.Add(wx.StaticText(self, label=tr("Categoría:")), 0, wx.TOP, 5)
        self.categoria = wx.Choice(self, choices=[tr(v) for v in self.categorias.values()], name=tr("Categoría:"))
        bloque.Add(self.categoria, 0, wx.EXPAND | wx.BOTTOM, 5)
        bloque.Add(wx.StaticText(self, label=tr(self.etiqueta_lista)), 0)
        self.lista = wx.ListBox(self, name=tr(self.etiqueta_lista), size=(400, 130))
        bloque.Add(self.lista, 0, wx.EXPAND | wx.BOTTOM, 5)
        self.descripcion = wx.StaticText(self, name=tr("Descripción:"))
        bloque.Add(self.descripcion, 0, wx.EXPAND)
        sizer.Insert(0, bloque, 0, wx.EXPAND | wx.ALL, 10)
        self.categoria.MoveBeforeInTabOrder(self.campos['argumento'])
        self.lista.MoveAfterInTabOrder(self.categoria)
        self.categoria.SetSelection(list(self.categorias).index(self._categoria_nombre(self.funcion)))
        self._categoria(None)
        self.lista.SetSelection([f.canonica for f in self.disponibles].index(self.funcion))
        self._funcion(None)
        self.categoria.Bind(wx.EVT_CHOICE, self._categoria)
        self.lista.Bind(wx.EVT_LISTBOX, self._funcion)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.categoria.SetFocus()

    def _categoria(self, event):
        self.disponibles = self._opciones_categoria(list(self.categorias)[self.categoria.GetSelection()])
        self.lista.Set([tr(f.nombre) for f in self.disponibles])
        self.lista.SetSelection(0)
        self._funcion(None)

    def _funcion(self, event):
        funcion = self.disponibles[self.lista.GetSelection()]
        self.descripcion.SetLabel(tr(funcion.nombre) + ": " + tr(funcion.descripcion))
        self.descripcion.Wrap(400)
        self.GetSizer().Fit(self)
        self.Layout()

    def _construir(self, valores):
        return construir_funcion(self._nombre_validando, valores['argumento'])

    def _aceptar(self, event):
        if self._token is not None:
            return
        self._nombre_validando = self.disponibles[self.lista.GetSelection()].canonica
        super()._aceptar(event)

    def _habilitar_edicion(self, habilitar):
        super()._habilitar_edicion(habilitar)
        self.categoria.Enable(habilitar)
        self.lista.Enable(habilitar)


@dataclass(frozen=True)
class OpcionEstructura:
    canonica: str
    nombre: str
    descripcion: str


class DialogoCatalogo(DialogoFuncion):
    categorias = {"estructuras": N_("Estructuras matemáticas"), **CATEGORIAS}
    etiqueta_lista = N_("Función o estructura:")

    def __init__(self, parent, inicial=""):
        super().__init__(parent, "fraccion", inicial)
        self.SetTitle(tr("Insertar expresión..."))

    def _categoria_nombre(self, nombre):
        if nombre in dict(ESTRUCTURAS):
            return "estructuras"
        return super()._categoria_nombre(nombre)

    def _opciones_categoria(self, categoria):
        if categoria == "estructuras":
            return tuple(OpcionEstructura(tipo, nombre,
                N_("Al aceptar se abrirá el constructor con este argumento como primer dato."))
                for tipo, nombre in ESTRUCTURAS)
        return super()._opciones_categoria(categoria)

    def _aceptar(self, event):
        if self._token is not None:
            return
        categoria = list(self.categorias)[self.categoria.GetSelection()]
        if categoria != "estructuras":
            return super()._aceptar(event)
        from dialogos_constructores import solicitar_expresion
        campo = self.campos['argumento']
        seleccion = campo.GetSelection()
        cursor = campo.GetInsertionPoint()
        tipo = self.disponibles[self.lista.GetSelection()].canonica
        expresion = solicitar_expresion(self, tipo, campo.GetValue())
        if expresion is not None:
            self.expresion = expresion
            self.EndModal(wx.ID_OK)
        else:
            campo.SetFocus()
            if seleccion[0] == seleccion[1]:
                campo.SetInsertionPoint(cursor)
            else:
                campo.SetSelection(*seleccion)


def solicitar_catalogo(parent, inicial):
    dialogo = DialogoCatalogo(parent, inicial)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.expresion
        return None
    finally:
        dialogo.Destroy()


def crear_menu(parent, campo):
    menu = wx.Menu()
    def agregar(destino, nombre, accion, habilitado=True):
        item = destino.Append(wx.ID_ANY, tr(nombre))
        item.Enable(habilitado)
        destino.Bind(wx.EVT_MENU, lambda e: accion(), id=item.GetId())
    for nombre, accion, habilitado in (
        (N_("Deshacer"), campo.Undo, campo.CanUndo()),
        (N_("Rehacer"), campo.Redo, campo.CanRedo()),
        (N_("Cortar"), campo.Cut, campo.CanCut()),
        (N_("Copiar"), campo.Copy, campo.CanCopy()),
        (N_("Pegar"), campo.Paste, campo.CanPaste()),
        (N_("Eliminar"), lambda: campo.Remove(*campo.GetSelection()), campo.GetSelection()[0] != campo.GetSelection()[1]),
        (N_("Seleccionar todo"), campo.SelectAll, True)):
        agregar(menu, nombre, accion, habilitado)
    menu.AppendSeparator()
    def grupo(titulo, opciones):
        submenu = wx.Menu()
        for tipo, nombre in opciones:
            agregar(submenu, nombre, lambda t=tipo: insertar_constructor(parent, campo, t))
        menu.AppendSubMenu(submenu, tr(titulo))
    grupo(N_("Insertar estructuras"), ESTRUCTURAS)
    for categoria, titulo in CATEGORIAS.items():
        grupo(titulo, [("funcion:" + f.canonica, f.nombre) for f in funciones_categoria(categoria)])
    grupo(N_("Constantes y símbolos compatibles"), [("constante:" + v, n) for v, n in CONSTANTES])
    return menu


def instalar_menu(parent, campo):
    if not campo.IsEditable() or getattr(campo, '_menu_matematico', False):
        return
    campo._menu_matematico = True
    def abrir(event):
        # EVT_CONTEXT_MENU cubre Aplicaciones, Shift+F10 y ratón en Windows.
        # No cambiamos foco, selección o cursor al abrirlo, tampoco con ratón.
        menu = crear_menu(parent, campo)
        try:
            posicion = event.GetPosition()
            if posicion == wx.DefaultPosition:
                campo.PopupMenu(menu)
            else:
                campo.PopupMenu(menu, campo.ScreenToClient(posicion))
        finally:
            menu.Destroy()
    campo.Bind(wx.EVT_CONTEXT_MENU, abrir)


def boton_catalogo(parent, campo):
    boton = wx.Button(parent, label=tr("Insertar expresión..."), name=tr("Insertar expresión..."))
    boton.Bind(wx.EVT_BUTTON, lambda e: insertar_constructor(parent, campo, "catalogo"))
    return boton
