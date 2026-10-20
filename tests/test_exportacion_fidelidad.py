"""Estructura y significado exportados; no simula la lectura de NVDA o JAWS."""
import ast
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest
import sympy as sp

import exportar
import historial
import i18n
from puente import ResultadoOperacion

NS = {"m": "http://www.w3.org/1998/Math/MathML"}


def operadores(raiz):
    return [e.text for e in raiz.iter() if e.tag.rsplit("}", 1)[-1] == "mo"]


def numero_mathml(nodo):
    """Decodifica números racionales para comparar los datos de las celdas."""
    etiqueta = nodo.tag.rsplit('}', 1)[-1]
    if etiqueta == 'mn':
        return sp.Rational(nodo.text)
    if etiqueta == 'mfrac':
        return numero_mathml(nodo[0]) / numero_mathml(nodo[1])
    if etiqueta in ('mrow', 'mtd'):
        if len(nodo) == 1:
            return numero_mathml(nodo[0])
        if len(nodo) == 2 and nodo[0].text == '-':
            return -numero_mathml(nodo[1])
    raise AssertionError(ET.tostring(nodo, encoding='unicode'))


@pytest.mark.parametrize("contenido,esperados", [
    ('<mfenced><mn>1</mn><mn>2</mn><mn>3</mn></mfenced>', ['(', ',', ',', ')']),
    ('<mfenced open="{" close="}"><mn>1</mn><mn>2</mn></mfenced>', ['{', ',', '}']),
    ('<mfenced open="" close="" separators=" ; | "><mi>a</mi><mi>b</mi><mi>c</mi><mi>d</mi></mfenced>', [';', '|', '|']),
    ('<mfenced separators=""><mi>a</mi><mi>b</mi></mfenced>', ['(', ')']),
    ('<mfenced/>', ['(', ')']),
    ('<mfenced><mfenced open="[" close="]"><mn>1</mn><mn>2</mn></mfenced><mn>3</mn></mfenced>', ['(', '[', ',', ']', ',', ')']),
])
def test_mfenced_separadores_y_anidamiento(contenido, esperados):
    raiz = ET.fromstring(exportar._sin_mfenced(contenido))
    assert operadores(raiz) == esperados
    assert all(not e.tag.endswith('mfenced') for e in raiz.iter())
    assert [e.text for e in raiz.iter() if e.tag == 'mn'] == [e.text for e in ET.fromstring(contenido).iter('mn')]


def test_mfenced_namespace_y_entidades():
    xml = '<mfenced xmlns="http://www.w3.org/1998/Math/MathML" open="&lt;" close="&gt;"><mi>&pi;</mi><mi>x</mi></mfenced>'
    raiz = ET.fromstring(exportar._sin_mfenced(xml))
    assert raiz.tag == '{' + NS['m'] + '}mrow'
    assert operadores(raiz) == ['<', ',', '>']
    assert raiz.find('.//m:mi', NS).text == 'π'


@pytest.mark.parametrize('izq,der,abre,cierra', [(False, False, '[', ']'), (True, True, '(', ')'), (False, True, '[', ')'), (True, False, '(', ']')])
def test_intervalos_conservan_extremos_y_apertura(izq, der, abre, cierra):
    intervalo = sp.Interval(-2, 2, left_open=izq, right_open=der)
    raiz = ET.fromstring(exportar._mathml_de(intervalo))
    assert operadores(raiz) == [abre, ',', cierra]
    assert [e.text for e in raiz.iter('mn')] == ['-2', '2']


@pytest.mark.parametrize('entrada,numeros,delimitadores', [('x^2-3*x+2=0', ['1', '2'], ['{', ',', '}']), ('x^2<=4', ['-2', '2'], ['[', ',', ']'])])
def test_soluciones_mathml_y_html_conservan_datos(core, entrada, numeros, delimitadores):
    res = core.ecuacion(entrada)
    for xml in [exportar.mathml(res), exportar.a_html(res).split('<math ', 1)[1].split('</math>', 1)[0]]:
        if not xml.startswith('<math'):
            xml = '<math ' + xml + '</math>'
        raiz = ET.fromstring(xml)
        pertenencia = next(e for e in raiz.iter() if e.tag.endswith('mrow') and any(h.text == '∈' for h in e))
        assert operadores(pertenencia)[-3:] == delimitadores
        assert [e.text for e in pertenencia.findall('.//m:mn', NS)] == numeros
        assert exportar.resultado_corto(res) in raiz.attrib['alttext']


