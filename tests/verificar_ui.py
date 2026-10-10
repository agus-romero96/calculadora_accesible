"""
Verificación automática de la interfaz (abre la ventana real unos 15 segundos).

No forma parte de la suite de pytest porque necesita escritorio. Ejecútela a mano
tras cambiar main.py:

    python -X utf8 tests/verificar_ui.py

Comprueba: cálculos rápidos y lentos en el proceso de cálculo, el diálogo
"Calculando", la cancelación (que detiene de verdad el proceso), errores
inesperados del cálculo, los menús, copiar al portapapeles, exportar, el cambio
de idioma, la ayuda (F1), que cada operación del registro (puente.REGISTRO) pide
sus datos y llama a su método, y que al cerrar la ventana termina el proceso de cálculo.
wx.MessageBox y el diálogo de guardar se sustituyen para que nada modal bloquee, y
el cambio de idioma no se guarda (no altera la preferencia del usuario). El
historial se guarda en una carpeta temporal, no en el del usuario.

El núcleo es tests/nucleo_pruebas.py: el cálculo ocurre en otro proceso, así que
los casos lentos o con error se piden con la entrada ("dormir 2", "fallar").
Todo el arranque está bajo  if __name__ == "__main__": el proceso de cálculo
vuelve a importar este archivo y no debe abrir otra ventana.
"""
import json
import os
import sys
import tempfile
import time

CARPETA_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(CARPETA_TESTS))
sys.path.insert(0, CARPETA_TESTS)

resultados = []
mensajes = []


def check(nombre, cond): resultados.append((nombre, bool(cond)))


def cuando_libre(siguiente, limite=15):
    """Llama a siguiente() cuando termina el cálculo en curso (sin depender de cuánto tarda)."""
    inicio = time.monotonic()
    def comprobar():
        if f._calculo_actual is None or time.monotonic() - inicio > limite:
            siguiente()
        else:
            wx.CallLater(100, comprobar)
    wx.CallLater(100, comprobar)


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
    f.proceso.calcular("evaluar", "1")  # espera a que el proceso de cálculo termine de arrancar
    f.input_text.SetValue("2+2"); f.on_evaluar_inteligente(None)
    wx.CallLater(300, lambda: (check("rápido: resultado", f.output_text.GetValue() == "RESULTADO: 4"),
                               check("rápido: sin diálogo", f._dlg_progreso is None),
                               check("rápido: libre", f._calculo_actual is None), paso2()))


def paso2():  # lento: aparece diálogo y luego resultado
    f.input_text.SetValue("dormir 2"); f.on_evaluar_inteligente(None)
    def durante():
        check("lento: diálogo visible", f._dlg_progreso is not None)
        check("lento: info dice calculando", f.lbl_info.GetValue().startswith("Calculando"))
        f.input_text.SetValue("3+3"); f.on_operacion("simplificar")  # debe rechazarse
        check("lento: rechaza segundo cálculo", any("en curso" in m for m in mensajes))
    def despues():
        check("lento: resultado", f.output_text.GetValue() == "RESULTADO: lento")
        check("lento: diálogo cerrado", f._dlg_progreso is None)
        paso3()
    wx.CallLater(1000, durante); wx.CallLater(3000, despues)


def paso3():  # cancelar: se detiene el proceso que calculaba
    calculando = f.proceso._proceso
    f.output_text.SetValue("previo"); f.input_text.SetValue("dormir 30"); f.on_evaluar_inteligente(None)
    def cancelar():
        check("cancelar: diálogo visible", f._dlg_progreso is not None)
        f._cancelar_calculo()
        check("cancelar: el proceso que calculaba ya no existe", not calculando.is_alive())
        check("cancelar: otro proceso listo", f.proceso.esta_vivo() and f.proceso.pid != calculando.pid)
    def despues():
        check("cancelar: resultado ignorado", f.output_text.GetValue() == "previo")
        check("cancelar: libre", f._calculo_actual is None and f._dlg_progreso is None)
        check("cancelar: info", f.lbl_info.GetValue().startswith("Cálculo cancelado"))
        paso4()
    wx.CallLater(1000, cancelar); wx.CallLater(1500, despues)


def paso4():  # excepción inesperada en el cálculo -> error, sin colgarse
    f.input_text.SetValue("fallar"); n = len(mensajes); f.on_operacion("factorizar")
    def despues():
        check("excepción: se muestra como error", any("Error inesperado" in m for m in mensajes[n:]))
        check("excepción: libre", f._calculo_actual is None)
        paso5()
    cuando_libre(despues)


