import os
import sys
import threading
import time

import wx
import wx.lib.dialogs

import exportar
import i18n
from i18n import N_, tr
from algebra.classic_systems import MotorSistemasClasicos
from historial import Historial, ruta_historial
from puente import CoreMatematico, ResultadoOperacion
import ventana_historial
from _version import __version__


def texto_info():
    return tr("Escriba su expresión. F1 Ayuda. Alt para menús.")


class CalculadoraAccesible(wx.Frame):
    # Si un cálculo tarda más que esto, se abre el diálogo "Calculando…" (NVDA lo anuncia)
    MS_ANTES_DE_AVISAR = 600

    # Verbo que se muestra al preguntar la variable (la clave es el código de la operación)
    VERBOS = {"derivar": N_("derivar"), "integrar": N_("integrar")}

    def __init__(self):
        super().__init__(parent=None, title=f"Jansen Calculator v{__version__}", size=(800, 750))

        self.core = CoreMatematico()
        # Último resultado mostrado (ResultadoOperacion): lo que se copia y se exporta
        self.ultimo_resultado = None
        # Operaciones guardadas (menú Historial); se conservan entre sesiones
        self.historial = Historial(ruta_historial())

        # Estado del cálculo en segundo plano. _calculo_actual es un "token" único por
        # cálculo: si el usuario cancela, se pone a None y el resultado tardío se descarta.
        self._calculo_actual = None
        self._dlg_progreso = None
        self._timer_aviso = None
        self._timer_pulso = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_pulso, self._timer_pulso)

        self._wx_locale = None
        self._aplicar_locale_wx()

        self.init_ui()
        self.crear_menus()
        self.crear_atajos()
        self.Centre()
        self.input_text.SetFocus()

    # --- IDIOMA ---

    def _aplicar_locale_wx(self):
        """
        Traduce los textos propios de wxWidgets (botones Aceptar/Cancelar de los diálogos).
        El catálogo de wx está en wx/locale; en el ejecutable compilado se copia a wx_locale/.
        """
        if getattr(sys, "frozen", False):
            carpeta = os.path.join(i18n.carpeta_recursos(), "wx_locale")
        else:
            carpeta = os.path.join(os.path.dirname(wx.__file__), "locale")
        wx.Locale.AddCatalogLookupPathPrefix(carpeta)
        idioma = wx.LANGUAGE_SPANISH if i18n.idioma_actual() == "es" else wx.LANGUAGE_ENGLISH
        self._wx_locale = None  # libera el anterior antes de crear el nuevo
        self._wx_locale = wx.Locale(idioma)

    def on_idioma(self, codigo):
        if codigo == i18n.idioma_actual():
            return
        i18n.establecer_idioma(codigo)
        i18n.guardar_idioma(codigo)
        self._aplicar_locale_wx()
        self.crear_menus()
        self.actualizar_textos()
        wx.MessageBox(tr("Idioma cambiado a {idioma}. Los nuevos resultados se mostrarán en este idioma.",
                         idioma=i18n.IDIOMAS[codigo]),
                      tr("Idioma"), wx.OK | wx.ICON_INFORMATION)
        self.input_text.SetFocus()

    # --- INTERFAZ ---

    def init_ui(self):
        panel = wx.Panel(self)
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # Info
        self.lbl_info = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.BORDER_NONE)
        self.lbl_info.SetBackgroundColour(panel.GetBackgroundColour())
        sizer_main.Add(self.lbl_info, flag=wx.EXPAND | wx.ALL, border=10)

        # Input
        self.lbl_input = wx.StaticText(panel)
        sizer_main.Add(self.lbl_input, flag=wx.LEFT, border=10)
        self.input_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self.input_text.SetFont(wx.Font(14, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer_main.Add(self.input_text, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # Botones
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_calc = wx.Button(panel)
        self.btn_calc.Bind(wx.EVT_BUTTON, self.on_evaluar_inteligente)
        self.btn_clear = wx.Button(panel)
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_limpiar)
        btn_sizer.Add(self.btn_calc, 1, wx.RIGHT | wx.EXPAND, 5)
        btn_sizer.Add(self.btn_clear, 0, wx.EXPAND)
        sizer_main.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=10)

        # Output
        self.lbl_res = wx.StaticText(panel)
        sizer_main.Add(self.lbl_res, flag=wx.LEFT, border=10)
        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.output_text.SetFont(wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.output_text.SetBackgroundColour(wx.Colour(250, 250, 250))
        sizer_main.Add(self.output_text, proportion=2, flag=wx.EXPAND | wx.ALL, border=10)

        self.panel = panel
        panel.SetSizer(sizer_main)
        self.actualizar_textos()

    def actualizar_textos(self):
        """Etiquetas de la ventana en el idioma actual (también al cambiar de idioma)."""
        self.lbl_info.SetValue(texto_info())
        self.lbl_input.SetLabel(tr("&Entrada Matemática:"))
        self.btn_calc.SetLabel(tr("&Calcular (Ctrl+Enter)"))
        self.btn_clear.SetLabel(tr("&Borrar (Ctrl+Retroceso)"))
        self.lbl_res.SetLabel(tr("&Resultados:"))
        self.panel.Layout()

    def crear_atajos(self):
        entries = [
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RETURN, 1001),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_BACK, 1002)
        ]
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))
        self.Bind(wx.EVT_MENU, self.on_evaluar_inteligente, id=1001)
        self.Bind(wx.EVT_MENU, self.on_limpiar, id=1002)

    def _item(self, menu, texto, atajo, manejador):
        """Añade una opción de menú. El atajo va aparte: wx lo reconoce en inglés (Ctrl+Shift)."""
        etiqueta = tr(texto) + (f"\t{atajo}" if atajo else "")
        self.Bind(wx.EVT_MENU, manejador, menu.Append(wx.ID_ANY, etiqueta))

    def crear_menus(self):
        """Construye (o reconstruye, al cambiar de idioma) la barra de menús."""
        menubar = wx.MenuBar()

        # Operaciones
        m_ops = wx.Menu()
        m_ops.Append(1001, tr("Evaluar") + "\tCtrl+Enter")
        self._item(m_ops, N_("Simplificar"), "Ctrl+S", self.on_simplificar)
        self._item(m_ops, N_("Factorizar"), "Ctrl+F", self.on_factorizar)
        m_ops.AppendSeparator()
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), m_ops.Append(wx.ID_EXIT, tr("Salir") + "\tAlt+F4"))

        # Cálculo
        m_calc = wx.Menu()
        self._item(m_calc, N_("Derivar"), "Ctrl+D", self.on_derivar)
        self._item(m_calc, N_("Derivada Orden N"), "Ctrl+Shift+D", self.on_derivada_enecima)
        m_calc.AppendSeparator()
        self._item(m_calc, N_("Integrar"), "Ctrl+I", self.on_integrar)
        self._item(m_calc, N_("Límite"), "Ctrl+L", self.on_limite)

        # Álgebra
        m_alg = wx.Menu()
        self._item(m_alg, N_("Sistemas (Gauss-Jordan)"), "Ctrl+G", self.on_sistema_gauss)

        # Sistemas 2x2 por métodos clásicos (submenú)
        m_clasicos = wx.Menu()
        for metodo, nombre in MotorSistemasClasicos.NOMBRES_METODO.items():
            item = m_clasicos.Append(wx.ID_ANY, tr(nombre))
            self.Bind(wx.EVT_MENU, lambda e, m=metodo, n=nombre: self.on_sistema_clasico(m, tr(n).lower()), item)
        m_alg.AppendSubMenu(m_clasicos, tr("Sistema 2x2 por &método clásico"))

        m_alg.AppendSeparator()
        self._item(m_alg, N_("Matriz Inversa (Cofactores)"), "Ctrl+M", self.on_inversa_cofactores)

        # Resultado: copiar y exportar
        m_res = wx.Menu()
        self._item(m_res, N_("Copiar resultado"), "Ctrl+Shift+C", self.on_copiar_resultado)
        self._item(m_res, N_("Copiar explicación completa"), "Ctrl+Shift+A", self.on_copiar_explicacion)
        self._item(m_res, N_("Copiar como LaTeX"), "Ctrl+Shift+L", self.on_copiar_latex)
        self._item(m_res, N_("Copiar como MathML"), "Ctrl+Shift+M", self.on_copiar_mathml)
        m_res.AppendSeparator()
        self._item(m_res, N_("Exportar a archivo..."), "Ctrl+E", self.on_exportar)

        # Historial de la sesión
        m_hist = wx.Menu()
        self._item(m_hist, N_("Ver historial..."), "Ctrl+H", self.on_ver_historial)
        self._item(m_hist, N_("Exportar historial..."), "Ctrl+Shift+E", self.on_exportar_historial)
        m_hist.AppendSeparator()
        self._item(m_hist, N_("Borrar historial"), None, self.on_borrar_historial)

        # Idioma (el nombre del menú está en los dos idiomas para encontrarlo siempre)
        m_idioma = wx.Menu()
        for codigo, nombre in i18n.IDIOMAS.items():
            item = m_idioma.AppendRadioItem(wx.ID_ANY, nombre)
            item.Check(codigo == i18n.idioma_actual())
            self.Bind(wx.EVT_MENU, lambda e, c=codigo: self.on_idioma(c), item)

        m_help = wx.Menu()
        self._item(m_help, N_("Ayuda"), "F1", self.mostrar_ayuda)

        menubar.Append(m_ops, tr("&Operaciones"))
        menubar.Append(m_calc, tr("&Cálculo"))
        menubar.Append(m_alg, tr("&Álgebra"))
        menubar.Append(m_res, tr("Res&ultado"))
        menubar.Append(m_hist, tr("&Historial"))
        menubar.Append(m_idioma, tr("&Idioma / Language"))
        menubar.Append(m_help, tr("A&yuda"))
        self.SetMenuBar(menubar)

    # --- LÓGICA DE UX MEJORADA ---

    def _avisar_ocupado(self):
        wx.MessageBox(tr("Ya hay un cálculo en curso. Espere a que termine o cancélelo."),
                      tr("Calculadora ocupada"), wx.OK | wx.ICON_INFORMATION)

    def obtener_texto(self):
        # Comprobar antes de mostrar diálogos de variable/orden para no pedir datos en vano
        if self._calculo_actual is not None:
            self._avisar_ocupado()
            return None
        txt = self.input_text.GetValue().strip()
        if not txt:
            # ERROR EN DIÁLOGO (User Request)
            wx.MessageBox(tr("El campo de entrada está vacío.\nPor favor escriba una expresión matemática."),
                          tr("Atención"), wx.OK | wx.ICON_WARNING)
            self.input_text.SetFocus()
            return None
        return txt

    def presentar_resultado(self, res: ResultadoOperacion):
        # Si el motor reportó un fallo, mostramos DIÁLOGO
        if res.es_error:
            wx.MessageBox(res.texto, tr("Error Matemático"), wx.OK | wx.ICON_ERROR)
            self.input_text.SetFocus()  # Volvemos al input para que corrija
        else:
            self.ultimo_resultado = res
            self.historial.agregar(res)
            self._mostrar_texto(res.texto)

    def _mostrar_texto(self, texto):
        self.output_text.SetValue(texto)
        self.output_text.SetInsertionPoint(0)
        self.output_text.SetFocus()

    # --- CÁLCULO EN SEGUNDO PLANO ---
    # SymPy puede tardar segundos (o no terminar) en simplify/limit/integrate.
    # Si se ejecutara en el hilo de la interfaz, la ventana se congelaría sin que
    # el lector de pantalla anuncie nada. Por eso: los diálogos de datos se muestran
    # aquí (hilo de UI), y solo el cálculo va a un hilo aparte.

    def _ejecutar(self, tarea, descripcion):
        """
        Ejecuta tarea() (que devuelve un ResultadoOperacion) en un hilo aparte.
        Si tarda más de MS_ANTES_DE_AVISAR, muestra un diálogo "Calculando…" con
        botón Cancelar. El resultado se presenta en el hilo de la interfaz.
        """
        if self._calculo_actual is not None:
            self._avisar_ocupado()
            return

        token = object()
        self._calculo_actual = token
        self.lbl_info.SetValue(tr("Calculando: {descripcion}...", descripcion=descripcion))
        entrada = self.input_text.GetValue().strip()

        def trabajo():
            try:
                resultado = tarea()
            except Exception as e:
                resultado = ResultadoOperacion(operacion="", entrada=entrada,
                                               texto=tr("Error inesperado: {error}", error=e), es_error=True)
            wx.CallAfter(self._finalizar_calculo, token, resultado)

        threading.Thread(target=trabajo, daemon=True).start()
        self._timer_aviso = wx.CallLater(self.MS_ANTES_DE_AVISAR, self._mostrar_progreso, token, descripcion)

    def _mostrar_progreso(self, token, descripcion):
        if token is not self._calculo_actual:
            return  # ya terminó (o se canceló) antes de hacer falta el aviso
        self._dlg_progreso = wx.ProgressDialog(
            tr("Calculando"),
            tr("Calculando {descripcion}. Puede tardar unos segundos.\n"
               "Pulse Cancelar para abandonar este cálculo.", descripcion=descripcion),
            parent=self,
            style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME,
        )
        self._timer_pulso.Start(200)

    def _on_pulso(self, event):
        if self._dlg_progreso is None:
            self._timer_pulso.Stop()
            return
        continuar, _ = self._dlg_progreso.Pulse()
        if not continuar:
            self._cancelar_calculo()

    def _cerrar_progreso(self):
        if self._timer_aviso is not None:
            self._timer_aviso.Stop()
            self._timer_aviso = None
        self._timer_pulso.Stop()
        if self._dlg_progreso is not None:
            self._dlg_progreso.Destroy()
            self._dlg_progreso = None

    def _cancelar_calculo(self):
        # Python no permite detener un hilo: el cálculo sigue en segundo plano,
        # pero su resultado se descartará (el token deja de coincidir).
        self._calculo_actual = None
        self._cerrar_progreso()
        self.lbl_info.SetValue(tr("Cálculo cancelado.") + " " + texto_info())
        self.input_text.SetFocus()

    def _finalizar_calculo(self, token, resultado):
        if token is not self._calculo_actual:
            return  # cálculo cancelado: se ignora el resultado tardío
        self._calculo_actual = None
        self._cerrar_progreso()
        self.lbl_info.SetValue(texto_info())
        self.presentar_resultado(resultado)

    def _resolver_ambiguedad_variable(self, txt, operacion):
        """
        Analiza variables y pregunta al usuario si hay más de una.
        Retorna: La variable elegida (str) o None si el usuario canceló.
        """
        vars_detectadas = self.core.DetectarVariables(txt)

        # Caso 1: Multivariable (x, y) -> Preguntar
        if len(vars_detectadas) > 1:
            dlg = wx.SingleChoiceDialog(
                self,
                tr("La expresión tiene varias variables ({variables}).\n¿Respecto a cuál desea {operacion}?",
                   variables=", ".join(vars_detectadas), operacion=tr(self.VERBOS[operacion])),
                tr("Selección de Variable"),
                vars_detectadas
            )
            try:
                return dlg.GetStringSelection() if dlg.ShowModal() == wx.ID_OK else None
            finally:
                dlg.Destroy()

        # Caso 2: Integrar constante (0 variables) -> Preguntar
        if len(vars_detectadas) == 0 and operacion == "integrar":
            return self._pedir_texto(
                tr("Está integrando una constante.\n¿Cuál es la variable de integración? (ej: x, t)"),
                tr("Variable Requerida"))

        # Caso 3: Una sola variable o constante en derivada -> Dejar pasar (el motor manejará defaults)
        return None

    # --- HANDLERS ---
    # Patrón: 1) pedir datos con diálogos (hilo de UI)  2) _ejecutar(cálculo)

    def _pedir_texto(self, mensaje, titulo, valor=""):
        """Diálogo de texto. Devuelve el texto (sin espacios extremos) o None si se cancela."""
        dlg = wx.TextEntryDialog(self, mensaje, titulo, valor)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            return dlg.GetValue().strip()
        finally:
            dlg.Destroy()

    def on_evaluar_inteligente(self, event):
        txt = self.obtener_texto()
        if not txt: return
        if "\n" in txt and "=" in txt:
            lineas = txt.split('\n')
            self._ejecutar(lambda: self.core.sistema_gauss(lineas), tr("el sistema por Gauss-Jordan"))
        else:
            self._ejecutar(lambda: self.core.evaluar(txt), tr("la evaluación"))

    def on_simplificar(self, event):
        txt = self.obtener_texto()
        if txt: self._ejecutar(lambda: self.core.simplificar(txt), tr("la simplificación"))

    def on_factorizar(self, event):
        txt = self.obtener_texto()
        if txt: self._ejecutar(lambda: self.core.factorizar(txt), tr("la factorización"))

    # --- CÁLCULO INTELIGENTE ---

    def on_derivar(self, event):
        txt = self.obtener_texto()
        if not txt: return

        # Pregunta preventiva si hay varias variables
        var_elegida = self._resolver_ambiguedad_variable(txt, "derivar")

        # Si había varias variables y no eligió ninguna, el usuario canceló.
        # Si no había ambigüedad, var_elegida es None y el motor infiere la variable.
        vars_detectadas = self.core.DetectarVariables(txt)
        if len(vars_detectadas) > 1 and var_elegida is None:
            return

        self._ejecutar(lambda: self.core.derivar(txt, var_elegida), tr("la derivada"))

    def on_integrar(self, event):
        txt = self.obtener_texto()
        if not txt: return

        var_elegida = self._resolver_ambiguedad_variable(txt, "integrar")

        vars_detectadas = self.core.DetectarVariables(txt)
        # Si era ambigua o constante y no eligió nada (Cancel), salimos
        if (len(vars_detectadas) > 1 or len(vars_detectadas) == 0) and var_elegida is None:
            return

        self._ejecutar(lambda: self.core.integrar(txt, var_elegida), tr("la integral"))

    def on_derivada_enecima(self, event):
        expr = self.obtener_texto()
        if not expr: return

        # Aquí siempre preguntamos porque es avanzado
        var = self._pedir_texto(tr("Variable:"), tr("Derivada N"))
        if var is None: return

        orden_txt = self._pedir_texto(tr("Orden (número entero mayor o igual que 1):"), tr("Derivada N"))
        if orden_txt is None: return
        try:
            orden = int(orden_txt)
        except ValueError:
            wx.MessageBox(tr("El orden debe ser un número entero."), tr("Error"), wx.OK | wx.ICON_ERROR)
            return

        self._ejecutar(lambda: self.core.derivada_enecima(expr, var, orden),
                       tr("la derivada de orden {orden}", orden=orden))

    def on_limite(self, event):
        expr = self.obtener_texto()
        if not expr: return

        var = self._pedir_texto(tr("Variable:"), tr("Límite"))
        if var is None: return

        tendencia = self._pedir_texto(
            tr("Tendencia (ej: 0, 2, oo, -oo; para un límite lateral agregue + o -, ej: 0+):"),
            tr("Límite"))
        if tendencia is None: return

        self._ejecutar(lambda: self.core.limite(expr, var, tendencia), tr("el límite"))

    def on_sistema_gauss(self, event):
        txt = self.obtener_texto()
        if not txt: return
        lineas = txt.split('\n')
        self._ejecutar(lambda: self.core.sistema_gauss(lineas), tr("el sistema por Gauss-Jordan"))

    def on_sistema_clasico(self, metodo, nombre):
        """Sistema 2x2 por sustitución, igualación o reducción."""
        txt = self.obtener_texto()
        if not txt: return
        lineas = txt.split('\n')
        self._ejecutar(lambda: self.core.sistema_clasico(lineas, metodo),
                       tr("el sistema por {metodo}", metodo=nombre))

    def on_inversa_cofactores(self, event):
        txt = self.obtener_texto()
        if txt: self._ejecutar(lambda: self.core.inversa(txt), tr("la matriz inversa"))

    def on_limpiar(self, event):
        self.input_text.Clear()
        self.output_text.Clear()
        self.ultimo_resultado = None
        self.input_text.SetFocus()

    # --- COPIAR Y EXPORTAR ---

    def _resultado_disponible(self):
        if self.ultimo_resultado is None:
            wx.MessageBox(tr("Todavía no hay un resultado. Haga un cálculo primero."),
                          tr("Sin resultado"), wx.OK | wx.ICON_INFORMATION)
            return None
        return self.ultimo_resultado

    @staticmethod
    def _poner_en_portapapeles(texto) -> bool:
        """
        En Windows el portapapeles puede estar ocupado un instante (el historial del
        portapapeles, el lector de pantalla u otro programa lo abren tras cada cambio),
        así que se reintenta. Flush() deja el texto disponible aunque se cierre la calculadora.
        """
        for _ in range(10):
            if wx.TheClipboard.Open():
                try:
                    copiado = wx.TheClipboard.SetData(wx.TextDataObject(texto))
                finally:
                    wx.TheClipboard.Close()
                if copiado:
                    wx.TheClipboard.Flush()
                    return True
            time.sleep(0.05)
        return False

    def _copiar(self, texto, descripcion):
        """Copia al portapapeles y lo confirma con un diálogo (el lector de pantalla lo lee)."""
        if not self._poner_en_portapapeles(texto):
            wx.MessageBox(tr("No se pudo abrir el portapapeles."), tr("Error"), wx.OK | wx.ICON_ERROR)
            return
        vista = texto if len(texto) <= 200 else texto[:200] + "…"
        wx.MessageBox(tr("Copiado: {que}.", que=descripcion) + "\n\n" + vista,
                      tr("Copiado al portapapeles"), wx.OK | wx.ICON_INFORMATION)

    def on_copiar_resultado(self, event):
        res = self._resultado_disponible()
        if res: self._copiar(exportar.resultado_corto(res), tr("el resultado"))

    def on_copiar_explicacion(self, event):
        res = self._resultado_disponible()
        if res: self._copiar(res.texto, tr("la explicación completa"))

    def on_copiar_latex(self, event):
        res = self._resultado_disponible()
        if res: self._copiar(exportar.latex(res), tr("el resultado en LaTeX"))

    def on_copiar_mathml(self, event):
        res = self._resultado_disponible()
        if res: self._copiar(exportar.mathml(res), tr("el resultado en MathML"))

    def _exportar_con_dialogo(self, titulo, nombre_archivo, guardar):
        """Pide archivo y formato (lista 'Tipo' del diálogo Guardar) y llama a guardar(formato, ruta)."""
        claves = list(exportar.FORMATOS)
        filtros = "|".join(f"{tr(nombre)} (*.{ext})|*.{ext}" for nombre, ext in exportar.FORMATOS.values())
        dlg = wx.FileDialog(self, titulo, defaultFile=f"{nombre_archivo}.html",
                            wildcard=filtros, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            formato = claves[dlg.GetFilterIndex()]
            ruta = dlg.GetPath()
        finally:
            dlg.Destroy()

        extension = "." + exportar.FORMATOS[formato][1]
        if not ruta.lower().endswith(extension):
            ruta = os.path.splitext(ruta)[0] + extension
        try:
            guardar(formato, ruta)
        except Exception as e:
            wx.MessageBox(tr("No se pudo guardar el archivo:\n{error}", error=e), tr("Error"), wx.OK | wx.ICON_ERROR)
            return
        wx.MessageBox(tr("Resultado exportado en:\n{ruta}", ruta=ruta), titulo, wx.OK | wx.ICON_INFORMATION)

    def on_exportar(self, event):
        res = self._resultado_disponible()
        if res:
            self._exportar_con_dialogo(tr("Exportar resultado"), res.operacion or "resultado",
                                       lambda formato, ruta: exportar.guardar(res, formato, ruta))

    # --- HISTORIAL ---

    def _historial_disponible(self) -> bool:
        if not len(self.historial):
            wx.MessageBox(tr("El historial está vacío. Los cálculos que haga se irán guardando aquí."),
                          tr("Historial de operaciones"), wx.OK | wx.ICON_INFORMATION)
            return False
        return True

    def on_ver_historial(self, event):
        if self._calculo_actual is not None:
            self._avisar_ocupado()
            return
        if not self._historial_disponible():
            return
        dlg = ventana_historial.DialogoHistorial(self, self.historial)
        try:
            dlg.ShowModal()
            accion, elegido = dlg.accion, dlg.elegido
        finally:
            dlg.Destroy()

        if accion == ventana_historial.MOSTRAR:
            # Vuelve a ser el resultado actual: se puede copiar y exportar
            self.ultimo_resultado = elegido
            self._mostrar_texto(elegido.texto)
        elif accion == ventana_historial.USAR_ENTRADA:
            self.input_text.SetValue(elegido.entrada)
            self.input_text.SetInsertionPointEnd()
            self.input_text.SetFocus()
        else:
            self.input_text.SetFocus()

    def on_exportar_historial(self, event):
        if not self._historial_disponible():
            return
        entradas = self.historial.entradas()
        self._exportar_con_dialogo(tr("Exportar historial"), tr("historial"),
                                   lambda formato, ruta: exportar.guardar_historial(entradas, formato, ruta))

    def on_borrar_historial(self, event):
        if not self._historial_disponible():
            return
        if wx.MessageBox(tr("¿Borrar todas las operaciones del historial?"), tr("Borrar historial"),
                         wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            self.historial.vaciar()
            wx.MessageBox(tr("Historial borrado."), tr("Borrar historial"), wx.OK | wx.ICON_INFORMATION)
        self.input_text.SetFocus()

    # --- AYUDA ---

    def mostrar_ayuda(self, event):
        # Manual pensado para NVDA, en locales/ayuda_<idioma>.txt
        ruta = os.path.join(i18n.carpeta_locales(), f"ayuda_{i18n.idioma_actual()}.txt")
        try:
            with open(ruta, encoding="utf-8") as f:
                manual = f.read()
        except OSError:
            manual = tr("No se encontró el archivo de ayuda.")
        # El texto va al cuadro grande y el foco se mueve ahí; ya no es un resultado
        # que se pueda copiar o exportar.
        self.ultimo_resultado = None
        self._mostrar_texto(manual)


if __name__ == "__main__":
    # Verificación del ejecutable compilado, sin abrir la ventana:
    #   CalculadoraAccesible.exe --autoprueba informe.txt
    if len(sys.argv) > 1 and sys.argv[1] == "--autoprueba":
        import autoprueba
        sys.exit(autoprueba.ejecutar(sys.argv[2] if len(sys.argv) > 2 else None))

    i18n.iniciar_idioma()
    app = wx.App()
    frame = CalculadoraAccesible()
    frame.Show()
    app.MainLoop()
