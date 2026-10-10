"""
Explicación paso a paso de una integral indefinida, sin saltos.

SymPy (manualintegrate.integral_steps) da el árbol de reglas: cada nodo es una regla
(potencia, sustitución, partes...) con su integrando y sus subreglas. Aquí cada nodo se
explica con la misma estructura que las derivadas (ver calculo/pasos.py):
  1. Regla: el enunciado general, antes de aplicarlo.
  2. En este caso: qué parte de la integral es cada pieza de la regla.
  3. La sustitución y las cuentas intermedias ("2 + 1 = 3", "du = 2*x dx").
  4. Queda: la expresión tras el paso.
Las reglas que necesitan integrar antes otras partes (suma, constante, sustitución,
partes) se explican en un planteamiento, las integrales de sus partes, y la sustitución.

La primitiva se construye con la propia explicación; Calculo comprueba derivándola que
es una primitiva de la función antes de mostrar los pasos.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import sympy
from sympy import Symbol
from sympy.integrals.manualintegrate import (
    AddRule, AlternativeRule, CompleteSquareRule, ConstantRule, ConstantTimesRule, CyclicPartsRule,
    DontKnowRule, ExpRule, PartsRule, PowerRule, ReciprocalRule, RewriteRule, URule,
)

from calculo.derivadas import Regla
from calculo.pasos import (PasoCalculo, agrupa_semejantes, como_potencia, entre_parentesis, forma_final, multiplica_numeros,
                           suma_texto, texto)
from i18n import N_, tr

CONSTANTE = Regla(N_("Integral de una constante"), N_("Integral de una constante"), "")
POTENCIA = Regla(N_("Regla de la potencia"), N_("Regla de la potencia"), "")
RECIPROCA = Regla(N_("Integral que da un logaritmo"), N_("Integral de 1/x"), "")
EXPONENCIAL = Regla(N_("Integral de la exponencial"), N_("Integral exponencial inmediata"), "")
TABLA = Regla(N_("Integral inmediata"), N_("Integral inmediata"), "")
FACTOR_CONSTANTE = Regla(N_("Regla del factor constante"), N_("Constante por función"), "")
SUMA = Regla(N_("Regla de la suma"), N_("Linealidad"), "")
SUSTITUCION = Regla(N_("Cambio de variable"), N_("Sustitución"), "")
PARTES = Regla(N_("Integración por partes"), N_("Integración por partes"), "")
PARTES_CICLICAS = Regla(N_("Integración por partes cíclica"), N_("Integración por partes"), "")
REESCRIBIR = Regla(N_("Reescribir la función"), N_("Reescribir la función"), "")
COMPLETAR_CUADRADO = Regla(N_("Completar el cuadrado"), N_("Reescribir la función"), "")

# Nombres para leer las variables de las sustituciones (SymPy las llama _u)
NOMBRES_SUSTITUCION = ["u", "t", "w", "z"]


class SinExplicacion(Exception):
    """La integral (o una de sus partes) no tiene una regla que se pueda explicar paso a paso."""


class ExplicadorIntegral:
    """Explica el árbol de manualintegrate y va anotando cada regla en self.pasos."""

    def __init__(self, var: Symbol, alternativa: int = 0):
        self.var = var
        # Cuando SymPy ofrece varios caminos (AlternativeRule), cuál se explica: el primero
        # suele ser el de clase, pero puede llegar a otra forma (log(x^2)/2 en vez de log(x))
        self.alternativa = alternativa
        self.pasos: List[PasoCalculo] = []
        self._reglas: List[Regla] = []
        self._nombres: Dict[Any, Symbol] = {}  # variable de sustitución -> nombre para leer

    @property
    def principal(self) -> Optional[Regla]:
        return self._reglas[0] if self._reglas else None

    # ---------------- Texto ----------------

    def _t(self, expr: Any) -> str:
        return texto(sympy.sympify(expr).xreplace(self._nombres))

    def _p(self, expr: Any) -> str:
        return entre_parentesis(sympy.sympify(expr).xreplace(self._nombres))

    def _integral(self, f: Any, v: Any) -> str:
        """∫ f dx (con paréntesis si f es una suma)."""
        cuerpo = f"({self._t(f)})" if sympy.sympify(f).is_Add else self._t(f)
        return f"∫ {cuerpo} d{self._t(v)}"

    def _diferencial(self, expr: Any) -> str:
        """Lo que va delante de dx: entre paréntesis solo si es una suma."""
        return f"({self._t(expr)})" if sympy.sympify(expr).is_Add else self._t(expr)

    def _paso(self, regla: Regla, f: Any, v: Any, rol: str, enunciado: str = "", partes: str = "",
              calculo: Tuple[str, ...] = (), queda: Any = None, final: str = "") -> None:
        integral = self._integral(f, v)
        if rol:
            titulo = tr("{regla} en {expresion} ({rol})", regla=tr(regla.nombre), expresion=integral, rol=rol)
        else:
            titulo = tr("{regla} en {expresion}", regla=tr(regla.nombre), expresion=integral)
        if final:
            titulo = tr("{titulo}: {final}", titulo=titulo, final=final)
        if queda is None:
            queda_texto = ""
        elif isinstance(queda, str):
            queda_texto = queda
        else:
            queda_texto = self._t(queda)
        self.pasos.append(PasoCalculo(titulo, regla=enunciado, partes=partes, calculo=tuple(calculo), queda=queda_texto))

    # ---------------- Selección de la regla ----------------

    def explicar(self, regla: Any, integrando: Any = None, rol: str = "") -> Any:
        """Explica la integral del nodo (añade sus pasos) y devuelve su primitiva.

        integrando: la función que de verdad se integra en este nodo. Un factor constante
        pasa a su subregla la función sin la constante, aunque el nodo guarde otra forma.
        """
        f = regla.integrand if integrando is None else integrando
        if isinstance(regla, AlternativeRule):
            return self.explicar(regla.alternatives[self.alternativa], f, rol)
        if isinstance(regla, DontKnowRule):
            raise SinExplicacion(str(f))
        if isinstance(regla, ConstantTimesRule):
            return self._factor_constante(regla, f, rol)
        if isinstance(regla, AddRule):
            return self._suma(regla, f, rol)
        if isinstance(regla, URule):
            return self._sustitucion(regla, f, rol)
        if isinstance(regla, CyclicPartsRule):
            return self._partes_ciclicas(regla, f, rol)
        if isinstance(regla, PartsRule):
            return self._partes(regla, f, rol)
        if isinstance(regla, RewriteRule):
            return self._reescribir(regla, f, rol)
        if isinstance(regla, ConstantRule):
            return self._constante(regla, f, rol)
        if isinstance(regla, PowerRule):
            return self._potencia(regla, f, rol)
        if isinstance(regla, ReciprocalRule):
            return self._reciproca(regla, f, rol)
        if isinstance(regla, ExpRule):
            return self._exponencial(regla, f, rol)
        return self._tabla(regla, f, rol)

    # ---------------- Integrales inmediatas ----------------

    def _constante(self, regla: Any, f: Any, rol: str) -> Any:
        v = regla.variable
        primitiva = f * v
        self._reglas.append(CONSTANTE)
        self._paso(CONSTANTE, f, v, rol,
                   tr("la integral de una constante c es c*{x}: ∫ c d{x} = c*{x}.", x=self._t(v)),
                   tr("el integrando {c} no depende de {x}: es una constante.", c=self._t(f), x=self._t(v)),
                   [tr("Sustituimos c = {c}: {formula}.", c=self._t(f), formula=f"{self._p(f)}*{self._t(v)}")],
                   primitiva)
        return primitiva

    def _potencia(self, regla: Any, f: Any, rol: str) -> Any:
        v, base, n = regla.variable, regla.base, regla.exp
        m = n + 1
        primitiva = base ** m / m
        x = self._t(base)
        forma = f"{x}^{self._p(n)}"
        partes = tr("la base es {x} y el exponente n es {n}", x=x, n=self._t(n))
        partes += como_potencia(f, forma) if self._t(f) != x else tr(", porque {expresion} es lo mismo que {potencia}.",
                                                                       expresion=x, potencia=f"{x}^1")
        calculo = [tr("Sumamos 1 al exponente: {n} + 1 = {m}.", n=self._t(n), m=self._t(m)) if n.is_Number
                   else tr("El exponente nuevo es {n} + 1.", n=self._t(n)),
                   tr("Dividimos entre el exponente nuevo: {formula}.", formula=f"{x}^{self._p(m)}/{self._p(m)}")]
        if m.is_Rational and not m.is_Integer:
            calculo.append(tr("Dividir entre {m} es multiplicar por {inverso}.", m=self._t(m), inverso=self._t(1 / m)))
        calculo += forma_final(base.xreplace(self._nombres), m)
        self._reglas.append(POTENCIA)
        self._paso(POTENCIA, f, v, rol,
                   tr("la integral de {x}^n es {x}^(n+1)/(n+1), si n no es -1: se suma 1 al exponente "
                      "y se divide entre el exponente nuevo.", x=self._t(v)),
                   partes, calculo, primitiva)
        return primitiva

    def _reciproca(self, regla: Any, f: Any, rol: str) -> Any:
        v, base = regla.variable, regla.base
        primitiva = sympy.log(base)
        x = self._t(base)
        self._reglas.append(RECIPROCA)
        self._paso(RECIPROCA, f, v, rol,
                   tr("la integral de 1/{x} es log(|{x}|), el logaritmo natural del valor absoluto: es el caso "
                      "n = -1, el único que la regla de la potencia no cubre. La calculadora lo escribe log({x}).", x=x),
                   tr("el integrando es 1/{x}, es decir {x}^(-1).", x=x),
                   queda=primitiva)
        return primitiva

    def _exponencial(self, regla: Any, f: Any, rol: str) -> Any:
        v, base = regla.variable, regla.base
        primitiva = regla.eval()
        x = self._t(v)
        self._reglas.append(EXPONENCIAL)
        if base == sympy.E:
            self._paso(EXPONENCIAL, f, v, rol,
                       tr("la integral de e^{x}, que se escribe exp({x}), es la propia exp({x}), "
                          "porque exp({x}) es su propia derivada.", x=x),
                       tr("la base es el número e y el exponente es {x}.", x=x),
                       queda=primitiva)
        else:
            self._paso(EXPONENCIAL, f, v, rol,
                       tr("la integral de a^{x}, con a constante y positiva, es a^{x}/log(a) "
                          "(log es el logaritmo natural).", x=x),
                       tr("la base a es {a} y el exponente es {x}.", a=self._t(base), x=x),
                       [tr("Sustituimos a = {a}: {formula}.", a=self._t(base),
                           formula=f"{self._p(base)}^{x}/log({self._t(base)})")],
                       primitiva)
        return primitiva

    def _tabla(self, regla: Any, f: Any, rol: str) -> Any:
        """Integrales de la tabla (sin, cos, sec^2, 1/(1+x^2)...): el resultado y su comprobación."""
        v = regla.variable
        try:
            primitiva = regla.eval()
        except Exception as e:
            raise SinExplicacion(str(f)) from e
        if primitiva.has(sympy.Integral):
            raise SinExplicacion(str(f))
        derivada = sympy.diff(primitiva, v)
        if sympy.simplify(derivada - f) == 0:
            derivada = f  # escrita como el integrando: la comprobación se lee de un vistazo
        self._reglas.append(TABLA)
        self._paso(TABLA, f, v, rol,
                   tr("hay funciones cuya integral se conoce de memoria (la tabla de integrales inmediatas): "
                      "cada una es la función cuya derivada es el integrando."),
                   tr("en la tabla, {integral} = {primitiva}.", integral=self._integral(f, v), primitiva=self._t(primitiva)),
                   [tr("Comprobación: la derivada de {primitiva} es {derivada}.", primitiva=self._t(primitiva),
                       derivada=self._t(derivada))],
                   primitiva)
        return primitiva

    # ---------------- Reglas que integran antes sus partes ----------------

    def _factor_constante(self, regla: Any, f: Any, rol: str) -> Any:
        v, c, g = regla.variable, regla.constant, regla.other
        partes = tr("la constante c es {c} y f = {f}", c=self._t(c), f=self._t(g))
        _, resto = f.as_independent(v, as_Add=False)
        if resto != g:
            # p. ej. x/(x^2+1) = 1/2 * 2*x/(x^2+1): así aparece la derivada de x^2+1
            partes += tr(", porque {expresion} = {producto}.", expresion=self._t(f),
                         producto=f"{self._p(c)}*{self._p(g)}")
        else:
            partes += "."
        self._reglas.append(FACTOR_CONSTANTE)
        self._paso(FACTOR_CONSTANTE, f, v, rol,
                   tr("una constante que multiplica sale fuera de la integral: "
                      "∫ c*f({x}) d{x} = c*∫ f({x}) d{x}.", x=self._t(v)),
                   partes)
        primitiva_g = self.explicar(regla.substep, g, tr("f del factor constante"))
        primitiva = c * primitiva_g
        calculo = [tr("Multiplicamos la constante por la integral de f, {integral}: {formula}.",
                      integral=self._t(primitiva_g), formula=f"{self._p(c)}*{self._p(primitiva_g)}")]
        calculo += multiplica_numeros(c, primitiva_g)
        self._paso(FACTOR_CONSTANTE, f, v, rol, calculo=calculo, queda=primitiva, final=tr("sustitución"))
        return primitiva

    def _suma(self, regla: Any, f: Any, rol: str) -> Any:
        v = regla.variable
        terminos = [s.integrand for s in regla.substeps]
        self._reglas.append(SUMA)
        self._paso(SUMA, f, v, rol,
                   tr("la integral de una suma o resta es la suma o resta de las integrales: "
                      "∫ (f + g) d{x} = ∫ f d{x} + ∫ g d{x}. Se integra cada término por separado.", x=self._t(v)),
                   tr("hay {n} términos: {terminos}.", n=len(terminos), terminos="; ".join(self._t(t) for t in terminos)))
        primitivas = [self.explicar(s, None, tr("término {i} de la suma", i=i)) for i, s in enumerate(regla.substeps, 1)]
        primitiva = sympy.Add(*primitivas)
        self._paso(SUMA, f, v, rol,
                   calculo=[tr("Juntamos las integrales de los términos: {suma}.",
                               suma=suma_texto([p.xreplace(self._nombres) for p in primitivas]))]
                   + agrupa_semejantes([p.xreplace(self._nombres) for p in primitivas]),
                   queda=primitiva, final=tr("sustitución"))
        return primitiva

    def _sustitucion(self, regla: Any, f: Any, rol: str) -> Any:
        v, u, g = regla.variable, regla.u_var, regla.u_func
        usados = {s.name for s in self._nombres.values()} | {s.name for s in f.free_symbols}
        self._nombres[u] = Symbol(next((n for n in NOMBRES_SUSTITUCION if n not in usados), "u"))
        nu, x = self._t(u), self._t(v)
        dg = sympy.diff(g, v)
        h = regla.substep.integrand
        calculo = [tr("Derivamos {u}: d{u} = {derivada} d{x}.", u=nu, derivada=self._diferencial(dg), x=x)]
        if dg != 1:
            # f = h(g)*g': así se ve qué parte del integrando es du (con su signo y su constante)
            calculo.append(tr("Escribimos el integrando como una función de {g} por su derivada: {f} = {producto}.",
                              g=self._t(g), f=self._t(f), producto=f"{self._p(h.subs(u, g))}*{self._p(dg)}"))
        calculo.append(tr("Cambiamos {g} por {u} y {derivada} d{x} por d{u}.", g=self._t(g), u=nu,
                          derivada=self._diferencial(dg), x=x))
        calculo.append(tr("Reescribimos la integral en {u}: {antes} = {despues}.", u=nu,
                          antes=self._integral(f, v), despues=self._integral(h, u)))
        self._reglas.append(SUSTITUCION)
        self._paso(SUSTITUCION, f, v, rol,
                   tr("si se toma {u} = g({x}), entonces d{u} = g'({x}) d{x}: la integral se reescribe en {u}, "
                      "se integra en {u} y al final se vuelve a {x} sustituyendo {u} = g({x}).", u=nu, x=x),
                   tr("tomamos {u} = {g}, porque su derivada, {derivada}, aparece en el integrando "
                      "(salvo quizá una constante).", u=nu, g=self._t(g), derivada=self._t(dg)),
                   calculo, self._integral(h, u))
        primitiva_u = self.explicar(regla.substep, h, tr("la integral en {u}", u=nu))
        primitiva = primitiva_u.subs(u, g)
        self._paso(SUSTITUCION, f, v, rol,
                   calculo=[tr("Volvemos a {x} sustituyendo {u} = {g} en {primitiva}: {resultado}.", x=x, u=nu,
                               g=self._t(g), primitiva=self._t(primitiva_u), resultado=self._t(primitiva))],
                   queda=primitiva, final=tr("sustitución"))
        return primitiva

    def _partes(self, regla: Any, f: Any, rol: str) -> Any:
        v, u, dv = regla.variable, regla.u, regla.dv
        if regla.second_step is None:
            raise SinExplicacion(str(f))
        x = self._t(v)
        du = sympy.diff(u, v)
        self._reglas.append(PARTES)
        self._paso(PARTES, f, v, rol,
                   tr("∫ u dv = u*v - ∫ v du. Se elige como u la parte que se simplifica al derivar "
                      "y como dv la que se sabe integrar."),
                   tr("u = {u} y dv = {dv} d{x}.", u=self._t(u), dv=self._t(dv), x=x),
                   [tr("Derivamos u: du = {du} d{x}.", du=self._diferencial(du), x=x),
                    tr("Para v hay que integrar dv: v = {integral}.", integral=self._integral(dv, v))])
        primitiva_v = self.explicar(regla.v_step, dv, tr("v, la integral de dv"))
        resto = regla.second_step.integrand
        self._paso(PARTES, f, v, rol,
                   calculo=[tr("Sustituimos u, v y du en u*v - ∫ v du: {formula}.",
                               formula=f"{self._p(u)}*{self._p(primitiva_v)} - {self._integral(resto, v)}")],
                   queda=f"{self._t(u * primitiva_v)} - {self._integral(resto, v)}", final=tr("sustitución"))
        primitiva_resto = self.explicar(regla.second_step, resto, tr("∫ v du de las partes"))
        primitiva = u * primitiva_v - primitiva_resto
        self._paso(PARTES, f, v, rol,
                   calculo=[tr("Restamos la integral que quedaba, {integral}: {formula}.",
                               integral=self._t(primitiva_resto),
                               formula=f"{self._t(u * primitiva_v)} - {self._p(primitiva_resto)}")],
                   queda=primitiva, final=tr("resultado"))
        return primitiva

    def _partes_ciclicas(self, regla: Any, f: Any, rol: str) -> Any:
        v, c = regla.variable, regla.coefficient
        x = self._t(v)
        calculo = []
        terminos = []
        signo = 1
        for i, partes in enumerate(regla.parts_rules, 1):
            primitiva_v = partes.v_step.eval()
            calculo.append(tr("Partes {i}: u = {u}, dv = {dv} d{x}, así que du = {du} d{x} y v = {v}.", i=i,
                              u=self._t(partes.u), dv=self._t(partes.dv), x=x,
                              du=self._diferencial(sympy.diff(partes.u, v)), v=self._t(primitiva_v)))
            terminos.append(signo * partes.u * primitiva_v)
            signo = -signo
        resto = sympy.Add(*terminos)
        primitiva = resto / (1 - c)
        calculo += [tr("Al aplicar partes {n} veces vuelve a aparecer I: I = {resto} + {c}*I.", n=len(regla.parts_rules),
                       resto=self._t(resto), c=self._p(c)),
                    tr("Pasamos {c}*I al otro lado: (1 - {c})*I = {resto}, y 1 - {c} = {uno_menos}.", c=self._p(c),
                       resto=self._t(resto), uno_menos=self._t(1 - c)),
                    tr("Despejamos I dividiendo entre {uno_menos}: I = {resultado}.", uno_menos=self._t(1 - c),
                       resultado=self._t(primitiva))]
        self._reglas.append(PARTES_CICLICAS)
        self._paso(PARTES_CICLICAS, f, v, rol,
                   tr("a veces, al integrar por partes (∫ u dv = u*v - ∫ v du) dos veces, vuelve a aparecer la "
                      "integral original I: se pasa al otro lado de la igualdad y se despeja I como en una ecuación."),
                   tr("I = {integral}.", integral=self._integral(f, v)),
                   calculo, primitiva)
        return primitiva

    def _reescribir(self, regla: Any, f: Any, rol: str) -> Any:
        v, g = regla.variable, regla.rewritten
        es_cuadrado = isinstance(regla, CompleteSquareRule)
        tipo = COMPLETAR_CUADRADO if es_cuadrado else REESCRIBIR
        self._reglas.append(tipo)
        if es_cuadrado:
            enunciado = tr("un polinomio de grado 2 se escribe como un cuadrado más una constante, "
                           "a*(x + b)^2 + c, para llevar la integral a una de la tabla.")
        else:
            enunciado = tr("antes de integrar, la función se escribe de otra forma equivalente que se sabe integrar "
                           "(una identidad, un desarrollo o una fracción separada).")
        self._paso(tipo, f, v, rol, enunciado,
                   tr("{antes} = {despues}.", antes=self._t(f), despues=self._t(g)),
                   queda=self._integral(g, v))
        return self.explicar(regla.substep, g, rol)
