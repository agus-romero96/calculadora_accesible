# Auditoría del Proyecto: Calculadora Accesible (v1.7.0)

Este documento reúne todos los errores (bugs), pasos matemáticos erróneos o confusos y propuestas de mejora de interfaz y accesibilidad encontrados en la revisión completa del código.

Está organizado con encabezados y listas numeradas (sin tablas) para que sea cómodo de leer línea por línea con lector de pantalla.

---

## Parte 1: Bugs Matemáticos, de Parser y de Exportación

### 1. Ecuaciones racionales: raíces extrañas que dividen entre cero (`algebra/resolucion.py`, líneas 175 a 185)
- **Qué ocurre**: La función `_preparar(lado)` evalúa cada sumando con `t.doit()` antes de detectar las incógnitas y las restricciones del dominio. Si la ecuación tiene un término como `x/x` o `(x - 2)/(x - 2)`, `t.doit()` lo convierte en `1` y borra el denominador.
- **Cómo reproducirlo**:
  - Escribir `(x - 2)/(x - 2) + x = 3` y pulsar `Ctrl+R`. Devuelve `RESULTADO: x = 2`, cuando en `x = 2` la ecuación original divide entre cero y no tiene solución.
  - Escribir `x/x = 1` y pulsar `Ctrl+R`. Da error diciendo `"No hay ninguna incógnita"`, cuando la solución es todos los reales salvo el 0.
- **Cómo corregirlo**: Detectar las variables y los denominadores sobre la expresión sin simplificar antes de llamar a `_preparar`, o no evaluar en `_preparar` términos que contengan variables en un denominador.

### 2. Ecuaciones racionales igualadas a cero: fallo que pierde el paso a paso (`algebra/resolucion.py`, líneas 164, 732 y 781 a 800)
- **Qué ocurre**: En `_racional`, se obtienen los términos de cada lado con `_terminos(expr)`, que filtra el `0` y devuelve una lista vacía `[]`. Cuando un lado de la ecuación racional es `0`, `nuevos["der"]` queda vacío y en la línea 800 `nuevos["der"][0]` lanza `IndexError: list index out of range`. El bloque `except` exterior lo captura y descarta toda la explicación paso a paso.
- **Cómo reproducirlo**:
  - Escribir `1/x - 2 = 0`, `(x - 1)/(x + 2) = 0` o `1/x + 1/(x + 1) = 0` y pulsar `Ctrl+R`. Muestra el resultado de SymPy con el aviso `"No se pudo explicar esta ecuación paso a paso"`.
- **Cómo corregirlo**: Si `nuevos["der"]` (o `nuevos["izq"]`) queda vacío, usar `sympy.S.Zero`.

### 3. Ecuaciones de primer grado con coeficientes irracionales (`algebra/ecuaciones.py`, líneas 99 a 108 y `calculo/pasos.py`, línea 113)
- **Qué ocurre**: En `despejar`, `con_izq = izquierda.coeff(variable) * variable` queda como `x*(1 + sqrt(2))` sin expandir, por lo que `sin_izq = izquierda - con_izq` no se cancela a `0` sino que queda `x + sqrt(2)*x - x*(1 + sqrt(2))`. Después, el bucle cree que esos términos no tienen `x` y genera pasos falsos pasándolos al otro lado.
- **Cómo reproducirlo**:
  - Escribir `sqrt(2)*x + x = 1` y pulsar `Ctrl+R`.
- **Cómo corregirlo**: Calcular `sin_izq = sympy.expand(izquierda - con_izq)` (o separar los términos con `.has(variable)`) y sacar factor común `(1 + sqrt(2))*x`.

### 4. Sistemas 2x2 por método clásico cuando una ecuación solo tiene una incógnita (`algebra/classic_systems.py`, líneas 51 y 107 a 261)
- **Qué ocurre**:
  1. En `_sustitucion` (líneas 107-115), si ningún coeficiente es `1` o `-1`, elige despejar `x` en la primera ecuación sin comprobar si `x` aparece en ella.
  2. En `_igualacion` (líneas 147-156), intenta despejar la misma incógnita en las dos ecuaciones aunque en una de ellas su coeficiente sea `0`.
  3. En `_reduccion` (líneas 194-205), si en la ecuación 1 falta `x` y en la ecuación 2 falta `y` (por ejemplo `y = 3` y `x = 2`), calcula `mcm = sympy.ilcm(0, 1) = 0` y divide `0 / 0 = nan`, o multiplica una ecuación por `0`. Además, en las líneas 257-261 sustituye siempre en la primera ecuación aunque no contenga la incógnita eliminada.
  4. En `_parsear_ecuaciones` (línea 51), si una ecuación se reduce a una constante (`x - x = 0`), `sympy.Poly(0)` lanza `GeneratorsNeeded`.
- **Cómo reproducirlo**:
  - Escribir en dos líneas `2*y = 4` y `3*x + 2*y = 10` y resolver por Sustitución, Igualación o Reducción.
  - Escribir en dos líneas `y = 3` y `x = 2` y resolver por Reducción o Igualación.

### 5. Evaluar expresiones que dan números complejos o infinito (`aritmetica.py`, líneas 96 a 100)
- **Qué ocurre**: Cuando el resultado exacto de `Evaluar` no es un entero o racional simple (por ejemplo `sqrt(-4) = 2*I`, `asin(2)`, `tan(pi/2) = zoo` o `log(0) = -oo`), `es_trivial` vale `False` y la línea 98 ejecuta `f"{decimal:.10f}"` sobre un objeto que no es un decimal real, lanzando `TypeError: unsupported format string`.
- **Cómo reproducirlo**:
  - Escribir `sqrt(-4)`, `asin(2)`, `log(0)` o `tan(pi/2)` y pulsar `Ctrl+Enter`.
- **Cómo corregirlo**: Si el resultado es infinito (`oo`, `-oo`, `zoo`, `nan`) o tiene parte imaginaria no nula (`not exacto.is_real`), informar claramente que no es un número real finito en lugar de formatearlo con `:.10f`.

