"""
Integración por sustitución trigonométrica, explicada con el formato de calculo/pasos.py
(Regla, En este caso, las cuentas y Queda), para integrandos con sqrt(A + B*x^2):

  - A > 0, B < 0 (a^2 - x^2): x = k*sin(t), y A - A*sin(t)^2 = A*cos(t)^2;
  - A > 0, B > 0 (a^2 + x^2): x = k*tan(t), y A + A*tan(t)^2 = A*sec(t)^2;
  - A < 0, B > 0 (x^2 - a^2): x = k*sec(t), y A*sec(t)^2 - A = A*tan(t)^2,
con k = sqrt(|A|/|B|). Pasos: el caso, dx, la raíz con la identidad pitagórica, la integral
en t (con el explicador de integrales), y la vuelta a x con el triángulo rectángulo: sus tres
lados (Pitágoras) y cada razón trigonométrica que aparece.

Calculo comprueba derivando que la primitiva es correcta. Si la de SymPy trae números
complejos o trozos (Piecewise), se muestra esta, que es real.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import sympy
from sympy import S, Symbol

from calculo.derivadas import Regla
from calculo.integrales import ExplicadorIntegral
from calculo.pasos import PasoCalculo, entre_parentesis, texto
from i18n import N_, tr

SUSTITUCION_TRIG = Regla(N_("Sustitución trigonométrica"), N_("Sustitución trigonométrica"), "")


class SinExplicacion(Exception):
    """El integrando no es de los casos de clase: se explica con las reglas de SymPy."""


def _radical(f: Any, x: Symbol) -> Optional[Tuple[Any, Any, Any]]:
    """(base, A, B) si f tiene una sola raíz sqrt(A + B*x^2) (o potencias impares de ella)."""
    bases = {p.base for p in f.atoms(sympy.Pow) if p.base.has(x) and p.exp.is_Rational and p.exp.q == 2}
    if len(bases) != 1:
        return None
    base = bases.pop()
    if not base.is_polynomial(x) or sympy.degree(base, x) != 2:
        return None
    poli = sympy.Poly(base, x)
    b2, b1, a = poli.all_coeffs()
    if b1 != 0 or not (a.is_number and b2.is_number) or a == 0:
        return None
    if a < 0 and b2 < 0:
        return None  # sqrt(-4 - x^2) no es real
    return base, a, b2


def _con_raiz(f: Any, base: Any, raiz: Symbol) -> Any:
    """f con sqrt(base)^n escrito como raiz^n."""
    return f.replace(lambda e: e.is_Pow and e.base == base and e.exp.is_Rational and e.exp.q == 2,
                     lambda e: raiz ** (2 * e.exp))


def aplica(f: Any, x: Symbol) -> bool:
    """
    Si conviene la sustitución trigonométrica: f es un cociente de polinomios en x y en
    sqrt(A + B*x^2). Si f es impar en x (x/sqrt(4 - x^2)), el cambio u = A + B*x^2 es más directo;
    1/sqrt(a^2 - x^2) es de la tabla (asin).
    """
    try:
        datos = _radical(f, x)
        if datos is None:
            return False
        base, a, b = datos
        r = sympy.Dummy("r")
        g = _con_raiz(f, base, r)
        if g.has(base) or not g.is_rational_function(x, r):
            return False
        if sympy.simplify(g.subs(x, -x) + g) == 0 and not sympy.fraction(sympy.cancel(g / x))[1].has(x):
            return False  # x*P(x^2, raíz): el cambio u = A + B*x^2 es más directo
        if a > 0 and b < 0 and sympy.simplify(f * sympy.sqrt(base)).is_number:
            return False  # c/sqrt(a^2 - x^2): arcoseno, de la tabla
        return True
    except Exception:
        return False


class ExplicadorTrig:
    def __init__(self, var: Symbol):
        self.x = var
        self.pasos: List[PasoCalculo] = []
        # El ángulo se llama t (NVDA no lee la letra griega theta); w si la variable ya es t
        self.t = "t" if var.name != "t" else "w"

    @property
    def principal(self) -> Regla:
        return SUSTITUCION_TRIG

    def _paso(self, titulo: str, regla: str = "", partes: str = "", calculo=(), queda: str = "") -> None:
        self.pasos.append(PasoCalculo(titulo, regla=regla, partes=partes, calculo=tuple(calculo), queda=queda))

    def explicar(self, f: Any) -> Any:
        x = self.x
        datos = _radical(f, x)
        if datos is None:
            raise SinExplicacion()
        base, a, b = datos
        t = Symbol(self.t)
        k = sympy.sqrt(abs(a) / abs(b))
        raiz_a = sympy.sqrt(abs(a))
        raiz_b = sympy.sqrt(abs(b))
        raiz = f"sqrt({texto(base)})"
        integral_x = f"∫ ({texto(f)}) d{x}" if f.is_Add else f"∫ {texto(f)} d{x}"

        # 1. El caso
        if a > 0 and b < 0:
            caso, cambio, d_cambio = "sin", k * sympy.sin(t), k * sympy.cos(t)
            identidad = f"1 - sin({self.t})^2 = cos({self.t})^2"
            nueva_raiz = raiz_a * sympy.cos(t)
            intervalo = tr("{t} entre -pi/2 y pi/2, donde cos({t}) >= 0", t=self.t)
        elif a > 0 and b > 0:
            caso, cambio, d_cambio = "tan", k * sympy.tan(t), k * sympy.sec(t) ** 2
            identidad = f"1 + tan({self.t})^2 = sec({self.t})^2"
            nueva_raiz = raiz_a * sympy.sec(t)
            intervalo = tr("{t} entre -pi/2 y pi/2, donde sec({t}) > 0", t=self.t)
        else:
            caso, cambio, d_cambio = "sec", k * sympy.sec(t), k * sympy.sec(t) * sympy.tan(t)
            identidad = f"sec({self.t})^2 - 1 = tan({self.t})^2"
            nueva_raiz = raiz_a * sympy.tan(t)
            intervalo = tr("{t} entre 0 y pi/2 ({variable} >= {k}), donde tan({t}) >= 0", t=self.t, variable=x, k=texto(k))
        forma = {"sin": "a^2 - x^2", "tan": "a^2 + x^2", "sec": "x^2 - a^2"}[caso]
        self._paso(tr("Elegir la sustitución trigonométrica", t=self.t),
                   regla=tr("una raíz de la forma sqrt(a^2 - x^2) se simplifica con x = a*sin({t}); sqrt(a^2 + x^2), con "
                            "x = a*tan({t}); y sqrt(x^2 - a^2), con x = a*sec({t}). En cada caso una identidad pitagórica "
                            "convierte lo de dentro de la raíz en un cuadrado.", t=self.t),
                   partes=tr("la raíz es {raiz}, del tipo {forma}: A = {a} y B = {b}.", t=self.t, raiz=raiz, forma=forma,
                             a=texto(a), b=texto(b)),
                   calculo=(tr("k = sqrt(|A|/|B|) = sqrt({a}/{b}) = {k}.", t=self.t, a=texto(abs(a)), b=texto(abs(b)), k=texto(k)),
                            tr("Tomamos {variable} = {cambio}.", t=self.t, variable=x, cambio=texto(cambio))),
                   queda=f"{x} = {texto(cambio)}")

        # 2. dx
        self._paso(tr("Calcular d{variable}", t=self.t, variable=x),
                   regla=tr("se deriva el cambio respecto a {t}: d{variable} = (derivada de {cambio}) d{t}.", t=self.t, variable=x,
                            cambio=texto(cambio)),
                   partes=f"{x} = {texto(cambio)}.",
                   calculo=(tr("La derivada de {cambio} es {derivada}.", t=self.t, cambio=texto(cambio), derivada=texto(d_cambio)),),
                   queda=f"d{x} = {texto(d_cambio)} d{self.t}")

        # 3. La raíz
        dentro = sympy.expand(base.subs(x, cambio))
        lineas = [tr("Sustituimos {variable} = {cambio} dentro de la raíz: {base} = {dentro}.", t=self.t, variable=x,
                     cambio=texto(cambio), base=texto(base), dentro=texto(dentro))]
        factor = abs(a)
        if caso == "sin":
            sin_factor = f"{texto(factor)}*(1 - sin({self.t})^2)"
        elif caso == "tan":
            sin_factor = f"{texto(factor)}*(1 + tan({self.t})^2)"
        else:
            sin_factor = f"{texto(factor)}*(sec({self.t})^2 - 1)"
        cuadrado = sympy.trigsimp(dentro)
        lineas.append(tr("Sacamos {factor} factor común: {dentro} = {factorizado}.", t=self.t, factor=texto(factor),
                         dentro=texto(dentro), factorizado=sin_factor))
        lineas.append(tr("Identidad pitagórica: {identidad}, así que queda {cuadrado}.", t=self.t, identidad=identidad,
                         cuadrado=texto(sympy.Mul(factor, (nueva_raiz / raiz_a) ** 2))))
        lineas.append(tr("La raíz: sqrt({cuadrado}) = {raiz} (con {intervalo}).", t=self.t,
                         cuadrado=texto(sympy.Mul(factor, (nueva_raiz / raiz_a) ** 2)), raiz=texto(nueva_raiz),
                         intervalo=intervalo))
        if sympy.simplify(cuadrado - factor * (nueva_raiz / raiz_a) ** 2) != 0:
            raise SinExplicacion()
        self._paso(tr("Simplificar la raíz", t=self.t),
                   regla=tr("al sustituir, lo de dentro de la raíz se convierte en un número por un cuadrado gracias a "
                            "la identidad pitagórica, y la raíz desaparece.", t=self.t),
                   partes=tr("la raíz es {raiz}.", t=self.t, raiz=raiz),
                   calculo=lineas, queda=f"{raiz} = {texto(nueva_raiz)}")

        # 4. La integral en el ángulo
        r = sympy.Dummy("r")
        g = _con_raiz(f, base, r)
        en_theta = g.subs({x: cambio, r: nueva_raiz}) * d_cambio
        simplificada = sympy.simplify(sympy.trigsimp(en_theta))
        escrita = f"{entre_parentesis(g.subs({x: cambio, r: nueva_raiz}))}*{entre_parentesis(d_cambio)}"
        self._paso(tr("Escribir la integral en {t}", t=self.t),
                   regla=tr("se cambia {variable} por {cambio}, la raíz por {raiz_nueva} y d{variable} por {dx} d{t}; "
                            "después se simplifica.", t=self.t, variable=x, cambio=texto(cambio), raiz_nueva=texto(nueva_raiz),
                            dx=texto(d_cambio)),
                   partes=tr("la integral es {integral}.", t=self.t, integral=integral_x),
                   calculo=(tr("Sustituimos: {integral} = ∫ {escrita} d{t}.", t=self.t, integral=integral_x, escrita=escrita),
                            tr("Simplificamos el integrando: {escrita} = {simplificada}.", t=self.t, escrita=escrita,
                               simplificada=texto(simplificada))),
                   queda=f"∫ {entre_parentesis(simplificada)} d{self.t}")
        primitiva_t = self._integrar_en_theta(simplificada, t)
        if sympy.simplify(sympy.diff(primitiva_t, t) - simplificada) != 0:
            raise SinExplicacion()

        # 5. Volver a x con el triángulo
        return self._volver(primitiva_t, t, caso, x, raiz_a, raiz_b, base)

    def _integrar_en_theta(self, g: Any, t: Symbol) -> Any:
        """La integral en el ángulo: con el explicador de integrales o, si no la sabe, con la tabla trigonométrica."""
        try:
            regla = sympy.integrals.manualintegrate.integral_steps(g, t)
            explicador = ExplicadorIntegral(t)
            primitiva = explicador.explicar(regla, g)
            self.pasos.extend(explicador.pasos)
            return primitiva
        except Exception:
            pass
        constante, funcion = g.as_independent(t, as_Add=False)
        tabla = [
            (sympy.sec(t) ** 2, sympy.tan(t)),
            (sympy.csc(t) ** 2, -sympy.cot(t)),
            (sympy.sec(t), sympy.log(sympy.sec(t) + sympy.tan(t))),
            (sympy.csc(t), -sympy.log(sympy.csc(t) + sympy.cot(t))),
            (sympy.sec(t) ** 3, (sympy.sec(t) * sympy.tan(t) + sympy.log(sympy.sec(t) + sympy.tan(t))) / 2),
        ]
        for integrando, primitiva in tabla:
            if sympy.simplify(funcion - integrando) == 0:
                break
        else:
            raise SinExplicacion()
        derivada = sympy.simplify(sympy.diff(primitiva, t))
        if sympy.simplify(derivada - integrando) != 0:
            raise SinExplicacion()
        total = constante * primitiva
        calculo = [tr("Comprobación: la derivada de {primitiva} es {derivada}, que es {integrando}.", t=self.t,
                      primitiva=texto(primitiva), derivada=texto(derivada), integrando=texto(integrando))]
        if constante != 1:
            calculo.insert(0, tr("El número {c} sale fuera de la integral: ∫ {g} d{t} = {c}*∫ {f} d{t}.", t=self.t, c=texto(constante),
                                 g=entre_parentesis(g), f=entre_parentesis(integrando)))
            calculo.append(tr("Multiplicamos por {c}: {cuenta} = {total}.", t=self.t, c=texto(constante),
                              cuenta=f"{entre_parentesis(constante)}*({texto(primitiva)})", total=texto(total)))
        self._paso(tr("Integral trigonométrica de la tabla", t=self.t),
                   regla=tr("algunas integrales de funciones trigonométricas se conocen de memoria: ∫ sec({t})^2 d{t} = tan({t}), "
                            "∫ csc({t})^2 d{t} = -cot({t}), ∫ sec({t}) d{t} = log(sec({t}) + tan({t})), ∫ csc({t}) d{t} = "
                            "-log(csc({t}) + cot({t})) y ∫ sec({t})^3 d{t} = (sec({t})*tan({t}) + log(sec({t}) + tan({t})))/2 (esta "
                            "última sale integrando por partes).", t=self.t),
                   partes=tr("en la tabla, ∫ {f} d{t} = {p}.", t=self.t, f=texto(integrando), p=texto(primitiva)),
                   calculo=calculo, queda=texto(total))
        return total

    def _volver(self, primitiva_t: Any, t: Symbol, caso: str, x: Symbol, raiz_a: Any, raiz_b: Any, base: Any) -> Any:
        expandida = sympy.expand_trig(primitiva_t)
        # 1/cos(t) es sec(t) y 1/sin(t) es csc(t): así se leen directamente en el triángulo
        expandida = expandida.replace(
            lambda e: e.is_Pow and e.exp == -1 and isinstance(e.base, (sympy.cos, sympy.sin)),
            lambda e: (sympy.sec if isinstance(e.base, sympy.cos) else sympy.csc)(e.base.args[0]))
        lado_x = raiz_b * x
        r = sympy.sqrt(base)  # la raíz del enunciado: es el tercer lado del triángulo
        if caso == "sin":
            opuesto, hipotenusa, adyacente = lado_x, raiz_a, r
            razon = tr("sin({t}) = {x}/{k}: el cateto opuesto mide {op} y la hipotenusa {hip}.", t=self.t, x=texto(lado_x),
                       k=texto(raiz_a), op=texto(lado_x), hip=texto(raiz_a))
            pitagoras = tr("Cateto adyacente, por Pitágoras: sqrt({hip}^2 - {op}^2) = {lado}.", t=self.t, hip=texto(raiz_a),
                           op=entre_parentesis(lado_x), lado=texto(r))
            angulo = sympy.asin(opuesto / hipotenusa)
            angulo_txt = f"{self.t} = asin({texto(opuesto / hipotenusa)})"
        elif caso == "tan":
            opuesto, adyacente, hipotenusa = lado_x, raiz_a, r
            razon = tr("tan({t}) = {x}/{k}: el cateto opuesto mide {op} y el adyacente {ady}.", t=self.t, x=texto(lado_x),
                       k=texto(raiz_a), op=texto(lado_x), ady=texto(raiz_a))
            pitagoras = tr("Hipotenusa, por Pitágoras: sqrt({op}^2 + {ady}^2) = {lado}.", t=self.t, op=entre_parentesis(lado_x),
                           ady=texto(raiz_a), lado=texto(r))
            angulo = sympy.atan(opuesto / adyacente)
            angulo_txt = f"{self.t} = atan({texto(opuesto / adyacente)})"
        else:
            hipotenusa, adyacente, opuesto = lado_x, raiz_a, r
            razon = tr("sec({t}) = {x}/{k}, es decir, cos({t}) = {k}/{x}: la hipotenusa mide {hip} y el cateto adyacente "
                       "{ady}.", t=self.t, x=texto(lado_x), k=texto(raiz_a), hip=texto(lado_x), ady=texto(raiz_a))
            pitagoras = tr("Cateto opuesto, por Pitágoras: sqrt({hip}^2 - {ady}^2) = {lado}.", t=self.t, hip=entre_parentesis(lado_x),
                           ady=texto(raiz_a), lado=texto(r))
            angulo = sympy.acos(adyacente / hipotenusa)
            angulo_txt = f"{self.t} = acos({texto(adyacente / hipotenusa)})"
        razones = {
            sympy.sin(t): (opuesto / hipotenusa, N_("sin({t}) = opuesto/hipotenusa")),
            sympy.cos(t): (adyacente / hipotenusa, N_("cos({t}) = adyacente/hipotenusa")),
            sympy.tan(t): (opuesto / adyacente, N_("tan({t}) = opuesto/adyacente")),
            sympy.sec(t): (hipotenusa / adyacente, N_("sec({t}) = hipotenusa/adyacente")),
            sympy.csc(t): (hipotenusa / opuesto, N_("csc({t}) = hipotenusa/opuesto")),
            sympy.cot(t): (adyacente / opuesto, N_("cot({t}) = adyacente/opuesto")),
        }
        lineas = [razon, pitagoras]
        usadas = {}
        for funcion, (valor, nombre) in razones.items():
            if expandida.has(funcion):
                usadas[funcion] = valor
                lineas.append(f"{tr(nombre, t=self.t)} = {texto(valor)}.")
        if expandida.has(t) and expandida.subs(usadas).has(t):
            lineas.append(tr("El ángulo: {angulo}.", t=self.t, angulo=angulo_txt))
        en_x = expandida.subs(usadas).subs(t, angulo)
        resultado = sympy.simplify(en_x)
        # La sustitución, sin operar y en el orden en que se escribió: 2*asin(x/2) + 2*(x/2)*(sqrt(4 - x^2)/2)
        cuenta = texto(expandida)
        for funcion, valor in usadas.items():
            cuenta = cuenta.replace(texto(funcion), entre_parentesis(valor))
        # El ángulo suelto (no la t de sqrt o tan) por su valor
        cuenta = re.sub(rf"(?<![A-Za-z_]){self.t}(?![A-Za-z_(])", texto(angulo), cuenta)
        lineas.append(tr("Sustituimos en {primitiva}: {cuenta}.", t=self.t, primitiva=texto(expandida), cuenta=cuenta))
        if cuenta != texto(resultado):
            lineas.append(tr("Operamos: {antes} = {despues}.", t=self.t, antes=cuenta, despues=texto(resultado)))
        self._paso(tr("Volver a {variable} con el triángulo rectángulo", t=self.t, variable=x),
                   regla=tr("el cambio dice una razón trigonométrica de {t}; se dibuja un triángulo rectángulo con esos dos "
                            "lados, el tercero sale por Pitágoras, y de él se leen las demás razones.", t=self.t),
                   partes=tr("la primitiva en {t} es {primitiva}.", t=self.t, primitiva=texto(primitiva_t))
                   + (" " + tr("Con las fórmulas del ángulo doble, sin(2*{t}) = 2*sin({t})*cos({t}) y cos(2*{t}) = "
                               "cos({t})^2 - sin({t})^2, queda {expandida}.", t=self.t, expandida=texto(expandida))
                      if expandida != primitiva_t else ""),
                   calculo=lineas, queda=texto(resultado))
        return resultado
