"""
Paso a paso de los límites: cada estrategia y el modo general explican con el formato
estándar (Regla, En este caso, cuentas, Queda), sin saltos, y llegan al valor de SymPy.
"""
import pytest

from calculo.lim_estrategias.general import LimiteGeneral
from tests_limites import construir_casos

EXTRA = [
    ("x^2+3*x", "2"), ("(x^2-4)/(x-2)", "2"), ("1/x", "0"), ("1/x", "oo"), ("1/x^2", "0"), ("x^3", "-oo"),
    ("exp(-x)", "oo"), ("x*exp(-x)", "oo"), ("x*log(x)", "0+"), ("(exp(x)-1)/x", "0"), ("(1+2/x)^x", "oo"),
    ("x^x", "0+"), ("(1+x)^(1/x)", "0"), ("sqrt(x^2+x)-x", "oo"), ("1/x-1/(x^2)", "0+"), ("log(x)", "0+"),
    ("atan(x)", "oo"), ("(x-sin(x))/x^3", "0"), ("(2^x-1)/x", "0"), ("abs(x-1)/(x-1)", "1"), ("1/(x-3)", "3+"),
]
CASOS = [(c.expr, c.tend) for c in construir_casos()] + EXTRA


def pasos(core, expresion, tendencia):
    return core.CalcularLimite(expresion, "x", tendencia).split("PASO A PASO:")[1]


@pytest.mark.parametrize("expresion, tendencia", CASOS)
def test_todo_limite_se_explica(core, expresion, tendencia):
    salida = core.CalcularLimite(expresion, "x", tendencia)
    assert "PASO A PASO:" in salida
    assert "No se pudo explicar" not in salida
    assert "Motor Viejo" not in salida


@pytest.mark.parametrize("expresion, tendencia", CASOS)
def test_cada_paso_tiene_regla_y_partes(core, expresion, tendencia):
    texto = pasos(core, expresion, tendencia)
    bloques = [b for b in texto.split("\n") if b and b[0].isdigit()]
    assert bloques
    for i, inicio in enumerate(bloques):
        paso = texto[texto.index(inicio):texto.index(bloques[i + 1]) if i + 1 < len(bloques) else None]
        assert "Regla: " in paso and "En este caso: " in paso, paso


def test_cancelacion_factoriza_y_sustituye(core):
    texto = pasos(core, "(x^3-8)/(x^2-4)", "2")
    assert "Numerador: 2^3 - 8 = 0." in texto
    assert "Denominador: 2^2 - 4 = 0." in texto
    assert "Sale 0/0, una forma indeterminada" in texto
    assert "Factorizamos el numerador: x^3 - 8 = (x - 2)*(x^2 + 2*x + 4)." in texto
    assert "Factorizamos el denominador: x^2 - 4 = (x - 2)*(x + 2)." in texto
    assert "El factor común es x - 2: vale 0 en x = 2" in texto
    assert "Cancelamos x - 2: (x - 2)*(x^2 + 2*x + 4)/((x - 2)*(x + 2)) = (x^2 + 2*x + 4)/(x + 2)." in texto
    assert "Sustituimos: (2^2 + 2*2 + 4)/(2 + 2) = 12/4 = 3." in texto


def test_racionalizacion_con_el_conjugado(core):
    texto = pasos(core, "(sqrt(1+x)-1)/x", "0")
    assert "en el numerador está sqrt(x + 1) - 1: A = sqrt(x + 1) y B = 1, y su conjugado es sqrt(x + 1) + 1." in texto
    assert "En el numerador: (sqrt(x + 1) - 1)*(sqrt(x + 1) + 1) = (sqrt(x + 1))^2 - 1^2 = x." in texto
    assert "La expresión queda x/(x*(sqrt(x + 1) + 1))." in texto
    assert "Sustituimos: 1/(sqrt(0 + 1) + 1) = 1/2." in texto