### 6. Funciones escritas en español (`sen`, `tg`) y símbolos Unicode (`π`, `√`, `×`) (`parser_matematico.py`, líneas 19 a 45 y 119 a 193)
- **Qué ocurre**:
  1. `"sen"` y `"tg"` no están en `FUNCIONES_CONOCIDAS` ni en el contexto del parser. Si el usuario escribe `sen(x)`, el parser lo parte letra a letra como `s * E * n * x` (tres variables multiplicadas por el número `e` de Euler) sin dar error.
  2. Si el usuario escribe `arcsin(x)` o `arccos(x)`, el mensaje de sugerencia parte el prefijo `arc` con asteriscos y pregunta: `"¿Quiso decir a*r*c*sin(x)?"`.
  3. `pasos_aritmetica.leer_cuenta` convierte `√`, `π` y `×`, pero `ParserMatematico.parsear` no lo hace; al evaluar `2π`, `ParserMatematico` cree que `π` es una variable y falla antes de llegar a `leer_cuenta`.
  4. La validación de paréntesis (línea 116) solo cuenta cuántos `(` y `)` hay, por lo que `")("` pasa esa comprobación y muestra un `SyntaxError` crudo de Python.
- **Cómo reproducirlo**:
  - Simplificar `sen(x)` (`Ctrl+S`): devuelve `RESULTADO: E*n*s*x`.
  - Simplificar `arcsin(x)`: sugiere `a*r*c*sin(x)`.
  - Evaluar `2π` o `√(4)` (`Ctrl+Enter`).

### 7. Derivada implícita: términos semejantes sin agrupar en el resultado (`calculo/implicita.py`, líneas 254 a 322)
- **Qué ocurre**: En `MotorImplicita._despejar`, las listas `con` (términos con `y'`) y `sin` (términos sin `y'`) se forman juntando los términos de ambos lados pero nunca se suman entre sí antes de construir el texto del cociente `final`. Si la suma de `sin` vale `0` (por ejemplo `[1, -1]`), `sympy.gcd(0, 2*y)` da `2*y`, divide cada término entre `2*y` y devuelve `1/(2*y) - 1/(2*y)` en lugar de `0`.
- **Cómo reproducirlo**:
  - Escribir `x + y^2 = x + 1` y pulsar `Ctrl+J`: devuelve `RESULTADO: dy/dx = (1/(2*y) - 1/(2*y))` y afirma que el numerador y el denominador tienen factor común `2*y`.
  - Escribir `x^2 + 3*y = x + y` y pulsar `Ctrl+J`: devuelve `RESULTADO: dy/dx = (1 - 2*x)/(3 - 1)` sin restar `3 - 1 = 2`.
  - Escribir `x + y^2 = 2*x` y pulsar `Ctrl+J`: devuelve `RESULTADO: dy/dx = (2 - 1)/(2*y)`.

### 8. Ecuaciones diferenciales: `Despeje._logaritmo` corrompe la solución cuando `C` no está sumando (`calculo/edo.py`, líneas 479 a 503)
- **Qué ocurre**: Al despejar `log(y) = der`, `_logaritmo` comprueba `if not (self.constantes and der.has(C)):` y asume siempre que `der` tiene la forma `resto + C`, escribiendo `y = C * exp(der - C)`. Cuando `C` está dentro de una fracción (como `log(y) = 1/(-x + C)`), `der - C` sigue teniendo `C`, así que inventa el paso falso `exp(1/(-x + C)) = exp(C)*exp(-C + 1/(-x + C))`, falla la comprobación con SymPy y descarta todos los pasos.
- **Cómo reproducirlo**:
  - Escribir `y' = y*log(y)^2` y pulsar `Ctrl+Shift+R`.

### 9. Ecuaciones diferenciales: `Despeje._paso` elimina la rama negativa de `Abs(u)` aunque `C` esté sumando (`calculo/edo.py`, líneas 411 a 419)
- **Qué ocurre**: Cuando despeja `Abs(u) = der` y `der` contiene `C`, asume que `±der` se absorbe siempre cambiando `C` por `-C` (`"Como C es cualquier constante, ±C también lo es"`). Eso solo es cierto si `C` multiplica a todo el lado derecho (`C*f(x)`), pero no si suma (`x + C`, donde `+(x + C)` tiene pendiente `1` y `-(x + C) = -x - C` tiene pendiente `-1`).

### 10. Ecuaciones diferenciales con raíces pares (`sqrt(y)`): fallo de comprobación y soluciones particulares falsas (`calculo/edo.py`, líneas 465 a 472, 858 a 899, 1066 a 1076 y 2109 a 2120)
- **Qué ocurre**:
  1. En `y' = 2*x*sqrt(y)`, al elevar al cuadrado `sqrt(y) = x^2/2 + C` queda `y = (x^2/2 + C)^2`, que solo cumple la ecuación donde `x^2/2 + C >= 0`. A diferencia de `_bernoulli` (que guarda esa condición en `self._condiciones`), `_separable` no la guarda, por lo que `_comprobadas` y `checkodesol` ven que `2*x*(x^2/2 + C) != 2*x*Abs(x^2/2 + C)` y descartan toda la explicación paso a paso.
  2. En `y' = sqrt(y)`, el paso de `"Comprobación"` escribe `Lado izquierdo: x/2 + C`, `Lado derecho: sqrt((x/2 + C)^2) = Abs(x/2 + C)` y concluye `"Los dos lados valen lo mismo"` sin mencionar que solo coinciden cuando `x/2 + C >= 0`.
  3. En `y' = sqrt(y), y(0) = 1`, al sustituir `x = 0, y = 1` en `y = (x/2 + C)^2` salen `C = 1` y `C = -1`. `_condicion_inicial` (línea 2113) solo comprueba si la curva pasa por `(0, 1)`, pero no si cumple la ecuación diferencial en `x = 0`. Para `C = -1`, `y = (x/2 - 1)^2` tiene `y'(0) = -1 != sqrt(1) = 1`, por lo que devuelve una solución particular falsa.
