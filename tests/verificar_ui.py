"""
Verificación automática de la interfaz (abre la ventana real unos 10 segundos).

No forma parte de la suite de pytest porque necesita escritorio. Ejecútela a mano
tras cambiar main.py:

    python -X utf8 tests/verificar_ui.py

Comprueba: cálculos rápidos y lentos en segundo plano, el diálogo "Calculando",
la cancelación, errores inesperados del hilo, los menús y la ayuda (F1).
wx.MessageBox se sustituye por un registro para que ningún diálogo modal bloquee.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wx
mensajes = []
wx.MessageBox = lambda msg, *a, **k: mensajes.append(msg)
import main
app = wx.App()
f = main.CalculadoraAccesible(); f.Show()
resultados = []
def check(nombre, cond): resultados.append((nombre, bool(cond)))

def paso1():  # rápido: sin diálogo de progreso
    f.input_text.SetValue("2+2"); f.on_evaluar_inteligente(None)
    wx.CallLater(300, lambda: (check("rápido: resultado", f.output_text.GetValue() == "RESULTADO: 4"),
                               check("rápido: sin diálogo", f._dlg_progreso is None),
                               check("rápido: libre", f._calculo_actual is None), paso2()))

def paso2():  # lento: aparece diálogo y luego resultado
    orig = f.core.Evaluar
    f.core.Evaluar = lambda t: (time.sleep(2), "RESULTADO: lento")[1]
    f.input_text.SetValue("1+1"); f.on_evaluar_inteligente(None)
    def durante():
        check("lento: diálogo visible", f._dlg_progreso is not None)
        check("lento: info dice calculando", f.lbl_info.GetValue().startswith("Calculando"))
        f.input_text.SetValue("3+3"); f.on_simplificar(None)  # debe rechazarse
        check("lento: rechaza segundo cálculo", any("en curso" in m for m in mensajes))
    def despues():
        check("lento: resultado", f.output_text.GetValue() == "RESULTADO: lento")
        check("lento: diálogo cerrado", f._dlg_progreso is None)
        f.core.Evaluar = orig; paso3()
    wx.CallLater(1000, durante); wx.CallLater(3000, despues)

def paso3():  # cancelar: el resultado tardío se ignora
    orig = f.core.Evaluar
    f.core.Evaluar = lambda t: (time.sleep(2), "RESULTADO: NO DEBE APARECER")[1]
    f.output_text.SetValue("previo"); f.input_text.SetValue("5"); f.on_evaluar_inteligente(None)
    wx.CallLater(1000, f._cancelar_calculo)
    def despues():
        check("cancelar: resultado ignorado", f.output_text.GetValue() == "previo")
        check("cancelar: libre", f._calculo_actual is None and f._dlg_progreso is None)
        check("cancelar: info", f.lbl_info.GetValue().startswith("Cálculo cancelado"))
        f.core.Evaluar = orig; paso4()
    wx.CallLater(3200, despues)

def paso4():  # excepción inesperada en el hilo -> error, sin colgarse
    orig = f.core.Factorizar
    f.core.Factorizar = lambda t: 1/0
    f.input_text.SetValue("x"); n = len(mensajes); f.on_factorizar(None)
    def despues():
        check("excepción: se muestra como error", any("Error inesperado" in m for m in mensajes[n:]))
        check("excepción: libre", f._calculo_actual is None)
        f.core.Factorizar = orig; paso5()
    wx.CallLater(400, despues)

def paso5():  # menú y sistemas clásicos
    mb = f.GetMenuBar(); alg = mb.GetMenu(mb.FindMenu("Álgebra"))
    labels = [i.GetItemLabelText() for i in alg.GetMenuItems()]
    check("menú: submenú clásicos", any("método clásico" in l for l in labels))
    sub = [i for i in alg.GetMenuItems() if i.IsSubMenu()][0].GetSubMenu()
    check("menú: 3 métodos", [i.GetItemLabelText() for i in sub.GetMenuItems()] == ["Sustitución", "Igualación", "Reducción"])
    check("menú: Gauss con Ctrl+G", any("Gauss" in i.GetItemLabel() and "Ctrl+G" in i.GetItemLabel() for i in alg.GetMenuItems()))
    f.input_text.SetValue("x + y = 10\nx - y = 2"); f.on_sistema_clasico("igualacion", "igualación")
    def despues():
        out = f.output_text.GetValue()
        check("clásico: igualación resuelve", "RESOLUCIÓN POR IGUALACION" in out and out.rstrip().endswith("y = 4"))
        f.input_text.SetValue("x*y^2"); f._resolver_ambiguedad_variable = lambda t, o: "y"
        f.on_derivar(None)
        wx.CallLater(500, fin)
    wx.CallLater(800, despues)

def fin():
    check("derivar vía fachada con variable elegida", f.output_text.GetValue().startswith("RESULTADO: 2*x*y"))
    f.mostrar_ayuda(None)
    check("ayuda: menciona Ctrl+G y 2x", "Ctrl + G" in f.output_text.GetValue() and "x*sin(x)" in f.output_text.GetValue())
    for n, ok in resultados: print(("OK  " if ok else "FAIL"), n)
    fallos = sum(not ok for _, ok in resultados)
    print(f"\n{len(resultados) - fallos}/{len(resultados)} comprobaciones correctas")
    app.codigo_salida = 1 if fallos else 0
    f.Destroy(); app.ExitMainLoop()

wx.CallLater(200, paso1)
app.codigo_salida = 1
wx.CallLater(20000, lambda: (print("TIEMPO AGOTADO"), app.ExitMainLoop()))
app.MainLoop()
sys.exit(app.codigo_salida)
