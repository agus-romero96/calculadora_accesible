"""
Puntos críticos, extremos locales e intervalos de crecimiento de y = f(x), explicados con el
formato de calculo/pasos.py (Regla, En este caso, las cuentas y Queda):

  1. Dominio: los valores que anulan un denominador quedan fuera.
  2. La derivada f'(x), con el paso a paso de Derivar.
  3. Puntos críticos: f'(x) = 0. Una fracción vale 0 si su numerador vale 0, y exp(u) nunca vale
     0; el numerador se resuelve con el motor de ecuaciones (grado 1 o 2) o se factoriza antes
     (factor común, Ruffini...) y se aplica el producto nulo.
  4. Tabla de signos de f'(x): un número de prueba por intervalo y el signo de cada factor;
     f' > 0 creciente, f' < 0 decreciente.
  5. Criterio de la primera derivada: un cambio de signo de f' es un máximo (+ a -) o un mínimo
     (- a +); f(x0) con sus cuentas.
  6. Criterio de la segunda derivada: f''(x) y su signo en cada punto crítico, como confirmación.

El cálculo es el de SymPy (solveset, continuous_domain) y vale para cualquier función con un
número finito de puntos críticos; la explicación, para las que son cociente de polinomios
(y exponenciales). Si no se puede explicar, se da el resultado sin pasos y con una nota.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sympy
from sympy import S

from algebra.resolucion import MotorEcuaciones, SinExplicacion, _aproximado, _cuenta, describible, intervalo_texto
from calculo.calculo import Calculo
from calculo.pasos import PasoCalculo, texto, texto_paso
from calculo.rectas import cuentas_sustitucion
from i18n import tr
from pasos_aritmetica import ExplicadorFactorizar
from pasos_aritmetica import SinExplicacion as SinFactorizacion


@dataclass
class ResultadoExtremos:
    texto: str
    es_error: bool = False
    valor: Optional[Dict[str, Any]] = None   # criticos, maximos, minimos, crece, decrece
    variable: Any = None
    expresion: Any = None
    avisos: List[str] = field(default_factory=list)


def _conjunto_texto(conjunto: Any) -> str:
    """Intervalos unidos: (-∞, -1) ∪ (1, ∞); 'ningún intervalo' si está vacío."""
    if conjunto == S.EmptySet:
        return tr("ningún intervalo")
    piezas = list(conjunto.args) if isinstance(conjunto, sympy.Union) else [conjunto]
    return " ∪ ".join(intervalo_texto(p) for p in sorted(piezas, key=lambda p: float(p.inf)))


def lineas_resultado(valor: Dict[str, Any], x: Any, aproximar: bool = True) -> List[str]:
    """El resultado, una línea por dato (lo usan el informe y la exportación); los valores irracionales, con decimales."""
    numero = _aproximado if aproximar else texto
    criticos = sorted(valor["criticos"], key=float)
    lineas = [tr("Puntos críticos: {puntos}", puntos=", ".join(f"{x} = {texto(c)}" for c in criticos)
                 if criticos else tr("ninguno"))]
    for c, fc in valor["maximos"]:
        lineas.append(tr("Máximo local en {variable} = {punto}: f({punto}) = {valor}", variable=x, punto=texto(c),
                         valor=numero(fc)))
    for c, fc in valor["minimos"]:
        lineas.append(tr("Mínimo local en {variable} = {punto}: f({punto}) = {valor}", variable=x, punto=texto(c),
                         valor=numero(fc)))
    if not valor["maximos"] and not valor["minimos"]:
        lineas.append(tr("Sin extremos locales"))
    lineas.append(tr("Creciente en {intervalos}", intervalos=_conjunto_texto(valor["crece"])))
    lineas.append(tr("Decreciente en {intervalos}", intervalos=_conjunto_texto(valor["decrece"])))
    return lineas


def _orden_factor(base: Any, x: Any) -> Tuple[int, float]:
    """Orden de los factores en la tabla: exponenciales, después los de grado 1 por su raíz (como los puntos críticos)."""
    if isinstance(base, sympy.exp):
        return (0, 0.0)
    if sympy.degree(base, x) == 1:
        return (1, float(sympy.solve(base, x)[0]))
    return (2, 0.0)


def _signo(v: Any) -> str:
    return "+" if v > 0 else "-"


def _signo_texto(v: Any) -> str:
    return tr("positivo") if v > 0 else tr("negativo")


class MotorExtremos:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido
        self.calculo = Calculo(parser_compartido)
        self.ecuaciones = MotorEcuaciones(parser_compartido)

    # --- Fachada ---

    def resolver(self, expresion: str, variable: Optional[str] = None) -> ResultadoExtremos:
        try:
            expr = self.parser.parsear(expresion).doit()
            x, avisos = self.calculo._resolver_variable(expr, variable, "DERIVADA")
            otras = sorted(s.name for s in expr.free_symbols - {x})
            if otras:
                raise ValueError(tr("La función tiene otras letras ({letras}): el signo de la derivada dependería de su "
                                    "valor. Esta operación estudia funciones de una sola variable.",
                                    letras=", ".join(otras)))
            if not expr.has(x):
                raise ValueError(tr("La función es constante: su derivada es 0 en todos los puntos, así que no crece, "
                                    "no decrece y no tiene extremos que estudiar."))
            return self._estudiar(expresion, expr, x, avisos)
        except ValueError as e:
            return ResultadoExtremos(tr("Error de Validación: {error}", error=str(e)), es_error=True)
        except Exception as e:
            return ResultadoExtremos(tr("Error del Sistema: {error}", error=str(e)), es_error=True)

    # --- El cálculo (SymPy) ---

    def _calcular(self, expr: Any, x: Any) -> Tuple[Any, Any, List[Any], Dict[str, Any]]:
        """(dominio, f', puntos que separan los intervalos, valor) con SymPy, sin explicar."""
        dominio = sympy.calculus.util.continuous_domain(expr, x, S.Reals)
        if not describible(dominio) or isinstance(dominio, sympy.FiniteSet):
            raise ValueError(tr("No se puede estudiar el dominio de esta función con los métodos de la calculadora."))
        df = sympy.simplify(sympy.diff(expr, x))
        # Puntos del dominio donde f' no existe (x^(2/3) en 0): pueden ser extremos, pero aún no se estudian
        try:
            # Solo en el interior: en un extremo del dominio (sqrt(x) en 0) no importa, los intervalos son abiertos
            sin_derivada = sympy.Intersection(sympy.calculus.util.singularities(df, x, S.Reals), dominio.interior)
        except Exception:
            sin_derivada = S.EmptySet
        if sin_derivada != S.EmptySet:
            raise ValueError(tr("La derivada no existe en {puntos}, que está en el dominio de la función: ahí puede haber "
                                "un pico. Esta operación estudia funciones derivables en todo su dominio.",
                                puntos=", ".join(f"{x} = {texto(p)}" for p in sin_derivada)
                                if isinstance(sin_derivada, sympy.FiniteSet) else texto(sin_derivada)))
        criticos = sympy.solveset(df, x, dominio)
        if not isinstance(criticos, sympy.FiniteSet) and criticos != S.EmptySet:
            raise ValueError(tr("La derivada se anula en infinitos puntos (o no se pueden hallar): esta operación "
                                "estudia funciones con un número finito de puntos críticos."))
        criticos = sorted(criticos, key=float) if criticos != S.EmptySet else []
        maximos, minimos, crece, decrece = [], [], [], []
        piezas = list(dominio.args) if isinstance(dominio, sympy.Union) else [dominio]
        for pieza in piezas:
            dentro = [c for c in criticos if pieza.contains(c) == S.true]
            bordes = [pieza.start] + dentro + [pieza.end]
            signos = []
            for a, b in zip(bordes, bordes[1:]):
                punto = MotorEcuaciones._punto_de_prueba(a, b)
                valor = sympy.N(df.subs(x, punto))
                signos.append(valor)
                (crece if valor > 0 else decrece).append(sympy.Interval.open(a, b))
            for c, izquierda, derecha in zip(dentro, signos, signos[1:]):
                fc = sympy.simplify(expr.subs(x, c))
                if izquierda > 0 > derecha:
                    maximos.append((c, fc))
                elif izquierda < 0 < derecha:
                    minimos.append((c, fc))
                else:
                    # Sin cambio de signo (x^3 en 0): la función sigue creciendo (o decreciendo) a través de c
                    (crece if izquierda > 0 else decrece).append(sympy.FiniteSet(c))
        valor = {"criticos": sympy.FiniteSet(*criticos), "maximos": maximos, "minimos": minimos,
                 "crece": sympy.Union(*crece) if crece else S.EmptySet,
                 "decrece": sympy.Union(*decrece) if decrece else S.EmptySet}
        separadores = sorted(set(criticos) | {e for p in piezas for e in (p.start, p.end) if e.is_finite}, key=float)
        return dominio, df, separadores, valor

    def _estudiar(self, entrada: str, expr: Any, x: Any, avisos: List[str]) -> ResultadoExtremos:
        dominio, df, separadores, valor = self._calcular(expr, x)
        try:
            pasos = self._explicar(entrada, expr, x, dominio, df, valor, avisos)
        except SinExplicacion:
            pasos = []
            avisos.append(tr("NOTA: hay explicación paso a paso para cocientes de polinomios (y productos por "
                             "exponenciales). Esta función la estudia SymPy, sin pasos."))
        except Exception:
            pasos = []
            avisos.append(tr("AVISO: no se pudo explicar paso a paso; el resultado es el que calcula SymPy."))
        lineas = [tr("RESULTADO:")] + lineas_resultado(valor, x) + avisos + ["=" * 30,
                  tr("Función: f({variable}) = {funcion}", variable=x, funcion=texto(expr)),
                  tr("Dominio: {dominio}", dominio=_conjunto_texto(dominio) if dominio != S.Reals
                     else tr("todos los números reales"))]
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return ResultadoExtremos("\n".join(lineas), valor=valor, variable=x, expresion=expr, avisos=avisos)

    # --- La explicación ---

    @staticmethod
    def _factores(expr: Any, x: Any) -> Tuple[Any, List[Tuple[Any, int]]]:
        """(constante, [(factor, exponente)]) de un producto de polinomios en x y exponenciales."""
        constante, factores = S.One, []
        for parte in sympy.Mul.make_args(sympy.factor(expr)):
            base, exponente = parte.as_base_exp()
            if not parte.has(x):
                constante *= parte
            elif isinstance(parte, sympy.exp):
                factores.append((parte, 1))
            elif base.is_polynomial(x) and exponente.is_Integer and exponente > 0:
                factores.append((base, int(exponente)))
            else:
                raise SinExplicacion()  # log, sqrt, sin...: sin explicación paso a paso
        return constante, factores

    def _explicar(self, entrada, expr, x, dominio, df, valor, avisos) -> List[PasoCalculo]:
        f_num, f_den = sympy.fraction(sympy.together(expr))
        num, den = sympy.fraction(sympy.factor(sympy.together(df)))
        for parte in (f_num, f_den):
            self._factores(parte, x)  # SinExplicacion si no es cociente de polinomios (y exponenciales)
        _, factores_num = self._factores(num, x)
        _, factores_den = self._factores(den, x)
        pasos: List[PasoCalculo] = [self._paso_dominio(f_den, x, dominio)]

        # La derivada
        derivada = self.calculo.CalcularDerivada(entrada, str(x))
        if not derivada.es_exitoso:
            raise SinExplicacion()
        pasos.append(PasoCalculo(
            tr("Derivar la función"),
            regla=tr("el signo de la derivada dice cómo cambia la función: si f'({variable}) > 0 es creciente, si "
                     "f'({variable}) < 0 es decreciente, y donde f'({variable}) = 0 puede haber un máximo o un mínimo. "
                     "Primero se calcula f'({variable}).", variable=x),
            partes=tr("f({variable}) = {funcion}.", variable=x, funcion=texto(expr)),
            calculo=(tr("Los pasos de la derivada van a continuación."),) if derivada.pasos else (),
            queda=f"f'({x}) = {texto(derivada.resultado)}"))
        pasos.extend(derivada.pasos)
        avisos += [a for a in derivada.advertencias if a not in avisos]

        # Puntos críticos
        pasos += self._pasos_criticos(derivada.resultado, num, den, factores_num, x, valor)

        # Tabla de signos de f'
        pasos.append(self._tabla(df, num, den, factores_num, factores_den, x, dominio, valor))

        # Extremos: primera y segunda derivada
        criticos = sorted(valor["criticos"], key=float)
        if criticos:
            # En un cociente, f'' es larga (otra regla del cociente) y solo confirmaría lo que ya decide f'
            cociente = f_den.has(x)
            pasos.append(self._primera_derivada(expr, x, criticos, valor, omite_segunda=cociente))
            if not cociente:
                pasos += self._segunda_derivada(df, x, criticos, valor, avisos)
        return pasos

    def _paso_dominio(self, f_den: Any, x: Any, dominio: Any) -> PasoCalculo:
        if not f_den.has(x):
            return PasoCalculo(
                tr("Dominio"),
                regla=tr("los puntos críticos y los intervalos se buscan dentro del dominio: los valores donde la función "
                         "existe. Un polinomio (o una exponencial) existe para todo número real."),
                partes=tr("la función no tiene denominadores con {variable}.", variable=x),
                queda=tr("todos los números reales"))
        lineas = []
        factorizado = sympy.factor(f_den)
        if texto(factorizado) != texto(f_den):
            lineas.append(tr("Factorizamos el denominador: {denominador}. Se anula si alguno de sus factores vale 0.",
                             denominador=f"{texto(f_den)} = {texto(factorizado)}"))
        vistos = []
        for base, _ in self._factores(f_den, x)[1]:
            if base in vistos:
                continue
            vistos.append(base)
            ceros = sorted(sympy.solveset(base, x, S.Reals), key=float)
            if not ceros:
                lineas.append(tr("El denominador {denominador} no se anula para ningún número real.", denominador=texto(base)))
            elif sympy.degree(base, x) == 1:
                lineas += self.ecuaciones._producto_nulo([base], x)[0]
            else:
                lineas.append(tr("{denominador}: se anula en {valores}.", denominador=texto(base),
                                 valores=tr(" y ").join(f"{x} = {texto(c)}" for c in ceros)))
        return PasoCalculo(
            tr("Dominio"),
            regla=tr("los puntos críticos y los intervalos se buscan dentro del dominio. Una fracción no existe donde su "
                     "denominador vale 0: esos valores quedan fuera."),
            partes=tr("el denominador de f({variable}) es {denominador}.", variable=x, denominador=texto(f_den)),
            calculo=tuple(lineas),
            queda=_conjunto_texto(dominio))

    def _pasos_criticos(self, df_explicada, num, den, factores_num, x, valor) -> List[PasoCalculo]:
        """Resolver f'(x) = 0: el numerador (sin exponenciales ni constantes) igualado a 0."""
        pasos: List[PasoCalculo] = []
        # El numerador sin las exponenciales, con su número delante (3*x^2 - 3 = 0, no x^2 - 1 = 0)
        polinomio = self._factores(num, x)[0] * sympy.Mul(*[b ** e for b, e in factores_num
                                                                if not isinstance(b, sympy.exp)])
        exponenciales = [b for b, _ in factores_num if isinstance(b, sympy.exp)]
        lineas = []
        if den.has(x):
            lineas.append(tr("f'({variable}) es una fracción: vale 0 cuando su numerador vale 0 (el denominador no puede "
                             "valer 0, porque ahí la función no existe).", variable=x))
            lineas.append(tr("Escrita como una sola fracción: f'({variable}) = {fraccion}.", variable=x,
                             fraccion=f"({texto(num)})/({texto(den)})"))
        for e in exponenciales:
            lineas.append(tr("{exponencial} nunca vale 0 (una exponencial siempre es positiva): no da puntos críticos.",
                             exponencial=texto(e)))
        ecuacion = sympy.expand(polinomio)
        pasos.append(PasoCalculo(
            tr("Puntos críticos: resolver f'({variable}) = 0", variable=x),
            regla=tr("un punto crítico es un valor del dominio donde la derivada vale 0 (la tangente es horizontal): "
                     "ahí puede haber un máximo o un mínimo."),
            partes=f"f'({x}) = {texto(df_explicada)}.",
            calculo=tuple(lineas) or (tr("Igualamos la derivada a 0."),),
            queda=f"{texto(ecuacion)} = 0"))
        if not ecuacion.has(x):
            pasos.append(PasoCalculo(
                tr("Sin puntos críticos"),
                regla=tr("si lo que queda es un número distinto de 0, la derivada nunca se anula."),
                partes=tr("queda {numero} = 0.", numero=texto(ecuacion)),
                calculo=(tr("{numero} = 0 es falso: no hay puntos críticos.", numero=texto(ecuacion)),),
                queda=tr("ninguno")))
            return pasos
        if sympy.degree(ecuacion, x) <= 2:
            self.ecuaciones._polinomica(ecuacion, S.Zero, "=", x, pasos)
        elif len(sympy.Add.make_args(ecuacion)) == 1:
            # Un solo término, c*x^k = 0 (k >= 3): solo se anula si x = 0
            coeficiente, potencia = ecuacion.as_coeff_Mul()
            pasos.append(PasoCalculo(
                tr("Potencia igual a 0"),
                regla=tr("un producto vale 0 solo si alguno de sus factores vale 0, y una potencia {variable}^k vale 0 "
                         "solo si su base vale 0.", variable=x),
                partes=tr("{expresion} = 0: el número {numero} no es 0, así que {potencia} = 0.",
                          expresion=texto(ecuacion), numero=texto(coeficiente), potencia=texto(potencia)),
                calculo=(tr("{potencia} = 0 solo si {variable} = 0.", potencia=texto(potencia), variable=x),),
                queda=f"{x} = 0"))
        else:
            factorizador = ExplicadorFactorizar()
            try:
                producto = factorizador.explicar(ecuacion)
            except SinFactorizacion:
                raise SinExplicacion()
            pasos.extend(factorizador.pasos)
            factores = [b for b in (f.as_base_exp()[0] for f in sympy.Mul.make_args(producto)) if b.has(x)]
            lineales = [f for f in factores if sympy.degree(f, x) == 1]
            otros = [f for f in factores if sympy.degree(f, x) != 1]
            if any(sympy.degree(f, x) > 2 for f in otros):
                raise SinExplicacion()
            cuentas, raices = self.ecuaciones._producto_nulo(lineales, x)
            pasos.append(PasoCalculo(
                tr("Aplicar el producto nulo"),
                regla=tr("Propiedad del producto nulo: si un producto vale 0, alguno de sus factores vale 0."),
                partes=tr("{expresion} = {producto}.", expresion=texto(ecuacion), producto=texto(producto)),
                calculo=tuple(cuentas) or (tr("Los factores de grado 2 se resuelven a continuación."),),
                queda=tr(" o ").join(f"{x} = {texto(r)}" for r in sorted(set(raices), key=float)) or tr("ninguno")))
            for f in otros:
                self.ecuaciones._polinomica(f, S.Zero, "=", x, pasos)
        criticos = sorted(valor["criticos"], key=float)
        pasos.append(PasoCalculo(
            tr("Puntos críticos"),
            regla=tr("son las soluciones de f'({variable}) = 0 que están en el dominio.", variable=x),
            partes=tr("soluciones dentro del dominio: {soluciones}.",
                      soluciones=", ".join(f"{x} = {texto(c)}" for c in criticos) or tr("ninguna")),
            queda=", ".join(f"{x} = {texto(c)}" for c in criticos) or tr("ninguno")))
        return pasos

    def _tabla(self, df, num, den, factores_num, factores_den, x, dominio, valor) -> PasoCalculo:
        criticos = sorted(valor["criticos"], key=float)
        piezas = list(dominio.args) if isinstance(dominio, sympy.Union) else [dominio]
        fuera = sorted({e for p in piezas for e in (p.start, p.end) if e.is_finite}, key=float)
        constante = self._factores(num, x)[0] / self._factores(den, x)[0]
        factorizada = sympy.factor(df)
        lineas = []
        if texto(factorizada) != texto(df):
            lineas.append(tr("Factorizamos con las raíces: {polinomio} = {factorizado}.", polinomio=f"f'({x})",
                             factorizado=texto(factorizada)))
        intervalos = []
        for pieza in piezas:
            dentro = [c for c in criticos if pieza.contains(c) == S.true]
            bordes = [pieza.start] + dentro + [pieza.end]
            intervalos += [sympy.Interval.open(a, b) for a, b in zip(bordes, bordes[1:])]
        separan = sorted(set(criticos) | set(fuera), key=float)
        if separan and fuera:
            lineas.append(tr("Los puntos críticos y los que no están en el dominio ({puntos}) dividen la recta en "
                             "{n} intervalos: {intervalos}.", puntos=", ".join(texto(p) for p in separan),
                             n=len(intervalos), intervalos=", ".join(intervalo_texto(i) for i in intervalos)))
        elif separan:
            lineas.append(tr("Los puntos críticos {puntos} dividen la recta en {n} intervalos: {intervalos}.",
                             puntos=tr(" y ").join(texto(p) for p in separan), n=len(intervalos),
                             intervalos=", ".join(intervalo_texto(i) for i in intervalos)))
        else:
            lineas.append(tr("No hay puntos críticos ni puntos fuera del dominio: la derivada tiene el mismo signo en "
                             "toda la recta, y basta probar un número."))
        for intervalo in intervalos:
            punto = MotorEcuaciones._punto_de_prueba(intervalo.start, intervalo.end)
            lineas.append(tr("Intervalo {intervalo}: probamos con {variable} = {punto}.",
                             intervalo=intervalo_texto(intervalo), variable=x, punto=texto(punto)))
            signos = []
            if constante != 1:
                lineas.append(tr("   El número {numero}: {signo}.", numero=texto(constante), signo=_signo_texto(constante)))
                signos.append(_signo(constante))
            for base, exponente in sorted(factores_num + factores_den, key=lambda f: _orden_factor(f[0], x)):
                factor = base ** exponente
                if isinstance(base, sympy.exp):
                    lineas.append(tr("   {factor}: siempre positivo.", factor=texto(factor)))
                    signos.append("+")
                    continue
                cuenta, v = _cuenta(factor, x, punto)
                lineas.append(tr("   {factor} = {cuenta}: {signo}.", factor=texto(factor), cuenta=cuenta,
                                 signo=_signo_texto(v)))
                signos.append(_signo(v))
            resultado = "+" if signos.count("-") % 2 == 0 else "-"
            lineas.append(tr("   Signo de f'({variable}): {signos} = {resultado}. La función es {comportamiento} en "
                             "{intervalo}.", variable=x, signos="*".join(f"({s})" for s in signos) or "(+)",
                             resultado=resultado, comportamiento=tr("creciente") if resultado == "+" else
                             tr("decreciente"), intervalo=intervalo_texto(intervalo)))
        return PasoCalculo(
            tr("Intervalos de crecimiento"),
            regla=tr("entre dos puntos críticos seguidos (o puntos fuera del dominio) la derivada no cambia de signo: "
                     "basta probar un número de cada intervalo. Un producto o cociente es positivo si tiene un número "
                     "par de factores negativos. Si f' > 0, la función crece; si f' < 0, decrece."),
            partes=tr("f'({variable}) = {derivada}.", variable=x, derivada=texto(factorizada)),
            calculo=tuple(lineas),
            queda=tr("creciente en {crece}; decreciente en {decrece}", crece=_conjunto_texto(valor["crece"]),
                     decrece=_conjunto_texto(valor["decrece"])))

    def _primera_derivada(self, expr, x, criticos, valor, omite_segunda: bool = False) -> PasoCalculo:
        maximos = dict(valor["maximos"])
        minimos = dict(valor["minimos"])
        lineas = []
        for c in criticos:
            if c in maximos:
                lineas.append(tr("En {variable} = {punto}, f' pasa de + a -: la función sube y luego baja, así que es un "
                                 "máximo local.", variable=x, punto=texto(c)))
            elif c in minimos:
                lineas.append(tr("En {variable} = {punto}, f' pasa de - a +: la función baja y luego sube, así que es un "
                                 "mínimo local.", variable=x, punto=texto(c)))
            else:
                crece = valor["crece"].contains(c) == S.true
                lineas.append(tr("En {variable} = {punto}, f' no cambia de signo ({signo} a los dos lados): no es un "
                                 "extremo, y la función sigue {sentido} a través de ese punto.", variable=x,
                                 punto=texto(c), signo="+" if crece else "-",
                                 sentido=tr("creciendo") if crece else tr("decreciendo")))
                continue
            fc = maximos.get(c, minimos.get(c))
            lineas.append(tr("Valor de la función en {punto}:", punto=texto(c)))
            lineas += ["   " + l for l in cuentas_sustitucion(expr, x, c, fc)]
            lineas.append(tr("   f({punto}) = {valor}.", punto=texto(c), valor=texto(fc)))
        if omite_segunda and (maximos or minimos):
            lineas.append(tr("En un cociente, la segunda derivada exige otra regla del cociente y solo confirmaría lo que "
                             "ya decide el cambio de signo de f': no se calcula."))
        return PasoCalculo(
            tr("Criterio de la primera derivada"),
            regla=tr("en un punto crítico, si f' pasa de positiva a negativa la función tiene un máximo local; si pasa "
                     "de negativa a positiva, un mínimo local; si no cambia de signo, no hay extremo."),
            partes=tr("los signos de f' son los de la tabla del paso anterior."),
            calculo=tuple(lineas),
            queda="; ".join(lineas_resultado(valor, x)[1:-2]))

    def _segunda_derivada(self, df, x, criticos, valor, avisos) -> List[PasoCalculo]:
        segunda = self.calculo.CalcularDerivada(texto(df), str(x))
        if not segunda.es_exitoso:
            return []
        d2 = segunda.resultado
        pasos = [PasoCalculo(
            tr("Segunda derivada"),
            regla=tr("criterio de la segunda derivada: en un punto crítico x0, si f''(x0) < 0 hay un máximo local (la "
                     "curva es cóncava hacia abajo), si f''(x0) > 0 un mínimo local (cóncava hacia arriba), y si "
                     "f''(x0) = 0 el criterio no decide. Primero se deriva f'({variable}).", variable=x),
            partes=f"f'({x}) = {texto(df)}.",
            calculo=(tr("Los pasos de la derivada van a continuación."),) if segunda.pasos else (),
            queda=f"f''({x}) = {texto(d2)}")]
        pasos.extend(segunda.pasos)
        maximos, minimos = dict(valor["maximos"]), dict(valor["minimos"])
        lineas = []
        for c in criticos:
            v = sympy.simplify(d2.subs(x, c))
            lineas.append(tr("En {variable} = {punto}:", variable=x, punto=texto(c)))
            lineas += ["   " + l for l in cuentas_sustitucion(d2, x, c, v)]
            if v.is_zero:
                conclusion = tr("f''({punto}) = 0: el criterio no decide; vale lo que dice la primera derivada.",
                                punto=texto(c))
            elif v < 0:
                conclusion = tr("f''({punto}) = {valor}, negativo: máximo local, como dijo la primera derivada.",
                                punto=texto(c), valor=texto(v))
                if c not in maximos:
                    raise SinExplicacion()
            else:
                conclusion = tr("f''({punto}) = {valor}, positivo: mínimo local, como dijo la primera derivada.",
                                punto=texto(c), valor=texto(v))
                if c not in minimos:
                    raise SinExplicacion()
            lineas.append("   " + conclusion)
        pasos.append(PasoCalculo(
            tr("Criterio de la segunda derivada"),
            regla=tr("se sustituye cada punto crítico en f''({variable}): su signo confirma si es máximo o mínimo.",
                     variable=x),
            partes=f"f''({x}) = {texto(d2)}.",
            calculo=tuple(lineas),
            queda="; ".join(lineas_resultado(valor, x)[1:-2])))
        return pasos