- **Cómo reproducirlo**:
  - `y' = 2*x*sqrt(y)` (`Ctrl+Shift+R`): pierde todos los pasos.
  - `y' = sqrt(y), y(0) = 1` (`Ctrl+Shift+R`): devuelve la solución falsa `y = (x/2 - 1)^2` junto con la verdadera `y = (x/2 + 1)^2`.

### 11. Ecuaciones diferenciales: notación `y'(x)`, `y(t)` y `dy(x)/dx` mal interpretada (`calculo/edo.py`, líneas 587 y 612 a 621)
- **Qué ocurre**: En `_leer`:
  1. La línea 612 quita `(x)` de `y(x)` antes de que la línea 621 reemplace `y'` por el marcador `d1_y`. Si el usuario escribe `y'(x) = 2*x`, el `(x)` detrás de `y'` no se quita y queda `d1_y * x = 2*x`, resolviendo silenciosamente `x*y' = 2*x` (`y = 2*x + C`) en lugar de `y' = 2*x` (`y = x^2 + C`).
  2. La línea 612 descarta la letra entre paréntesis de `y(t)`, así que `y' = 2*y(t)` toma `x` como variable independiente en lugar de `t`.
  3. `dy(x)/dx = 2*x` no se reconoce como derivada de Leibniz porque `derivada_leibniz` se ejecuta antes de limpiar `y(x)`.
- **Cómo reproducirlo**:
  - Escribir `y'(x) = 2*x` y pulsar `Ctrl+Shift+R`: devuelve `RESULTADO: y = 2*x + C` (resultado matemáticamente incorrecto).

### 12. Ecuaciones diferenciales: fallo de `PolynomialError` en `_OrdenSuperior._forma` (`calculo/edo.py`, línea 2837)
- **Qué ocurre**: Al inspeccionar `g(x)` para ver si aplica coeficientes indeterminados, la línea 2837 ejecuta `sympy.Poly(f.args[0], x).degree() == 1` dentro de `exp(...)` sin comprobar antes `f.args[0].is_polynomial(x)`. Si `g(x)` tiene `exp(sqrt(x))`, `exp(1/x)` o `exp(sin(x))`, lanza `sympy.PolynomialError` y aborta la explicación en lugar de pasar a variación de parámetros.
- **Cómo reproducirlo**:
  - Escribir `y'' - 2*y' + y = exp(sqrt(x))` o `y'' + y = exp(sin(x))` y pulsar `Ctrl+Shift+R`.

### 13. Ecuaciones diferenciales de orden superior: fallo con condiciones iniciales cuando la solución tiene `log(Abs(...))` (`calculo/edo.py`, líneas 2898 a 2916)
- **Qué ocurre**: `_OrdenSuperior.condiciones` deriva `solucion` directamente con `sympy.diff(derivada, x)` sin cambiar antes `log(Abs(u))` por `log(u)` (como sí hacen `_comprobacion` y `_cumple`). Como las variables son reales, `sympy.diff(log(Abs(u)), x)` produce `Derivative(Abs(u), x)`, que no se puede evaluar en `x0` y hace fallar la explicación.
- **Cómo reproducirlo**:
  - `y'' + y = 1/cos(x), y(0) = 0, y'(0) = 0` (`Ctrl+Shift+R`).
  - `x^2*y'' - 3*x*y' + 4*y = 0, y1 = x^2, y(1) = 1, y'(1) = 2` (`Ctrl+Shift+R`).

### 14. Ecuaciones diferenciales reducibles de orden 2: pérdida de soluciones constantes, fallo en condiciones iniciales y en `y'' = f(y)` (`calculo/edo.py`, líneas 992, 1946 a 2002 y 2180 a 2185)
- **Qué ocurre**:
  1. En `y'' = y'^2`, al resolver `p' = p^2` encuentra la solución singular `p = 0`, pero la línea 1956 filtra `if s.lhs == p and s.has(C)` y descarta `p = 0` (`y' = 0 -> y = C1`), perdiendo las soluciones constantes y fallando si la condición inicial tiene `y'(x0) = 0`.
  2. Cuando tiene condiciones iniciales (por ejemplo `y'' = y'^2, y(0) = 0, y'(0) = -1`), intenta hallar `C1` y `C2` con `resolver_sistema`, que usa `algebra.ecuaciones.despejar` (solo válido para ecuaciones lineales en `C1`), fallando cuando `C1` está en `-1/C1 = -1` o `log(Abs(C1))`.
  3. En las ecuaciones sin `x` de la forma `y'' = f(y)` (como `y'' = 2*y^3`), `p*dp/dy = 2*y^3` da `p^2 = y^4 + C` (dos ramas `p = ±sqrt(...)`), y la línea 1983 (`if len(explicitas) != 1: return None`) las rechaza todas.
  4. Al llamar a `self._explicar(sub, pasos, avisos)` dentro de `_reducir_orden`, se insertan un segundo paso `"Planteamiento"` y un paso `"Comprobación"` intermedio de `p` a mitad del desarrollo antes de `"Volver a y"`.

### 15. Series de potencias con condiciones iniciales: términos desordenados o resultado `y = O(x^7)` (`calculo/edo.py`, líneas 97 a 116 y 2879 a 2896)
- **Qué ocurre**:
  1. En `condiciones_serie`, al sustituir `C1` y `C2` por números distintos de cero (por ejemplo `y(0) = 1, y'(0) = 1` o `y(0) = 2, y'(0) = 3`), la suma no agrupa ni ordena las potencias de menor a mayor: devuelve `y = 1 + x^3/6 + x^6/180 + x + x^4/12 + O(x^7)` (`x^6` antes que `x`) o `y = 2*(x^6/180 + x^3/6 + 1) + 3*(x^4/12 + x) + O(x^7)`.
  2. Si las condiciones son `y(0) = 0, y'(0) = 0`, filtra los términos que valen `0` y deja únicamente `RESULTADO: y = O(x^7)` en vez de `y = 0`.