def test_matriz_no_confunde_celdas_con_separadores(core):
    res = core.inversa('1 2\n3 4')
    raiz = ET.fromstring(exportar.mathml(res))
    tablas = raiz.findall('.//m:mtable', NS)
    tabla = tablas[-1]
    filas = tabla.findall('m:mtr', NS)
    assert len(filas) == 2
    assert all(len(f.findall('m:mtd', NS)) == 2 for f in filas)
    assert [[numero_mathml(c) for c in f] for f in filas] == res.valor.tolist()
    assert ',' not in operadores(tabla)


def test_taylor_mathml_nombre_orden_y_centro(core):
    res = core.taylor('sqrt(x)', None, 2, '4')
    raiz = ET.fromstring(exportar.mathml(res))
    nombre = raiz.find('.//m:msub', NS)
    assert [h.text for h in nombre] == ['P', '2']
    potencias = raiz.findall('.//m:msup', NS)
    assert len(potencias) == 1
    base, exponente = potencias[0]
    assert ''.join(base.itertext()) == '(x-4)'
    assert exponente.text == '2'
    assert exportar.resultado_corto(res).startswith('P_2(x) = 2 + (x - 4)/4')
    assert r'P_{2}' in exportar.latex(res)


def test_implicita_mathml_identifica_ambas_variables(core):
    res = core.derivada_implicita('t^2+z^2=1')
    raiz = ET.fromstring(exportar.mathml(res))
    fraccion = raiz.find('.//m:mfrac', NS)
    assert [''.join(h.itertext()) for h in fraccion] == ['dz', 'dt']
    assert exportar.resultado_corto(res).startswith('dz/dt =')
    assert r'\frac{dz}{dt}' in exportar.latex(res)


def test_extremos_tiene_datos_en_filas_y_latex_multilinea(core):
    res = core.extremos('x^3-3*x')
    raiz = ET.fromstring(exportar.mathml(res))
    filas = raiz.findall('.//m:mtable/m:mtr', NS)
    assert len(filas) == 5
    assert 'Máximo local: x=-1;f(-1)=2' == ''.join(filas[1].itertext())
    assert 'Mínimo local: x=1;f(1)=-2' == ''.join(filas[2].itertext())
    assert operadores(filas[3]).count(',') == 2
    tex = exportar.latex(res)
    assert tex.startswith(r'\begin{aligned}') and tex.endswith(r'\end{aligned}')


@pytest.mark.parametrize('idioma,prefijo', [('es', 'RESULTADO:'), ('en', 'RESULT:')])
def test_indeterminados_sin_prefijos_duplicados(core, idioma, prefijo):
    i18n.establecer_idioma(idioma)
    try:
        res = core.sistema_clasico(['x+y=1', '2*x+2*y=2'], 'reduccion')
        assert res.valor is None and not res.es_error
        assert not exportar.resultado_corto(res).startswith(prefijo)
        assert exportar.resumen(res).count(prefijo) == 1
    finally:
        i18n.establecer_idioma('es')


@pytest.mark.parametrize('operacion', ['limite', 'integral_definida', 'gauss', 'taylor', 'extremos'])
def test_historial_sin_objetos_recupera_resultado_multilinea_y_estado(core, tmp_path, operacion):
    casos = {'limite': lambda: core.limite('abs(x)/x','x','0'),
             'integral_definida': lambda: core.integral_definida('x^2',None,'0','1'),
             'gauss': lambda: core.sistema_gauss(['x+y=1','x-y=0']),
             'taylor': lambda: core.taylor('exp(x)',None,2,'0'),
             'extremos': lambda: core.extremos('x^2')}
    res = casos[operacion]()
    ruta = tmp_path / 'historial.json'
    historial.guardar([res], str(ruta))
    datos = json.loads(ruta.read_text(encoding='utf-8'))
    datos['entradas'][0]['sympy'] = 'ilegible'
    ruta.write_text(json.dumps(datos), encoding='utf-8')
    rec, = historial.cargar(str(ruta))
    corto = exportar.resultado_corto(rec)
    assert corto and 'None' not in corto and 'RESULTADO:' not in corto
    if operacion == 'gauss':
        assert 'x = 1/2' in corto and 'y = 1/2' in corto
    if operacion == 'extremos':
        assert 'Mínimo local' in corto and 'Creciente en' in corto
    if operacion == 'limite':
        assert 'No existe' in corto and 'No concluyente' not in corto
    for formato in exportar.FORMATOS:
        assert exportar.exportar(rec, formato)
    assert corto in ET.fromstring(exportar.mathml(rec)).attrib['alttext']


