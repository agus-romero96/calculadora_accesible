import wx
import wx.lib.dialogs
from operations import Algebra, DifFactorizaciones

class Calculadora(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Calculadora Científica Accesible", size=(450, 650))
        
        self.operaciones = Algebra()
        self.factorizacion = DifFactorizaciones(self.operaciones)
        
        self.init_ui()
        self.Centre()
        
    def init_ui(self):
        panel = wx.Panel(self)
        
        # --- SIZER PRINCIPAL (VERTICAL) ---
        sizer = wx.BoxSizer(wx.VERTICAL)

        # 1. Campo de Ecuación
        # Etiqueta descriptiva para lector de pantalla
        intro_label = wx.StaticText(panel, label="Escriba su expresión matemática aquí (Presione F1 para ver ayuda de símbolos):")
        self.expresion = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.expresion.SetName("Entrada de expresión. Escriba aquí su fórmula.")
        self.expresion.Bind(wx.EVT_TEXT_ENTER, self.on_enter_key) # Enter evalúa por defecto
        
        sizer.Add(intro_label, flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(self.expresion, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # 2. Panel de Derivada Enésima (Oculto por defecto)
        self.avanzado_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.orden_label = wx.StaticText(panel, label="Orden:")
        self.orden_derivada = wx.TextCtrl(panel, value="1", size=(50, -1))
        self.orden_derivada.SetName("Orden de la derivada")
        
        self.variable_label = wx.StaticText(panel, label="Var:")
        self.variable_campo = wx.TextCtrl(panel, value="x", size=(50, -1))
        self.variable_campo.SetName("Variable de derivación")
        
        self.btn_calcular_derivada = wx.Button(panel, label="Ejecutar Derivada N")
        self.btn_calcular_derivada.Bind(wx.EVT_BUTTON, self.on_calcular_enecima_accion)

        self.avanzado_sizer.Add(self.orden_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        self.avanzado_sizer.Add(self.orden_derivada, flag=wx.ALL, border=5)
        self.avanzado_sizer.Add(self.variable_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        self.avanzado_sizer.Add(self.variable_campo, flag=wx.ALL, border=5)
        self.avanzado_sizer.Add(self.btn_calcular_derivada, flag=wx.ALL, border=5)
        
        sizer.Add(self.avanzado_sizer, flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.ocultar_controles_avanzados()

        # 3. Área de Resultado
        res_label = wx.StaticText(panel, label="Resultado y Pasos (Use flechas para leer):")
        self.result_text = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_MULTILINE)
        self.result_text.SetName("Área de resultados.")
        self.result_text.SetBackgroundColour(wx.LIGHT_GREY)
        
        sizer.Add(res_label, flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(self.result_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

        # 4. Botones de Acción Rápida
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_eval = wx.Button(panel, label="Evaluar")
        btn_eval.Bind(wx.EVT_BUTTON, self.on_evaluate)
        
        btn_borrar = wx.Button(panel, label="Borrar Todo")
        btn_borrar.Bind(wx.EVT_BUTTON, self.on_limpiar)
        
        btn_sizer.Add(btn_eval, flag=wx.RIGHT, border=20)
        btn_sizer.Add(btn_borrar)
        
        sizer.Add(btn_sizer, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        panel.SetSizer(sizer)
        
        # Inicializar Menús y Atajos
        self.init_menu()
        self.init_accelerators(btn_borrar)

    def init_menu(self):
        menu_bar = wx.MenuBar()
        
        # --- MENÚ 1: BÁSICO ---
        basico_menu = wx.Menu()
        self.eval_item = basico_menu.Append(wx.ID_ANY, "Evaluar Expresión\tEnter", "Calcula el resultado numérico")
        self.simp_item = basico_menu.Append(wx.ID_ANY, "Simplificar Expresión\tCtrl+S", "Simplifica términos algebraicos")
        self.factor_item = basico_menu.Append(wx.ID_ANY, "Factorizar\tCtrl+F", "Convierte en producto de factores")
        basico_menu.AppendSeparator()
        self.salir_item = basico_menu.Append(wx.ID_EXIT, "Salir\tAlt+F4")
        
        self.Bind(wx.EVT_MENU, self.on_evaluate, self.eval_item)
        self.Bind(wx.EVT_MENU, self.on_simplificar, self.simp_item)
        self.Bind(wx.EVT_MENU, self.on_factorizar, self.factor_item)
        self.Bind(wx.EVT_MENU, self.on_salir, self.salir_item)
        
        menu_bar.Append(basico_menu, "&Básico")

        # --- MENÚ 2: ÁLGEBRA ---
        algebra_menu = wx.Menu()
        self.resolver_item = algebra_menu.Append(wx.ID_ANY, "Resolver Ecuación (Raíces)\tCtrl+R", "Despeja x de la ecuación")
        
        # --- NUEVO: SISTEMA DE ECUACIONES ---
        self.sistema_item = algebra_menu.Append(wx.ID_ANY, "Resolver Sistema Lineal (Gauss)\tCtrl+Shift+G", "Paso a paso para sistemas de ecuaciones")
        self.Bind(wx.EVT_MENU, self.on_sistema_ecuaciones, self.sistema_item)
        # ------------------------------------
        
        self.matriz_item = algebra_menu.Append(wx.ID_ANY, "Determinante de Matriz\tCtrl+M", "Calcula determinante de matriz cuadrada")
        
        self.Bind(wx.EVT_MENU, self.on_resolver_ecuacion, self.resolver_item)
        self.Bind(wx.EVT_MENU, self.on_determinante, self.matriz_item)
        
        menu_bar.Append(algebra_menu, "&Álgebra")

        # --- MENÚ 3: CÁLCULO ---
        calculo_menu = wx.Menu()
        self.deriv_item = calculo_menu.Append(wx.ID_ANY, "Derivar (Explicada)\tCtrl+D", "Derivada con regla aplicada")
        self.enecima_item = calculo_menu.Append(wx.ID_ANY, "Derivada Enésima (Avanzada)\tCtrl+Shift+D", "Muestra derivadas sucesivas")
        calculo_menu.AppendSeparator()
        self.int_item = calculo_menu.Append(wx.ID_ANY, "Integrar (Paso a Paso)\tCtrl+I", "Integral indefinida explicada")
        self.limite_item = calculo_menu.Append(wx.ID_ANY, "Calcular Límite\tCtrl+L", "Límite cuando x tiende a un valor")
        
        self.Bind(wx.EVT_MENU, self.on_derivar, self.deriv_item)
        self.Bind(wx.EVT_MENU, self.on_abrir_enecima, self.enecima_item)
        self.Bind(wx.EVT_MENU, self.on_integrar, self.int_item)
        self.Bind(wx.EVT_MENU, self.on_limite_dialogo, self.limite_item)
        
        menu_bar.Append(calculo_menu, "&Cálculo")
        
        # --- MENÚ 4: AYUDA ---
        ayuda_menu = wx.Menu()
        self.sintaxis_item = ayuda_menu.Append(wx.ID_ANY, "Guía de Símbolos y Sintaxis\tF1", "Muestra cómo escribir fórmulas")
        self.Bind(wx.EVT_MENU, self.mostrar_ayuda, self.sintaxis_item)
        
        menu_bar.Append(ayuda_menu, "A&yuda")

        self.SetMenuBar(menu_bar)

    def init_accelerators(self, borrar_btn):
        # Mapeo de teclas globales
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('B'), borrar_btn.GetId()), # Ctrl+B para borrar
            (wx.ACCEL_NORMAL, wx.WXK_F1, self.sintaxis_item.GetId()) # F1 Ayuda
        ])
        self.SetAcceleratorTable(accel_tbl)

    # --- CONTROL DE INTERFAZ ---
    def ocultar_controles_avanzados(self):
        self.orden_label.Hide()
        self.orden_derivada.Hide()
        self.variable_label.Hide()
        self.variable_campo.Hide()
        self.btn_calcular_derivada.Hide()
        self.Layout()

    def mostrar_controles_avanzados(self):
        self.orden_label.Show()
        self.orden_derivada.Show()
        self.variable_label.Show()
        self.variable_campo.Show()
        self.btn_calcular_derivada.Show()
        self.Layout()
        self.orden_derivada.SetFocus()
        self.orden_derivada.SelectAll()

    def get_val(self):
        return self.expresion.GetValue()

    def show_res(self, texto):
        self.result_text.SetValue(texto)
        self.result_text.SetFocus()
        self.result_text.SetInsertionPoint(0)
        # Ocultar paneles extra si se usó una operación normal
        self.ocultar_controles_avanzados()

    def on_enter_key(self, event):
        # Al pulsar Enter, por defecto Evaluamos (lo más común)
        self.on_evaluate(event)

    def on_limpiar(self, event):
        self.expresion.SetValue("")
        self.result_text.Clear()
        self.expresion.SetFocus()
        self.ocultar_controles_avanzados()
    
    def on_salir(self, event):
        self.Close()

    # --- OPERACIONES ---
    
    def on_evaluate(self, e): 
        self.show_res(self.operaciones.EvaluarExpresion(self.get_val()))

    def on_simplificar(self, e): 
        self.show_res(self.operaciones.SimplificarEcuacion(self.get_val()))

    def on_factorizar(self, e): 
        self.show_res(self.factorizacion.IntentarFactorizar(self.get_val()))

    def on_derivar(self, e): 
        self.show_res(self.operaciones.Derivada(self.get_val()))

    def on_integrar(self, e): 
        self.show_res(self.operaciones.Integral(self.get_val()))

    def on_determinante(self, e): 
        self.show_res(self.operaciones.Determinante(self.get_val()))

    # --- NUEVAS FUNCIONES DE OPERATIONS ---
    
    def on_resolver_ecuacion(self, e):
        expr = self.get_val()
        if not expr:
            self.show_res("Error: Escriba una ecuación primero (ej: x^2 - 4 = 0).")
            return
        # Intentamos resolver para 'x' por defecto
        try:
            res = self.operaciones.ResolverEcuacion(expr, variable='x')
            self.show_res(res)
        except AttributeError:
            self.show_res("Error: Actualice operations.py con la función ResolverEcuacion.")

    def on_limite_dialogo(self, e):
        # Diálogo accesible para pedir datos del límite
        expr = self.get_val()
        if not expr:
            self.show_res("Error: Escriba la función primero en el cuadro principal.")
            return

        # 1. Pedir Variable
        dlg_var = wx.TextEntryDialog(self, "Escriba la variable (ej: x):", "Calcular Límite - Paso 1", "x")
        if dlg_var.ShowModal() == wx.ID_OK:
            variable = dlg_var.GetValue()
        else:
            return # Cancelado

        # 2. Pedir Tendencia
        dlg_val = wx.TextEntryDialog(self, "La variable tiende a (número o 'oo' para infinito):", "Calcular Límite - Paso 2", "0")
        if dlg_val.ShowModal() == wx.ID_OK:
            tendencia = dlg_val.GetValue()
        else:
            return # Cancelado

        # Calcular
        try:
            res = self.operaciones.CalcularLimite(expr, variable, tendencia)
            self.show_res(res)
        except AttributeError:
            self.show_res("Error: Actualice operations.py con la función CalcularLimite.")

    def on_sistema_ecuaciones(self, event):
        """
        Diálogo inteligente: Ofrece métodos de secundaria solo para 2x2.
        """
        # Paso 1: Cantidad
        dlg_num = wx.TextEntryDialog(self, "¿Cuántas ecuaciones tiene el sistema? (ej: 2 o 3)", "Sistema Lineal", "2")
        if dlg_num.ShowModal() != wx.ID_OK: return
        
        try:
            num = int(dlg_num.GetValue())
            if num < 2:
                self.show_res("Error: Mínimo 2 ecuaciones.")
                return
        except ValueError:
            self.show_res("Error: Número inválido.")
            return

        # Paso 2: Ingreso de Ecuaciones
        dlg_ecus = wx.Dialog(self, title=f"Ingresar {num} Ecuaciones")
        sizer_dlg = wx.BoxSizer(wx.VERTICAL)
        
        lbl_info = wx.StaticText(dlg_ecus, label="Escriba ecuaciones (ej: x + y = 10):")
        sizer_dlg.Add(lbl_info, flag=wx.ALL, border=10)
        
        campos = []
        for i in range(num):
            txt = wx.TextCtrl(dlg_ecus)
            txt.SetName(f"Ecuación {i+1}")
            sizer_dlg.Add(txt, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
            campos.append(txt)
            
        # Paso 3: Selección de Método Dinámica
        lbl_met = wx.StaticText(dlg_ecus, label="Método:")
        sizer_dlg.Add(lbl_met, flag=wx.TOP|wx.LEFT, border=10)
        
        if num == 2:
            # ¡Menú completo para secundaria!
            opciones = [
                "Reducción (Suma y Resta) - Recomendado Colegio",
                "Sustitución - Paso a Paso",
                "Igualación - Paso a Paso",
                "Gauss-Jordan (Matricial)",
                "Regla de Cramer (Determinantes)"
            ]
        else:
            # Solo métodos universitarios para 3x3 o más
            opciones = ["Gauss-Jordan (General)", "Regla de Cramer"]
            
        radio_box = wx.RadioBox(dlg_ecus, choices=opciones, style=wx.RA_SPECIFY_ROWS)
        sizer_dlg.Add(radio_box, flag=wx.EXPAND|wx.ALL, border=10)

        # Botones
        btn_sizer = dlg_ecus.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer_dlg.Add(btn_sizer, flag=wx.ALIGN_CENTER|wx.ALL, border=15)
        
        dlg_ecus.SetSizer(sizer_dlg)
        dlg_ecus.Fit()
        dlg_ecus.Centre()
        
        if dlg_ecus.ShowModal() == wx.ID_OK:
            lista = [c.GetValue() for c in campos if c.GetValue().strip()]
            idx = radio_box.GetSelection()
            
            if len(lista) < num:
                self.show_res("Error: Faltan ecuaciones.")
            else:
                # Lógica de despacho
                try:
                    if num == 2:
                        # Mapeo de índices para menú de 2x2
                        if idx == 0: res = self.operaciones.ResolverSistemaEducativo2x2(lista, "reduccion")
                        elif idx == 1: res = self.operaciones.ResolverSistemaEducativo2x2(lista, "sustitucion")
                        elif idx == 2: res = self.operaciones.ResolverSistemaEducativo2x2(lista, "igualacion")
                        elif idx == 3: res = self.operaciones.ResolverSistemaPasos(lista) # Gauss
                        else: res = self.operaciones.ResolverSistemaCramer(lista)
                    else:
                        # Mapeo para menú de 3x3+
                        if idx == 0: res = self.operaciones.ResolverSistemaPasos(lista)
                        else: res = self.operaciones.ResolverSistemaCramer(lista)
                        
                    self.show_res(res)
                except Exception as e:
                    self.show_res(f"Error: {str(e)}")
        
        dlg_ecus.Destroy()

    # --- DERIVADA ENÉSIMA ---
    def on_abrir_enecima(self, event):
        self.mostrar_controles_avanzados()

    def on_calcular_enecima_accion(self, event):
        expr = self.get_val()
        if not expr:
            self.show_res("Error: Ingrese expresión primero.")
            return
        try:
            orden = int(self.orden_derivada.GetValue())
            var = self.variable_campo.GetValue().strip()
            if orden < 1: 
                self.show_res("Error: El orden debe ser 1 o mayor.")
                return
            res = self.operaciones.Enecima(expr, var, orden)
            self.show_res(res)
        except ValueError:
            self.show_res("Error: El orden debe ser un número entero.")

    # --- AYUDA DE SINTAXIS ---
    def mostrar_ayuda(self, event):
        msg = (
            "GUÍA RÁPIDA DE SÍMBOLOS:\n\n"
            "Operaciones Básicas:\n"
            "  + Suma, - Resta\n"
            "  * Multiplicación (ej: 3*x)\n"
            "  / División\n"
            "  ** Potencia (ej: x**2 es x al cuadrado)\n\n"
            "Funciones Comunes:\n"
            "  sqrt(x) : Raíz cuadrada\n"
            "  log(x)  : Logaritmo base 10\n"
            "  ln(x)   : Logaritmo natural\n"
            "  sin(x), cos(x), tan(x) : Trigonometría\n\n"
            "Constantes:\n"
            "  pi : Valor de Pi\n"
            "  e  : Valor de Euler\n"
            "  oo : Infinito (para límites)\n\n"
            "Consejo para NVDA:\n"
            "  Use Tab para moverse entre los campos.\n"
            "  Pulse F1 para volver a ver esta ayuda."
        )
        wx.MessageBox(msg, "Ayuda de Sintaxis y Comandos", wx.OK | wx.ICON_INFORMATION)