- **Cómo reproducirlo**:
  - `y'' - x*y = 0, y(0) = 1, y'(0) = 1` (`Ctrl+Shift+R`).
  - `y'' - x*y = 0, y(0) = 0, y'(0) = 0` (`Ctrl+Shift+R`).

### 16. Transformada de Laplace con exponencial y escalón: pérdida de factor constante (`calculo/edo.py`, líneas 3035 a 3038 y 3062 a 3063)
- **Qué ocurre**: Cuando el término derecho tiene `exp(a*t)*heaviside(t - c)` (por ejemplo `y' + y = exp(-t)*heaviside(t - 1), y(0) = 0`), la transformada tiene `exponencial = exp(-s - 1)`. La línea 3037 divide entre `exp(-s - 1)` pero la línea 3062 solo recupera `c = -exponencial.args[0].coeff(s) = 1`, perdiendo el factor `exp(-1)`. La comprobación por tramos detecta que la solución no cumple la ecuación y descarta los pasos.
- **Cómo reproducirlo**:
  - Escribir `y' + y = exp(-t)*heaviside(t - 1), y(0) = 0` y pulsar `Ctrl+Shift+R`.

### 17. Condición inicial en ecuaciones de Clairaut: ignora la solución singular (`calculo/edo.py`, líneas 2085 a 2090)
- **Qué ocurre**: En `_condicion_inicial`, cuando una solución no tiene constante `C` (como la solución singular `y = -x^2/4` de Clairaut), la línea 2086 comprueba `sympy.simplify(s.rhs - y0) == 0` sin sustituir `x = x0` (`s.rhs.subs(x, x0) - y0`), por lo que nunca comprueba si la solución singular cumple la condición inicial.
- **Cómo reproducirlo**:
  - Escribir `y = x*y' + y'^2, y(2) = -1` y pulsar `Ctrl+Shift+R`.

### 18. Límites que oscilan en el infinito: muestra `AccumBounds(-1, 1)` crudo (`calculo/router.py`, líneas 18 a 30 y `calculo/lim_estrategias/continuidad.py`, líneas 83 y 282 a 305)
- **Qué ocurre**: `ContinuidadComposicion` acepta límites internos `L = oo` o `-oo` y afirma que `sin` o `cos` *"es continua para todo L real"*, devolviendo `sin(oo) = AccumBounds(-1, 1)` como si fuera un resultado finito, y `humanizar_limite` en `router.py` no traduce `AccumBounds`.
- **Cómo reproducirlo**:
  - Calcular el límite de `sin(x)` o `sin(x^2)` cuando `x -> oo` (`Ctrl+L`): la primera línea dice `RESULTADO: AccumBounds(-1, 1)`.

### 19. Extremos, Recta tangente y Polinomio de Taylor en puntos no derivables (`abs(x)`, `x^(2/3)`) (`calculo/extremos.py`, líneas 127 a 136; `calculo/rectas.py`, líneas 189 a 202; `calculo/taylor.py`, líneas 197 a 241)
- **Qué ocurre**:
  1. En `Extremos y crecimiento` (`calculo/extremos.py`), como en SymPy `diff(Abs(x), x) = sign(x)` y `sign(0) = 0`, `solveset(sign(x), x, S.Reals)` devuelve `x = 0` como si la derivada valiera `0` en `0`, en lugar de detectar que `abs(x)` tiene un pico en `x = 0` donde no es derivable.
  2. En `Polinomio de Taylor` (`calculo/taylor.py`), para `abs(x)` de orden `1` en `x0 = 0`, evalúa `sign(0) = 0` pero `sympy.series` calcula la serie lateral derecha `x`; al no coincidir, muestra `RESULTADO: P_1(x) = x` con aviso de fallo en lugar de indicar que `abs(x)` no es derivable en `0`.
  3. En `Recta tangente` (`calculo/rectas.py`), para `x^(2/3)` en `x0 = 0`, el límite lateral izquierdo de la derivada en SymPy da un número complejo (`oo*(-1)**(1/3)`), por lo que solo ve el límite derecho `+oo` y dice que hay tangente vertical `x = 0` en lugar de detectar el pico (derivadas laterales `-oo` y `+oo`).

### 20. Exportación a MathML y HTML: `_sin_mfenced` borra las comas en conjuntos e intervalos (`exportar.py`, líneas 239 a 256)
- **Qué ocurre**: En MathML, la etiqueta `<mfenced open="{" close="}">` dibuja automáticamente comas entre sus elementos hijos, por lo que SymPy genera `<mfenced close="}" open="{"><mn>1</mn><mn>2</mn></mfenced>` sin `<mo>,</mo>` adentro. Al sustituir `<mfenced>` por `<mrow><mo>{</mo>...<mo>}</mo></mrow>` con una expresión regular simple sin intercalar `<mo>,</mo>` entre los hijos, el conjunto `{1, 2}` se convierte en `{12}` y el intervalo `[-2, 2]` se convierte en `[-2 2]`.
- **Cómo reproducirlo**:
  - Resolver `x^2 - 3*x + 2 = 0` (`Ctrl+R`) y copiar como MathML (`Ctrl+Shift+M`) o exportar a HTML (`Ctrl+E`): la solución se lee y se ve como `{12}` en lugar de `{1, 2}`.
  - Resolver `x^2 <= 4` (`Ctrl+R`) y exportar a HTML: el intervalo se lee como `[-2 2]`.