@pytest.mark.parametrize('estado', ['No concluyente', 'No existe el límite bilateral real'])
def test_estado_textual_no_se_reinterpreta(estado):
    res = ResultadoOperacion('limite', 'sqrt(x)', 'RESULTADO: ' + estado)
    assert exportar.resultado_corto(res) == estado
    assert estado in exportar.resumen(res)
    assert estado in exportar.latex(res)


@pytest.mark.parametrize('formato', list(exportar.FORMATOS) + ['mathml', 'corto', 'resumen'])
def test_restricciones_y_salvedades_no_desaparecen(core, formato):
    res = core.ecuacion_diferencial("y'=sqrt(y),y(0)=1")
    if formato in exportar.FORMATOS:
        texto = exportar.exportar(res, formato)
    else:
        texto = {'mathml': exportar.mathml, 'corto': exportar.resultado_corto, 'resumen': exportar.resumen}[formato](res)
    assert 'x/2 + 1 >= 0' in texto or 'x/2 + 1 &gt;= 0' in texto
    assert 'unicidad' in texto


def test_restriccion_original_en_formula_copiada(core):
    res = core.simplificar('(x-1)/(x-1)')
    for convertir in [exportar.resultado_corto, exportar.resumen, exportar.latex, exportar.mathml]:
        texto = convertir(res)
        assert 'x' in texto and ('≠' in texto or '!=' in texto or '\\neq' in texto)


def test_escapado_no_modifica_datos_ni_rompe_documentos():
    entrada = 'a|b & <c> "d" ```\n\\end{verbatim} % # _ $'
    res = ResultadoOperacion('evaluar', entrada, 'RESULTADO: `x` & <y>\n\\end{verbatim}')
    raiz = ET.fromstring(exportar.mathml(res))
    assert entrada.replace('\n', '; ') in raiz.attrib['alttext']
    assert '<y>' not in exportar.a_html(res)
    tex = exportar.a_latex(res)
    assert 'a|b' in tex and '\\begin{verbatim}' not in tex
    assert r'\textbackslash{}end\{verbatim\}' in tex
    md = exportar.a_markdown(res)
    assert '````text\n' + entrada + '\n````' in md
    assert json.loads(exportar.a_json(res))['input'] == entrada


def test_historial_multiformato_incluye_operaciones_y_semantica(core):
    lista = [core.ecuacion('x^2<=4'), core.sistema_gauss(['x+y=1','x-y=0']),
             core.integrar('x'), core.limite('sin(x)/x','x','0'), core.taylor('exp(x)',None,2,'0')]
    for formato in exportar.FORMATOS:
        texto = exportar.exportar_historial(lista, formato)
        assert all(exportar.nombre_operacion(r) in texto for r in lista)
    datos = json.loads(exportar.historial_a_json(lista))['entries']
    assert [e['operation'] for e in datos] == [r.operacion for r in lista]
    assert [e['result']['text'] for e in datos] == [exportar.resultado_corto(r) for r in lista]


