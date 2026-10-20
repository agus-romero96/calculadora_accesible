from __future__ import annotations

from typing import Any, List, Optional, Tuple
import sympy
from sympy import S

from calculo.pasos import PasoCalculo, entre_parentesis, texto
from i18n import N_, tr
from ._pasos import (cuenta, paso_evaluacion, paso_sustitucion, tendencia,
                     FORMA_CERO_CERO, FORMA_INF_MENOS_INF)
from ._base import (
    Estrategia,
    ResultadoEstrategia,
    ESTADO_FINITO,
    ESTADO_INFINITO,
    ESTADO_NO_CONCLUYENTE,
)


class RacionalizacionRaices(Estrategia):
    """
    Estrategia de Racionalización (enfocada en límites).

    Idea:
      - Detectar binomios del tipo (A + B) o (A - B) donde aparece una raíz (sqrt).
      - Multiplicar y dividir por el conjugado para generar un producto notable
        (A+B)(A-B) = A^2 - B^2
      - Simplificar y recién ahí evaluar el límite.

    Nota crucial:
      - NO usamos simplify() como pre-procesado, porque puede destruir la estructura
        (ej: (sqrt(1+x)-1)/(x/(sqrt(1+x)+1)) se simplifica a 1).
    """

    def nombre(self) -> str:
        return N_("Racionalización")

    def puede_resolver(self, expr, var, punto, **kwargs) -> bool:
        if cuenta(expr, var, punto) is not None:
            return False
        _, forma = paso_sustitucion(expr, var, punto, kwargs.get("dir"))
        if forma not in (FORMA_CERO_CERO, FORMA_INF_MENOS_INF):
            bloques = self._find_blocks(expr)
            if not any(paso_sustitucion(b, var, punto, kwargs.get("dir"))[1]
                       == FORMA_INF_MENOS_INF for b in bloques):
                return False
        expr_s = self._prep(expr)

        # Debe existir una raíz cuadrada en algún lugar
        if not self._tiene_raiz_cuadrada(expr_s):
            return False

        # Y además debe existir al menos un bloque conjugable (binomio con raíz)
        num, den = expr_s.as_numer_denom()
        candidatos = self._find_blocks(num) + self._find_blocks(den)

        # Caso típico: suma plana (sqrt(x+1) - sqrt(x)) con den=1
        if not candidatos and den == 1:
            candidatos = self._find_blocks(expr_s)

        return bool(candidatos)

    def resolver(self, expr, var, punto, **kwargs) -> ResultadoEstrategia:
        if not self.puede_resolver(expr, var, punto, **kwargs):
            return ResultadoEstrategia(aplica=False)
        dir_ = kwargs.get("dir", None)
        expr_s = self._prep(expr)

        pasos: List[Any] = []

        num, den = expr_s.as_numer_denom()

        # 1) Recolectar candidatos (binomios dentro de num/den, aunque estén anidados)
        intentos: List[Tuple[str, Any]] = []
        bloques_num = self._find_blocks(num)
        bloques_den = self._find_blocks(den)

        # Caso especial: suma “plana” cuando den = 1
        if den == 1 and expr_s.is_Add:
            bloques_num.extend(self._find_blocks(expr_s))

        for b in bloques_num:
            intentos.append((N_("Numerador"), b))
        for b in bloques_den:
            intentos.append((N_("Denominador"), b))

        if not intentos:
            return ResultadoEstrategia(
                aplica=True,
                estado=ESTADO_NO_CONCLUYENTE,
                resultado=None,
                nombre_estrategia=self.nombre(),
                explicacion=N_("No se encontraron binomios conjugables claros para racionalizar."),
                pasos=pasos,
                expr_original=expr,
                expr_trabajo=expr_s,
            )

        # 2) Probar racionalizar: el primero que produzca un límite evaluable gana
        for ubicacion, bloque in intentos:
            bloque_norm, conj = self._normalize_and_conjugate(bloque)


            try:
                # Racionalizamos multiplicando por conj/conj.
                # Expandimos SOLO el lado donde queremos disparar el producto notable.
                if ubicacion == "Numerador":
                    numerador_nuevo = sympy.expand(num * conj)
                    denominador_nuevo = sympy.Mul(den, conj, evaluate=False)
                else:
                    numerador_nuevo = sympy.Mul(num, conj, evaluate=False)
                    denominador_nuevo = sympy.expand(den * conj)

                nueva_expr = numerador_nuevo / denominador_nuevo

                # Cancelación es CLAVE para quitar el factor que causa 0/0
                nueva_expr_simp = sympy.cancel(nueva_expr)

            except Exception:
                continue

            limite_candidato = self._limite_seguro(nueva_expr_simp, var, punto, dir_)

            if self._es_resuelto(limite_candidato, var):
                res_final = sympy.simplify(limite_candidato)

                pasos = self._pasos(expr_s, var, punto, dir_, ubicacion, bloque, num, den, nueva_expr_simp, res_final)

                estado = ESTADO_FINITO
                if res_final in (S.Infinity, S.NegativeInfinity) or getattr(res_final, "is_infinite", False):
                    estado = ESTADO_INFINITO

                return ResultadoEstrategia(
                    aplica=True,
                    estado=estado,
                    resultado=res_final,
                    nombre_estrategia=self.nombre(),
                    explicacion=tr("Racionalización del {ubicacion}: el conjugado eliminó la indeterminación.", ubicacion=tr(ubicacion).lower()),
                    pasos=pasos,
                    expr_original=expr,
                    expr_trabajo=nueva_expr_simp,
                )

        return ResultadoEstrategia(
            aplica=True,
            estado=ESTADO_NO_CONCLUYENTE,
            resultado=None,
            nombre_estrategia=self.nombre(),
            explicacion=N_("Se intentaron racionalizaciones posibles, pero ninguna permitió evaluar el límite."),
            pasos=pasos,
            expr_original=expr,
            expr_trabajo=expr_s,
        )

    # ---------------- Pasos ----------------

    def _pasos(self, expr: Any, var: sympy.Symbol, punto: Any, dir_: Optional[str], ubicacion: str, bloque: Any,
               num: Any, den: Any, nueva: Any, valor: Any) -> List[PasoCalculo]:
        """Sustitución, racionalización con el conjugado (A - B)(A + B) = A^2 - B^2 y límite final."""
        paso_inicial, _ = paso_sustitucion(expr, var, punto, dir_)

        # El bloque como A - B, con A un término sin signo menos: sqrt(x + 1) - 1 da A = sqrt(x + 1) y B = 1;
        # 3 - sqrt(x + 9), A = 3 y B = sqrt(x + 9)
        positivos = [termino for termino in bloque.args if not termino.could_extract_minus_sign()]
        a = positivos[0] if positivos else bloque.args[0]
        b = sympy.expand(a - bloque)
        conjugado = a + b
        cuadrados = sympy.expand(a ** 2 - b ** 2)
        lado = num if ubicacion == "Numerador" else den
        lado_nuevo = sympy.expand(lado * conjugado)
        otro = den if ubicacion == "Numerador" else num
        en_el_lado = tr("numerador") if ubicacion == "Numerador" else tr("denominador")

        calculo = [tr("Multiplicamos el numerador y el denominador por el conjugado, {conjugado}: "
                      "es multiplicar por 1, así que el límite no cambia.", conjugado=texto(conjugado)),
                   tr("En el {lado}: ({a} - {b})*({a} + {b}) = {a2} - {b2} = {resultado}.", lado=en_el_lado,
                      a=texto(a), b=entre_parentesis(b) if b.could_extract_minus_sign() else texto(b),
                      a2=f"{entre_parentesis(a)}^2", b2=f"{entre_parentesis(b)}^2", resultado=texto(cuadrados))]
        if lado != bloque:
            calculo.append(tr("Con el resto de factores, el {lado} queda {nuevo}.", lado=en_el_lado, nuevo=texto(lado_nuevo)))
        if ubicacion == "Numerador":
            transformada = f"{entre_parentesis(lado_nuevo)}/({texto(otro)}*{entre_parentesis(conjugado)})" if otro != 1                 else f"{entre_parentesis(lado_nuevo)}/{entre_parentesis(conjugado)}"
        else:
            transformada = f"{texto(otro)}*{entre_parentesis(conjugado)}/{entre_parentesis(lado_nuevo)}" if otro != 1                 else f"{entre_parentesis(conjugado)}/{entre_parentesis(lado_nuevo)}"
        calculo.append(tr("La expresión queda {expresion}.", expresion=transformada))
        if texto(nueva) != transformada:
            calculo.append(tr("Simplificamos la expresión transformada: {expresion}.",
                              expresion=texto(nueva)))
        paso = PasoCalculo(
            tr("Racionalizar con el conjugado"),
            regla=tr("si una resta (o suma) con raíces, A - B, produce la indeterminación, se multiplican numerador "
                     "y denominador por su conjugado, A + B: como (A - B)*(A + B) = A^2 - B^2, las raíces cuadradas "
                     "desaparecen al elevarlas al cuadrado."),
            partes=tr("en el {lado} está {bloque}: A = {a} y B = {b}, y su conjugado es {conjugado}.", lado=en_el_lado,
                      bloque=texto(bloque), a=texto(a), b=texto(b), conjugado=texto(conjugado)),
            calculo=tuple(calculo),
            queda=tr("lim {expresion} cuando {tendencia}", expresion=texto(nueva), tendencia=tendencia(var, punto, dir_)))
        return [p for p in (paso_inicial, paso, paso_evaluacion(nueva, var, punto, dir_, valor)) if p]

    # ---------------- Helpers ----------------

    def _prep(self, expr: Any) -> Any:
        """
        Preparación *suave*:
        - together() agrupa fracciones (ideal para fracción-de-fracciones)
        - NO simplify(), NO cancel() aquí (para no destruir patrones tipo #37)
        """
        try:
            return sympy.together(expr)
        except Exception:
            return expr

    def _es_raiz_cuadrada(self, node: Any) -> bool:
        # Detecta x**(1/2); sqrt(x) en SymPy también es Pow(..., 1/2)
        if isinstance(node, sympy.Pow):
            try:
                return sympy.simplify(node.exp - S.Half) == 0
            except Exception:
                return False
        return False

    def _tiene_raiz_cuadrada(self, expr: Any) -> bool:
        try:
            return any(self._es_raiz_cuadrada(t) for t in sympy.preorder_traversal(expr))
        except Exception:
            return False

    def _find_blocks(self, expr_part: Any) -> List[Any]:
        """
        Encuentra binomios (Add de 2 términos) donde al menos uno tenga raíz cuadrada.
        ✅ FIX: antes solo funcionaba si expr_part era Add; ahora recorre TODO el árbol.
        """
        out: List[Any] = []
        try:
            for node in sympy.preorder_traversal(expr_part):
                if isinstance(node, sympy.Add):
                    args = node.args
                    if len(args) == 2 and any(self._tiene_raiz_cuadrada(a) for a in args):
                        out.append(node)
        except Exception:
            pass

        # únicos, preservando orden
        uniq: List[Any] = []
        seen = set()
        for b in out:
            s = sympy.srepr(b)
            if s not in seen:
                seen.add(s)
                uniq.append(b)
        return uniq

    def _normalize_and_conjugate(self, block: Any) -> Tuple[Any, Any]:
        """
        Para Add(a, b), conjugado = a - b.
        Si el bloque era a - b, SymPy lo representa como Add(a, -b),
        y entonces a - (-b) = a + b, que es el conjugado correcto.
        """
        a, b = block.args[0], block.args[1]
        conj = a - b
        return block, conj

    def _es_resuelto(self, val: Any, var: sympy.Symbol) -> bool:
        """
        ✅ FIX: consideramos 'resuelto' si:
          - SymPy devolvió algo evaluado (no Limit, no None, no nan/zoo)
          - y el resultado YA NO DEPENDE de la variable del límite (var).
        Esto permite parámetros (a, b, etc.) sin rechazar todo por free_symbols.
        """
        if not self._es_limite_evaluable(val):
            return False
        if val is sympy.nan or val is sympy.zoo:
            return False
        if isinstance(val, sympy.Limit):
            return False

        try:
            return var not in val.free_symbols
        except Exception:
            # Si no sabemos, preferimos no declararlo resuelto
            return False