### 21. Exportación y modo "Solo el resultado": doble prefijo `RESULTADO: RESULTADO:` (`exportar.py`, líneas 60 a 63, 77 a 79 y 110 a 112)
- **Qué ocurre**:
  1. Cuando `res.valor is None` (por ejemplo, en un sistema incompatible o con infinitas soluciones en Gauss-Jordan o sistemas 2x2), `resultado_corto(res)` devuelve la primera línea de `res.texto`, que ya empieza por `"RESULTADO: ..."`. Luego `resumen(res)` le vuelve a poner delante `"RESULTADO: "`, mostrando `RESULTADO: RESULTADO: Infinitas soluciones...`.
  2. En `resultado_corto(res)`, las líneas 60-63 llaman a `humanizar_limite(valor)` y `humanizar_integral(valor)` antes de comprobar `if valor is None:` (línea 77). Si una entrada del historial perdió el objeto SymPy al cargarse (`valor=None`), devuelve `"None"` o `"No concluyente"` en vez de leer la primera línea del texto.
- **Cómo reproducirlo**:
  - Escribir en dos líneas `x + y = 2` y `2*x + 2*y = 4`, pulsar `Ctrl+Enter` y luego `Ctrl+Shift+P` (ocultar paso a paso).

### 22. Exportación a MathML/LaTeX en Polinomio de Taylor, Derivada implícita y Extremos (`exportar.py`, líneas 201, 208 a 215, 279 a 307 y 405)
- **Qué ocurre**:
  1. `exportar.latex()` tiene casos especiales para `implicita` (añade `\frac{dy}{dx} =`) y `taylor` (añade `P_n(x) =` y ordena en potencias de `x - x0`), pero `exportar.mathml()` no los tiene: en MathML solo sale la expresión suelta y con las potencias al revés.
  2. `_latex_extremos` une sus líneas con `\\`, pero `a_latex` lo mete dentro de `\begin{equation*} ... \end{equation*}` (donde `\\` no salta de línea en LaTeX si no lleva `\begin{aligned}` o `\begin{gathered}`).

### 23. Matrices: entradas con espacios/comas, matriz vacía `"[]"` y ceros sin evaluar (`algebra/matrix_logic.py`, líneas 55 a 79 y 105; `algebra/determinante.py`, líneas 92 a 143)
- **Qué ocurre**:
  1. `_parsear_matriz_seguro` hace `fila.replace(',', ' ').split()`, partiendo por espacios incluso cuando el usuario separó las columnas con comas (`"x + 1, 2"` se parte en 4 elementos).
  2. Como `ParserMatematico` usa `evaluate=False`, una entrada como `1 - 1` en una matriz no se evalúa a `0`, y `determinante.py` (`v == 0`) no la detecta como cero al elegir la fila o columna con más ceros.
  3. Si se escribe `[]` y se pulsa `Ctrl+M` (Matriz inversa), `filas == 0` no se valida y genera un informe vacío diciendo `det(A) =  = 0` seguido de `Queda: det(A) = 1`.

---

## Parte 2: Pasos Pedagógicos Erróneos o Confusos

### 1. Estrategias de límites que se activan cuando NO hay indeterminación (`calculo/lim_estrategias/`)
- **Racionalización innecesaria (`racionalizacion.py`, líneas 37 a 131)**:
  - No comprueba si la sustitución directa ya da el resultado ni si existe indeterminación `0/0` o `oo - oo`.
  - **Ejemplo**: Límite de `sqrt(x) + 1` cuando `x -> 4` (`Ctrl+L`). En el paso 1 sustituye y obtiene `3`, pero aun así aplica el método de Racionalización, multiplica y divide por `1 - sqrt(x)` y dice: `"Simplificamos (se cancela el factor que producía la indeterminación)"`. Lo mismo ocurre en `(sqrt(x) - 1)/(x + 1)` cuando `x -> 0` (que vale `-1` directamente).
- **Límite trigonométrico notable innecesario (`trigonometria.py`, líneas 192 a 272)**:
  - No comprueba si el denominador también tiende a `0`.
  - **Ejemplo**: Límite de `sin(x)` cuando `x -> 0` (`Ctrl+L`). En el paso 1 ya obtiene `sin(0) = 0`, pero en el paso 2 divide y multiplica artificialmente por `x`: `sin(x) = (sin(x)/x)*x` para aplicar `sin(x)/x -> 1`.
- **Comparación de grados en infinito sobre polinomios y constantes (`infinito.py`, líneas 37 a 55)**:
  - Como `1` es un polinomio de grado `0`, `LimiteRacionalInfinito` intercepta cualquier polinomio o constante cuando `x -> oo` (sin que haya fracción), dejando en código muerto el método de término dominante de `LimiteGeneral._termino_principal`.
  - **Ejemplo**: Límite de `5` cuando `x -> oo` (`Ctrl+L`) dice: `"el numerador tiene grado 0 y su término principal es 5; el denominador tiene grado 0 y su término principal es 1... Los grados son iguales (0 = 0)"`.
- **Continuidad por composición sobre funciones simples o sin explicar el límite interior (`continuidad.py`, líneas 83 y 146 a 157)**:
  - Para `x^3` cuando `x -> 2`, aplica `"Continuidad por composición"` con `f = elevar a 3` y `g(x) = x` en lugar de sustitución directa.
  - Para `exp((x^2 - 1)/(x - 1))` cuando `x -> 1`, dice `"g(x) tiende a 2"` sin explicar cómo se resolvió la indeterminación `0/0` de dentro.
- **Tendencia fraccionaria sin evaluar en el encabezado (`calculo/router.py`, línea 133)**:
  - `_parsear_tendencia` no llama a `.doit()`, así que si la tendencia es `1/2` o `pi/2`, el informe muestra `cuando x -> 1*1/2` o `x -> pi*1/2`.

### 2. Variable interna `_u` de SymPy visible en integrales por sustitución (`calculo/integrales.py`, línea 159)
- **Qué ocurre**: En `ExplicadorIntegral._potencia`, cuando viene de un cambio de variable `u`, pasa `f` sin reemplazar `_u` por `u` a `como_potencia(f, forma)`.
- **Ejemplo**: Integrar `(x + 1)^3` o `2*x*(x^2 + 1)^3` (`Ctrl+I`). El paso 2 dice:
  `"En este caso: la base es u y el exponente n es 3, porque _u^3 es lo mismo que u^3."`

