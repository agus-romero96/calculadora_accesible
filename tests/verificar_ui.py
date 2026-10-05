"""
Verificación automática de la interfaz (abre la ventana real unos 15 segundos).

No forma parte de la suite de pytest porque necesita escritorio. Ejecútela a mano
tras cambiar main.py:

    python -X utf8 tests/verificar_ui.py

Comprueba: cálculos rápidos y lentos en segundo plano, el diálogo "Calculando",
la cancelación, errores inesperados del hilo, los menús, copiar al portapapeles,
exportar, el cambio de idioma y la ayuda (F1).
wx.MessageBox y el diálogo de guardar se sustituyen para que nada modal bloquee, y
el cambio de idioma no se guarda (no altera la preferencia del usuario).
"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wx
mensajes = []
wx.MessageBox = lambda msg, *a, **k: mensajes.append(msg)
import i18n
i18n.guardar_idioma = lambda codigo: None
i18n.establecer_idioma("es")
import main
from puente import ResultadoOperacion

app = wx.App()
f = main.CalculadoraAccesible(); f.Show()
resultados = []
carpeta_tmp = tempfile.mkdtemp()


def check(nombre, cond): resultados.append((nombre, bool(cond)))


def falso(texto, segundos=0):
    """Sustituto de una operación del núcleo que tarda 'segundos' y devuelve 'texto'."""
    return lambda *a: (time.sleep(segundos), ResultadoOperacion(operacion="evaluar", entrada="", texto=texto))[1]


def portapapeles():
    # Igual que al copiar: el portapapeles de Windows puede estar ocupado un instante
    for _ in range(10):
        datos = wx.TextDataObject()
        if wx.TheClipboard.Open():
            leido = wx.TheClipboard.GetData(datos)
            wx.TheClipboard.Close()
            if leido:
                return datos.GetText()
        time.sleep(0.05)
    return None


def paso1():  # rápido: sin diálogo de progreso
    f.input_text.SetValue("2+2"); f.on_evaluar_inteligente(None)
    wx.CallLater(300, lambda: (check("rápido: resultado", f.output_text.GetValue() == "RESULTADO: 4"),
                               check("rápido: sin diálogo", f._dlg_progreso is None),
                               check("rápido: libre", f._calculo_actual is None), paso2()))


def paso2():  # lento: aparece diálogo y luego resultado
    orig = f.core.evaluar
    f.core.evaluar = falso("RESULTADO: lento", 2)
    f.input_text.SetValue("1+1"); f.on_evaluar_inteligente(None)
    def durante():
        check("lento: diálogo visible", f._dlg_progreso is not None)
        check("lento: info dice calculando", f.lbl_info.GetValue().startswith("Calculando"))
        f.input_text.SetValue("3+3"); f.on_simplificar(None)  # debe rechazarse
        check("lento: rechaza segundo cálculo", any("en curso" in m for m in mensajes))
    def despues():
        check("lento: resultado", f.output_text.GetValue() == "RESULTADO: lento")
        check("lento: diálogo cerrado", f._dlg_progreso is None)
        f.core.evaluar = orig; paso3()
    wx.CallLater(1000, durante); wx.CallLater(3000, despues)


def paso3():  # cancelar: el resultado tardío se ignora
    orig = f.core.evaluar
    f.core.evaluar = falso("RESULTADO: NO DEBE APARECER", 2)
    f.output_text.SetValue("previo"); f.input_text.SetValue("5"); f.on_evaluar_inteligente(None)
    wx.CallLater(1000, f._cancelar_calculo)
    def despues():
        check("cancelar: resultado ignorado", f.output_text.GetValue() == "previo")
        check("cancelar: libre", f._calculo_actual is None and f._dlg_progreso is None)
        check("cancelar: info", f.lbl_info.GetValue().startswith("Cálculo cancelado"))
        f.core.evaluar = orig; paso4()
    wx.CallLater(3200, despues)


def paso4():  # excepción inesperada en el hilo -> error, sin colgarse
    orig = f.core.factorizar
    f.core.factorizar = lambda t: 1 / 0
    f.input_text.SetValue("x"); n = len(mensajes); f.on_factorizar(None)
    def despues():
        check("excepción: se muestra como error", any("Error inesperado" in m for m in mensajes[n:]))
        check("excepción: libre", f._calculo_actual is None)
        f.core.factorizar = orig; paso5()
    wx.CallLater(400, despues)


def paso5():  # menú y sistemas clásicos
    mb = f.GetMenuBar(); alg = mb.GetMenu(mb.FindMenu("Álgebra"))
    labels = [i.GetItemLabelText() for i in alg.GetMenuItems()]
    check("menú: submenú clásicos", any("método clásico" in l for l in labels))
    sub = [i for i in alg.GetMenuItems() if i.IsSubMenu()][0].GetSubMenu()
    check("menú: 3 métodos", [i.GetItemLabelText() for i in sub.GetMenuItems()] == ["Sustitución", "Igualación", "Reducción"])
    check("menú: Gauss con Ctrl+G", any("Gauss" in i.GetItemLabel() and "Ctrl+G" in i.GetItemLabel() for i in alg.GetMenuItems()))
    check("menú: Resultado e Idioma", mb.FindMenu("Resultado") != wx.NOT_FOUND and mb.FindMenu("Idioma / Language") != wx.NOT_FOUND)
    f.input_text.SetValue("x + y = 10\nx - y = 2"); f.on_sistema_clasico("igualacion", "igualación")
    def despues():
        out = f.output_text.GetValue()
        check("clásico: igualación resuelve", "RESOLUCIÓN POR IGUALACIÓN" in out and out.rstrip().endswith("y = 4"))
        paso6()
    wx.CallLater(800, despues)


def paso6():  # copiar al portapapeles
    n = len(mensajes)
    f.on_copiar_resultado(None)
    check("copiar: resultado en portapapeles", portapapeles() == "x = 6, y = 4")
    check("copiar: confirma con diálogo", any("Copiado" in m for m in mensajes[n:]))
    f.on_copiar_latex(None)
    check("copiar: LaTeX", portapapeles().startswith(r"\begin{cases}"))
    f.on_copiar_mathml(None)
    check("copiar: MathML", portapapeles().startswith("<math"))
    f.on_copiar_explicacion(None)
    check("copiar: explicación", portapapeles().startswith("RESOLUCIÓN POR IGUALACIÓN"))
    paso7()


class DialogoGuardarFalso:
    """Sustituye a wx.FileDialog: 'elige' una ruta sin extensión y un formato."""
    indice = 0
    def __init__(self, *a, **k): pass
    def ShowModal(self): return wx.ID_OK
    def GetFilterIndex(self): return DialogoGuardarFalso.indice
    def GetPath(self): return os.path.join(carpeta_tmp, "exportado")
    def Destroy(self): pass


def paso7():  # exportar (HTML = primer formato, JSON = último)
    original = wx.FileDialog
    wx.FileDialog = DialogoGuardarFalso
    try:
        DialogoGuardarFalso.indice = 0
        f.on_exportar(None)
        ruta_html = os.path.join(carpeta_tmp, "exportado.html")
        check("exportar: HTML con extensión añadida", os.path.exists(ruta_html))
        check("exportar: HTML con MathML", "<math" in open(ruta_html, encoding="utf-8").read())
        DialogoGuardarFalso.indice = list(main.exportar.FORMATOS).index("json")
        f.on_exportar(None)
        datos = json.load(open(os.path.join(carpeta_tmp, "exportado.json"), encoding="utf-8"))
        check("exportar: JSON", datos["result"]["text"] == "x = 6, y = 4")
    finally:
        wx.FileDialog = original
    f.on_limpiar(None)
    n = len(mensajes)
    f.on_copiar_resultado(None)
    check("sin resultado: avisa", any("no hay un resultado" in m for m in mensajes[n:]))
    paso8()


def paso8():  # derivar con variable elegida
    original = f._resolver_ambiguedad_variable
    f._resolver_ambiguedad_variable = lambda t, o: "y"
    f.input_text.SetValue("x*y^2")
    f.on_derivar(None)
    f._resolver_ambiguedad_variable = original  # la derivada ya pidió la variable
    wx.CallLater(500, paso9)


def paso9():  # cambio de idioma
    check("derivar vía fachada con variable elegida", f.output_text.GetValue().startswith("RESULTADO: 2*x*y"))
    f.mostrar_ayuda(None)
    check("ayuda: menciona Ctrl+G y 2x", "Ctrl + G" in f.output_text.GetValue() and "x*sin(x)" in f.output_text.GetValue())
    f.on_idioma("en")
    mb = f.GetMenuBar()
    check("inglés: menús traducidos", mb.FindMenu("Calculus") != wx.NOT_FOUND and mb.FindMenu("Result") != wx.NOT_FOUND)
    check("inglés: etiquetas traducidas", f.btn_calc.GetLabel() == "&Calculate (Ctrl+Enter)")
    check("inglés: radio marcado", any(i.IsChecked() and i.GetItemLabelText() == "English"
                                       for i in mb.GetMenu(mb.FindMenu("Language / Idioma")).GetMenuItems()))
    f.input_text.SetValue("x^3"); f.on_derivar(None)
    def despues():
        check("inglés: resultado traducido", f.output_text.GetValue().startswith("RESULT: 3*x**2"))
        f.mostrar_ayuda(None)
        check("inglés: ayuda en inglés", f.output_text.GetValue().startswith("USER MANUAL"))
        f.on_idioma("es")
        check("vuelta a español", f.GetMenuBar().FindMenu("Cálculo") != wx.NOT_FOUND
              and f.lbl_info.GetValue().startswith("Escriba"))
        fin()
    wx.CallLater(500, despues)


def fin():
    for n, ok in resultados: print(("OK  " if ok else "FAIL"), n)
    fallos = sum(not ok for _, ok in resultados)
    print(f"\n{len(resultados) - fallos}/{len(resultados)} comprobaciones correctas")
    app.codigo_salida = 1 if fallos else 0
    f.Close()  # como el usuario: al cerrar la última ventana termina el bucle de eventos


wx.CallLater(200, paso1)
app.codigo_salida = 1
wx.CallLater(30000, lambda: (print("TIEMPO AGOTADO"), app.ExitMainLoop()))
app.MainLoop()
sys.exit(app.codigo_salida)
