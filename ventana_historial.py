"""
Diálogo del historial de operaciones (accesible con teclado y lector de pantalla).

Lista con la operación más reciente primero. Enter = Mostrar, Supr = Eliminar,
Esc = Cerrar. Al cerrar con una acción, la ventana principal consulta
'accion' y 'elegido' para mostrar el resultado o reutilizar su entrada.
"""
import wx

from historial import Historial, describir
from i18n import tr

MOSTRAR = "mostrar"
USAR_ENTRADA = "usar_entrada"


class DialogoHistorial(wx.Dialog):
    def __init__(self, parent, historial: Historial):
        super().__init__(parent, title=tr("Historial de operaciones"), size=(700, 450),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.historial = historial
        self.accion = None
        self.elegido = None
        self._visibles = []  # ResultadoOperacion en el orden de la lista (más reciente primero)

        sizer = wx.BoxSizer(wx.VERTICAL)
        etiqueta = wx.StaticText(self, label=tr("&Operaciones (la más reciente primero):"))
        sizer.Add(etiqueta, flag=wx.LEFT | wx.TOP, border=10)
        self.lista = wx.ListBox(self, style=wx.LB_SINGLE)
        self.lista.Bind(wx.EVT_LISTBOX_DCLICK, self._on_mostrar)
        self.lista.Bind(wx.EVT_KEY_DOWN, self._on_tecla)
        sizer.Add(self.lista, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

        botones = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_mostrar = wx.Button(self, label=tr("&Mostrar"))
        self.btn_usar = wx.Button(self, label=tr("&Usar entrada"))
        self.btn_eliminar = wx.Button(self, label=tr("&Eliminar (Supr)"))
        self.btn_vaciar = wx.Button(self, label=tr("&Borrar todo"))
        btn_cerrar = wx.Button(self, wx.ID_CANCEL, label=tr("&Cerrar"))
        for boton, manejador in ((self.btn_mostrar, self._on_mostrar), (self.btn_usar, self._on_usar),
                                 (self.btn_eliminar, self._on_eliminar), (self.btn_vaciar, self._on_vaciar)):
            boton.Bind(wx.EVT_BUTTON, manejador)
            botones.Add(boton, flag=wx.RIGHT, border=5)
        botones.Add(btn_cerrar)
        sizer.Add(botones, flag=wx.ALL, border=10)

        self.SetSizer(sizer)
        self.btn_mostrar.SetDefault()  # Enter en la lista = Mostrar
        self.actualizar_lista(0)
        self.lista.SetFocus()

    # --- Lista ---

    def actualizar_lista(self, seleccion: int) -> None:
        self._visibles = list(reversed(self.historial.entradas()))
        self.lista.Set([describir(r, self.historial.numero(r)) for r in self._visibles])
        hay = bool(self._visibles)
        if hay:
            self.lista.SetSelection(min(seleccion, len(self._visibles) - 1))
        for boton in (self.btn_mostrar, self.btn_usar, self.btn_eliminar, self.btn_vaciar):
            boton.Enable(hay)

    def seleccionado(self):
        indice = self.lista.GetSelection()
        return self._visibles[indice] if indice != wx.NOT_FOUND else None

    # --- Acciones ---

    def _terminar(self, accion: str) -> None:
        elegido = self.seleccionado()
        if elegido is None:
            return
        self.accion, self.elegido = accion, elegido
        self.EndModal(wx.ID_OK)

    def _on_mostrar(self, event):
        self._terminar(MOSTRAR)

    def _on_usar(self, event):
        self._terminar(USAR_ENTRADA)

    def _on_eliminar(self, event):
        elegido = self.seleccionado()
        if elegido is None:
            return
        indice = self.lista.GetSelection()
        self.historial.eliminar(elegido)
        self.actualizar_lista(indice)
        self.lista.SetFocus()

    def _on_vaciar(self, event):
        if wx.MessageBox(tr("¿Borrar todas las operaciones del historial?"), tr("Borrar historial"),
                         wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self) != wx.YES:
            return
        self.historial.vaciar()
        self.actualizar_lista(0)
        self.lista.SetFocus()

    def _on_tecla(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self._on_eliminar(event)
        else:
            event.Skip()