### 3. Mensaje falso de "fórmulas del ángulo doble" en sustitución trigonométrica (`calculo/sustitucion_trig.py`, líneas 237 a 241 y 298 a 301)
- **Qué ocurre**: En `ExplicadorTrig._volver`, se transforma `1/sin(t)` en `csc(t)` y `1/cos(t)` en `sec(t)` sobre la variable `expandida`, y luego `if expandida != primitiva_t:` asume que cualquier cambio se debió a las fórmulas del ángulo doble.
- **Ejemplo**: Integrar `1 / (x^2 * sqrt(x^2 + 4))` (`Ctrl+I`). El paso 7 dice:
  `"En este caso: la primitiva en t es -1/(4*sin(t)). Con las fórmulas del ángulo doble, sin(2*t) = 2*sin(t)*cos(t) y cos(2*t) = cos(t)^2 - sin(t)^2, queda -csc(t)/4."`

### 4. Fracciones parciales: término `0/(...)`, completar el cuadrado innecesario e igualdad falsa en logaritmo (`calculo/fracciones_parciales.py`, líneas 128 a 136, 433 a 435 y 478 a 484)
- **Qué ocurre**:
  1. Cuando un coeficiente de una fracción repetida sale `0` (por ejemplo al integrar `(x^2 - 2*x + 2)/(x - 1)^3`), el paso `"Descomposición en fracciones simples"` escribe `0/(x - 1)^2` en la integral.
  2. Cuando un factor cuadrático no tiene término en `x` (como `x^2 + 4` al integrar `(x + 1)/(x^2 + 4)`), el paso sigue diciendo: `"Completamos el cuadrado: x^2 + 4 = x^2 + 4 (porque 4 - 0 = 4)"`.
  3. Al integrar `1/(2*x + 1)` (coeficiente `a != 1`), la línea 433 escribe la igualdad falsa: `∫ 1/(2*x + 1) dx = 1*log(2*x + 1) (y como la derivada de 2*x + 1 es 2, se divide entre 2) = log(2*x + 1)/2`.

### 5. Transformada de Laplace: regla inalcanzable en `_regla` y explicaciones de `_regla_inversa` (`calculo/edo.py`, líneas 3087 a 3091 y 3145 a 3162)
- **Qué ocurre**:
  1. En `_Laplace._regla` (línea 3087), la condición `termino / sympy.exp(t) != termino and termino.has(t)` se cumple siempre para cualquier exponencial `exp(a*t)`. Por tanto, la línea 3090 (`"L{exp(a*t)} = 1/(s - a)"`) es código muerto que nunca se ejecuta, y `exp(3*t)` se explica erróneamente como `"primer teorema de traslación: exp(a*t)*f(t) da F(s - a)"`.
  2. En `_regla_inversa` (líneas 3145-3162), cuando `A == 0` al completar el cuadrado (por ejemplo en `1/(s^2 + 2*s + 5)`), escribe `"el numerador, 1 = 0*(s + 1) + 1"`, y si el denominador cuadrático está repetido (`1/(s^2 + 1)^2`), no comprueba que el exponente del factor sea `1`.

### 6. EDO exacta con factor integrante: los pasos de la integral salen antes de presentar el factor integrante (`calculo/edo.py`, líneas 1710 a 1727)
- **Qué ocurre**: En `_exacta`, la línea 1710 hace `pasos.extend(pasos_m)` antes de añadir el paso `"Factor integrante"`. Así, justo después de decir que la ecuación no es exacta, aparece de golpe el paso `"Integral que da un logaritmo en ∫ 1/x dx"` sin haber explicado qué es `(M_y - N_x)/N` ni por qué se integra `1/x`. Además, si la primitiva es `x`, la línea 1716 escribe la repetición `m(x) = exp(x) = exp(x).`.
- **Ejemplo**: `(x*y - 1) dx + (x^2 - x*y) dy = 0` (`Ctrl+Shift+R`).

### 7. Repetición de `"Queda y = ..."` y `"De la primera fila"` en EDOs (`calculo/edo.py`, líneas 1383 a 1395, 1508 a 1524, 1780 a 1790, 2060 a 2074 y 3275 a 3281)
- **Qué ocurre**:
  1. `Despeje` añade `"Queda y = ..."` como última línea de `despeje.lineas`. En `_separable` se quita esa última línea porque `PasoCalculo.queda` ya imprime `"Queda: y = ..."`, pero en `_lineal`, `_bernoulli`, `_exacta` y `_con_cambio` no se quita, por lo que el lector de pantalla lee dos veces seguidas `"Queda y = ..."` y `"Queda: y = ..."`.
  2. En sistemas lineales (`_Sistema`, línea 3279), si la primera fila de `A - r*I` es `[0, 0]`, toma la segunda fila pero el texto dice igualmente `"De la primera fila: ..."`.

### 8. Simplificación y Factorización de polinomios y fracciones (`aritmetica.py` y `pasos_aritmetica.py`)
- **Expresiones ya factorizadas marcadas como irreducibles (`aritmetica.py`, línea 185)**:
  - Si se factoriza `(x + 1)*(x + 2)` o `(x + 1)^2` (`Ctrl+F`), `resultado == expr` es verdadero, por lo que dice `Estrategia: Irreducible` y avisa `"No se encontraron factores más simples en los racionales (Q)"`, contradiciendo los pasos de factorización que muestra arriba.
- **Salto de signo en diferencia de cuadrados (`aritmetica.py`, líneas 169 a 180)**:
  - En `-x^2 + 4` (`Ctrl+F`), los pasos factorizan `(2 - x)*(2 + x)`, pero en el paso final de `"Comprobación"`, `Queda:` salta sin explicación a `-(x - 2)*(x + 2)`.
