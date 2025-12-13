import wx
import wx.lib.dialogs
from puente import CoreMatematico

class CalculadoraAccesible(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Calculadora Científica Accesible", size=(700, 750))
        
        # 1. Instanciamos el "Cerebro" Matemático
        self.core = CoreMatematico()
        
        # 2. Construimos la Interfaz
        self.init_ui()
        self.crear_menus()
        
        # 3. Configuración Final
        self.Centre()
        # Foco inicial en la entrada para empezar a escribir de inmediato
        self.input_text.SetFocus()

    def init_ui(self):
        panel = wx.Panel(self)
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # --- SECCIÓN A: INSTRUCCIONES ACCESIBLES ---
        lbl_instrucciones = wx.StaticText(
            panel, 
            label=("Escriba su expresión matemática o sistema de ecuaciones abajo.\n"
                   "Atajos: F1 (Ayuda), Ctrl+Enter (Calcular), Alt (Menú de Herramientas)")
        )
        sizer_main.Add(lbl_instrucciones, flag=wx.ALL | wx.EXPAND, border=10)

        # --- SECCIÓN B: LIENZO DE ENTRADA (INPUT) ---
        # TE_MULTILINE: Permite escribir sistemas de ecuaciones o matrices grandes.
        self.input_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self.input_text.SetName("Entrada Matemática. Escriba aquí fórmulas o ecuaciones.")
        
        # Fuente grande y legible
        font_modern = wx.Font(14, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.input_text.SetFont(font_modern)
        
        # Capturamos teclas especiales dentro de la caja
        self.input_text.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        
        sizer_main.Add(self.input_text, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # --- SECCIÓN C: BOTONERA (ACCESIBILIDAD VISUAL/MOUSE) ---
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_calc = wx.Button(panel, label="Calcular / Evaluar (Ctrl+Enter)")
        btn_calc.Bind(wx.EVT_BUTTON, self.on_evaluar_inteligente)
        
        btn_clear = wx.Button(panel, label="Borrar Todo (Ctrl+Borrar)")
        btn_clear.Bind(wx.EVT_BUTTON, self.on_limpiar)
        
        btn_sizer.Add(btn_calc, proportion=1, flag=wx.RIGHT, border=5)
        btn_sizer.Add(btn_clear, proportion=0)
        
        sizer_main.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=10)

        # --- SECCIÓN D: LIENZO DE RESULTADOS (OUTPUT) ---
        lbl_res = wx.StaticText(panel, label="Resultados y Explicación Paso a Paso:")
        sizer_main.Add(lbl_res, flag=wx.LEFT, border=10)

        self.output_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.output_text.SetName("Pantalla de Resultados.")
        self.output_text.SetBackgroundColour(wx.Colour(245, 245, 245)) # Gris muy claro
        self.output_text.SetFont(font_modern)
        
        sizer_main.Add(self.output_text, proportion=2, flag=wx.EXPAND | wx.ALL, border=10)

        panel.SetSizer(sizer_main)

    def crear_menus(self):
        menubar = wx.MenuBar()

        # --- 1. MENÚ BÁSICO (ARITMÉTICA) ---
        menu_ops = wx.Menu()
        item_eval = menu_ops.Append(wx.ID_ANY, "&Evaluar Expresión\tCtrl+Enter", "Calcula valor numérico o resuelve sistemas automáticamente")
        item_simp = menu_ops.Append(wx.ID_ANY, "&Simplificar\tCtrl+S", "Reduce términos algebraicos")
        item_fact = menu_ops.Append(wx.ID_ANY, "&Factorizar\tCtrl+F", "Transforma sumas en productos")
        menu_ops.AppendSeparator()
        item_exit = menu_ops.Append(wx.ID_EXIT, "Salir\tAlt+F4", "Cierra la aplicación")

        self.Bind(wx.EVT_MENU, self.on_evaluar_inteligente, item_eval)
        self.Bind(wx.EVT_MENU, self.on_simplificar, item_simp)
        self.Bind(wx.EVT_MENU, self.on_factorizar, item_fact)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), item_exit)

        # --- 2. MENÚ ÁLGEBRA (SISTEMAS Y MATRICES) ---
        menu_alg = wx.Menu()
        
        # Submenú Sistemas Lineales
        menu_sis = wx.Menu()
        sis_gauss = menu_sis.Append(wx.ID_ANY, "Método &Gauss-Jordan (Universal)", "Paso a paso matrices")
        sis_red = menu_sis.Append(wx.ID_ANY, "Método de &Reducción (2x2)", "Suma y Resta escolar")
        sis_sust = menu_sis.Append(wx.ID_ANY, "Método de &Sustitución (2x2)", "Despeje escolar")
        sis_igual = menu_sis.Append(wx.ID_ANY, "Método de &Igualación (2x2)", "Igualación escolar")
        menu_alg.AppendSubMenu(menu_sis, "Resolver &Sistema de Ecuaciones")
        
        # Matrices
        menu_alg.AppendSeparator()
        mat_inv = menu_alg.Append(wx.ID_ANY, "Matriz &Inversa (Cofactores)\tCtrl+I", "Cálculo paso a paso por adjunta")
        
        # Conexiones Álgebra
        self.Bind(wx.EVT_MENU, self.on_sistema_gauss, sis_gauss)
        self.Bind(wx.EVT_MENU, lambda e: self.procesar_sistema_clasico("reduccion"), sis_red)
        self.Bind(wx.EVT_MENU, lambda e: self.procesar_sistema_clasico("sustitucion"), sis_sust)
        self.Bind(wx.EVT_MENU, lambda e: self.procesar_sistema_clasico("igualacion"), sis_igual)
        self.Bind(wx.EVT_MENU, self.on_inversa_cofactores, mat_inv)

        # --- 3. MENÚ CÁLCULO (AQUÍ ESTÁ LO QUE FALTABA) ---
        menu_calc = wx.Menu()
        
        calc_der = menu_calc.Append(wx.ID_ANY, "&Derivar Función (Simple)\tCtrl+D", "Derivada primera con reglas")
        calc_der_n = menu_calc.Append(wx.ID_ANY, "Derivada de Orden &N (Superior)\tCtrl+Shift+D", "Derivadas sucesivas (ej: 3ra derivada)")
        menu_calc.AppendSeparator()
        calc_int = menu_calc.Append(wx.ID_ANY, "I&ntegrar Función\tCtrl+Shift+I", "Integral indefinida paso a paso")
        calc_lim = menu_calc.Append(wx.ID_ANY, "Calcular &Límite...\tCtrl+L", "Límite en un punto o infinito")

        # Conexiones Cálculo
        self.Bind(wx.EVT_MENU, self.on_derivar, calc_der)
        self.Bind(wx.EVT_MENU, self.on_derivada_enecima, calc_der_n)
        self.Bind(wx.EVT_MENU, self.on_integrar, calc_int)
        self.Bind(wx.EVT_MENU, self.on_limite, calc_lim)

        # --- 4. AYUDA ---
        menu_help = wx.Menu()
        help_syntax = menu_help.Append(wx.ID_ANY, "Guía de Símbolos\tF1", "Muestra ayuda rápida")
        self.Bind(wx.EVT_MENU, self.mostrar_ayuda, help_syntax)

        menubar.Append(menu_ops, "&Operaciones")
        menubar.Append(menu_alg, "&Álgebra")
        menubar.Append(menu_calc, "&Cálculo")
        menubar.Append(menu_help, "A&yuda")
        
        self.SetMenuBar(menubar)

    # --- LÓGICA DE INTERACCIÓN (CORE UX) ---

    def on_key_down(self, event):
        # Ctrl+Enter dispara la evaluación inteligente
        if event.GetKeyCode() == wx.WXK_RETURN and event.ControlDown():
            self.on_evaluar_inteligente(None)
        # Ctrl+Backspace limpia todo
        elif event.GetKeyCode() == wx.WXK_BACK and event.ControlDown():
            self.on_limpiar(None)
        else:
            event.Skip()

    def obtener_texto(self):
        txt = self.input_text.GetValue().strip()
        if not txt:
            wx.MessageBox("El campo de entrada está vacío.", "Atención", wx.ICON_WARNING)
            return None
        return txt

    def presentar_resultado(self, texto):
        """
        Clave de Accesibilidad: Mueve el foco y prepara el cursor para lectura.
        """
        self.output_text.SetValue(str(texto))
        self.output_text.SetFocus()
        self.output_text.SetInsertionPoint(0)

    # --- HANDLERS: ARITMÉTICA Y GENERAL ---

    def on_evaluar_inteligente(self, event):
        txt = self.obtener_texto()
        if not txt: return
        
        # Detectar si es sistema (múltiples líneas con =)
        lineas = [l for l in txt.split('\n') if l.strip()]
        if len(lineas) > 1 and "=" in txt:
            try:
                self.presentar_resultado(self.core.ResolverSistemaGauss(lineas))
            except Exception as e:
                self.presentar_resultado(f"Error interpretando sistema: {e}")
        else:
            try:
                self.presentar_resultado(self.core.Evaluar(txt))
            except Exception as e:
                self.presentar_resultado(f"Error evaluando: {e}")

    def on_simplificar(self, event):
        txt = self.obtener_texto()
        if txt:
            self.presentar_resultado(self.core.Simplificar(txt))

    def on_factorizar(self, event):
        txt = self.obtener_texto()
        if txt:
            self.presentar_resultado(self.core.Factorizar(txt))

    def on_limpiar(self, event):
        self.input_text.Clear()
        self.output_text.Clear()
        self.input_text.SetFocus()

    # --- HANDLERS: ÁLGEBRA ---

    def on_sistema_gauss(self, event):
        txt = self.obtener_texto()
        if not txt:
            return
        lineas = [l for l in txt.split('\n') if l.strip()]
        if len(lineas) < 2:
            self.presentar_resultado("Para Gauss, escriba al menos 2 ecuaciones (una por línea).")
            return
        self.presentar_resultado(self.core.ResolverSistemaGauss(lineas))

    def procesar_sistema_clasico(self, metodo):
        txt = self.obtener_texto()
        if not txt: return
        lineas = [l for l in txt.split('\n') if l.strip()]
        if len(lineas) != 2:
            self.presentar_resultado(f"El método de {metodo} requiere exactamente 2 ecuaciones.")
            return
        try:
            # puente.py -> ResolverSistemaEducativo
            self.presentar_resultado(self.core.ResolverSistemaEducativo(lineas, metodo))
        except Exception as e:
            self.presentar_resultado(f"Error: {e}")

    def on_inversa_cofactores(self, event):
        txt = self.obtener_texto()
        if txt: self.presentar_resultado(self.core.MatrizInversaCofactores(txt))

    # --- HANDLERS: CÁLCULO (Derivadas, Integrales, Límites) ---

    def on_derivar(self, event):
        """Derivada simple (orden 1)."""
        txt = self.obtener_texto()
        if txt: self.presentar_resultado(self.core.Derivar(txt))

    def on_integrar(self, event):
        txt = self.obtener_texto()
        if txt: self.presentar_resultado(self.core.Integrar(txt))

    def on_derivada_enecima(self, event):
        """Pide Variable y Orden N mediante diálogos simples."""
        expr = self.obtener_texto()
        if not expr: return

        # 1. Pedir Variable
        dlg_var = wx.TextEntryDialog(self, "Escriba la variable de derivación (ej: x):", "Derivada Enésima", "x")
        if dlg_var.ShowModal() != wx.ID_OK: return
        variable = dlg_var.GetValue()

        # 2. Pedir Orden
        dlg_ord = wx.TextEntryDialog(self, "Escriba el orden de la derivada (ej: 2, 3):", "Derivada Enésima", "2")
        if dlg_ord.ShowModal() != wx.ID_OK: return
        
        try:
            orden = int(dlg_ord.GetValue())
            # puente.py -> DerivadaEnecima
            res = self.core.DerivadaEnecima(expr, variable, orden)
            self.presentar_resultado(res)
        except ValueError:
            self.presentar_resultado("Error: El orden debe ser un número entero.")
        except Exception as e:
            self.presentar_resultado(f"Error cálculo: {e}")

    def on_limite(self, event):
        """Pide Variable y Tendencia."""
        expr = self.obtener_texto()
        if not expr: return

        # 1. Pedir Variable
        dlg_var = wx.TextEntryDialog(self, "Variable del límite (ej: x):", "Calcular Límite", "x")
        if dlg_var.ShowModal() != wx.ID_OK: return
        variable = dlg_var.GetValue()

        # 2. Pedir Tendencia
        dlg_ten = wx.TextEntryDialog(self, f"¿A qué valor tiende '{variable}'? (Use 'oo' para infinito):", "Calcular Límite", "0")
        if dlg_ten.ShowModal() != wx.ID_OK:
            return
        tendencia = dlg_ten.GetValue()

        try:
            # puente.py -> CalcularLimite
            res = self.core.CalcularLimite(expr, variable, tendencia)
            self.presentar_resultado(res)
        except Exception as e:
            self.presentar_resultado(f"Error cálculo límite: {e}")

    def mostrar_ayuda(self, event):
        info = (
            "GUÍA RÁPIDA DE SINTAXIS\n"
            "-----------------------\n"
            "Operaciones: +, -, *, /, ** (potencia)\n"
            "Funciones: sqrt(x), sin(x), cos(x), ln(x), exp(x)\n"
            "Constantes: pi, e, oo (infinito)\n\n"
            "Sistemas de Ecuaciones:\n"
            "Escriba una ecuación por línea.\n"
            "Ejemplo:\n"
            "2x + y = 10\n"
            "x - y = 5\n\n"
            "Matrices:\n"
            "Use corchetes anidados. Ej: [[1, 2], [3, 4]]"
        )
        self.presentar_resultado(info)

if __name__ == "__main__":
    app = wx.App()
    frame = CalculadoraAccesible()
    frame.Show()
    app.MainLoop()