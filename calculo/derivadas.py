"""
Explicación paso a paso de una derivada, sin saltos.

Cada regla se explica con la misma estructura (ver calculo/pasos.py), pensada para
leerse línea a línea con un lector de pantalla:
  1. Regla: el enunciado general, antes de aplicarla
     ("la derivada de x^n es n*x^(n-1)").
  2. En este caso: qué parte de la expresión es cada pieza de la regla
     ("la base es x y el exponente n es 3").
  3. La sustitución y las cuentas intermedias ("3*x^(3-1)", "3 - 1 = 2").
  4. Queda: la expresión tras el paso ("3*x^2").

Las reglas que necesitan derivar antes sus partes (suma, producto, cociente, cadena,
factor constante) se explican en dos pasos: el planteamiento (1 y 2), luego la
derivada de cada parte, y al final la sustitución (3 y 4) con esas derivadas.

La derivada se construye con la propia explicación; CalcularDerivada la compara con
la de SymPy antes de mostrarla.
"""
from __future__ import annotations

from typing import Any, List, NamedTuple, Optional, Tuple

import sympy
from sympy import Dummy, Symbol

from calculo.pasos import (PasoCalculo, agrupa_semejantes, como_potencia, entre_parentesis as _p, forma_final,
                           multiplica_numeros, suma_texto, texto)
from i18n import N_, tr


class Regla(NamedTuple):
    nombre: str        # título de sus pasos
    estrategia: str    # estrategia del resultado (ANÁLISIS)
    diagnostico: str
    implicitas: Tuple[str, ...] = ()  # otras estrategias que usa sin pasos propios


CONSTANTE = Regla(N_("Derivada de una constante"), N_("Constante"), N_("Función constante."))
VARIABLE = Regla(N_("Derivada de la variable"), N_("Directa"), N_("Elemental."))
POTENCIA = Regla(N_("Regla de la potencia"), N_("Potencia"), N_("Polinomio."))
POTENCIA_NEGATIVA = Regla(N_("Regla de la potencia"), N_("Potencia Negativa"), N_("Potencia con exponente negativo."))
POTENCIA_COEFICIENTE = Regla(N_("Regla de la potencia con coeficiente"), N_("Multiplicación por Constante"),
                             N_("Coeficiente extraído."), (N_("Potencia"),))
FACTOR_CONSTANTE = Regla(N_("Regla del factor constante"), N_("Multiplicación por Constante"), N_("Coeficiente extraído."))
SUMA = Regla(N_("Regla de la suma"), N_("Linealidad"), N_("Suma algebraica."))
PRODUCTO = Regla(N_("Regla del producto"), N_("Regla del Producto"), N_("Producto de funciones."))
COCIENTE = Regla(N_("Regla del cociente"), N_("Regla del Cociente"), N_("Función racional."))
CADENA_POTENCIA = Regla(N_("Regla de la cadena con potencia"), N_("Regla de la Cadena"), N_("Potencia de función."))
EXPONENCIAL = Regla(N_("Derivada de la exponencial"), N_("Exponencial"), N_("Función exponencial."))
CADENA_EXPONENCIAL = Regla(N_("Regla de la cadena con exponencial"), N_("Exponencial"), N_("Función exponencial."),
                           (N_("Regla de la Cadena"),))
LOGARITMICA = Regla(N_("Derivación logarítmica"), N_("Potencia General (Logarítmica)"), N_("Función elevado a función."),
                    (N_("Regla del Producto"), N_("Regla de la Cadena")))
ELEMENTAL = Regla(N_("Derivada de una función elemental"), N_("Directa"), N_("Elemental."))
CADENA = Regla(N_("Regla de la cadena"), N_("Regla de la Cadena"), N_("Composición."))
DIRECTA = Regla(N_("Derivada directa"), N_("Directa"), N_("Elemental."))

# Estrategias que no se citan como secundarias
_TRIVIALES = {CONSTANTE.estrategia, VARIABLE.estrategia}


def _resta_exponente(n: Any) -> List[str]:
    """Cuenta del exponente nuevo (n - 1) y, si sale 0, por qué desaparece la potencia."""
    if not n.is_Number:
        return [tr("El exponente nuevo es {n} - 1.", n=texto(n))]
    cuentas = [tr("Restamos 1 al exponente: {n} - 1 = {resultado}.", n=texto(n), resultado=texto(n - 1))]
    if n - 1 == 0:
        cuentas.append(tr("Cualquier base elevada a 0 vale 1, así que la potencia desaparece."))
    return cuentas