- **Suma/diferencia de cubos de grado 6 (`pasos_aritmetica.py`, líneas 811 a 835)**:
  - En `x^6 + 64` (`Ctrl+F`), la factorización `(x^2 + 4)*(x^4 - 4*x^2 + 16)` es correcta sobre los racionales. El error está en justificar la irreducibilidad del segundo factor mediante un discriminante cuadrático, pues tiene grado 4.
  - Corrección de esta auditoría: los factores antes propuestos, `(x^2 + 4)*(x^2 - 2*x + 4)*(x^2 + 2*x + 4)`, se expanden como `x^6 + 8*x^4 + 32*x^2 + 64`, no como `x^6 + 64`. Se conserva la factorización correcta y se elimina únicamente la justificación inaplicable.
- **Simplificación de fracciones explicada como propiedad distributiva o "ya simplificada" (`pasos_aritmetica.py`, líneas 527 a 632)**:
  - Simplificar `(x - 1)/(x - 1)` o `(2*x + 4)/2` (`Ctrl+S`): como `crudo.doit()` cancela el denominador antes de entrar al explicador, se envía a `_polinomio` y dice que aplicó `"Desarrollar (propiedad distributiva)"`.
  - Simplificar `(2*x + 2)/(2*x + 4)` (`Ctrl+S`): como el factor común `2` es numérico, salta el paso de cancelar y dice `"Ya está simplificada"`, aunque devuelve `(x + 1)/(x + 2)`.
- **Producto `(x + 1)*(x^2 - x + 1)` explicado como suma por diferencia (`pasos_aritmetica.py`, líneas 499 a 500)**:
  - Al simplificar `(x + 1)*(x^2 - x + 1)`, como son 2 factores y el resultado `x^3 + 1` tiene 2 términos, dice `"Regla: suma por diferencia: (a + b)*(a - b) = a^2 - b^2"`.
- **Propiedad distributiva con funciones explicada como identidad (`pasos_aritmetica.py`, líneas 561 a 566)**:
  - Al simplificar `2*(sin(x) + 1)`, por contener `sin(x)` salta el paso `"Desarrollar"` y lo titula `"Aplicar identidades"` (`log(exp(u)) = u...`).

### 9. Detalles en Evaluar, Rectas, Taylor, Extremos, Integrales definidas y Determinantes
- **Evaluar (`pasos_aritmetica.py`)**:
  - En divisiones con negativos (`-6/2`, líneas 231 y 324), la regla de los signos dice `"menos por más da menos"` en lugar de `"menos entre más da menos"`.
  - En raíces de fracciones (`sqrt(4/9)`, línea 358, y también en `algebra/resolucion.py`, línea 552), escribe `"porque 2/3^2 = 4/9"` sin paréntesis en `(2/3)^2`.
  - En `log10(2)` (línea 371), dice `"log10(2) = log(2)/log(10) (valor exacto conocido)"`.
  - En potencias con exponente `1` (`5^1`), mayor que `6` (`2^7`) o irracional (`2^pi`) (línea 345), dice `"una potencia con exponente natural n es la base multiplicada por sí misma n veces"`.
  - En expresiones con signo menos delante de paréntesis (`-(2 + 3)`), anuncia `"con 2 operaciones"` pero aplica el cambio de signo en silencio sin paso propio.
- **Exponente `-1` en `forma_final` (`calculo/pasos.py`, líneas 94 a 96)**:
  - Al integrar `1/x^2`, escribe `"Un exponente negativo pasa la potencia al denominador: x^(-1) = 1/x^1."` en lugar de `1/x`.
- **Constantes simbólicas (`pi/4`, `sqrt(2)`) en Recta tangente y Polinomio de Taylor (`calculo/rectas.py`, líneas 109 a 113; `calculo/taylor.py`, líneas 48 a 50 y 169)**:
  - Como SymPy ordena los números antes que `x` en `sstr(x - pi/4)` dando `"-pi/4 + x"`, en `Recta tangente` de `sin(x)` en `pi/4` aparece un paso diciendo `"Operamos: x - pi/4 = -pi/4 + x"`; y en `Taylor` de `sin(x)` en `pi/4` escribe `(-pi/4 + x)^2` en lugar de `(x - pi/4)^2`. Además, para cualquier `x0 != 0` en Taylor, el paso 1 pone dobles paréntesis `((x - 1)^2)`.
- **Producto nulo incompleto en Extremos (`calculo/extremos.py`, líneas 330 a 343)**:
  - Cuando `f'(x) = 0` tiene a la vez factores de grado 1 y de grado 2 (por ejemplo `x^4/4 - x^2`, donde `f'(x) = x*(x^2 - 2)`), el paso `"Aplicar el producto nulo"` solo menciona `x = 0` en `Queda:` sin avisar que falta resolver `x^2 - 2 = 0`.
- **Integral definida divergente con límites invertidos (`a > b`) (`calculo/calculo.py`, líneas 641 a 651)**:
  - Al integrar `1/x` entre `1` y `-1`, añade el paso `"Cambiar el signo"` después de `"Conclusión"` y escribe `"-(nan) = nan"`.
- **Aviso de variable en integral multivariable (`calculo/calculo.py`, líneas 137 a 138)**:
  - Cuando se llama a `CalcularIntegral("x + a")` sin indicar variable, el aviso dice `"Se asume derivación respecto a 'x'"` en lugar de `"integración"`.
- **Orden de pasos en Determinante 4x4 (`algebra/determinante.py`, líneas 107 y 139 a 195)**:
  - Calcula los determinantes de los menores 3x3 (`M11`, `M12`...) en los pasos 2 y 3 antes de explicar qué fila y columna se quitaron para formar cada menor (eso recién aparece en el último paso), y reutiliza los mismos nombres `b_ij`, `N_ij`, `D_ij` en todos los menores 3x3.

---

## Parte 3: Mejoras de Interfaz y Accesibilidad (UX)

