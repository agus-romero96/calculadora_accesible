import sys
import os
import re
from dataclasses import dataclass
from typing import Optional, Any, List, Dict, Tuple

import sympy as sp

# Ajuste de path para asegurar que encuentre puente.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from puente import CoreMatematico


# ---------------------------
# Utilidades de parseo salida
# ---------------------------

def extraer_metodo(salida: str) -> str:
    """
    - Si encuentra línea "MÉTODO: ..." devuelve el método.
    - Si no, si detecta motor viejo, devuelve "Modo General (Motor Viejo)".
    - Si no, "Desconocido".
    """
    for linea in salida.splitlines():
        if "MÉTODO:" in linea:
            return linea.split("MÉTODO:")[1].strip()

    if "Modo General" in salida or "CÁLCULO DE LÍMITE" in salida:
        return "Modo General (Motor Viejo)"

    return "Desconocido"


def extraer_resultado_txt(salida: str) -> Optional[str]:
    """
    Extrae el primer RESULTADO: ... (tu render nuevo) si existe.
    """
    m = re.search(r"^RESULTADO:\s*(.+?)\s*$", salida, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip()


def parsear_resultado_a_sympy(t: str) -> Any:
    t = t.strip()
    if t in {"+Infinito", "Infinity", "+Infinity"}:
        return sp.oo
    if t in {"-Infinito", "-Infinity"}:
        return -sp.oo
    if "No existe" in t or "No concluyente" in t or "Indeterminado" in t:
        return None
    try:
        return sp.sympify(t)
    except Exception:
        return t


def equiv(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if a in (sp.oo, -sp.oo) or b in (sp.oo, -sp.oo):
        return a == b
    try:
        return sp.simplify(a - b) == 0
    except Exception:
        return a == b


# ---------------------------
# Modelo de caso de prueba
# ---------------------------

@dataclass
class Caso:
    categoria: str
    expr: str
    tend: str
    esperado_metodo_contains: str  # substring esperada en el nombre del método
    expected_val: Optional[Any] = None  # si lo pones, también valida el resultado


# ---------------------------
# Construcción de casos (60 + extras)
# ---------------------------

def construir_casos() -> List[Caso]:
    casos: List[Caso] = []

    # ===== 20 TRIG =====
    trig = "Trigonometría"
    MTRIG = "Límites trigonométricos notables"
    casos += [
        Caso(trig, "sin(x)/x", "0", MTRIG, sp.Integer(1)),
        Caso(trig, "sin(5*x)/x", "0", MTRIG, sp.Integer(5)),
        Caso(trig, "3*sin(2*x)/x", "0", MTRIG, sp.Integer(6)),
        Caso(trig, "sin(2*x)/(3*x)", "0", MTRIG, sp.Rational(2, 3)),
        Caso(trig, "tan(x)/x", "0", MTRIG, sp.Integer(1)),
        Caso(trig, "tan(7*x)/x", "0", MTRIG, sp.Integer(7)),
        Caso(trig, "sin(2*x)/sin(3*x)", "0", MTRIG, sp.Rational(2, 3)),
        Caso(trig, "5*sin(4*x)/sin(10*x)", "0", MTRIG, sp.Integer(2)),
        Caso(trig, "(1-cos(x))/x**2", "0", MTRIG, sp.Rational(1, 2)),
        Caso(trig, "(1-cos(4*x))/x**2", "0", MTRIG, sp.Integer(8)),
        Caso(trig, "(cos(4*x)-1)/x**2", "0", MTRIG, sp.Integer(-8)),
        Caso(trig, "(1-cos(3*x))/(9*x**2)", "0", MTRIG, sp.Rational(1, 2)),
        Caso(trig, "sin(x)/(x*(x+1))", "0", MTRIG, sp.Integer(1)),
        Caso(trig, "tan(x)/(x*(x+2))", "0", MTRIG, sp.Rational(1, 2)),
        Caso(trig, "(1-cos(x))/(x**2*(x+1))", "0", MTRIG, sp.Rational(1, 2)),
        Caso(trig, "sin(x-2)/(x-2)", "2", MTRIG, sp.Integer(1)),
        Caso(trig, "sin(5*(x-2))/(x-2)", "2", MTRIG, sp.Integer(5)),
        Caso(trig, "(1-cos(3*(x-1)))/(x-1)**2", "1", MTRIG, sp.Rational(9, 2)),
        Caso(trig, "sin(2*(x-1))/sin(5*(x-1))", "1", MTRIG, sp.Rational(2, 5)),
        Caso(trig, "tan(4*(x+3))/(x+3)", "-3", MTRIG, sp.Integer(4)),
    ]

    # ===== 20 RACIONALIZACIÓN =====
    rac = "Racionalización"
    MRAC = "Racionalización"
    casos += [
        Caso(rac, "(sqrt(1+x)-1)/x", "0", MRAC, sp.Rational(1, 2)),
        Caso(rac, "x/(sqrt(1+x)-1)", "0", MRAC, sp.Integer(2)),
        Caso(rac, "(sqrt(1+2*x)-1)/x", "0", MRAC, sp.Integer(1)),
        Caso(rac, "(sqrt(4+x)-2)/x", "0", MRAC, sp.Rational(1, 4)),
        Caso(rac, "(sqrt(x+9)-3)/x", "0", MRAC, sp.Rational(1, 6)),
        Caso(rac, "(3-sqrt(x+9))/x", "0", MRAC, sp.Rational(-1, 6)),
        Caso(rac, "(sqrt(x)-2)/(x-4)", "4+", MRAC, sp.Rational(1, 4)),
        Caso(rac, "(2-sqrt(x))/(4-x)", "4-", MRAC, sp.Rational(1, 4)),
        Caso(rac, "sqrt(x+1)-sqrt(x)", "oo", MRAC, sp.Integer(0)),
        Caso(rac, "(sqrt(x+1)-sqrt(x))*sqrt(x)", "oo", MRAC, sp.Rational(1, 2)),
        Caso(rac, "sqrt(x+4)-sqrt(x)", "oo", MRAC, sp.Integer(0)),
        Caso(rac, "x/(sqrt(x**2+1)-x)", "oo", MRAC, sp.oo),
        Caso(rac, "(sqrt(1+x)-sqrt(1-x))/x", "0", MRAC, sp.Integer(1)),
        Caso(rac, "(sqrt(1+x)-sqrt(1-x))/(2*x)", "0", MRAC, sp.Rational(1, 2)),
        Caso(rac, "(sqrt(1+x)-1)/(sqrt(1+x)+1)", "0", MRAC, sp.Integer(0)),
        Caso(rac, "(sqrt(9+x)-3)/(sqrt(9+x)+3)", "0", MRAC, sp.Integer(0)),
        Caso(rac, "(sqrt(1+x)-1)/(x/(sqrt(1+x)+1))", "0", MRAC, sp.Integer(1)),
        Caso(rac, "(sqrt(16+x)-4)/(x)", "0", MRAC, sp.Rational(1, 8)),
        Caso(rac, "(sqrt(x+25)-5)/(x)", "0", MRAC, sp.Rational(1, 10)),
        Caso(rac, "(5-sqrt(x+25))/x", "0", MRAC, sp.Rational(-1, 10)),
    ]

    # ===== 20 INFINITO =====
    inf = "Infinito"
    MINF = "Comparación de grados"
    casos += [
        Caso(inf, "(3*x**2+1)/(5*x**2-7)", "oo", MINF, sp.Rational(3, 5)),
        Caso(inf, "(3*x**2+1)/(5*x**2-7)", "-oo", MINF, sp.Rational(3, 5)),
        Caso(inf, "(x**2+3*x)/(2*x**3+1)", "oo", MINF, sp.Integer(0)),
        Caso(inf, "(5*x**3-2)/(x**3+9)", "oo", MINF, sp.Integer(5)),
        Caso(inf, "(x**4)/(x**2+1)", "oo", MINF, sp.oo),
        Caso(inf, "(x**4)/(x**2+1)", "-oo", MINF, sp.oo),  # k par
        Caso(inf, "(x**3)/(x**2+1)", "oo", MINF, sp.oo),
        Caso(inf, "(x**3)/(x**2+1)", "-oo", MINF, -sp.oo),  # k impar
        Caso(inf, "(-2*x**3)/(x**2+1)", "oo", MINF, -sp.oo),
        Caso(inf, "(-2*x**3)/(x**2+1)", "-oo", MINF, sp.oo),
        Caso(inf, "(7*x**5)/(2*x**2)", "oo", MINF, sp.oo),
        Caso(inf, "(7*x**5)/(2*x**2)", "-oo", MINF, -sp.oo),
        Caso(inf, "(x**2)/(x**2)", "oo", MINF, sp.Integer(1)),
        Caso(inf, "(x**2+1)/(x**2)", "oo", MINF, sp.Integer(1)),
        Caso(inf, "(2*x**2-3*x+1)/(x**2+10)", "oo", MINF, sp.Integer(2)),
        Caso(inf, "(x+1)/(x**2+1)", "oo", MINF, sp.Integer(0)),
        Caso(inf, "(x**6 + x)/(2*x**6 - 9)", "oo", MINF, sp.Rational(1, 2)),
        Caso(inf, "(x**6 - x)/(2*x**6 - 9)", "-oo", MINF, sp.Rational(1, 2)),
        Caso(inf, "(x**5)/(x**2)", "-oo", MINF, -sp.oo),
        Caso(inf, "(-x**5)/(x**2)", "-oo", MINF, sp.oo),
    ]

    # ===== Extras fallback (5) =====
    fb = "Fallback"
    casos += [
        Caso(fb, "(1 + 1/x)**x", "oo", "Modo General"),
        Caso(fb, "log(x)/x", "oo", "Modo General"),          # no es racional polinomial puro
        Caso(fb, "sin(x)/x**2", "0", "Modo General"),        # diverge: trig notable no debe cerrarlo
        Caso(fb, "sqrt(x)/x", "0+", "Modo General"),         # diverge: racionalización no es el enfoque
        Caso(fb, "abs(x)/x", "0", "Modo General"),           # laterales distintos (si no tienes estrategia)
    ]

    return casos


# ---------------------------
# Runner
# ---------------------------

def auditar():
    core = CoreMatematico()
    casos = construir_casos()

    resumen: Dict[str, Dict[str, int]] = {}
    fallos: List[str] = []

    print("\n🕵️  AUDITORÍA EXTENDIDA DEL SISTEMA DE LÍMITES 🕵️")
    print("====================================================\n")

    for idx, c in enumerate(casos, start=1):
        salida = core.CalcularLimite(c.expr, "x", c.tend)

        metodo = extraer_metodo(salida)
        res_txt = extraer_resultado_txt(salida)
        got_val = parsear_resultado_a_sympy(res_txt) if res_txt else None

        ok_metodo = c.esperado_metodo_contains in metodo
        ok_val = True
        if c.expected_val is not None:
            ok_val = equiv(got_val, c.expected_val)

        ok = ok_metodo and ok_val

        resumen.setdefault(c.categoria, {"OK": 0, "FAIL": 0})
        resumen[c.categoria]["OK" if ok else "FAIL"] += 1

        icono = "✅" if ok else "❌"
        print(f"{icono} [{idx:02d}] {c.categoria}: {c.expr}  (x -> {c.tend})")
        print(f"    Método: {metodo}")
        if c.expected_val is not None:
            print(f"    Resultado: {got_val}   | Esperado: {c.expected_val}")
        else:
            print(f"    Resultado: {res_txt}")
        if not ok:
            fallos.append(
                f"[{idx:02d}] {c.categoria}\n"
                f" expr: {c.expr}\n"
                f" tend: {c.tend}\n"
                f" metodo_obt: {metodo}\n"
                f" metodo_esp_contiene: {c.esperado_metodo_contains}\n"
                f" resultado_txt: {res_txt}\n"
                f" obtenido: {got_val}\n"
                f" esperado: {c.expected_val}\n"
                f" salida:\n{salida}\n"
            )
        print("-" * 60)

    print("\n📌 RESUMEN POR CATEGORÍA")
    print("========================")
    for cat, d in resumen.items():
        print(f" - {cat:14s} OK={d['OK']:2d}  FAIL={d['FAIL']:2d}")

    if fallos:
        print("\n🔥 DETALLES DE FALLOS")
        print("=====================")
        for f in fallos[:20]:
            print(f)
            print("-" * 60)
        if len(fallos) > 20:
            print(f"(Mostrando 20 de {len(fallos)} fallos totales)")

        sys.exit(1)

    print("\n🎉 TODO VERDE: el sistema pasó la auditoría extendida.")
    sys.exit(0)


if __name__ == "__main__":
    auditar()
