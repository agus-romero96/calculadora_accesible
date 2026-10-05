import threading

import wx
import wx.lib.dialogs
from puente import CoreMatematico
from _version import __version__

TEXTO_INFO = "Escriba su expresión. F1 Ayuda. Alt para menús."


class CalculadoraAccesible(wx.Frame):
    # Si un cálculo tarda más que esto, se abre el diálogo "Calculando…" (NVDA lo anuncia)
    MS_ANTES_DE_AVISAR = 600

    def __init__(self):
        super().__init__(parent=None, title=f"Jansen Calculator v{__version__}", size=(800, 750))

        self.core = CoreMatematico()

        # Estado del cálculo en segundo plano. _calculo_actual es un "token" único por
        # cálculo: si el usuario cancela, se pone a None y el resultado tardío se descarta.
        self._calculo_actual = None
        self._dlg_progreso = None
        self._timer_aviso = None
        self._timer_pulso = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_pulso, self._timer_pulso)

        self.init_ui()
        self.crear_menus()
        self.crear_atajos()
        self.Centre()
        self.input_text.SetFocus()

    def init_ui(self):
        panel = wx.Panel(self)
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # Info
        self.lbl_info = wx.TextCtrl(panel, value=TEXTO_INFO, style=wx.TE_READONLY | wx.BORDER_NONE)
        self.lbl_info.SetBackgroundColour(panel.GetBackgroundColour())
        sizer_main.Add(self.lbl_info, flag=wx.EXPAND | wx.ALL, border=10)

        # Input
        lbl_input = wx.StaticText(panel, label="&Entrada Matemática:")
        sizer_main.Add(lbl_input, flag=wx.LEFT, border=10)
        self.input_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self.input_text.SetFont(wx.Font(14, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer_main.Add(self.input_text, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # Botones
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_calc = wx.Button(panel, label="&Calcular (Ctrl+Enter)")
        btn_calc.Bind(wx.EVT_BUTTON, self.on_evaluar_inteligente)
        btn_clear = wx.Button(panel, label="&Borrar (Ctrl+Back)")
        btn_clear.Bind(wx.EVT_BUTTON, self.on_limpiar)
        btn_sizer.Add(btn_calc, 1, wx.RIGHT | wx.EXPAND, 5)
        btn_sizer.Add(btn_clear, 0, wx.EXPAND)
        sizer_main.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=10)

        # Output
        lbl_res = wx.StaticText(panel, label="&Resultados:")
        sizer_main.Add(lbl_res, flag=wx.LEFT, border=10)
        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.output_text.SetFont(wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.output_text.SetBackgroundColour(wx.Colour(250, 250, 250))
        sizer_main.Add(self.output_text, proportion=2, flag=wx.EXPAND | wx.ALL, border=10)

        panel.SetSizer(sizer_main)

    def crear_atajos(self):
        entries = [
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RETURN, 1001),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_BACK, 1002)
        ]
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))
        self.Bind(wx.EVT_MENU, self.on_evaluar_inteligente, id=1001)
        self.Bind(wx.EVT_MENU, self.on_limpiar, id=1002)

    def crear_menus(self):
        menubar = wx.MenuBar()
        
        # Operaciones
        m_ops = wx.Menu()
        m_ops.Append(1001, "Evaluar\tCtrl+Enter")
        self.Bind(wx.EVT_MENU, self.on_simplificar, m_ops.Append(wx.ID_ANY, "Simplificar\tCtrl+S"))
        self.Bind(wx.EVT_MENU, self.on_factorizar, m_ops.Append(wx.ID_ANY, "Factorizar\tCtrl+F"))
        m_ops.AppendSeparator()
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), m_ops.Append(wx.ID_EXIT, "Salir\tAlt+F4"))

        # Cálculo
        m_calc = wx.Menu()
        self.Bind(wx.EVT_MENU, self.on_derivar, m_calc.Append(wx.ID_ANY, "Derivar\tCtrl+D"))
        self.Bind(wx.EVT_MENU, self.on_derivada_enecima, m_calc.Append(wx.ID_ANY, "Derivada Orden N\tCtrl+Shift+D"))
        m_calc.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.on_integrar, m_calc.Append(wx.ID_ANY, "Integrar\tCtrl+I"))
        self.Bind(wx.EVT_MENU, self.on_limite, m_calc.Append(wx.ID_ANY, "Límite\tCtrl+L"))

        # Álgebra y Ayuda
        m_alg = wx.Menu()
        self.Bind(wx.EVT_MENU, self.on_sistema_gauss, m_alg.Append(wx.ID_ANY, "Sistemas (Gauss-Jordan)\tCtrl+G"))

        # Sistemas 2x2 por métodos clásicos (submenú)
        m_clasicos = wx.Menu()
        for metodo, nombre in (("sustitucion", "Sustitución"), ("igualacion", "Igualación"), ("reduccion", "Reducción")):
            item = m_clasicos.Append(wx.ID_ANY, nombre)
            self.Bind(wx.EVT_MENU, lambda e, m=metodo, n=nombre: self.on_sistema_clasico(m, n.lower()), item)
        m_alg.AppendSubMenu(m_clasicos, "Sistema 2x2 por &método clásico")

        m_alg.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.on_inversa_cofactores, m_alg.Append(wx.ID_ANY, "Matriz Inversa (Cofactores)\tCtrl+M"))
        
        m_help = wx.Menu()
        self.Bind(wx.EVT_MENU, self.mostrar_ayuda, m_help.Append(wx.ID_ANY, "Ayuda\tF1"))

        menubar.Append(m_ops, "&Operaciones")
        menubar.Append(m_calc, "&Cálculo")
        menubar.Append(m_alg, "&Álgebra")
        menubar.Append(m_help, "A&yuda")
        self.SetMenuBar(menubar)

    # --- LÓGICA DE UX MEJORADA ---

    def obtener_texto(self):
        # Comprobar antes de mostrar diálogos de variable/orden para no pedir datos en vano
        if self._calculo_actual is not None:
            wx.MessageBox("Ya hay un cálculo en curso. Espere a que termine o cancélelo.",
                          "Calculadora ocupada", wx.OK | wx.ICON_INFORMATION)
            return None
        txt = self.input_text.GetValue().strip()
        if not txt:
            # ERROR EN DIÁLOGO (User Request)
            wx.MessageBox("El campo de entrada está vacío.\nPor favor escriba una expresión matemática.", 
                          "Atención", wx.OK | wx.ICON_WARNING)
            self.input_text.SetFocus()
            return None
        return txt

    # Prefijos con los que los motores reportan un fallo (comparados en minúsculas)
    PREFIJOS_ERROR = ("error", "no se puede calcular")

    def presentar_resultado(self, texto):
        # Si el motor reportó un fallo, mostramos DIÁLOGO
        if str(texto).lstrip().lower().startswith(self.PREFIJOS_ERROR):
             wx.MessageBox(str(texto), "Error Matemático", wx.OK | wx.ICON_ERROR)
             self.input_text.SetFocus() # Volvemos al input para que corrija
        else:
            self.output_text.SetValue(str(texto))
            self.output_text.SetInsertionPoint(0)
            self.output_text.SetFocus()

    # --- CÁLCULO EN SEGUNDO PLANO ---
    # SymPy puede tardar segundos (o no terminar) en simplify/limit/integrate.
    # Si se ejecutara en el hilo de la interfaz, la ventana se congelaría sin que
    # el lector de pantalla anuncie nada. Por eso: los diálogos de datos se muestran
    # aquí (hilo de UI), y solo el cálculo va a un hilo aparte.

    def _ejecutar(self, tarea, descripcion):
        """
        Ejecuta tarea() (que devuelve el texto del resultado) en un hilo aparte.
        Si tarda más de MS_ANTES_DE_AVISAR, muestra un diálogo "Calculando…" con
        botón Cancelar. El resultado se presenta en el hilo de la interfaz.
        """
        if self._calculo_actual is not None:
            wx.MessageBox("Ya hay un cálculo en curso. Espere a que termine o cancélelo.",
                          "Calculadora ocupada", wx.OK | wx.ICON_INFORMATION)
            return

        token = object()
        self._calculo_actual = token
        self.lbl_info.SetValue(f"Calculando: {descripcion}...")

        def trabajo():
            try:
                resultado = tarea()
            except Exception as e:
                resultado = f"Error inesperado: {e}"
            wx.CallAfter(self._finalizar_calculo, token, resultado)

        threading.Thread(target=trabajo, daemon=True).start()
        self._timer_aviso = wx.CallLater(self.MS_ANTES_DE_AVISAR, self._mostrar_progreso, token, descripcion)

    def _mostrar_progreso(self, token, descripcion):
        if token is not self._calculo_actual:
            return  # ya terminó (o se canceló) antes de hacer falta el aviso
        self._dlg_progreso = wx.ProgressDialog(
            "Calculando",
            f"Calculando {descripcion}. Puede tardar unos segundos.\n"
            "Pulse Cancelar para abandonar este cálculo.",
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
        self.lbl_info.SetValue("Cálculo cancelado. " + TEXTO_INFO)
        self.input_text.SetFocus()

    def _finalizar_calculo(self, token, resultado):
        if token is not self._calculo_actual:
            return  # cálculo cancelado: se ignora el resultado tardío
        self._calculo_actual = None
        self._cerrar_progreso()
        self.lbl_info.SetValue(TEXTO_INFO)
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
                f"La expresión tiene varias variables ({', '.join(vars_detectadas)}).\n¿Respecto a cuál desea {operacion}?", 
                "Selección de Variable", 
                vars_detectadas
            )
            if dlg.ShowModal() == wx.ID_OK:
                return dlg.GetStringSelection()
            else:
                return None # Cancelado

        # Caso 2: Integrar constante (0 variables) -> Preguntar
        if len(vars_detectadas) == 0 and operacion == "integrar":
            dlg = wx.TextEntryDialog(self, "Está integrando una constante.\n¿Cuál es la variable de integración? (ej: x, t)", "Variable Requerida")
            if dlg.ShowModal() == wx.ID_OK:
                return dlg.GetValue()
            return None

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
            self._ejecutar(lambda: self.core.ResolverSistemaGauss(lineas), "el sistema por Gauss-Jordan")
        else:
            self._ejecutar(lambda: self.core.Evaluar(txt), "la evaluación")

    def on_simplificar(self, event):
        txt = self.obtener_texto()
        if txt: self._ejecutar(lambda: self.core.Simplificar(txt), "la simplificación")

    def on_factorizar(self, event):
        txt = self.obtener_texto()
        if txt: self._ejecutar(lambda: self.core.Factorizar(txt), "la factorización")

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

        self._ejecutar(lambda: self.core.Derivar(txt, var_elegida), "la derivada")

    def on_integrar(self, event):
        txt = self.obtener_texto()
        if not txt: return

        var_elegida = self._resolver_ambiguedad_variable(txt, "integrar")

        vars_detectadas = self.core.DetectarVariables(txt)
        # Si era ambigua o constante y no eligió nada (Cancel), salimos
        if (len(vars_detectadas) > 1 or len(vars_detectadas) == 0) and var_elegida is None:
            return

        self._ejecutar(lambda: self.core.Integrar(txt, var_elegida), "la integral")

    def on_derivada_enecima(self, event):
        expr = self.obtener_texto()
        if not expr: return

        # Aquí siempre preguntamos porque es avanzado
        var = self._pedir_texto("Variable:", "Derivada N")
        if var is None: return

        orden_txt = self._pedir_texto("Orden (número entero mayor o igual que 1):", "Derivada N")
        if orden_txt is None: return
        try:
            orden = int(orden_txt)
        except ValueError:
            wx.MessageBox("El orden debe ser un número entero.", "Error", wx.OK | wx.ICON_ERROR)
            return

        self._ejecutar(lambda: self.core.DerivadaEnecima(expr, var, orden), f"la derivada de orden {orden}")

    def on_limite(self, event):
        expr = self.obtener_texto()
        if not expr: return

        var = self._pedir_texto("Variable:", "Límite")
        if var is None: return

        tendencia = self._pedir_texto(
            "Tendencia (ej: 0, 2, oo, -oo; para un límite lateral agregue + o -, ej: 0+):",
            "Límite")
        if tendencia is None: return

        self._ejecutar(lambda: self.core.CalcularLimite(expr, var, tendencia), "el límite")

    def on_sistema_gauss(self, event):
        txt = self.obtener_texto()
        if not txt: return
        lineas = txt.split('\n')
        self._ejecutar(lambda: self.core.ResolverSistemaGauss(lineas), "el sistema por Gauss-Jordan")

    def on_sistema_clasico(self, metodo, nombre):
        """Sistema 2x2 por sustitución, igualación o reducción."""
        txt = self.obtener_texto()
        if not txt: return
        lineas = txt.split('\n')
        self._ejecutar(lambda: self.core.ResolverSistemaEducativo(lineas, metodo), f"el sistema por {nombre}")

    def on_inversa_cofactores(self, event):
        txt = self.obtener_texto()
        if txt: self._ejecutar(lambda: self.core.MatrizInversaCofactores(txt), "la matriz inversa")

    def on_limpiar(self, event):
        self.input_text.Clear()
        self.output_text.Clear()
        self.input_text.SetFocus()

    def mostrar_ayuda(self, event):
        # Texto diseñado para ser leído claramente por NVDA
        # Usamos mayúsculas para separar secciones y listas claras.
        manual_novato = (
            "MANUAL DE USUARIO: CALCULADORA CIENTÍFICA ACCESIBLE\n"
            "===================================================\n\n"
            
            "1. ¿QUÉ ES ESTA HERRAMIENTA?\n"
            "   Es una calculadora avanzada que funciona como un chat.\n"
            "   Usted escribe una orden matemática en el cuadro de arriba,\n"
            "   presiona una combinación de teclas, y el resultado aparece\n"
            "   aquí abajo, listo para ser leído.\n\n"

            "2. FLUJO DE TRABAJO (CÓMO USARLA)\n"
            "   Paso A: Escriba su fórmula (ej: 2+2) en la entrada.\n"
            "   Paso B: Elija qué hacer (Calcular, Derivar, Integrar).\n"
            "           Puede usar el menú o los atajos de teclado.\n"
            "   Paso C: El foco saltará automáticamente a este cuadro\n"
            "           para leerle el resultado paso a paso.\n\n"

            "3. ATAJOS DE TECLADO (MEMORIZAR ESTOS)\n"
            "   [Ctrl + Enter]     : CALCULAR (Aritmética básica, Sistemas).\n"
            "   [Ctrl + S]         : SIMPLIFICAR una expresión.\n"
            "   [Ctrl + F]         : FACTORIZAR un polinomio.\n"
            "   [Ctrl + D]         : DERIVAR una función.\n"
            "   [Ctrl + Mayús + D] : DERIVADA de orden N.\n"
            "   [Ctrl + I]         : INTEGRAR una función.\n"
            "   [Ctrl + L]         : Calcular LÍMITE.\n"
            "   [Ctrl + G]         : Resolver SISTEMA por Gauss-Jordan.\n"
            "   [Ctrl + M]         : MATRIZ INVERSA por cofactores.\n"
            "   [Ctrl + Borrar]    : LIMPIAR pantalla para empezar de cero.\n"
            "   [F1]               : Ver esta ayuda.\n"
            "   [Alt]              : Acceder a la barra de menús.\n"
            "   Sistemas 2x2 por sustitución, igualación o reducción:\n"
            "   menú Álgebra, submenú 'Sistema 2x2 por método clásico'.\n\n"

            "   Si un cálculo tarda, se abre el diálogo 'Calculando'.\n"
            "   Puede pulsar Cancelar para abandonarlo.\n\n"

            "4. GUÍA DE ESCRITURA (SINTAXIS)\n"
            "   Para que la calculadora le entienda, escriba así:\n\n"
            "   * Multiplicación: Puede usar el asterisco o escribir\n"
            "     el número pegado: 2*x, 2x, 3sin(x) y 2(x+1) son válidos.\n"
            "     IMPORTANTE: entre una variable y una función use\n"
            "     siempre el asterisco.\n"
            "     CORRECTO: x*sin(x)     INCORRECTO: xsin(x)\n\n"
            "   * Potencias: Use el sombrero (^) o doble asterisco (**).\n"
            "     Ejemplo: x^2  o  x**2\n\n"
            "   * Funciones: Use paréntesis siempre.\n"
            "     Ejemplo: sin(x), cos(x), ln(x), sqrt(x)\n\n"
            "   * Constantes matemáticas:\n"
            "     Escriba 'pi' para el número Pi.\n"
            "     Escriba 'e' para el número de Euler.\n"
            "     Escriba 'oo' (doble letra o) para Infinito.\n\n"
            "   * Matrices (para la inversa): una fila por línea,\n"
            "     con los números separados por espacios. Ejemplo:\n"
            "       1 2\n"
            "       3 4\n\n"

            "5. EJEMPLOS PRÁCTICOS\n"
            "   - Derivar: Escriba '3*x^2 + 5'. Pulse Ctrl+D.\n"
            "   - Integrar: Escriba 'sin(x)'. Pulse Ctrl+I.\n"
            "   - Límite: Escriba 'sin(x)/x'. Pulse Ctrl+L.\n"
            "     Variable: x. Tendencia: 0.\n"
            "     Para un límite lateral escriba la tendencia con + o -,\n"
            "     por ejemplo 0+ (por la derecha) o 0- (por la izquierda).\n"
            "     Para infinito escriba oo, o -oo para menos infinito.\n"
            "   - Sistema 2x2: Escriba dos líneas:\n"
            "       x + y = 10\n"
            "       x - y = 2\n"
            "     Luego pulse Ctrl+Enter.\n\n"

            "6. SOLUCIÓN DE PROBLEMAS\n"
            "   - ¿Le pregunta por variables? Si escribe 'x + y', el sistema\n"
            "     le preguntará con cuál desea trabajar. Use las flechas\n"
            "     para elegir en el diálogo y pulse Enter.\n"
            "   - ¿Error de Sintaxis? Verifique que cerró todos los paréntesis\n"
            "     y que usó '*' entre una variable y una función.\n"
            "   - ¿Dice que hay un cálculo en curso? Espere a que termine,\n"
            "     o pulse Cancelar en el diálogo 'Calculando'."
        )
        
        # En lugar de MessageBox, usamos presentar_resultado.
        # Esto pone el texto en el cuadro grande y mueve el foco ahí.
        self.presentar_resultado(manual_novato)

if __name__ == "__main__":
    app = wx.App()
    frame = CalculadoraAccesible()
    frame.Show()
    app.MainLoop()