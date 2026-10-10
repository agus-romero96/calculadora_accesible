"""
Sistemas 2x2 por los métodos clásicos (sustitución, igualación, reducción), explicados con
el formato de calculo/pasos.py: Regla, En este caso, las cuentas y Queda.

Las ecuaciones intermedias se resuelven con algebra/ecuaciones.despejar(), que muestra cada
transformación (quitar paréntesis, agrupar, pasar términos, dividir), y al final se comprueba
la solución en las ecuaciones originales. El texto empieza por el RESULTADO, como el resto
de la calculadora.
"""
from typing import Any, Dict, List, Tuple

import sympy

from algebra.ecuaciones import comprobar, despejar, ecuacion_texto, normalizada, sin_evaluar, sustituir
from calculo.pasos import PasoCalculo, entre_parentesis, texto, texto_paso
from i18n import N_, tr

Ecuacion = Tuple[Any, Any]


class MotorSistemasClasicos:
    def __init__(self, parser_compartido):
        self.parser = parser_compartido

    # Nombre visible de cada método (el identificador interno no lleva tildes)
    NOMBRES_METODO = {
        "sustitucion": N_("Sustitución"),
        "igualacion": N_("Igualación"),
        "reduccion": N_("Reducción"),
    }

    # --- Lectura ---

    def _parsear_ecuaciones(self, lista_txt: List[str]) -> Tuple[List[Ecuacion], List[sympy.Symbol]]:
        """Ecuaciones (izquierda, derecha) tal como se escribieron, y sus incógnitas en orden alfabético."""
        ecuaciones: List[Ecuacion] = []
        todas = set()
        for txt in lista_txt:
            if not txt.strip():
                continue
            try:
                if "=" in txt:
                    partes = txt.split("=")
                    if len(partes) != 2:
                        raise ValueError(tr("debe tener exactamente un signo '='."))
                    # El parser no evalúa (evaluate=False): doit() da la forma normal
                    izquierda = self.parser.parsear(partes[0]).doit()
                    derecha = self.parser.parsear(partes[1]).doit()
                else:
                    izquierda, derecha = self.parser.parsear(txt).doit(), sympy.S.Zero
                if not sympy.Poly(izquierda - derecha).is_linear:
                    raise ValueError(tr("La ecuación '{txt}' no es lineal.", txt=txt))
                ecuaciones.append((izquierda, derecha))
                todas.update((izquierda - derecha).free_symbols)
            except Exception as e:
                raise ValueError(tr("Error de sintaxis en '{txt}': {e}", txt=txt, e=str(e)))
        return ecuaciones, sorted(todas, key=lambda s: s.name)

    # --- Pasos comunes ---

    def _paso_resolver(self, izquierda: Any, derecha: Any, variable: sympy.Symbol, escrita: str = None,
                       derecha_escrita: str = None) -> Tuple[PasoCalculo, Any]:
        lineas, valor = despejar(izquierda, derecha, variable, escrita, derecha_escrita)
        paso = PasoCalculo(
            tr("Resolver la ecuación en {variable}", variable=variable),
            regla=tr("una ecuación de primer grado se resuelve quitando paréntesis, agrupando términos semejantes, "
                     "pasando los términos con la incógnita a un lado y los números al otro (cambiando de signo), "
                     "y dividiendo entre el coeficiente de la incógnita."),
            partes=tr("la ecuación es {ecuacion}, con una sola incógnita, {variable}.",
                      ecuacion=f"{escrita or texto(izquierda)} = {derecha_escrita or texto(derecha)}",
                      variable=variable),
            calculo=tuple(lineas),
            queda=f"{variable} = {texto(valor)}")
        return paso, valor

    def _paso_hallar(self, variable: sympy.Symbol, expresion: Any, conocida: sympy.Symbol, valor_conocido: Any,
                     de_donde: str) -> Tuple[PasoCalculo, Any]:
        valor = sympy.simplify(expresion.subs(conocida, valor_conocido))
        cuenta = sustituir(expresion, {conocida: valor_conocido})
        cuenta = cuenta if cuenta == texto(valor) else f"{cuenta} = {texto(valor)}"
        paso = PasoCalculo(
            tr("Hallar {variable}", variable=variable),
            regla=tr("con una incógnita ya conocida, se sustituye su valor en una expresión de la otra."),
            partes=tr("{conocida} = {valor} y {de_donde}: {variable} = {expresion}.", conocida=conocida,
                      valor=texto(valor_conocido), de_donde=de_donde, variable=variable, expresion=texto(expresion)),
            calculo=(tr("Sustituimos {conocida} = {valor}: {variable} = {cuenta}.", conocida=conocida,
                        valor=texto(valor_conocido), variable=variable, cuenta=cuenta),),
            queda=f"{variable} = {texto(valor)}")
        return paso, valor

    def _paso_comprobar(self, ecuaciones: List[Ecuacion], solucion: Dict[sympy.Symbol, Any]) -> PasoCalculo:
        return PasoCalculo(
            tr("Comprobación"),
            regla=tr("se sustituyen los valores en las ecuaciones originales: si las dos se cumplen, la solución es correcta."),
            partes=", ".join(f"{v} = {texto(valor)}" for v, valor in solucion.items()) + ".",
            calculo=tuple(comprobar(ecuaciones, solucion)),
            queda=", ".join(f"{v} = {texto(valor)}" for v, valor in solucion.items()))

    @staticmethod
    def _coeficiente(ecuacion: Ecuacion, variable: sympy.Symbol) -> Any:
        return sympy.expand(ecuacion[0] - ecuacion[1]).coeff(variable)

    # --- Métodos ---

    def _sustitucion(self, ecs: List[Ecuacion], x: sympy.Symbol, y: sympy.Symbol) -> Tuple[List[PasoCalculo], Dict]:
        # Se despeja la incógnita con coeficiente 1 o -1, si la hay: así no aparecen fracciones
        candidatos = [(0, x), (0, y), (1, x), (1, y)]
        elegido = next((c for c in candidatos if abs(self._coeficiente(ecs[c[0]], c[1])) == 1), candidatos[0])
        i, var = elegido
        otra_var = y if var == x else x
        j = 1 - i
        (izq, der), (izq2, der2) = ecs[i], ecs[j]

        lineas, despeje = despejar(izq, der, var)
        coef = self._coeficiente(ecs[i], var)
        motivo = (tr(", porque su coeficiente es {c} y así no aparecen fracciones", c=texto(coef))
                  if abs(coef) == 1 else "")
        pasos = [PasoCalculo(
            tr("Despejar {variable} en la ecuación {i}", variable=var, i=i + 1),
            regla=tr("en el método de sustitución se despeja una incógnita en una de las ecuaciones y se sustituye "
                     "en la otra, que queda con una sola incógnita."),
            partes=tr("elegimos la ecuación {i}, {ecuacion}, y despejamos {variable}{motivo}.", i=i + 1,
                      ecuacion=ecuacion_texto(izq, der), variable=var, motivo=motivo),
            calculo=tuple(lineas),
            queda=f"{var} = {texto(despeje)}")]

        escrita = sustituir(izq2, {var: despeje}) if izq2.has(var) else texto(izq2)
        derecha_escrita = sustituir(der2, {var: despeje}) if der2.has(var) else texto(der2)
        nueva_izq, nueva_der = sin_evaluar(izq2, {var: despeje}), sin_evaluar(der2, {var: despeje})
        pasos.append(PasoCalculo(
            tr("Sustituir en la ecuación {j}", j=j + 1),
            regla=tr("donde aparece {variable} se escribe su despeje, entre paréntesis: valen lo mismo.", variable=var),
            partes=tr("la ecuación {j} es {ecuacion} y {variable} = {despeje}.", j=j + 1,
                      ecuacion=ecuacion_texto(izq2, der2), variable=var, despeje=texto(despeje)),
            calculo=(tr("Cambiamos {variable} por ({despeje}): {ecuacion}.", variable=var, despeje=texto(despeje),
                        ecuacion=f"{escrita} = {derecha_escrita}"),),
            queda=f"{escrita} = {derecha_escrita}"))

        paso, valor = self._paso_resolver(nueva_izq, nueva_der, otra_var, escrita, derecha_escrita)
        pasos.append(paso)
        paso, valor_var = self._paso_hallar(var, despeje, otra_var, valor, tr("el despeje del paso 1 es"))
        pasos.append(paso)
        return pasos, {x: valor if otra_var == x else valor_var, y: valor if otra_var == y else valor_var}

    def _igualacion(self, ecs: List[Ecuacion], x: sympy.Symbol, y: sympy.Symbol) -> Tuple[List[PasoCalculo], Dict]:
        # Se despeja en las dos la incógnita con más coeficientes 1 o -1
        def comodos(v):
            return sum(abs(self._coeficiente(e, v)) == 1 for e in ecs)
        var = x if comodos(x) >= comodos(y) else y
        otra_var = y if var == x else x

        pasos: List[PasoCalculo] = []
        despejes = []
        for i, (izq, der) in enumerate(ecs):
            lineas, despeje = despejar(izq, der, var)
            despejes.append(despeje)
            pasos.append(PasoCalculo(
                tr("Despejar {variable} en la ecuación {i}", variable=var, i=i + 1),
                regla=(tr("en el método de igualación se despeja la misma incógnita en las dos ecuaciones y se igualan "
                          "los dos despejes.") if i == 0 else
                       tr("se despeja la misma incógnita, {variable}, para poder igualar.", variable=var)),
                partes=tr("la ecuación {i} es {ecuacion}.", i=i + 1, ecuacion=ecuacion_texto(izq, der)),
                calculo=tuple(lineas) or (tr("{variable} ya está despejada.", variable=var),),
                queda=f"{var} = {texto(despeje)}"))

        igualdad = f"{texto(despejes[0])} = {texto(despejes[1])}"
        pasos.append(PasoCalculo(
            tr("Igualar los despejes"),
            regla=tr("si {variable} = A y {variable} = B, entonces A = B: queda una ecuación con una sola incógnita.",
                     variable=var),
            partes=tr("A = {a} y B = {b}.", a=texto(despejes[0]), b=texto(despejes[1])),
            calculo=(tr("Igualamos: {igualdad}.", igualdad=igualdad),),
            queda=igualdad))
        paso, valor = self._paso_resolver(despejes[0], despejes[1], otra_var)
        pasos.append(paso)
        paso, valor_var = self._paso_hallar(var, despejes[0], otra_var, valor, tr("el despeje de la ecuación 1 es"))
        pasos.append(paso)
        return pasos, {x: valor if otra_var == x else valor_var, y: valor if otra_var == y else valor_var}

    def _reduccion(self, ecs: List[Ecuacion], x: sympy.Symbol, y: sympy.Symbol) -> Tuple[List[PasoCalculo], Dict]:
        normales = [normalizada(izq, der, [x, y]) for izq, der in ecs]
        pasos: List[PasoCalculo] = []
        if any(ecuacion_texto(*n) != ecuacion_texto(*e) for n, e in zip(normales, ecs)):
            pasos.append(PasoCalculo(
                tr("Ordenar las ecuaciones"),
                regla=tr("para sumarlas, cada ecuación se escribe con las incógnitas a la izquierda, en el mismo orden, "
                         "y el número a la derecha (los términos que cambian de lado cambian de signo)."),
                partes=tr("las ecuaciones son {ecuaciones}.", ecuaciones="; ".join(ecuacion_texto(*e) for e in ecs)),
                calculo=tuple(tr("Ecuación {i}: {antes} queda {despues}.", i=i, antes=ecuacion_texto(*e),
                                 despues=ecuacion_texto(*n)) for i, (e, n) in enumerate(zip(ecs, normales), 1)),
                queda="; ".join(ecuacion_texto(*n) for n in normales)))

        # Se elimina la incógnita con el mínimo común múltiplo más pequeño (multiplicadores más sencillos)
        def coste(v):
            c1, c2 = (self._coeficiente(n, v) for n in normales)
            return sympy.ilcm(abs(c1), abs(c2)) if c1.is_Integer and c2.is_Integer and c1 and c2 else sympy.oo
        eliminada = x if coste(x) <= coste(y) else y
        queda_var = y if eliminada == x else x
        c1, c2 = (self._coeficiente(n, eliminada) for n in normales)
        if c1.is_Integer and c2.is_Integer:
            mcm = sympy.ilcm(abs(c1), abs(c2))
            m1 = mcm / abs(c1)
            m2 = -sympy.sign(c1) * sympy.sign(c2) * mcm / abs(c2)
        else:
            m1, m2 = c2, -c1
        pasos.append(PasoCalculo(
            tr("Elegir la incógnita que se elimina"),
            regla=tr("en el método de reducción se multiplican las ecuaciones por números elegidos para que una "
                     "incógnita tenga coeficientes opuestos (iguales y de signo contrario): al sumar las ecuaciones, "
                     "esa incógnita desaparece."),
            partes=tr("eliminamos {variable}: su coeficiente es {c1} en la ecuación 1 y {c2} en la ecuación 2.",
                      variable=eliminada, c1=texto(c1), c2=texto(c2)),
            calculo=(tr("Multiplicamos la ecuación 1 por {m1} y la ecuación 2 por {m2}: {c1}*{m1} = {p1} y {c2}*{m2} = {p2}, "
                        "que son opuestos.", m1=entre_parentesis(m1), m2=entre_parentesis(m2), c1=entre_parentesis(c1),
                        c2=entre_parentesis(c2), p1=texto(c1 * m1), p2=texto(c2 * m2)),),
            queda=tr("ecuación 1 por {m1}, ecuación 2 por {m2}", m1=texto(m1), m2=texto(m2))))

        multiplicadas = []
        lineas = []
        for i, ((izq, der), m) in enumerate(zip(normales, (m1, m2)), 1):
            nueva = (sympy.expand(m * izq), sympy.expand(m * der))
            multiplicadas.append(nueva)
            if m == 1:
                lineas.append(tr("Ecuación {i} por 1: queda igual, {ecuacion}.", i=i, ecuacion=ecuacion_texto(*nueva)))
            else:
                lineas.append(tr("Ecuación {i} por {m}: {m}*({izquierda}) = {m}*{derecha}, es decir {ecuacion}.", i=i,
                                 m=entre_parentesis(m), izquierda=texto(izq), derecha=entre_parentesis(der),
                                 ecuacion=ecuacion_texto(*nueva)))
        pasos.append(PasoCalculo(
            tr("Multiplicar las ecuaciones"),
            regla=tr("multiplicar los dos lados de una ecuación por el mismo número (distinto de 0) da una ecuación "
                     "equivalente: cada término se multiplica por ese número."),
            partes=tr("multiplicadores: {m1} para la ecuación 1 y {m2} para la ecuación 2.", m1=texto(m1), m2=texto(m2)),
            calculo=tuple(lineas),
            queda="; ".join(ecuacion_texto(*e) for e in multiplicadas)))

        (i1, d1), (i2, d2) = multiplicadas
        suma_izq, suma_der = sympy.expand(i1 + i2), sympy.expand(d1 + d2)
        lineas = []
        for v in (eliminada, queda_var):
            a, b = i1.coeff(v), i2.coeff(v)
            lineas.append(tr("Términos en {variable}: {a}*{variable} + {b}*{variable} = {suma}.", variable=v,
                             a=entre_parentesis(a), b=entre_parentesis(b), suma=texto((a + b) * v)))
        lineas.append(tr("Lado derecho: {a} + {b} = {suma}.", a=texto(d1), b=entre_parentesis(d2), suma=texto(suma_der)))
        pasos.append(PasoCalculo(
            tr("Sumar las ecuaciones"),
            regla=tr("se suman lado a lado (izquierda con izquierda y derecha con derecha): como los coeficientes de "
                     "{variable} son opuestos, sus términos se anulan.", variable=eliminada),
            partes=tr("sumamos {e1} y {e2}.", e1=ecuacion_texto(i1, d1), e2=ecuacion_texto(i2, d2)),
            calculo=tuple(lineas),
            queda=ecuacion_texto(suma_izq, suma_der)))

        paso, valor = self._paso_resolver(suma_izq, suma_der, queda_var)
        pasos.append(paso)

        # La otra incógnita, sustituyendo en la ecuación 1 original
        izq, der = ecs[0]
        escrita = sustituir(izq, {queda_var: valor}) if izq.has(queda_var) else texto(izq)
        derecha_escrita = sustituir(der, {queda_var: valor}) if der.has(queda_var) else texto(der)
        lineas, valor_elim = despejar(sin_evaluar(izq, {queda_var: valor}), sin_evaluar(der, {queda_var: valor}),
                                      eliminada, escrita, derecha_escrita)
        pasos.append(PasoCalculo(
            tr("Hallar {variable}", variable=eliminada),
            regla=tr("con una incógnita ya conocida, se sustituye su valor en una de las ecuaciones originales y se "
                     "despeja la otra."),
            partes=tr("{conocida} = {valor} y la ecuación 1 es {ecuacion}.", conocida=queda_var, valor=texto(valor),
                      ecuacion=ecuacion_texto(izq, der)),
            calculo=(tr("Sustituimos {conocida} = {valor}: {ecuacion}.", conocida=queda_var, valor=texto(valor),
                        ecuacion=f"{escrita} = {derecha_escrita}"),) + tuple(lineas),
            queda=f"{eliminada} = {texto(valor_elim)}"))
        solucion = {eliminada: valor_elim, queda_var: valor}
        return pasos, {x: solucion[x], y: solucion[y]}

    # --- Sistemas sin solución única ---

    def _paso_sin_solucion_unica(self, ecs: List[Ecuacion], x: sympy.Symbol, y: sympy.Symbol,
                                 incompatible: bool) -> PasoCalculo:
        (a1, b1, c1), (a2, b2, c2) = [(self._coeficiente(e, x), self._coeficiente(e, y), normalizada(*e, [x, y])[1])
                                      for e in ecs]
        lineas = [tr("Ecuación 1: {a}*{x} + {b}*{y} = {c}; ecuación 2: {a2}*{x} + {b2}*{y} = {c2}.", a=entre_parentesis(a1),
                     b=entre_parentesis(b1), c=texto(c1), a2=entre_parentesis(a2), b2=entre_parentesis(b2),
                     c2=texto(c2), x=x, y=y),
                  tr("Determinante de los coeficientes: {a}*{b2} - {b}*{a2} = {det}: las incógnitas tienen coeficientes "
                     "proporcionales.", a=entre_parentesis(a1), b2=entre_parentesis(b2), b=entre_parentesis(b1),
                     a2=entre_parentesis(a2), det=texto(a1 * b2 - b1 * a2))]
        if incompatible:
            lineas.append(tr("Los lados izquierdos son proporcionales pero los derechos no: las ecuaciones se "
                             "contradicen (son rectas paralelas, que no se cortan)."))
        else:
            lineas.append(tr("También los lados derechos son proporcionales: las dos ecuaciones dicen lo mismo (son la "
                             "misma recta), y cada punto de ella es una solución."))
        return PasoCalculo(
            tr("Comparar las ecuaciones"),
            regla=tr("un sistema 2x2 tiene una única solución solo si el determinante de los coeficientes, "
                     "a1*b2 - b1*a2, no es 0. Si es 0, las dos rectas son paralelas (sin solución) o la misma "
                     "(infinitas soluciones)."),
            partes=tr("las ecuaciones son {ecuaciones}.", ecuaciones="; ".join(ecuacion_texto(*e) for e in ecs)),
            calculo=tuple(lineas),
            queda=tr("sin solución") if incompatible else tr("infinitas soluciones"))

    # --- Fachada ---

    def ExplicarSistemaClasico(self, lista_ecuaciones: List[str], metodo_preferido: str = "sustitucion") -> str:
        return self.resolver(lista_ecuaciones, metodo_preferido)[0]

    def resolver(self, lista_ecuaciones: List[str], metodo_preferido: str = "sustitucion") -> Tuple[str, Any, bool]:
        """Devuelve (texto accesible, solución SymPy o None, es_error)."""
        try:
            if metodo_preferido not in self.NOMBRES_METODO:
                return tr("Error: Método desconocido. Use 'sustitucion', 'igualacion' o 'reduccion'."), None, True
            ecs, variables = self._parsear_ecuaciones(lista_ecuaciones)

            if len(variables) != 2 or len(ecs) != 2:
                # Derivación profesional: si no es 2x2, se sugiere la herramienta correcta
                return "\n".join([
                    tr("Nota: El sistema tiene {variables} variables y {ecuaciones} ecuaciones.",
                       variables=len(variables), ecuaciones=len(ecs)),
                    tr("Los métodos clásicos (Sustitución, etc.) son didácticos para 2x2."),
                    tr("Para este caso, por favor use la opción 'Gauss-Jordan' del menú, que es el método universal adecuado."),
                ]), None, False

            x, y = variables
            A, B = sympy.linear_eq_to_matrix([sympy.Eq(i, d) for i, d in ecs], variables)
            encabezado = [tr("MÉTODO: {metodo}", metodo=tr(self.NOMBRES_METODO[metodo_preferido])),
                          tr("Sistema 2x2 con las incógnitas {variables}:", variables=f"{x}, {y}")]
            encabezado += [tr("Ecuación {n}: {ecuacion}", n=n, ecuacion=ecuacion_texto(*e)) for n, e in enumerate(ecs, 1)]

            if A.det() == 0:
                incompatible = A.rank() < A.row_join(B).rank()
                resultado = (tr("Sin solución: SISTEMA INCOMPATIBLE (las rectas son paralelas).") if incompatible else
                             tr("Infinitas soluciones: SISTEMA INDETERMINADO (las dos ecuaciones son la misma recta)."))
                pasos = [self._paso_sin_solucion_unica(ecs, x, y, incompatible)]
                texto_final = self._componer([tr("RESULTADO: {valor}", valor=resultado)], encabezado, pasos)
                return texto_final, (sympy.EmptySet if incompatible else None), False

            metodo = {"sustitucion": self._sustitucion, "igualacion": self._igualacion,
                      "reduccion": self._reduccion}[metodo_preferido]
            pasos, solucion = metodo(ecs, x, y)

            # La verdad matemática: la solución de SymPy debe ser la de los pasos
            verdad = sympy.solve([sympy.Eq(i, d) for i, d in ecs], variables, dict=True)[0]
            if any(sympy.simplify(solucion[v] - verdad[v]) != 0 for v in variables):
                solucion = verdad
                pasos = []
            else:
                pasos.append(self._paso_comprobar(ecs, solucion))

            resultado = [tr("RESULTADO:")] + [f"{v} = {texto(solucion[v])}" for v in variables]
            return (self._componer(resultado, encabezado, pasos),
                    [sympy.Eq(v, solucion[v]) for v in variables], False)

        except ValueError as ve:
            return tr("Error de Validación: {error}", error=str(ve)), None, True
        except Exception as e:
            return tr("Error del Sistema: {error}", error=str(e)), None, True

    @staticmethod
    def _componer(resultado: List[str], encabezado: List[str], pasos: List[PasoCalculo]) -> str:
        lineas = resultado + ["=" * 30] + encabezado
        if pasos:
            lineas += ["", tr("PASO A PASO:")] + [texto_paso(i, p) for i, p in enumerate(pasos, 1)]
        return "\n".join(lineas)