### 1. Evitar pedir la variable cuando ya es única en `Límite` (`Ctrl+L`) y `Derivada de orden N` (`Ctrl+Shift+D`) (`main.py`, líneas 523 a 545)
- **Situación actual**: Todas las demás operaciones de cálculo (`Derivar`, `Integrar`, `Integral definida`, `Recta tangente`, `Extremos`, `Taylor`) detectan automáticamente la variable si solo hay una en la expresión (por ejemplo `x`) y solo preguntan si hay varias. En cambio, `Límite` y `Derivada de orden N` abren siempre un diálogo pidiendo `"Variable:"` con el cuadro en blanco.
- **Mejora propuesta**: Usar la misma detección automática de variable en `Límite` y `Derivada de orden N`. Así, al pulsar `Ctrl+L` en `sin(x)/x` solo se pide la **Tendencia**, y al pulsar `Ctrl+Shift+D` en `x^5` solo se pide el **Orden**. (Además, guardar en `ResultadoOperacion.parametros["variable"]` de `limite` el nombre de la variable resuelta para que aparezca siempre al exportar o resumir).

### 2. Validar la sintaxis antes de abrir diálogos de datos (`main.py`, líneas 394 a 415 y `puente.py`, líneas 446 a 461)
- **Situación actual**: Si el usuario escribe una expresión con un error de sintaxis (como `sin(x` sin cerrar paréntesis o `xsin(x)`) y pulsa `Ctrl+I` o `Ctrl+Shift+I`, `DetectarVariables` devuelve `[]` y la calculadora abre un diálogo engañoso diciendo: `"Está integrando una constante. ¿Cuál es la variable de integración?"`. En `Integral definida`, obliga a rellenar tres diálogos seguidos antes de avisar que faltaba un paréntesis.
- **Mejora propuesta**: Validar la expresión con el parser antes de pedir datos adicionales; si hay un error de sintaxis, mostrar el diálogo de error de inmediato y devolver el foco a la entrada. También, si al integrar una constante el usuario deja vacío el diálogo de variable, cancelar o asumir `x` en lugar de continuar con `""`.

### 3. Hacer que `Ctrl+Enter` detecte Ecuaciones Diferenciales y permitir varias líneas en EDOs (`main.py`, líneas 432 a 441 y `calculo/edo.py`, líneas 203 a 217)
- **Situación actual**:
  1. Si el usuario escribe `y' = 2*x*y` (o `dy/dx = x`) y pulsa `Ctrl+Enter` (el botón principal **Calcular**), `on_evaluar_inteligente` ve el signo `=` y lo envía a `Resolver ecuación o inecuación` (álgebra), dando error.
  2. Si el usuario escribe un sistema de ecuaciones diferenciales o una EDO con condiciones iniciales en varias líneas (como se hace en los sistemas de ecuaciones), `_partir` en `calculo/edo.py` solo separa por `,` y `;`, no por saltos de línea `\n`, y falla.
- **Mejora propuesta**:
  1. En `_partir` (`calculo/edo.py`), separar también por saltos de línea `\n`.
  2. En `on_evaluar_inteligente` (`main.py`), si la entrada tiene `=` y contiene apóstrofes de derivada (`y'`, `x'`), derivadas `dy/dx`, `dx/dt` o diferenciales `dx`, `dy`, enviarla automáticamente a **Ecuación diferencial** (`edo`).

### 4. Submenú o diálogo para descubrir los métodos de Ecuaciones Diferenciales (`puente.py`, línea 105 y `main.py`, líneas 193 a 201)
- **Situación actual**: Para usar **Transformada de Laplace**, **Series de potencias** o **Reducción de orden / Riccati** con solución conocida `y1`, hay que saber que se escribe `, laplace`, `, serie` o `, y1 = ...` en el cuadro de texto. Al recorrer el menú **Cálculo** con el lector de pantalla, esas funciones están ocultas.
- **Mejora propuesta**: Añadir en el menú **Cálculo** opciones accesibles (o variantes, manteniendo `Ctrl+Shift+R` directo para el modo automático):
  - Resolver ecuación diferencial (`Ctrl+Shift+R`)
  - Resolver EDO por transformada de Laplace
  - Resolver EDO en serie de potencias
  - Resolver EDO con solución conocida `y1`... (pidiendo `y1` en un diálogo si no se escribió en la entrada).

### 5. Orden de tabulación, foco y avisos para NVDA/JAWS (`main.py` y `ventana_historial.py`)
- **Cuadro informativo en la cadena de Tab (`main.py`, líneas 124 a 126)**:
  - `self.lbl_info` es un `wx.TextCtrl` de solo lectura sin etiqueta que recibe el foco al tabular. Convertir `lbl_info` en un control que no reciba foco por `Tab` (o asociarle nombre accesible) evita un paso innecesario al moverse con `Tab` entre `Entrada` y `Resultados`.
- **Cancelación no bloqueante (`proceso_calculo.py`, líneas 84 a 90 y 133 a 138)**:
  - Al pulsar **Cancelar** en un cálculo largo, `self._proceso.join(5)` y el arranque del nuevo proceso ocurren en el hilo de la interfaz gráfica. Hacerlo en un hilo en segundo plano permite que el diálogo se cierre al instante.
- **Diálogo de Historial (`ventana_historial.py`)**:
  - Cuando se borra la última operación con `Suprimir` o se pulsa `Borrar todo`, todos los botones salvo `Cerrar` se deshabilitan pero el foco se envía a la lista vacía (`self.lista.SetFocus()`). Si el historial queda vacío, mover el foco al botón `Cerrar` (o cerrar el diálogo tras confirmar).
  - Añadir un botón o atajo `Ctrl+C` en el historial para copiar directamente el resultado de la operación seleccionada sin necesidad de cerrar el historial.
- **Navegación rápida entre pasos en el cuadro de Resultados (`main.py`)**:
  - En desarrollos largos (Gauss-Jordan, determinantes 4x4, ecuaciones diferenciales), añadir dos atajos (por ejemplo `Alt+Abajo` y `Alt+Arriba`, o `F6` / `Shift+F6`) para saltar directamente al inicio del **siguiente paso** o del **paso anterior** (`1. `, `2. `, `3. `...) dentro del cuadro de resultados.
