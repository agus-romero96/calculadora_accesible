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
    # (hasta 2 s). Si no se puede leer, "" hace fallar la comprobación sin cortar los pasos.
    for _ in range(40):
        datos = wx.TextDataObject()
        if wx.TheClipboard.Open():
            leido = wx.TheClipboard.GetData(datos)
            wx.TheClipboard.Close()
            if leido:
                return datos.GetText()
        time.sleep(0.05)
    return ""


def paso1():  # rápido: sin diálogo de progreso
    f.proceso.calcular("evaluar", "1")  # espera a que el proceso de cálculo termine de arrancar
    f.input_text.SetValue("2+2"); f.on_evaluar_inteligente(None)
    wx.CallLater(300, lambda: (check("rápido: resultado", f.output_text.GetValue().splitlines()[0] == "RESULTADO: 4"),
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
        check("clásico: igualación resuelve", out.splitlines()[:3] == ["RESULTADO:", "x = 6", "y = 4"]
              and "MÉTODO: Igualación" in out)
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
    check("copiar: explicación", portapapeles().startswith("RESULTADO:") and "MÉTODO: Igualación" in portapapeles())
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
        "integral_definida": ("x^2", ["0", "oo"], None,
                              ("integral_definida", ("x^2", None, "0", "oo"), "la integral definida")),
        "limite": ("sin(x)/x", ["x", "0"], None, ("limite", ("sin(x)/x", "x", "0"), "el límite")),
        "tangente": ("x^3 - 2x", ["1"], None, ("recta_tangente", ("x^3 - 2x", None, "1"), "la recta tangente")),
        "extremos": ("x^3 - 3x", [], None, ("extremos", ("x^3 - 3x", None), "el estudio de extremos")),
        "implicita": ("x^2 + y^2 = 25", [], None,
                      ("derivada_implicita", ("x^2 + y^2 = 25",), "la derivada implícita")),
        "edo": ("y' = 2*x*y", [], None,
                ("ecuacion_diferencial", ("y' = 2*x*y",), "la ecuación diferencial")),
        "taylor": ("exp(x)", ["3", "0"], None,
                   ("taylor", ("exp(x)", None, 3, "0"), "el polinomio de Taylor de orden 3")),
        "ecuacion": ("x^2 - 4 <= 0", [], None, ("ecuacion", ("x^2 - 4 <= 0",), "la ecuación")),
        "gauss": (sistema, [], None, ("sistema_gauss", (sistema.split("\n"),), "el sistema por Gauss-Jordan")),
        "sistema_clasico": (sistema, [], "reduccion",
                            ("sistema_clasico", (sistema.split("\n"), "reduccion"), "el sistema por reducción")),
        "inversa": ("1 2\n3 4", [], None, ("inversa", ("1 2\n3 4",), "la matriz inversa")),
        "determinante": ("1 2\n3 4", [], None, ("determinante", ("1 2\n3 4",), "el determinante")),
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
        # Ctrl+Enter con una sola línea con =, < o > resuelve la ecuación o inecuación
        f.input_text.SetValue("2*x + 1 > 7"); llamadas.clear(); f.on_evaluar_inteligente(None)
        check("Ctrl+Enter: una inecuación se resuelve",
              llamadas == [("ecuacion", ("2*x + 1 > 7",), "la ecuación")])
        f.input_text.SetValue("x + y = 10\nx - y = 2"); llamadas.clear(); f.on_evaluar_inteligente(None)
        check("Ctrl+Enter: varias líneas siguen siendo un sistema", llamadas[0][0] == "sistema_gauss")
    finally:
        f._ejecutar, f._pedir_texto = original_ejecutar, original_pedir
    paso12()


def paso12():  # opción "Mostrar el paso a paso" (Ctrl+Shift+P)
    import configuracion
    mb = f.GetMenuBar()
    opciones = mb.GetMenu(mb.FindMenu("Opciones"))
    casilla = opciones.GetMenuItems()[0]
    check("modo: menú Opciones con la casilla marcada",
          casilla.IsCheckable() and casilla.IsChecked() and "Ctrl+Shift+P" in casilla.GetItemLabel())
    f.input_text.SetValue("x^2*sin(x)"); f.on_operacion("derivar")

    def despues():
        res = f.ultimo_resultado
        check("modo: por defecto, paso a paso", f.output_text.GetValue() == res.texto)
        f.on_modo_respuesta(None)
        check("modo: solo el resultado vuelve a mostrar el actual", f.output_text.GetValue() == main.exportar.resumen(res))
        check("modo: se guarda", configuracion.leer(configuracion.MODO_RESPUESTA) == "resultado")
        mb = f.GetMenuBar()
        check("modo: la casilla se desmarca",
              not mb.GetMenu(mb.FindMenu("Opciones")).GetMenuItems()[0].IsChecked())
        f.input_text.SetValue("x^3"); f.on_operacion("derivar")
        cuando_libre(despues_nuevo)

    def despues_nuevo():
        check("modo: un cálculo nuevo sale sin el paso a paso",
              f.output_text.GetValue().splitlines() == ["RESULTADO: 3*x**2", "Operación: Derivada",
                                                       "Entrada: x^3", "Variable: x"])
        check("modo: el historial guarda la explicación completa", f.historial.entradas()[-1].texto.count("\n") > 5)
        f.on_copiar_explicacion(None)
        check("modo: Copiar explicación sigue copiando el paso a paso", portapapeles() == f.ultimo_resultado.texto)
        f.on_modo_respuesta(None)
        check("modo: vuelve al paso a paso", f.output_text.GetValue() == f.ultimo_resultado.texto
              and configuracion.leer(configuracion.MODO_RESPUESTA) == "pasos")
        f.on_limpiar(None)
        n = len(mensajes)
        f.on_modo_respuesta(None)
        check("modo: sin resultado, lo confirma con un diálogo", any("solo el resultado" in m for m in mensajes[n:]))
        f.on_modo_respuesta(None)
        paso13()

    cuando_libre(despues)


def esperar(condicion, siguiente, limite=10):
    """Llama a siguiente() cuando se cumple condicion() (o se agota el límite)."""
    inicio = time.monotonic()
    def comprobar():
        if condicion() or time.monotonic() - inicio > limite:
            siguiente()
        else:
            wx.CallLater(50, comprobar)
    wx.CallLater(50, comprobar)


class DialogoMensajeFalso:
    """Sustituye a wx.MessageDialog: guarda el mensaje y 'pulsa' el botón de respuesta."""
    respuesta = None
    mensajes = []
    def __init__(self, padre, mensaje, *a, **k): DialogoMensajeFalso.mensajes.append(mensaje)
    def SetYesNoCancelLabels(self, *etiquetas): self.etiquetas = etiquetas
    def ShowModal(self): return DialogoMensajeFalso.respuesta
    def Destroy(self): pass


def paso13():  # actualizaciones: buscar, ofrecer, omitir, descargar e instalar (red simulada)
    import actualizador
    import configuracion
    mb = f.GetMenuBar()
    casilla = mb.GetMenu(mb.FindMenu("Opciones")).GetMenuItems()[1]
    check("actualizar: casilla 'al iniciar' marcada por defecto",
          casilla.IsCheckable() and casilla.IsChecked() and "actualizaciones" in casilla.GetItemLabelText())
    check("actualizar: opción en el menú Ayuda", any("actualizaciones" in i.GetItemLabelText()
                                                    for i in mb.GetMenu(mb.FindMenu("Ayuda")).GetMenuItems()))
    f.on_buscar_al_iniciar(None)
    check("actualizar: desmarcar 'al iniciar' se guarda",
          configuracion.leer(configuracion.BUSCAR_ACTUALIZACIONES) is False
          and not f.GetMenuBar().GetMenu(f.GetMenuBar().FindMenu("Opciones")).GetMenuItems()[1].IsChecked())
    f.on_buscar_al_iniciar(None)

    nueva = actualizador.Actualizacion("9.0.0", "- Novedad de prueba", "https://ejemplo/v9.0.0",
                                       url_instalador="https://ejemplo/setup.exe",
                                       nombre_instalador="setup.exe", tamano=4 * 1048576)
    respuestas = {"buscar": None}
    llamadas = []

    def buscar():
        if isinstance(respuestas["buscar"], Exception):
            raise respuestas["buscar"]
        return respuestas["buscar"]

    def descargar(act, progreso):
        for i in range(1, 5):
            time.sleep(0.15)
            if not progreso(i * 1048576, act.tamano):
                raise actualizador.DescargaCancelada()
        return os.path.join(carpeta_tmp, "setup.exe")

    originales = (actualizador.buscar_actualizacion, actualizador.descargar, actualizador.instalar,
                  main.es_instalada, wx.MessageDialog)
    actualizador.buscar_actualizacion = buscar
    actualizador.descargar = descargar
    actualizador.instalar = lambda ruta: llamadas.append(("instalar", ruta))
    main.es_instalada = lambda: True
    wx.MessageDialog = DialogoMensajeFalso
    f.Close = lambda *a: llamadas.append(("cerrar",))

    def restaurar():
        (actualizador.buscar_actualizacion, actualizador.descargar, actualizador.instalar,
         main.es_instalada, wx.MessageDialog) = originales
        del f.Close

    def buscando(): return f._buscando_actualizacion

    # 1. Ya está al día
    n = len(mensajes)
    f._buscar_actualizaciones(False)
    def al_dia():
        check("actualizar: al día lo dice", any("Ya tiene la última versión" in m for m in mensajes[n:]))
        check("actualizar: info restaurada", f.lbl_info.GetValue().startswith("Escriba"))
        respuestas["buscar"] = actualizador.ErrorActualizacion("No hay conexión con GitHub (prueba).")
        m = len(mensajes)
        f._buscar_actualizaciones(False)
        esperar(lambda: not buscando(), lambda: sin_conexion(m))

    # 2. Sin conexión: la búsqueda manual avisa; la automática calla
    def sin_conexion(m):
        check("actualizar: sin conexión avisa", any("No hay conexión con GitHub" in x for x in mensajes[m:]))
        m = len(mensajes)
        f._buscar_actualizaciones(True)
        esperar(lambda: not buscando(), lambda: automatica_sin_conexion(m))

    def automatica_sin_conexion(m):
        check("actualizar: la búsqueda al iniciar no avisa si falla", len(mensajes) == m)
        respuestas["buscar"] = nueva
        DialogoMensajeFalso.respuesta = wx.ID_CANCEL  # Más tarde
        f._buscar_actualizaciones(False)
        esperar(lambda: not buscando(), mas_tarde)

    # 3. Versión nueva: Más tarde no cambia nada; Omitir la recuerda
    def mas_tarde():
        ofrecido = DialogoMensajeFalso.mensajes[-1] if DialogoMensajeFalso.mensajes else ""
        check("actualizar: ofrece la versión nueva con sus novedades", "9.0.0" in ofrecido and "Novedad de prueba" in ofrecido)
        check("actualizar: Más tarde no descarga ni omite",
              not llamadas and configuracion.leer(configuracion.VERSION_OMITIDA) is None)
        DialogoMensajeFalso.respuesta = wx.ID_NO  # Omitir esta versión
        f._buscar_actualizaciones(False)
        esperar(lambda: not buscando(), omitir)

    def omitir():
        check("actualizar: Omitir la recuerda", configuracion.leer(configuracion.VERSION_OMITIDA) == "9.0.0")
        DialogoMensajeFalso.mensajes.clear()
        f._buscar_actualizaciones(True)
        esperar(lambda: not buscando(), omitida_al_iniciar)

    def omitida_al_iniciar():
        check("actualizar: la omitida no se ofrece al iniciar", not DialogoMensajeFalso.mensajes)
        # 4. Actualizar ahora: descarga con progreso, instala y cierra
        DialogoMensajeFalso.respuesta = wx.ID_YES
        f._buscar_actualizaciones(False)
        esperar(lambda: llamadas, actualizado, limite=15)

    def actualizado():
        check("actualizar: descarga, instala y cierra",
              llamadas == [("instalar", os.path.join(carpeta_tmp, "setup.exe")), ("cerrar",)])
        check("actualizar: avisa antes de cerrar", any("se cerrará para instalar" in m for m in mensajes))
        # 5. Si se rechaza el permiso de administrador, sigue abierta
        def rechazar(ruta): raise actualizador.ErrorActualizacion("cancelada por el usuario")
        actualizador.instalar = rechazar
        llamadas.clear()
        n = len(mensajes)
        f._buscar_actualizaciones(False)
        esperar(lambda: any("No se instaló" in m for m in mensajes[n:]), lambda: rechazado(n), limite=15)

    def rechazado(n):
        check("actualizar: permiso rechazado, avisa y no cierra",
              any("No se instaló" in m for m in mensajes[n:]) and not llamadas)
        restaurar()
        fin()

    esperar(lambda: not buscando(), al_dia)


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
    def tiempo_agotado():
        # Lo comprobado hasta aquí indica en qué paso se quedó
        for n, ok in resultados: print(("OK  " if ok else "FAIL"), n)
        abiertas = [f"{type(v).__name__} {v.GetTitle()!r}" for v in wx.GetTopLevelWindows()]
        print(f"TIEMPO AGOTADO tras {len(resultados)} comprobaciones; ventanas abiertas: {abiertas}", flush=True)
        os._exit(1)  # el bucle de eventos puede no terminar (ver "Pendiente" en el CHANGELOG)
    wx.CallLater(60000, tiempo_agotado)
    app.MainLoop()
    sys.exit(app.codigo_salida)