class ExplicadorDerivada:
    """Deriva una expresión respecto de var y va anotando cada regla en self.pasos."""

    def __init__(self, var: Symbol):
        self.var = var
        self.pasos: List[PasoCalculo] = []
        self._reglas: List[Regla] = []  # en el orden en que se aplican; la primera es la principal

    # ---------------- Análisis del resultado ----------------

    @property
    def principal(self) -> Regla:
        return self._reglas[0] if self._reglas else DIRECTA

    @property
    def secundarias(self) -> List[str]:
        estrategias = list(self.principal.implicitas)
        for regla in self._reglas[1:]:
            estrategias.append(regla.estrategia)
            estrategias.extend(regla.implicitas)
        vistas = {self.principal.estrategia} | _TRIVIALES
        return [e for e in dict.fromkeys(estrategias) if e not in vistas]

    # ---------------- Pasos ----------------

    def _titulo(self, regla: Regla, expr: Any, rol: str, sustitucion: bool = False) -> str:
        if rol:
            titulo = tr("{regla} en {expresion} ({rol})", regla=tr(regla.nombre), expresion=texto(expr), rol=rol)
        else:
            titulo = tr("{regla} en {expresion}", regla=tr(regla.nombre), expresion=texto(expr))
        return tr("{titulo}: sustitución", titulo=titulo) if sustitucion else titulo

    def _paso(self, regla: Regla, expr: Any, rol: str, enunciado: str = "", partes: str = "",
              calculo: Tuple[str, ...] = (), queda: Optional[Any] = None, sustitucion: bool = False) -> None:
        self.pasos.append(PasoCalculo(
            self._titulo(regla, expr, rol, sustitucion), regla=enunciado, partes=partes,
            calculo=tuple(calculo), queda="" if queda is None else texto(queda)))

    # ---------------- Selección de la regla ----------------

    def derivar(self, expr: Any, rol: str = "") -> Any:
        """Explica la derivada de expr (añade sus pasos) y la devuelve."""
        x = self.var
        if not expr.has(x):
            return self._constante(expr, rol)
        if expr == x:
            return self._variable(rol)
        if expr.is_Add:
            return self._suma(expr, rol)
        if expr.is_Mul:
            coeficiente, resto = expr.as_independent(x, as_Add=False)
            if coeficiente != 1:
                if resto == x or (resto.is_Pow and resto.base == x and not resto.exp.has(x)):
                    return self._potencia(resto, rol, coeficiente)
                return self._factor_constante(coeficiente, resto, expr, rol)
            factores = expr.as_ordered_factors()
            # Factores con exponente negativo (1/v): es un cociente
            denominador = [f for f in factores if f.is_Pow and f.exp.could_extract_minus_sign()]
            if denominador:
                numerador = [f for f in factores if f not in denominador]
                return self._cociente(sympy.Mul(*numerador), sympy.Mul(*[1 / f for f in denominador]), expr, rol)
            return self._producto(factores, expr, rol)
        if expr.is_Pow:
            base, exponente = expr.as_base_exp()
            if not exponente.has(x):
                if base == x:
                    return self._potencia(expr, rol)
                return self._cadena_potencia(base, exponente, expr, rol)
            if not base.has(x):
                return self._exponencial(base, exponente, expr, rol)
            return self._logaritmica(base, exponente, expr, rol)
        if isinstance(expr, sympy.exp):
            return self._exponencial(sympy.E, expr.args[0], expr, rol)
        if expr.is_Function and len(expr.args) == 1:
            return self._funcion(expr, rol)
        return self._directa(expr, rol)

    # ---------------- Reglas sin partes que derivar ----------------

    def _constante(self, expr: Any, rol: str) -> Any:
        self._reglas.append(CONSTANTE)
        self._paso(CONSTANTE, expr, rol,
                   tr("la derivada de una constante es 0, porque su valor no cambia."),
                   tr("{expresion} no depende de {x}: es una constante.", expresion=texto(expr), x=self.var),
                   queda=sympy.S.Zero)
        return sympy.S.Zero

    def _variable(self, rol: str) -> Any:
        x = self.var
        self._reglas.append(VARIABLE)
        self._paso(VARIABLE, x, rol,
                   tr("la derivada de {x} respecto de {x} es 1.", x=x),
                   tr("la expresión es la propia variable {x}.", x=x),
                   queda=sympy.S.One)
        return sympy.S.One

    def _potencia(self, expr: Any, rol: str, coeficiente: Any = 1) -> Any:
        """x^n (n constante), o c*x^n: un solo paso con todas las cuentas."""
        x = self.var
        n = expr.exp if expr.is_Pow else sympy.S.One
        resultado = coeficiente * n * x ** (n - 1)
        forma = f"{x}^{_p(n)}"
        nota = como_potencia(expr, forma)

        sustitucion = f"{_p(n)}*{x}^({texto(n)} - 1)"
        if coeficiente == 1:
            regla = POTENCIA_NEGATIVA if n.is_negative else POTENCIA
            enunciado = tr("la derivada de {x}^n es n*{x}^(n-1): el exponente baja multiplicando y se le resta 1.", x=x)
            partes = tr("la base es {x} y el exponente n es {n}", x=x, n=texto(n)) + nota
            calculo = [tr("Sustituimos n = {n}: {formula}.", n=texto(n), formula=sustitucion)]
        else:
            regla = POTENCIA_COEFICIENTE
            enunciado = tr("la derivada de c*{x}^n es c*n*{x}^(n-1): el coeficiente se mantiene, "
                           "el exponente baja multiplicando y se le resta 1.", x=x)
            partes = tr("el coeficiente c es {c}, la base es {x} y el exponente n es {n}",
                        c=texto(coeficiente), x=x, n=texto(n)) + nota
            calculo = [tr("Sustituimos c = {c} y n = {n}: {formula}.", c=texto(coeficiente), n=texto(n),
                          formula=f"{_p(coeficiente)}*{sustitucion}")]
            calculo += multiplica_numeros(coeficiente, n)
        calculo += _resta_exponente(n) + forma_final(x, n - 1)

        self._reglas.append(regla)
        self._paso(regla, coeficiente * expr, rol, enunciado, partes, calculo, resultado)
        return resultado

    def _exponencial(self, base: Any, exponente: Any, expr: Any, rol: str) -> Any:
        """e^u o a^u con a constante; si u no es la variable, con la regla de la cadena."""
        x = self.var
        es_e = base == sympy.E
        potencia = texto(expr) if es_e else f"{_p(base)}^{_p(exponente)}"
        if exponente == x:
            self._reglas.append(EXPONENCIAL)
            if es_e:
                resultado = expr
                enunciado = tr("la derivada de e^{x}, que se escribe exp({x}), es la propia exp({x}).", x=x)
                partes = tr("la base es el número e y el exponente es {x}.", x=x)
                calculo = []
            else:
                resultado = expr * sympy.log(base)
                enunciado = tr("la derivada de a^{x}, con a constante y positiva, es a^{x}*log(a) (log es el logaritmo natural, ln).", x=x)
                partes = tr("la base a es {a} y el exponente es {x}.", a=texto(base), x=x)
                calculo = [tr("Sustituimos a = {a}: {formula}.", a=texto(base), formula=f"{potencia}*log({texto(base)})")]
            self._paso(EXPONENCIAL, expr, rol, enunciado, partes, calculo, resultado)
            return resultado

        self._reglas.append(CADENA_EXPONENCIAL)
        if es_e:
            enunciado = tr("la derivada de e^u, que se escribe exp(u), es exp(u)*u', donde u es una función de {x} (regla de la cadena).", x=x)
            partes = tr("la base es el número e y el exponente es u = {u}.", u=texto(exponente))
        else:
            enunciado = tr("la derivada de a^u, con a constante y positiva, es a^u*log(a)*u', "
                           "donde u es una función de {x} (regla de la cadena) y log es el logaritmo natural.", x=x)
            partes = tr("la base a es {a} y el exponente es u = {u}.", a=texto(base), u=texto(exponente))
        self._paso(CADENA_EXPONENCIAL, expr, rol, enunciado, partes)

        du = self.derivar(exponente, tr("u, el exponente de la exponencial"))
        if es_e:
            formula = f"{potencia}*{_p(du)}"
            resultado = expr * du
        else:
            formula = f"{potencia}*log({texto(base)})*{_p(du)}"
            resultado = expr * sympy.log(base) * du
        self._paso(CADENA_EXPONENCIAL, expr, rol,
                   calculo=[tr("Sustituimos u' = {du}: {formula}.", du=texto(du), formula=formula)],
                   queda=resultado, sustitucion=True)
        return resultado

    def _funcion(self, expr: Any, rol: str) -> Any:
        """sin, cos, log, asin...: su derivada con u = el argumento; con la cadena si u no es la variable."""
        x = self.var
        u = expr.args[0]
        nombre = expr.func.__name__
        auxiliar = Dummy("u", real=True)
        externa = sympy.diff(expr.func(auxiliar), auxiliar)
        if externa.has(sympy.Derivative):
            return self._directa(expr, rol)
        # Para leer la regla: "u" sin las suposiciones de la variable auxiliar
        regla_funcion = tr("la derivada de {f}(u) es {derivada}", f=nombre,
                           derivada=texto(externa.subs(auxiliar, Symbol("u"))))

        if u == x:
            resultado = externa.subs(auxiliar, x)
            self._reglas.append(ELEMENTAL)
            self._paso(ELEMENTAL, expr, rol,
                       tr("{regla}; aquí u es directamente {x}.", regla=regla_funcion, x=x),
                       tr("la función es {f} y su argumento es {x}, así que no hace falta la regla de la cadena.",
                          f=nombre, x=x),
                       [tr("Sustituimos u = {x}: {formula}.", x=x, formula=texto(resultado))],
                       resultado)
            return resultado

        self._reglas.append(CADENA)
        self._paso(CADENA, expr, rol,
                   tr("la derivada de f(u) es f'(u)*u', donde u es la función de dentro (regla de la cadena). "
                      "Para esta función, {regla}.", regla=regla_funcion),
                   tr("la función de fuera es {f} y la de dentro es u = {u}.", f=nombre, u=texto(u)))
        du = self.derivar(u, tr("u, la función de dentro"))
        derivada_externa = externa.subs(auxiliar, u)
        resultado = derivada_externa * du
        calculo = [tr("Sustituimos u = {u} en f'(u): {externa}.", u=texto(u), externa=texto(derivada_externa)),
                   tr("Multiplicamos por u' = {du}: {formula}.", du=texto(du),
                      formula=f"{_p(derivada_externa)}*{_p(du)}")]
        calculo += multiplica_numeros(derivada_externa, du)
        self._paso(CADENA, expr, rol, calculo=calculo, queda=resultado, sustitucion=True)
        return resultado

    def _directa(self, expr: Any, rol: str) -> Any:
        resultado = sympy.diff(expr, self.var)
        self._reglas.append(DIRECTA)
        self._paso(DIRECTA, expr, rol,
                   tr("esta expresión no tiene una regla paso a paso en la calculadora; se usa la derivada que da SymPy."),
                   queda=resultado)
        return resultado

    # ---------------- Reglas que derivan antes sus partes ----------------

    def _factor_constante(self, coeficiente: Any, resto: Any, expr: Any, rol: str) -> Any:
        x = self.var
        self._reglas.append(FACTOR_CONSTANTE)
        self._paso(FACTOR_CONSTANTE, expr, rol,
                   tr("la derivada de c*f({x}) es c*f'({x}): la constante queda multiplicando y solo se deriva f.", x=x),
                   tr("la constante c es {c} y f = {f}.", c=texto(coeficiente), f=texto(resto)))
        df = self.derivar(resto, tr("f del factor constante"))
        resultado = coeficiente * df
        calculo = [tr("Multiplicamos la constante por f' = {df}: {formula}.", df=texto(df),
                      formula=f"{_p(coeficiente)}*{_p(df)}")]
        calculo += multiplica_numeros(coeficiente, df)
        self._paso(FACTOR_CONSTANTE, expr, rol, calculo=calculo, queda=resultado, sustitucion=True)
        return resultado

    def _suma(self, expr: Any, rol: str) -> Any:
        terminos = expr.as_ordered_terms()
        self._reglas.append(SUMA)
        self._paso(SUMA, expr, rol,
                   tr("la derivada de una suma o resta es la suma o resta de las derivadas: (u + v)' = u' + v'. "
                      "Se deriva cada término por separado."),
                   tr("hay {n} términos: {terminos}.", n=len(terminos), terminos="; ".join(texto(t) for t in terminos)))
        derivadas = [self.derivar(t, tr("término {i} de la suma", i=i)) for i, t in enumerate(terminos, 1)]
        resultado = sympy.Add(*derivadas)
        self._paso(SUMA, expr, rol,
                   calculo=[tr("Juntamos las derivadas de los términos: {suma}.", suma=suma_texto(derivadas))]
                   + agrupa_semejantes(derivadas),
                   queda=resultado, sustitucion=True)
        return resultado

    def _producto(self, factores: List[Any], expr: Any, rol: str) -> Any:
        u, v = factores[0], sympy.Mul(*factores[1:])
        self._reglas.append(PRODUCTO)
        self._paso(PRODUCTO, expr, rol,
                   tr("la derivada de u*v es u'*v + u*v': se deriva un factor cada vez, dejando el otro igual, y se suman."),
                   tr("u = {u} y v = {v}.", u=texto(u), v=texto(v)))
        du = self.derivar(u, tr("u del producto"))
        dv = self.derivar(v, tr("v del producto"))
        resultado = du * v + u * dv
        self._paso(PRODUCTO, expr, rol,
                   calculo=[tr("Sustituimos u' = {du} y v' = {dv} en u'*v + u*v': {formula}.", du=texto(du), dv=texto(dv),
                               formula=f"{_p(du)}*{_p(v)} + {_p(u)}*{_p(dv)}")],
                   queda=resultado, sustitucion=True)
        return resultado

    def _cociente(self, u: Any, v: Any, expr: Any, rol: str) -> Any:
        self._reglas.append(COCIENTE)
        self._paso(COCIENTE, expr, rol,
                   tr("la derivada de u/v es (u'*v - u*v')/v^2: derivada del numerador por el denominador, "
                      "menos el numerador por la derivada del denominador, todo dividido entre el denominador al cuadrado."),
                   tr("el numerador es u = {u} y el denominador es v = {v}.", u=texto(u), v=texto(v)))
        du = self.derivar(u, tr("u del cociente"))
        dv = self.derivar(v, tr("v del cociente"))
        resultado = (du * v - u * dv) / v ** 2
        self._paso(COCIENTE, expr, rol,
                   calculo=[tr("Sustituimos u' = {du} y v' = {dv} en (u'*v - u*v')/v^2: {formula}.",
                               du=texto(du), dv=texto(dv),
                               formula=f"({_p(du)}*{_p(v)} - {_p(u)}*{_p(dv)})/{_p(v)}^2")],
                   queda=resultado, sustitucion=True)
        return resultado

    def _cadena_potencia(self, base: Any, n: Any, expr: Any, rol: str) -> Any:
        x = self.var
        forma = f"{_p(base)}^{_p(n)}"
        nota = como_potencia(expr, forma)
        self._reglas.append(CADENA_POTENCIA)
        self._paso(CADENA_POTENCIA, expr, rol,
                   tr("la derivada de u^n es n*u^(n-1)*u', donde u es una función de {x}: "
                      "la regla de la potencia, multiplicada por la derivada de la base (regla de la cadena).", x=x),
                   tr("la base es u = {u} y el exponente n es {n}", u=texto(base), n=texto(n)) + nota)
        du = self.derivar(base, tr("u, la base de la potencia"))
        resultado = n * base ** (n - 1) * du
        calculo = [tr("Sustituimos n = {n} y u' = {du}: {formula}.", n=texto(n), du=texto(du),
                      formula=f"{_p(n)}*{_p(base)}^({texto(n)} - 1)*{_p(du)}")]
        calculo += _resta_exponente(n) + forma_final(base, n - 1)
        calculo += multiplica_numeros(n, du)
        self._paso(CADENA_POTENCIA, expr, rol, calculo=calculo, queda=resultado, sustitucion=True)
        return resultado

    def _logaritmica(self, u: Any, v: Any, expr: Any, rol: str) -> Any:
        x = self.var
        self._reglas.append(LOGARITMICA)
        self._paso(LOGARITMICA, expr, rol,
                   tr("si la base y el exponente dependen de {x}, ninguna regla de potencias sirve. "
                      "Con y = u^v se toma el logaritmo natural (log): log(y) = v*log(u). Derivando los dos lados "
                      "(producto a la derecha, cadena a la izquierda): y'/y = v'*log(u) + v*u'/u, "
                      "y despejando: y' = u^v*(v'*log(u) + v*u'/u).", x=x),
                   tr("la base es u = {u} y el exponente es v = {v}.", u=texto(u), v=texto(v)))
        du = self.derivar(u, tr("u, la base"))
        dv = self.derivar(v, tr("v, el exponente"))
        resultado = expr * (dv * sympy.log(u) + v * du / u)
        self._paso(LOGARITMICA, expr, rol,
                   calculo=[tr("Sustituimos u' = {du} y v' = {dv}: {formula}.", du=texto(du), dv=texto(dv),
                               formula=f"{_p(expr)}*({_p(dv)}*log({texto(u)}) + {_p(v)}*{_p(du)}/{_p(u)})")],
                   queda=resultado, sustitucion=True)
        return resultado