def paso5():  # menú y sistemas clásicos
    mb = f.GetMenuBar(); alg = mb.GetMenu(mb.FindMenu("Álgebra"))
    labels = [i.GetItemLabelText() for i in alg.GetMenuItems()]
    check("menú: submenú clásicos", any("método clásico" in l for l in labels))
    sub = [i for i in alg.GetMenuItems() if i.IsSubMenu()][0].GetSubMenu()
    check("menú: 3 métodos", [i.GetItemLabelText() for i in sub.GetMenuItems()] == ["Sustitución", "Igualación", "Reducción"])
    check("menú: Gauss con Ctrl+G", any("Gauss" in i.GetItemLabel() and "Ctrl+G" in i.GetItemLabel() for i in alg.GetMenuItems()))
    check("menú: Resultado e Idioma", mb.FindMenu("Resultado") != wx.NOT_FOUND and mb.FindMenu("Idioma / Language") != wx.NOT_FOUND)
    f.input_text.SetValue("x + y = 10\nx - y = 2"); f.on_operacion("sistema_clasico", "igualacion")
    def despues():
        out = f.output_text.GetValue()
        check("clásico: igualación resuelve", "RESOLUCIÓN POR IGUALACIÓN" in out and out.rstrip().endswith("y = 4"))
        paso6()
    cuando_libre(despues)


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
    f.on_operacion("derivar")
    f._resolver_ambiguedad_variable = original  # la derivada ya pidió la variable
    cuando_libre(paso9)


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
    f.input_text.SetValue("x^3"); f.on_operacion("derivar")
    def despues():
        check("inglés: resultado traducido", f.output_text.GetValue().startswith("RESULT: 3*x**2"))
        f.mostrar_ayuda(None)
        check("inglés: ayuda en inglés", f.output_text.GetValue().startswith("USER MANUAL"))
        f.on_idioma("es")
        check("vuelta a español", f.GetMenuBar().FindMenu("Cálculo") != wx.NOT_FOUND
              and f.lbl_info.GetValue().startswith("Escriba"))
        paso10()
    cuando_libre(despues)


def paso10():  # historial
    import ventana_historial
    entradas = f.historial.entradas()
    check("historial: guarda los cálculos correctos (no los errores)",
          len(entradas) >= 4 and not any(r.es_error for r in entradas))
    check("historial: menú Historial", f.GetMenuBar().FindMenu("Historial") != wx.NOT_FOUND)

    # El diálogo (sin mostrarlo): lista, la más reciente primero, y Suprimir
    dlg = ventana_historial.DialogoHistorial(f, f.historial)
    lineas = dlg.lista.GetStrings()
    check("historial: lista con la más reciente primero",
          len(lineas) == len(entradas) and lineas[0].startswith(f"{len(entradas)}. Derivada: x^3"))
    check("historial: primera fila seleccionada", dlg.lista.GetSelection() == 0)
    evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    evento.SetKeyCode(wx.WXK_DELETE)
    dlg._on_tecla(evento)
    check("historial: Suprimir elimina", len(f.historial) == len(entradas) - 1)
    dlg.Destroy()

    # Mostrar y Usar entrada desde la ventana principal (ShowModal simulado)
    original = ventana_historial.DialogoHistorial.ShowModal
    gauss = next(r for r in f.historial.entradas() if r.operacion == "sistema_clasico")

    def elegir(accion):
        def mostrar_modal(self):
            self.accion, self.elegido = accion, gauss
            return wx.ID_OK
        return mostrar_modal

    try:
        ventana_historial.DialogoHistorial.ShowModal = elegir(ventana_historial.MOSTRAR)
        f.on_ver_historial(None)
        check("historial: Mostrar vuelve a mostrar el resultado",
              f.output_text.GetValue() == gauss.texto and f.ultimo_resultado is gauss)
        cantidad = len(f.historial)
        f.on_copiar_resultado(None)
        check("historial: el resultado mostrado se puede copiar", portapapeles() == "x = 6, y = 4")
        check("historial: Mostrar no duplica la entrada", len(f.historial) == cantidad)
        ventana_historial.DialogoHistorial.ShowModal = elegir(ventana_historial.USAR_ENTRADA)
        f.on_ver_historial(None)
        check("historial: Usar entrada", f.input_text.GetValue() == "x + y = 10\nx - y = 2")
    finally:
        ventana_historial.DialogoHistorial.ShowModal = original

    # Exportar el historial completo
    original_dlg = wx.FileDialog
    wx.FileDialog = DialogoGuardarFalso
    try:
        DialogoGuardarFalso.indice = list(main.exportar.FORMATOS).index("json")
        f.on_exportar_historial(None)
        datos = json.load(open(os.path.join(carpeta_tmp, "exportado.json"), encoding="utf-8"))
        check("historial: exportar todo", len(datos["entries"]) == len(f.historial))
    finally:
        wx.FileDialog = original_dlg

    # Se guarda en disco: al abrir de nuevo la calculadora vuelve el mismo historial
    guardado = main.Historial(main.ruta_historial()).entradas()
    check("historial: se conserva al volver a abrir",
          main.ruta_historial().startswith(carpeta_appdata)
          and [r.entrada for r in guardado] == [r.entrada for r in f.historial.entradas()])
    paso11()