def test_racionalizacion_de_infinito_menos_infinito(core):
    texto = pasos(core, "sqrt(x+1)-sqrt(x)", "oo")
    assert "Sale ∞ - ∞, una forma indeterminada" in texto
    assert "Regla: un número fijo dividido entre algo que crece sin límite tiende a 0." in texto


def test_trigonometrico_explica_el_resto(core):
    texto = pasos(core, "sin(5*x)/x", "0")
    assert "el núcleo es sin(5*x)/(5*x) con u = 5*x (u → 0: 5*0 = 0)." in texto
    assert "R es la expresión dividida entre el núcleo: R = (sin(5*x)/x)/(sin(5*x)/(5*x)) = 5." in texto
    assert "Multiplicamos los dos límites: 1 * 5 = 5." in texto
    # Un seno en el denominador del resto: el límite notable invertido
    texto = pasos(core, "sin(2*x)/sin(3*x)", "0")
    assert "3*x/sin(3*x) → 1 porque es el inverso del límite notable." in texto


def test_grados_en_infinito(core):
    texto = pasos(core, "(7*x**5)/(2*x**2)", "-oo")
    assert "x^3 tiene exponente impar: cuando x → -oo es negativo." in texto
    assert "El coeficiente 7/2 es positivo, así que el límite es -oo." in texto
    texto = pasos(core, "(3*x**2+1)/(5*x**2-7)", "oo")
    assert "Cociente de los términos principales: (3*x^2)/(5*x^2) = 3/5." in texto


def test_continuidad_explica_el_limite_de_dentro(core):
    texto = pasos(core, "sqrt(x^2+9)", "4")
    assert "Límite de la función de dentro, sustituyendo: g(4) = 4^2 + 9 = 25." in texto
    assert "Evaluamos f en L: sqrt(25) = 5." in texto
    # El límite de dentro es notable: sus pasos van antes
    texto = pasos(core, "exp(sin(x)/x)", "0")
    assert texto.index("Límite trigonométrico notable") < texto.index("Continuidad de una composición")
    assert "calculado en los pasos anteriores: L = 1." in texto


def test_modo_general_laterales_con_valor_absoluto(core):
    salida = core.CalcularLimite("abs(x)/x", "x", "0")
    assert "MÉTODO: Modo General (límites laterales)" in salida
    assert "x es negativo cerca de 0 por la izquierda, así que Abs(x) = -x." in salida
    assert "La expresión queda (-x)/x = -1." in salida
    assert "No coinciden: el límite no existe." in salida


def test_modo_general_lhopital(core):
    salida = core.CalcularLimite("log(x)/x", "x", "oo")
    assert "MÉTODO: Modo General (regla de L'Hôpital)" in salida
    assert "Derivamos el numerador: (log(x))' = 1/x." in salida
    assert "Derivamos el denominador: (x)' = 1." in salida


def test_modo_general_forma_exponencial(core):
    salida = core.CalcularLimite("(1+1/x)^x", "x", "oo")
    assert "MÉTODO: Modo General (forma exponencial)" in salida
    assert "forma 1^∞, indeterminada." in salida
    assert "Reescribimos: x*log(1 + 1/x) = log(1 + 1/x)/(1/x)." in salida
    assert "exp(1) = E." in salida


def test_modo_general_numero_entre_cero(core):
    salida = core.CalcularLimite("1/x^2", "x", "0")
    assert "El denominador, x^2, tiende a 0 con valores positivos por la izquierda y por la derecha." in salida
    assert salida.startswith("RESULTADO: +Infinito")


def test_explicacion_que_no_llega_al_valor_no_se_muestra(core, monkeypatch):
    monkeypatch.setattr(LimiteGeneral, "_limite", lambda self, *a, **k: ("x", 42))
    salida = core.CalcularLimite("log(x)/x", "x", "oo")
    assert salida.startswith("RESULTADO: 0")
    assert "MÉTODO: Modo General (SymPy)" in salida
    assert "No se pudo explicar este límite paso a paso" in salida
    assert "PASO A PASO" not in salida