def test_copiar_despacha_las_representaciones_sin_gui(core):
    # Se ejecutan los handlers reales aislados de wx: comprueba el texto enviado,
    # sin afirmar que se haya probado el portapapeles del sistema operativo.
    arbol = ast.parse(Path('main.py').read_text(encoding='utf-8-sig'))
    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == 'CalculadoraAccesible')
    nombres = ['on_copiar_resultado', 'on_copiar_explicacion', 'on_copiar_latex', 'on_copiar_mathml']
    funciones = [n for n in clase.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
    entorno = {'exportar': exportar, 'tr': lambda s: s}
    exec(compile(ast.Module(body=funciones, type_ignores=[]), 'main.py', 'exec'), entorno)
    res = core.ecuacion('x^2-3*x+2=0')
    enviados = []
    falso = SimpleNamespace(_resultado_disponible=lambda: res, _copiar=lambda texto, _: enviados.append(texto))
    for nombre in nombres:
        entorno[nombre](falso, None)
    assert enviados == [exportar.resultado_corto(res), res.texto, exportar.latex(res), exportar.mathml(res)]
    assert operadores(ET.fromstring(enviados[-1])).count(',') == 1


def test_transporte_portapapeles_con_objeto_wx_sustituido(core):
    arbol = ast.parse(Path('main.py').read_text(encoding='utf-8-sig'))
    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == 'CalculadoraAccesible')
    funcion = next(n for n in clase.body if isinstance(n, ast.FunctionDef) and n.name == '_poner_en_portapapeles')
    funcion.decorator_list = []
    llamadas = []
    clipboard = SimpleNamespace(Open=lambda: True, SetData=lambda objeto: llamadas.append(objeto.texto) or True,
                                Close=lambda: llamadas.append('cerrado'), Flush=lambda: llamadas.append('persistido'))
    entorno = {'wx': SimpleNamespace(TheClipboard=clipboard, TextDataObject=lambda s: SimpleNamespace(texto=s))}
    exec(compile(ast.Module(body=[funcion], type_ignores=[]), 'main.py', 'exec'), entorno)
    xml = exportar.mathml(core.ecuacion('x^2<=4'))
    assert entorno['_poner_en_portapapeles'](xml)
    assert llamadas == [xml, 'cerrado', 'persistido']
    ET.fromstring(llamadas[0])


def test_condiciones_en_ingles_y_persistencia(core, tmp_path):
    i18n.establecer_idioma('en')
    try:
        res = core.ecuacion_diferencial("y'=sqrt(y),y(0)=1")
        ruta = tmp_path / 'historial.json'
        historial.guardar([res], str(ruta))
        rec, = historial.cargar(str(ruta))
        assert exportar.resultado_corto(rec) == exportar.resultado_corto(res)
        assert 'x/2 + 1 >= 0' in exportar.resultado_corto(rec)
        assert 'Dominio de' not in exportar.resultado_corto(rec)
        assert 'Dominio de' not in exportar.mathml(rec)
    finally:
        i18n.establecer_idioma('es')


@pytest.mark.parametrize('formato', exportar.FORMATOS)
def test_guardar_historial_conserva_restricciones_de_metadatos(core, tmp_path, formato):
    res = replace(core.evaluar('1+1'), parametros={'restricciones': 'x != 0'})
    ruta = tmp_path / ('salida.' + exportar.FORMATOS[formato][1])
    exportar.guardar_historial([res], formato, str(ruta))
    assert 'x != 0' in ruta.read_text(encoding='utf-8')


def test_mfenced_agrupa_argumentos_y_distingue_separadores_de_operadores():
    raiz = ET.fromstring(exportar._sin_mfenced('<mfenced separators="+"><mi>a</mi><mi>b</mi></mfenced>'))
    assert [h.tag for h in raiz] == ['mo', 'mrow', 'mo']
    assert raiz[0].attrib['fence'] == raiz[2].attrib['fence'] == 'true'
    assert raiz[1][1].text == '+' and raiz[1][1].attrib['separator'] == 'true'


def test_latex_filas_con_corchetes_no_son_argumentos_de_saltos():
    res = ResultadoOperacion('inversa', '1 0\n0 1', 'RESULTADO:\n[1, 0]\n[0, 1]')
    tex = exportar.a_latex(res)
    assert r'\strut [1, 0]\par' in tex and r'\strut [0, 1]\par' in tex
    assert '\\\\\n[' not in tex


def test_markdown_preserva_subindices_en_parametros():
    res = ResultadoOperacion('evaluar', '2', 'RESULTADO: 2', parametros={'restricciones': 'x_1 != x_2'})
    assert '- ` Restricciones del dominio: x_1 != x_2 `' in exportar.a_markdown(res)