def paso11():  # cada operación del registro pide sus datos y llama a su método
    from puente import REGISTRO
    sistema = "x + y = 10\nx - y = 2"
    # clave: (entrada, respuestas a los diálogos, variante del submenú, (método, argumentos, descripción))
    casos = {
        "evaluar": ("5x^3", [], None, ("evaluar", ("5x^3",), "la evaluación")),
        "simplificar": ("5x^3", [], None, ("simplificar", ("5x^3",), "la simplificación")),
        "factorizar": ("5x^3", [], None, ("factorizar", ("5x^3",), "la factorización")),
        "derivar": ("5x^3", [], None, ("derivar", ("5x^3", None), "la derivada")),
        "derivada_n": ("5x^3", ["x", "3"], None, ("derivada_enecima", ("5x^3", "x", 3), "la derivada de orden 3")),
        # Integrar una constante: pide la variable
        "integrar": ("5", ["t"], None, ("integrar", ("5", "t"), "la integral")),
        "limite": ("sin(x)/x", ["x", "0"], None, ("limite", ("sin(x)/x", "x", "0"), "el límite")),
        "gauss": (sistema, [], None, ("sistema_gauss", (sistema.split("\n"),), "el sistema por Gauss-Jordan")),
        "sistema_clasico": (sistema, [], "reduccion",
                            ("sistema_clasico", (sistema.split("\n"), "reduccion"), "el sistema por reducción")),
        "inversa": ("1 2\n3 4", [], None, ("inversa", ("1 2\n3 4",), "la matriz inversa")),
    }
    check("registro: cada operación tiene caso", set(casos) == {op.clave for op in REGISTRO})
    llamadas = []
    original_ejecutar, original_pedir = f._ejecutar, f._pedir_texto
    f._ejecutar = lambda metodo, args, descripcion: llamadas.append((metodo, args, descripcion))
    try:
        for op in REGISTRO:
            if op.clave not in casos:
                continue
            entrada, respuestas, variante, esperado = casos[op.clave]
            pendientes = list(respuestas)
            f._pedir_texto = lambda *a, **k: pendientes.pop(0)
            f.input_text.SetValue(entrada)
            llamadas.clear()
            f.on_operacion(op.clave, variante)
            check(f"registro: {op.clave}", llamadas == [esperado] and not pendientes)
        # Cancelar el diálogo de la variable no calcula nada
        f._pedir_texto = lambda *a, **k: None
        f.input_text.SetValue("5"); llamadas.clear(); f.on_operacion("integrar")
        check("registro: cancelar un diálogo no calcula", llamadas == [])
    finally:
        f._ejecutar, f._pedir_texto = original_ejecutar, original_pedir
    fin()


def fin():
    calculando = f.proceso._proceso
    f.Close()  # como el usuario: al cerrar la última ventana termina el bucle de eventos
    check("cerrar: termina el proceso de cálculo", not calculando.is_alive())
    for n, ok in resultados: print(("OK  " if ok else "FAIL"), n)
    fallos = sum(not ok for _, ok in resultados)
    print(f"\n{len(resultados) - fallos}/{len(resultados)} comprobaciones correctas")
    app.codigo_salida = 1 if fallos else 0


if __name__ == "__main__":
    # El historial se guarda junto a la configuración: una carpeta temporal en lugar de la del usuario
    carpeta_appdata = tempfile.mkdtemp()
    os.environ["APPDATA"] = carpeta_appdata
    # Se comparan los textos del código, no los de locales/es.json (editable)
    os.environ["CALCULADORA_TEXTOS_ORIGEN"] = "1"
    import wx
    wx.MessageBox = lambda msg, *a, **k: mensajes.append(msg)
    import i18n
    i18n.guardar_idioma = lambda codigo: None
    i18n.establecer_idioma("es")
    import main
    from nucleo_pruebas import NucleoPruebas

    app = wx.App()
    f = main.CalculadoraAccesible(nucleo=NucleoPruebas); f.Show()
    carpeta_tmp = tempfile.mkdtemp()

    wx.CallLater(200, paso1)
    app.codigo_salida = 1
    wx.CallLater(60000, lambda: (print("TIEMPO AGOTADO"), app.ExitMainLoop()))
    app.MainLoop()
    sys.exit(app.codigo_salida)
