import multiprocessing
import os
import sys
import threading
import time

import wx
import wx.lib.dialogs

import actualizador
import configuracion
import exportar
import i18n
from i18n import N_, tr
from historial import Historial, ruta_historial
from proceso_calculo import ProcesoCalculo
from puente import OPERACION, REGISTRO, CoreMatematico, ResultadoOperacion
import ventana_historial
from _version import __version__


def es_instalada() -> bool:
    """True en el ejecutable compilado; False al ejecutar el código fuente (las pruebas lo sustituyen)."""
    return getattr(sys, "frozen", False)


def texto_info():
    return tr("Escriba su expresión. F1 Ayuda. Alt para menús.")


class CalculadoraAccesible(wx.Frame):
    # Si un cálculo tarda más que esto, se abre el diálogo "Calculando…" (NVDA lo anuncia)
    MS_ANTES_DE_AVISAR = 600
    # Espera tras abrir la ventana antes de buscar actualizaciones (no retrasa el arranque)
    MS_ANTES_DE_BUSCAR_ACTUALIZACIONES = 3000
    # Largo máximo de las novedades de una versión en el diálogo de actualización
    LARGO_MAXIMO_NOVEDADES = 1500

    # Menús con las operaciones del registro (Operacion.menu), en el orden de la barra
    MENUS = {"operaciones": N_("&Operaciones"), "calculo": N_("&Cálculo"), "algebra": N_("&Álgebra")}

    def __init__(self, nucleo=None):
        """nucleo: clase del núcleo matemático (por defecto CoreMatematico); las pruebas pasan otra."""
        super().__init__(parent=None, title=f"Jansen Calculator v{__version__}", size=(800, 750))

        # Los cálculos se hacen en un proceso aparte, que se puede detener al cancelar.
        # Aquí solo se usa el núcleo para detectar variables (rápido) antes de los diálogos.
        self.core = (nucleo or CoreMatematico)()
        self.proceso = ProcesoCalculo(fabrica=nucleo)
        # Último resultado mostrado (ResultadoOperacion): lo que se copia y se exporta
        self.ultimo_resultado = None
        # Operaciones guardadas (menú Historial); se conservan entre sesiones
        self.historial = Historial(ruta_historial())
        # Explicación paso a paso o solo el resultado (menú Opciones); se recuerda
        self.modo_respuesta = configuracion.leer(configuracion.MODO_RESPUESTA)
        self.buscar_al_iniciar = configuracion.leer(configuracion.BUSCAR_ACTUALIZACIONES)
        self._buscando_actualizacion = False

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
        self.Bind(wx.EVT_CLOSE, self._on_cerrar)
        self.Centre()
        self.input_text.SetFocus()

        # Al ejecutar el código fuente no se busca: se actualiza con git
        if es_instalada() and self.buscar_al_iniciar:
            wx.CallLater(self.MS_ANTES_DE_BUSCAR_ACTUALIZACIONES, self._buscar_actualizaciones, True)

    def _on_cerrar(self, event):
        # Detiene el proceso de cálculo, aunque esté a mitad de un cálculo
        self._calculo_actual = None
        self._cerrar_progreso()
        self.proceso.cerrar()
        event.Skip()

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
        idioma = wx.Locale.FindLanguageInfo(i18n.idioma_actual()).Language
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

        # Menús de operaciones, construidos a partir del registro (puente.REGISTRO)
        menus = {clave: wx.Menu() for clave in self.MENUS}
        menus["operaciones"].Append(1001, tr("Evaluar") + "\tCtrl+Enter")
        for op in REGISTRO:
            if op.menu is None:
                continue
            menu = menus[op.menu]
            if op.separador_antes:
                menu.AppendSeparator()
            if op.variantes:
                # Submenú: una opción por variante (p. ej. los métodos clásicos de un sistema 2x2)
                submenu = wx.Menu()
                for variante, nombre in op.variantes.items():
                    item = submenu.Append(wx.ID_ANY, tr(nombre))
                    self.Bind(wx.EVT_MENU, lambda e, c=op.clave, v=variante: self.on_operacion(c, v), item)
                menu.AppendSubMenu(submenu, tr(op.etiqueta))
            else:
                self._item(menu, op.etiqueta, op.atajo, lambda e, c=op.clave: self.on_operacion(c))
        menus["operaciones"].AppendSeparator()
        self.Bind(wx.EVT_MENU, lambda e: self.Close(),
                  menus["operaciones"].Append(wx.ID_EXIT, tr("Salir") + "\tAlt+F4"))

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

        # Opciones (se recuerdan entre sesiones)
        m_opciones = wx.Menu()
        item = m_opciones.AppendCheckItem(wx.ID_ANY, tr("Mostrar el &paso a paso") + "	Ctrl+Shift+P")
        item.Check(self.modo_respuesta == configuracion.MODO_PASOS)
        self.Bind(wx.EVT_MENU, self.on_modo_respuesta, item)
        item = m_opciones.AppendCheckItem(wx.ID_ANY, tr("Buscar actualizaciones al &iniciar"))
        item.Check(self.buscar_al_iniciar)
        self.Bind(wx.EVT_MENU, self.on_buscar_al_iniciar, item)

        m_help = wx.Menu()
        self._item(m_help, N_("Ayuda"), "F1", self.mostrar_ayuda)
        self._item(m_help, N_("Buscar &actualizaciones..."), None, lambda e: self._buscar_actualizaciones(False))

        for clave, titulo in self.MENUS.items():
            menubar.Append(menus[clave], tr(titulo))
        menubar.Append(m_res, tr("Res&ultado"))
        menubar.Append(m_hist, tr("&Historial"))
        menubar.Append(m_opciones, tr("O&pciones"))
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
            self._mostrar_texto(self._texto_resultado(res))

    def _texto_resultado(self, res: ResultadoOperacion) -> str:
        """El resultado como se muestra: con la explicación paso a paso o solo el resultado."""
        if self.modo_respuesta == configuracion.MODO_RESULTADO:
            return exportar.resumen(res)
        return res.texto

    def on_modo_respuesta(self, event):
        """Alterna entre la explicación paso a paso y solo el resultado (Ctrl+Shift+P)."""
        pasos = self.modo_respuesta != configuracion.MODO_PASOS
        self.modo_respuesta = configuracion.MODO_PASOS if pasos else configuracion.MODO_RESULTADO
        configuracion.guardar(configuracion.MODO_RESPUESTA, self.modo_respuesta)
        self.crear_menus()  # la casilla del menú refleja el modo también si se cambió con el atajo
        if self.ultimo_resultado is not None:
            # El resultado actual se vuelve a mostrar en el nuevo modo: el lector de pantalla
            # lo lee, y así se puede ver el paso a paso de un resultado sin recalcularlo
            self._mostrar_texto(self._texto_resultado(self.ultimo_resultado))
        else:
            wx.MessageBox(tr("Los resultados se mostrarán con la explicación paso a paso.") if pasos
                          else tr("Se mostrará solo el resultado, sin el paso a paso."),
                          tr("Opciones"), wx.OK | wx.ICON_INFORMATION)
            self.input_text.SetFocus()

    def _mostrar_texto(self, texto):
        self.output_text.SetValue(texto)
        self.output_text.SetInsertionPoint(0)
        self.output_text.SetFocus()

    # --- CÁLCULO EN SEGUNDO PLANO ---
    # SymPy puede tardar segundos (o no terminar) en simplify/limit/integrate.
    # Si se ejecutara en el hilo de la interfaz, la ventana se congelaría sin que
    # el lector de pantalla anuncie nada. Por eso: los diálogos de datos se muestran
    # aquí (hilo de UI), y el cálculo va al proceso de cálculo (proceso_calculo.py),
    # esperado desde un hilo aparte. Al cancelar se detiene ese proceso.

    def _ejecutar(self, metodo, args, descripcion):
        """
        Ejecuta core.metodo(*args) (que devuelve un ResultadoOperacion) en el proceso de
        cálculo. Si tarda más de MS_ANTES_DE_AVISAR, muestra un diálogo "Calculando…" con
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
                resultado = self.proceso.calcular(metodo, *args)
                if resultado is None:
                    return  # cancelado: el proceso ya se detuvo
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
        # Se detiene el proceso de cálculo (y se arranca otro para el siguiente cálculo).
        # El token deja de coincidir, por si el resultado llegó justo antes.
        self._calculo_actual = None
        self.proceso.cancelar()
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

    def _resolver_ambiguedad_variable(self, txt, op):
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
                   variables=", ".join(vars_detectadas), operacion=tr(op.verbo)),
                tr("Selección de Variable"),
                vars_detectadas
            )
            try:
                return dlg.GetStringSelection() if dlg.ShowModal() == wx.ID_OK else None
            finally:
                dlg.Destroy()

        # Caso 2: Integrar constante (0 variables) -> Preguntar
        if len(vars_detectadas) == 0 and op.variable_obligatoria:
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
            clave = "gauss"
        elif any(signo in txt for signo in "=<>≤≥"):
            clave = "ecuacion"  # una sola línea con =, < o >: ecuación o inecuación
        else:
            clave = "evaluar"
        self._calcular(OPERACION[clave], txt)

    def on_operacion(self, clave, variante=None):
        """Opción de menú de una operación del registro (variante: opción de su submenú)."""
        txt = self.obtener_texto()
        if txt:
            self._calcular(OPERACION[clave], txt, variante)

    def _calcular(self, op, txt, variante=None):
        """Pide los datos de la operación (según op.datos) y la ejecuta en el proceso de cálculo."""
        datos = self.PEDIR_DATOS[op.datos](self, txt, op)
        if datos is None:
            return  # el usuario canceló un diálogo (o el dato no era válido)
        args, valores = datos
        if variante is not None:
            args = args + (variante,)
            valores = {**valores, "metodo": tr(op.variantes[variante]).lower()}
        self._ejecutar(op.metodo, args, tr(op.descripcion, **valores))

    # --- DATOS QUE PIDE CADA OPERACIÓN ---
    # Cada función recibe el texto de entrada y la operación, y devuelve (argumentos del
    # método, valores de los {marcadores} de la descripción), o None si el usuario canceló.

    def _datos_expresion(self, txt, op):
        return (txt,), {}

    def _datos_lineas(self, txt, op):
        return (txt.split('\n'),), {}

    def _datos_expresion_variable(self, txt, op):
        # Pregunta preventiva si hay varias variables (o ninguna, si la variable es obligatoria)
        var_elegida = self._resolver_ambiguedad_variable(txt, op)

        # Si había que elegir y no eligió ninguna, el usuario canceló.
        # Si no había ambigüedad, var_elegida es None y el motor infiere la variable.
        vars_detectadas = self.core.DetectarVariables(txt)
        hay_que_elegir = len(vars_detectadas) > 1 or (not vars_detectadas and op.variable_obligatoria)
        if hay_que_elegir and var_elegida is None:
            return None
        return (txt, var_elegida), {}

    def _datos_variable_limites(self, txt, op):
        # La variable como al integrar (se pregunta si hay varias o es una constante)
        datos = self._datos_expresion_variable(txt, op)
        if datos is None: return None
        (_, var), _ = datos

        inferior = self._pedir_texto(tr("Límite inferior (ej: 0, -1, pi, -oo):"), tr("Integral definida"))
        if inferior is None: return None
        superior = self._pedir_texto(tr("Límite superior (ej: 1, pi/2, oo):"), tr("Integral definida"))
        if superior is None: return None
        return (txt, var, inferior, superior), {}

    def _datos_variable_punto(self, txt, op):
        # La variable como al derivar (se pregunta si hay varias); después, el punto x0
        datos = self._datos_expresion_variable(txt, op)
        if datos is None: return None
        (_, var), _ = datos

        punto = self._pedir_texto(tr("Punto x0 donde se traza la tangente (ej: 1, -2, pi/4):"),
                                  tr("Recta tangente y normal"))
        if punto is None: return None
        return (txt, var, punto), {}

    def _datos_variable_orden(self, txt, op):
        # Aquí siempre preguntamos porque es avanzado
        var = self._pedir_texto(tr("Variable:"), tr("Derivada N"))
        if var is None: return None

        orden_txt = self._pedir_texto(tr("Orden (número entero mayor o igual que 1):"), tr("Derivada N"))
        if orden_txt is None: return None
        try:
            orden = int(orden_txt)
        except ValueError:
            wx.MessageBox(tr("El orden debe ser un número entero."), tr("Error"), wx.OK | wx.ICON_ERROR)
            return None
        return (txt, var, orden), {"orden": orden}

    def _datos_variable_tendencia(self, txt, op):
        var = self._pedir_texto(tr("Variable:"), tr("Límite"))
        if var is None: return None

        tendencia = self._pedir_texto(
            tr("Tendencia (ej: 0, 2, oo, -oo; para un límite lateral agregue + o -, ej: 0+):"),
            tr("Límite"))
        if tendencia is None: return None
        return (txt, var, tendencia), {}

    # Operacion.datos -> función que pide esos datos
    PEDIR_DATOS = {
        "expresion": _datos_expresion,
        "lineas": _datos_lineas,
        "expresion_variable": _datos_expresion_variable,
        "variable_limites": _datos_variable_limites,
        "variable_punto": _datos_variable_punto,
        "variable_orden": _datos_variable_orden,
        "variable_tendencia": _datos_variable_tendencia,
    }

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
            self._mostrar_texto(self._texto_resultado(elegido))
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

    # --- ACTUALIZACIONES ---
    # La consulta y la descarga (actualizador.py) van en un hilo, para no congelar la
    # ventana; los diálogos, en el hilo de la interfaz. La búsqueda automática (al abrir)
    # no dice nada si no hay versión nueva o no hay conexión; la del menú Ayuda, sí.

    def on_buscar_al_iniciar(self, event):
        self.buscar_al_iniciar = not self.buscar_al_iniciar
        configuracion.guardar(configuracion.BUSCAR_ACTUALIZACIONES, self.buscar_al_iniciar)
        self.crear_menus()

    def _buscar_actualizaciones(self, automatica):
        if self._buscando_actualizacion:
            return
        self._buscando_actualizacion = True
        if not automatica:
            self.lbl_info.SetValue(tr("Buscando actualizaciones..."))

        def trabajo():
            try:
                encontrada, error = actualizador.buscar_actualizacion(), None
            except Exception as e:
                encontrada, error = None, e
            wx.CallAfter(self._resultado_busqueda, automatica, encontrada, error)

        threading.Thread(target=trabajo, daemon=True).start()

    def _resultado_busqueda(self, automatica, act, error):
        if not self:
            return  # la ventana se cerró mientras se consultaba
        self._buscando_actualizacion = False
        if not automatica:
            self.lbl_info.SetValue(texto_info())
            if error is not None:
                wx.MessageBox(tr("No se pudo comprobar si hay una versión nueva.\n{error}", error=error),
                              tr("Buscar actualizaciones"), wx.OK | wx.ICON_WARNING)
            elif act is None:
                wx.MessageBox(tr("Ya tiene la última versión ({version}).", version=__version__),
                              tr("Buscar actualizaciones"), wx.OK | wx.ICON_INFORMATION)
            if act is None:
                self.input_text.SetFocus()
                return
        elif act is None or act.version == configuracion.leer(configuracion.VERSION_OMITIDA):
            return
        elif self._calculo_actual is not None:
            # No interrumpir un cálculo: se ofrece cuando termine
            wx.CallLater(2000, self._resultado_busqueda, automatica, act, None)
            return
        self._ofrecer_actualizacion(act)

    def _ofrecer_actualizacion(self, act):
        mensaje = tr("Hay una versión nueva de la calculadora: {nueva}. Usted tiene la {actual}.",
                     nueva=act.version, actual=__version__)
        if act.notas:
            notas = act.notas
            if len(notas) > self.LARGO_MAXIMO_NOVEDADES:
                notas = notas[:self.LARGO_MAXIMO_NOVEDADES] + "…"
            mensaje += "\n\n" + tr("Novedades:") + "\n" + notas
        mensaje += "\n\n" + tr("¿Desea descargarla e instalarla ahora?")
        dlg = wx.MessageDialog(self, mensaje, tr("Actualización disponible"),
                               wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION)
        # Escape equivale a Cancelar: por eso "Más tarde" es Cancelar y no "Omitir"
        dlg.SetYesNoCancelLabels(tr("&Actualizar ahora"), tr("&Omitir esta versión"), tr("&Más tarde"))
        try:
            respuesta = dlg.ShowModal()
        finally:
            dlg.Destroy()

        if respuesta == wx.ID_NO:
            # No se volverá a ofrecer al abrir la calculadora (sí al buscar desde el menú)
            configuracion.guardar(configuracion.VERSION_OMITIDA, act.version)
        elif respuesta == wx.ID_YES:
            if es_instalada() and act.url_instalador:
                self._descargar_e_instalar(act)
                return
            # Código fuente, o una versión publicada sin instalador: se abre su página
            wx.LaunchDefaultBrowser(act.pagina)
        self.input_text.SetFocus()

    def _descargar_e_instalar(self, act):
        """Descarga el instalador con un diálogo de progreso (con Cancelar) y lo ejecuta."""
        estado = {"descargado": 0, "total": act.tamano, "cancelar": False, "fin": None}

        def progreso(descargado, total):
            estado["descargado"], estado["total"] = descargado, total
            return not estado["cancelar"]

        def trabajo():
            try:
                estado["fin"] = ("descargado", actualizador.descargar(act, progreso=progreso))
            except actualizador.DescargaCancelada:
                estado["fin"] = ("cancelado", None)
            except Exception as e:
                estado["fin"] = ("error", e)

        # El mensaje inicial es largo para que el diálogo tenga el ancho de los siguientes
        dlg = wx.ProgressDialog(
            tr("Descargando actualización"),
            tr("Descargando la versión {version}: {mb} de {total_mb} MB.",
               version=act.version, mb="0.0", total_mb=f"{act.tamano / 1048576:.1f}"),
            maximum=100, parent=self,
            style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
        def actualizar_dialogo():
            # Cada 200 ms mientras dura la descarga (wx.CallLater: sin temporizador ligado a la ventana)
            if estado["fin"] is None:
                total = estado["total"]
                porcentaje = min(99, estado["descargado"] * 100 // total) if total else 0
                continuar, _ = dlg.Update(porcentaje, tr("Descargando la versión {version}: {mb} de {total_mb} MB.",
                                                         version=act.version,
                                                         mb=f"{estado['descargado'] / 1048576:.1f}",
                                                         total_mb=f"{total / 1048576:.1f}"))
                if not continuar:
                    estado["cancelar"] = True
                wx.CallLater(200, actualizar_dialogo)
                return
            dlg.Destroy()
            # Fuera de este callback, porque puede acabar cerrando la ventana
            wx.CallAfter(self._descarga_terminada, act, *estado["fin"])

        threading.Thread(target=trabajo, daemon=True).start()
        wx.CallLater(200, actualizar_dialogo)

    def _descarga_terminada(self, act, resultado, valor):
        if resultado == "cancelado":
            self.input_text.SetFocus()
            return
        if resultado == "error":
            wx.MessageBox(tr("No se pudo descargar la actualización.\n{error}", error=valor),
                          tr("Actualización"), wx.OK | wx.ICON_ERROR)
            self.input_text.SetFocus()
            return
        wx.MessageBox(tr("Descarga completa. La calculadora se cerrará para instalar la versión {version} "
                         "y se abrirá de nuevo al terminar.\nWindows le pedirá permiso para instalarla.",
                         version=act.version),
                      tr("Actualización"), wx.OK | wx.ICON_INFORMATION)
        try:
            actualizador.instalar(valor)
        except actualizador.ErrorActualizacion as e:
            # Por ejemplo, si se rechazó el permiso de administrador: la calculadora sigue abierta
            wx.MessageBox(tr("No se instaló la actualización.\n{error}", error=e),
                          tr("Actualización"), wx.OK | wx.ICON_WARNING)
            self.input_text.SetFocus()
            return
        self.Close()  # el instalador necesita que la calculadora esté cerrada

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
    # En el ejecutable compilado, el proceso de cálculo es otra copia del .exe:
    # freeze_support() lo reconoce y ejecuta solo el cálculo (sin abrir la ventana)
    multiprocessing.freeze_support()

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
