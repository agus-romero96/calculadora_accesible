import wx
import wx.lib.dialogs
from puente import CoreMatematico
from _version import __version__

class CalculadoraAccesible(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title=f"Jansen Calculator v{__version__}", size=(800, 750))
        
        self.core = CoreMatematico()
        self.init_ui()
        self.crear_menus()
        self.crear_atajos()
        self.Centre()
        self.input_text.SetFocus()

    def init_ui(self):
        panel = wx.Panel(self)
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # Info
        self.lbl_info = wx.TextCtrl(panel, value="Escriba su expresión. F1 Ayuda. Alt para menús.", style=wx.TE_READONLY | wx.BORDER_NONE)
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
        self.Bind(wx.EVT_MENU, self.on_sistema_gauss, m_alg.Append(wx.ID_ANY, "Sistemas (Gauss)"))
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
        txt = self.input_text.GetValue().strip()
        if not txt:
            # ERROR EN DIÁLOGO (User Request)
            wx.MessageBox("El campo de entrada está vacío.\nPor favor escriba una expresión matemática.", 
                          "Atención", wx.OK | wx.ICON_WARNING)
            self.input_text.SetFocus()
            return None
        return txt

    def presentar_resultado(self, texto):
        # Si el resultado comienza con "Error" o "Ambigüedad", mostramos DIÁLOGO
        if str(texto).startswith("Error") or "Ambigüedad" in str(texto):
             wx.MessageBox(str(texto), "Error Matemático", wx.OK | wx.ICON_ERROR)
             self.input_text.SetFocus() # Volvemos al input para que corrija
        else:
            self.output_text.SetValue(str(texto))
            self.output_text.SetInsertionPoint(0)
            self.output_text.SetFocus()

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

    def on_evaluar_inteligente(self, event):
        txt = self.obtener_texto()
        if not txt: return
        try:
            if "\n" in txt and "=" in txt:
                self.presentar_resultado(self.core.ResolverSistemaGauss(txt.split('\n')))
            else:
                self.presentar_resultado(self.core.Evaluar(txt))
        except Exception as e:
            self.presentar_resultado(f"Error: {e}")

    def on_simplificar(self, event):
        txt = self.obtener_texto()
        if txt: self.presentar_resultado(self.core.Simplificar(txt))

    def on_factorizar(self, event):
        txt = self.obtener_texto()
        if txt: self.presentar_resultado(self.core.Factorizar(txt))

    # --- CÁLCULO INTELIGENTE ---

    def on_derivar(self, event):
        txt = self.obtener_texto()
        if not txt: return
        
        # Pregunta preventiva
        var_elegida = self._resolver_ambiguedad_variable(txt, "derivar")
        
        # Si var_elegida es None, puede ser que:
        # 1. Usuario canceló -> no hacemos nada.
        # 2. No había ambigüedad -> llamamos a Derivar normalmente (Core usará default).
        
        # Verificamos si el usuario canceló el diálogo (si hubo diálogo)
        # (Lógica simplificada: Si hay multivariable y devuelve None, es cancel)
        vars_detectadas = self.core.DetectarVariables(txt)
        if len(vars_detectadas) > 1 and var_elegida is None:
            return # Cancelado

        # Llamada al core (si var_elegida es None, el core usa su lógica default 'x')
        res = self.core.calculo.CalcularDerivada(txt, variable=var_elegida)
        self.presentar_resultado(self.core.calculo.RenderizarTexto(res))

    def on_integrar(self, event):
        txt = self.obtener_texto()
        if not txt: return

        var_elegida = self._resolver_ambiguedad_variable(txt, "integrar")
        
        vars_detectadas = self.core.DetectarVariables(txt)
        # Si era ambigua o constante y no eligió nada (Cancel), salimos
        if (len(vars_detectadas) > 1 or len(vars_detectadas) == 0) and var_elegida is None:
            return

        res = self.core.calculo.CalcularIntegral(txt, variable=var_elegida)
        self.presentar_resultado(self.core.calculo.RenderizarTexto(res))

    def on_derivada_enecima(self, event):
        expr = self.obtener_texto()
        if not expr: return
        
        # Aquí siempre preguntamos porque es avanzado
        dlg_var = wx.TextEntryDialog(self, "Variable:", "Derivada N")
        if dlg_var.ShowModal() != wx.ID_OK: return
        var = dlg_var.GetValue()

        dlg_ord = wx.TextEntryDialog(self, "Orden (número):", "Derivada N")
        if dlg_ord.ShowModal() != wx.ID_OK: return
        
        try:
            orden = int(dlg_ord.GetValue())
            self.presentar_resultado(self.core.DerivadaEnecima(expr, var, orden))
        except:
            wx.MessageBox("El orden debe ser un número entero.", "Error", wx.OK | wx.ICON_ERROR)

    def on_limite(self, event):
        expr = self.obtener_texto()
        if not expr: return
        
        dlg_var = wx.TextEntryDialog(self, "Variable:", "Límite")
        if dlg_var.ShowModal() != wx.ID_OK: return
        var = dlg_var.GetValue()
        
        dlg_ten = wx.TextEntryDialog(self, "Tendencia:", "Límite")
        if dlg_ten.ShowModal() != wx.ID_OK: return
        
        self.presentar_resultado(self.core.CalcularLimite(expr, var, dlg_ten.GetValue()))

    def on_sistema_gauss(self, event):
        txt = self.obtener_texto()
        if txt: self.presentar_resultado(self.core.ResolverSistemaGauss(txt.split('\n')))

    def on_inversa_cofactores(self, event):
        """
        Manejador para el cálculo de Matriz Inversa por Cofactores.
        """
        txt = self.obtener_texto()
        if not txt: 
            return
            
        try:
            # Llamamos al puente. Asegúrate de que tu puente.py tenga este método expuesto.
            resultado = self.core.MatrizInversaCofactores(txt)
            self.presentar_resultado(resultado)
        except AttributeError:
            self.presentar_resultado("Error: El núcleo matemático (puente.py) no tiene conectado el módulo de matrices.")
        except Exception as e:
            self.presentar_resultado(f"Error de cálculo: {str(e)}")

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
            "   [Ctrl + Enter] : CALCULAR (Aritmética básica, Sistemas).\n"
            "   [Ctrl + D]     : DERIVAR una función.\n"
            "   [Ctrl + I]     : INTEGRAR una función.\n"
            "   [Ctrl + L]     : Calcular LÍMITE.\n"
            "   [Ctrl + Borrar]: LIMPIAR pantalla para empezar de cero.\n"
            "   [F1]           : Ver esta ayuda.\n"
            "   [Alt]          : Acceder a la barra de menús.\n\n"

            "4. GUÍA DE ESCRITURA (SINTAXIS)\n"
            "   Para que la calculadora le entienda, escriba así:\n\n"
            "   * Multiplicación: Use siempre el asterisco.\n"
            "     CORRECTO: 2*x     INCORRECTO: 2x\n\n"
            "   * Potencias: Use el sombrero (^) o doble asterisco (**).\n"
            "     Ejemplo: x^2  o  x**2\n\n"
            "   * Funciones: Use paréntesis siempre.\n"
            "     Ejemplo: sin(x), cos(x), ln(x), sqrt(x)\n\n"
            "   * Constantes matemáticas:\n"
            "     Escriba 'pi' para el número Pi.\n"
            "     Escriba 'e' para el número de Euler.\n"
            "     Escriba 'oo' (doble letra o) para Infinito.\n\n"

            "5. EJEMPLOS PRÁCTICOS\n"
            "   - Derivar: Escriba '3*x^2 + 5'. Pulse Ctrl+D.\n"
            "   - Integrar: Escriba 'sin(x)'. Pulse Ctrl+I.\n"
            "   - Sistema 2x2: Escriba dos líneas:\n"
            "       x + y = 10\n"
            "       x - y = 2\n"
            "     Luego pulse Ctrl+Enter.\n\n"

            "6. SOLUCIÓN DE PROBLEMAS\n"
            "   - ¿Le pregunta por variables? Si escribe 'x + y', el sistema\n"
            "     le preguntará con cuál desea trabajar. Use las flechas\n"
            "     para elegir en el diálogo y pulse Enter.\n"
            "   - ¿Error de Sintaxis? Verifique que cerró todos los paréntesis\n"
            "     y que usó '*' para multiplicar."
        )
        
        # En lugar de MessageBox, usamos presentar_resultado.
        # Esto pone el texto en el cuadro grande y mueve el foco ahí.
        self.presentar_resultado(manual_novato)

if __name__ == "__main__":
    app = wx.App()
    frame = CalculadoraAccesible()
    frame.Show()
    app.MainLoop()