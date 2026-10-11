# Registro de cambios

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/). La versión actual está en `_version.py`.

## [Sin publicar]

### Corregido

- **Salto al quitar paréntesis cuando las incógnitas se cancelan.** En `2*(x + 1) - (2*x + 2)` el resultado es un número, y `despejar()` lo trataba como una cuenta solo de números: mostraba "Operamos: 2*(x + 1) - (2*x + 2) = 0" sin la propiedad distributiva. Ahora solo se opera de una vez si no hay incógnitas; si las hay, se desarrolla y se agrupan los términos semejantes a la vista.
- **MathML inválido en las desigualdades estrictas**: SymPy escribe `<mo><</mo>` sin escapar, y un HTML exportado o un MathML copiado con `<` o `>` no era XML válido. Se escapan al generar el MathML.
- **Historial: los conjuntos con varios intervalos no se recuperaban.** El historial reconstruye cada objeto SymPy sin evaluarlo, y `Union` no se puede construir así (necesita comparar los extremos); la entrada se guardaba sin su valor. Los conjuntos se reconstruyen con su constructor normal: ya están en forma canónica, así que no cambian. (Este fallo y el anterior no afectaban a ninguna operación previa: aparecieron con las inecuaciones.)

## [1.5.0] - 2026-10-10

Versión del paso a paso: todas las operaciones (derivadas, integrales, límites, álgebra, Evaluar, Simplificar y Factorizar) explican cada regla sin saltos, con el mismo formato (Regla, En este caso, las cuentas intermedias y Queda), empiezan por el resultado y comprueban sus pasos contra SymPy. Añade la integral definida y corrige derivadas e integrales de logaritmos en otra base.

### Añadido

- **Integral definida** (menú **Cálculo**, `Ctrl+Shift+I`). Pide el límite inferior y el superior: números, expresiones (`pi/2`), parámetros (`k`) u `oo` / `-oo`. El valor lo calcula SymPy; la explicación es la de clase:
  - **Regla de Barrow** si la función es continua en un intervalo acotado: los pasos de la primitiva (los mismos de la integral indefinida), `F(x)` y `F(b) − F(a)`. Si el límite inferior es mayor, se invierten y se cambia el signo; si son iguales, vale 0.
  - **Integral impropia** si un límite es infinito o la función no es continua en el intervalo: se divide en tramos en los puntos de discontinuidad (y en 0 si los dos límites son infinitos), se toma el límite lateral de la primitiva en cada extremo impropio y se dice si cada tramo converge o diverge. Aplicar Barrow sin comprobar la continuidad es un error clásico: con `1/x^2` entre -1 y 1 "daría" -2, pero la integral diverge.
  - La explicación solo se muestra si su valor coincide con el de SymPy; si no, se da el de SymPy con un aviso.
  - La primitiva de `1/x` se escribe `log(Abs(x))`: SymPy da `log(x)`, y entre -2 y -1 los pasos mostrarían logaritmos de negativos (`iπ`) aunque el resultado sea real.
  - Si no hay primitiva elemental (o la forma exacta de SymPy usa números complejos, como en `exp(x^3)`), se da el valor decimal con un aviso. Los valores irracionales llevan su aproximación: `pi/4 (≈ 0.785398)`.
  - Las integrales que divergen dan `+Infinito`/`-Infinito (la integral diverge)` o `No existe (la integral diverge)`; son un resultado, no un error. Se copian y exportan igual (en LaTeX, `\int\limits_{0}^{1} x^{2}\, dx = \frac{1}{3}`) y se guardan en el historial.
  - Es la primera operación añadida con el registro: el motor (`Calculo.CalcularIntegralDefinida`), su método en la fachada, una entrada en el registro y un tipo de datos nuevo en la interfaz (`variable_limites`).
  - Pruebas: `tests/test_integral_definida.py` (42: 20 integrales con su valor y método, divergentes incluidas, los pasos de los casos difíciles, errores de datos y exportación), y casos en las pruebas de inglés, historial, exportación, errores y registro; la suite tiene 2802. La autoprueba del ejecutable tiene un caso nuevo (17), porque la continuidad usa un módulo de SymPy que no se usaba. `tests/verificar_ui.py`: 87 comprobaciones.
  - Ayuda (F1) y README: atajo y ejemplo.

### Cambiado

- **Paso a paso de las derivadas, sin saltos.** La explicación anterior daba resultados "por arte de magia": "Regla de la Potencia. Polinomio simple. [Fórmula]: 3*x^(3-1)", sin decir qué regla era, qué parte de la expresión era el exponente ni cuánto daba la cuenta, y en un producto o un cociente las derivadas de `u` y `v` aparecían ya hechas. Con un lector de pantalla, que no permite echar un vistazo atrás para reconstruir lo que falta, cada salto obligaba a calcular de cabeza. Ahora cada regla se explica siempre en el mismo orden, una línea por parte:
  1. **Regla**: el enunciado general antes de aplicarlo ("la derivada de x^n es n*x^(n-1): el exponente baja multiplicando y se le resta 1").
  2. **En este caso**: qué parte de la expresión es cada pieza ("la base es x y el exponente n es 3"), y por qué cuando no se ve a simple vista ("el exponente n es 1/2, porque sqrt(x) es lo mismo que x^(1/2)"; "x es lo mismo que x^1").
  3. La sustitución y cada cuenta: "Sustituimos n = 3: 3*x^(3 - 1)", "Restamos 1 al exponente: 3 - 1 = 2", "Multiplicamos los números: 3 * 4 = 12", "Un exponente negativo pasa la potencia al denominador", "Cualquier base elevada a 0 vale 1".
  4. **Queda**: la expresión tras ese paso.
  - Las reglas compuestas (suma, factor constante, producto, cociente, cadena, derivación logarítmica) se explican en dos pasos: el planteamiento (regla y partes), luego la derivada de cada parte en su propio paso, y al final la sustitución con esas derivadas. Cada parte dice a qué regla pertenece ("Regla de la potencia en x^2 (u del producto)"), para que dos `u` anidadas no se confundan.
  - Si el resultado final se escribe de forma más compacta que lo que sale de las reglas (factor común, identidades), un último paso "Simplificación" muestra la igualdad, en lugar de cambiar la expresión sin decirlo.
  - Reglas: constante, variable, suma, potencia (con coeficiente, raíces y exponentes negativos), factor constante, producto, cociente, cadena con potencias, exponencial `e^u` y `a^u`, cualquier función elemental de SymPy (`sin`, `log`, `atan`, `sinh`, `Abs`...; su derivada se calcula, no se escribe a mano en una tabla) y potencia general `u^v`.
  - La derivada se construye con la propia explicación y se compara con la de SymPy: si no coincidiera, se muestra el resultado de SymPy sin pasos y con un aviso, nunca una explicación que llegue a otro resultado. Antes, los pasos se escribían aparte del cálculo y nada comprobaba que llevaran al resultado.
  - **Derivada de orden N**: cada derivada se explica igual (antes solo se mostraba "Resultado iterativo." y la expresión). Si la explicación se hace demasiado larga (más de 30 pasos en una derivada o 120 en total), desde ahí se muestran solo los resultados, con un aviso.
  - La estrategia principal y las secundarias (ANÁLISIS) se mantienen, así que las exportaciones y el historial no cambian de forma.
  - Código: `calculo/derivadas.py` (`ExplicadorDerivada`, una función por regla) sustituye a `_analizar_estructura_derivada`; `calculo/pasos.py` define `PasoCalculo` (con los campos nuevos `regla`, `partes`, `calculo` y `queda`) y su texto, compartido con las integrales, cuyos pasos se ven igual que antes.
  - `tests/test_derivadas.py`: 115 pruebas (52 expresiones que se explican hasta el resultado mostrado y con la estructura completa en cada paso, las cuentas de los casos típicos, los nombres de las partes anidadas, la explicación que no coincide, y la derivada de orden N).
  - Ayuda (F1) y README: cómo se lee cada paso.
- **Paso a paso de las integrales, con el mismo estándar.** Antes cada paso solo nombraba la regla: "Integral Inmediata. Aplicamos regla: Regla de la potencia. [Fórmula]: Tabla de integrales", sin decir el resultado de ese paso; en la sustitución, "Elegimos u = x^2 + 1" sin decir cuánto vale `du` ni cómo queda la integral en `u`; y en partes no se veía `v` ni la integral que queda. Ahora cada regla se explica como en las derivadas (**Regla**, **En este caso**, las cuentas, **Queda**):
  - Potencia: "Sumamos 1 al exponente: 1/2 + 1 = 3/2", "Dividimos entre el exponente nuevo: x^(3/2)/(3/2)", "Dividir entre 3/2 es multiplicar por 2/3". `1/x` se explica aparte (el caso `n = -1`, que da un logaritmo).
  - Cambio de variable: qué se toma como `u` y por qué, `du`, el integrando escrito como una función de `u` por su derivada ("sin(x)/cos(x) = (-1/cos(x))*(-sin(x))": así se ve el signo de `du`, que antes se perdía), qué se cambia por `u` y por `du`, la integral en `u` y la vuelta a `x`.
  - Integración por partes: `u`, `dv`, `du`, la integral de `dv` (`v`) en su propio paso, la fórmula con todo sustituido y la integral que queda, también explicada. Las partes cíclicas (`exp(x)*sin(x)`) muestran las dos integraciones y cómo se despeja la integral.
  - Integrales de la tabla (`sin`, `sec^2`, `1/(1+x^2)`...): el resultado y su comprobación derivando ("la derivada de -cos(x) es sin(x)").
  - Factor constante, suma y funciones reescritas (identidades como `sin(x)^2 = 1/2 - cos(2*x)/2`, fracciones separadas), cada una con sus partes. Si el factor constante se ajusta para completar una derivada, se dice: "x/(x^2 + 1) = (1/2)*(2*x/(x^2 + 1))".
  - Al final, la **constante de integración** (por qué se suma `C`) y, si la forma de SymPy es otra, un paso que muestra que es la misma ("Simplificación") o que se diferencia en una constante ("Otra forma de la primitiva", por ejemplo `(x+1)^3/3` y `x^3/3 + x^2 + x`).
  - La primitiva se construye con la propia explicación y se comprueba derivándola; si no llega al resultado mostrado, se prueba el otro camino que ofrezca SymPy (`(x^2+1)/x` por sustitución da `log(x^2)/2`, que no se reduce a `log(x)`; separando la fracción, sí), y si tampoco, se da el resultado sin pasos con un aviso. Las integrales sin regla explicable (`1/cos(x)`, `abs(x)`) dan el resultado con ese aviso, en lugar de un paso "Método Desconocido".
  - La estrategia principal es la regla explicada ("Integral inmediata", "Reescribir la función"...) en lugar del nombre interno de SymPy ("Sin", "Rewrite", "CyclicParts").
  - **Integral definida**: la regla de Barrow se enuncia y sustituye cada límite en `F` ("F(1) = 1^3/3 = 1/3"); las impropias explican cada tramo, su extremo impropio y su límite, y por qué converge o diverge.
  - Código: `calculo/integrales.py` (`ExplicadorIntegral`, una función por regla de `manualintegrate`) sustituye a `_regla_a_pasos`. Las funciones que escriben expresiones en los pasos (`texto`, `entre_parentesis`, `multiplica_numeros`...) pasan de `calculo/derivadas.py` a `calculo/pasos.py`, compartidas por los dos.
  - `tests/test_integrales.py`: 119 pruebas (52 integrales que se explican hasta el resultado con la estructura completa, los casos típicos de cada regla, la alternativa, el aviso y la integral definida). La autoprueba busca el nuevo texto de la integración por partes.
- **Paso a paso de los límites, con el mismo estándar.** Cada estrategia escribía viñetas sin estructura ("Aplicamos together(): ...", "Aplicamos cancel(): x + 1", "Construimos el núcleo K = sin(u)/u... Calculamos lim R = 5"), con nombres de funciones de SymPy y resultados intermedios sin justificar; y los límites que no resolvía ninguna estrategia mostraban el informe de otro motor (diagnóstico, normalización, "L'Hôpital limitado") que a menudo acababa en "no se obtuvo un cierre concluyente" aunque el resultado fuera correcto. Ahora todos los límites se explican con el formato de derivadas e integrales (**Regla**, **En este caso**, las cuentas, **Queda**):
  - Primero, siempre, la **sustitución directa** y la forma que sale: "Numerador: 2^3 - 8 = 0. Denominador: 2^2 - 4 = 0. Sale 0/0, una forma indeterminada..." (en el infinito, a qué tiende cada parte; en una suma, cada término, para el `∞ - ∞`).
  - **Simplificación y cancelación**: factoriza numerador y denominador, dice cuál es el factor común y por qué se puede cancelar (`x ≠ a` mientras se acerca), cancela y sustituye con las cuentas ("(2^2 + 2*2 + 4)/(2 + 2) = 12/4 = 3").
  - **Racionalización**: `A`, `B` y el conjugado, por qué multiplicar por él no cambia el límite, `(A - B)*(A + B) = A^2 - B^2` con las raíces de la expresión, la expresión transformada, la simplificada y su límite.
  - **Límites trigonométricos notables**: el núcleo, por qué `u → 0`, el resto `R` como la expresión dividida entre el núcleo, su límite (con el núcleo invertido `v/sin(v) → 1` si hace falta, como en `sin(2x)/sin(3x)`) y el producto final.
  - **Comparación de grados**: grados y términos principales, su cociente y, si diverge, el signo (exponente par o impar, coeficiente positivo o negativo).
  - **Continuidad por composición**: el límite de la función de dentro (sustituyendo, o con sus propios pasos si es un límite notable, como en `exp(sin(x)/x)`), la continuidad de la de fuera y la evaluación.
  - **Modo general** (nuevo, `calculo/lim_estrategias/general.py`), que sustituye al motor anterior (`calculo/limite.py`, eliminado): sustitución directa, límites laterales (con el valor absoluto quitado a cada lado: "x es negativo cerca de 0 por la izquierda, así que Abs(x) = -x"), número entre cero con el signo de cada parte, **regla de L'Hôpital** (derivada del numerador y del denominador, y el nuevo cociente), formas `1^∞`, `0^0` y `∞^0` (`f^g = exp(g*log(f))`), `0*∞` y `∞ - ∞` reescritas como cociente, el término de mayor grado de un polinomio y el límite de una constante. `(1 + 1/x)^x` se explica ahora en siete pasos hasta `E`.
  - El método del modo general dice qué técnica usó ("Modo General (regla de L'Hôpital)"). El valor sigue siendo el de SymPy, y la explicación solo se muestra si llega a él; si no, el resultado va con un aviso ("Modo General (SymPy)"). De 90 límites de prueba (los 65 de la auditoría y 25 más), los 90 se explican.
  - El enrutador evalúa la expresión antes de calcular (`doit()`), como derivadas e integrales: los pasos ya no muestran formas como `sqrt(x + 1) - 1*1`.
  - Los nombres de los métodos no cambian (la auditoría de `tests_limites.py` sigue en 65/65). Los avisos de una estrategia ahora se muestran.
  - `tests/test_pasos_limites.py`: 183 pruebas (los 90 límites se explican con la estructura completa, el contenido de cada método y la explicación que no llega al valor).
  - Ayuda (F1) y README.

- **Derivada de orden N y términos semejantes.** La derivada de orden N empezaba con "Inicio. Función original. [Fórmula]: x**5" y cada derivada con "Derivada 2. Derivamos el resultado anterior" (también la primera, que deriva la función original), sin regla. Ahora empieza con el planteamiento ("hay que derivar 3 veces: f'(x), f''(x), f'''(x)") y cada derivada dice cuál es y de cuál sale ("Derivada 2: f''(x). Regla: f''(x) es la derivada de f'(x)"); las que no se explican regla a regla (por ser demasiado largas) también dan su valor con ese formato, en lugar de "Resultado iterativo".
  - Al juntar las derivadas (o las integrales) de una suma, los términos semejantes se agrupaban sin decirlo: "... + 3*x^2*cos(x) + 3*x^2*cos(x) ..." pasaba a "6*x^2*cos(x)" en la línea siguiente. Ahora una línea lo dice: "Agrupamos términos semejantes: 3*x^2*cos(x) + 3*x^2*cos(x) = 6*x^2*cos(x)" (`agrupa_semejantes` en `calculo/pasos.py`).
  - `tests/test_derivadas.py`: los títulos y el planteamiento de la derivada de orden N, la derivada larga sin reglas y los términos semejantes.

- **Paso a paso de Álgebra, con el mismo estándar.** Los métodos clásicos daban saltos grandes: en sustitución, "Reemplazamos en la Ecuación 1. Operación: 5*y = 10", sin escribir `2*(y + 1) + 3*y = 12`, quitar el paréntesis, agrupar ni pasar el 2 al otro lado; Gauss-Jordan decía la operación ("F2 - (-3)*F1") y mostraba la matriz nueva, sin la cuenta de ningún elemento; y la inversa explicaba un único cofactor "de ejemplo" y daba los demás hechos. Además, en Álgebra el resultado iba al final, cuando en el resto de la calculadora va primero (para no tener que escuchar todo el desarrollo). Ahora:
  - **Resultado primero** en las tres operaciones (`RESULTADO:` y una solución por línea), y después el método y el paso a paso con el formato estándar (**Regla**, **En este caso**, las cuentas, **Queda**).
  - **Ecuaciones de primer grado** (`algebra/ecuaciones.py`, nuevo), usadas por los tres métodos clásicos: quitar paréntesis ("2*(y + 1) + 3*y = 2*y + 3*y + 2"), agrupar términos semejantes, pasar cada término al otro lado diciendo si es sumar o restar en los dos lados, operar cada lado y dividir ("y = 10/5 = 2"). Las sustituciones se escriben en el orden en que está la ecuación ("2*3 + 3*2"), no en el que SymPy reordena los términos.
  - **Sustitución, igualación y reducción**: por qué se despeja una incógnita y no otra (coeficiente 1, sin fracciones), la ecuación sustituida o igualada, la incógnita que se elimina con sus multiplicadores (el mínimo común múltiplo), cada ecuación multiplicada y la suma término a término. Las ecuaciones que no están ordenadas se ordenan en un paso propio. Los sistemas sin solución única explican el determinante y por qué las rectas son paralelas o la misma.
  - **Gauss-Jordan**: la matriz aumentada (de qué ecuación sale cada fila), cada intercambio con su motivo, cada normalización y cada eliminación con la cuenta de cada elemento, la lectura de la solución fila a fila (con las variables libres o la fila imposible) y la comprobación.
  - **Matriz inversa**: el determinante con sus cuentas (`1*4 - 2*3 = 4 - 6 = -2`; en 3x3 y 4x4, por la primera fila), los n² cofactores con su menor, su determinante y su signo, la adjunta, la división de cada elemento entre el determinante y la comprobación `A·A⁻¹ = I` elemento a elemento. Una matriz singular explica su determinante 0 y por qué no tiene inversa.
  - La solución mostrada es siempre la de SymPy; en los métodos clásicos, si la de los pasos no coincidiera, se daría sin pasos.
  - `tests/test_pasos_algebra.py`: 34 pruebas (las ecuaciones de primer grado, seis sistemas por los tres métodos con la estructura completa y la comprobación, los casos sin solución única, las cuentas de Gauss-Jordan y de la inversa). `tests/test_algebra.py` y `tests/verificar_ui.py` comprueban el resultado primero.
  - Ayuda (F1) y README.

- **Paso a paso de Evaluar, Simplificar y Factorizar, con el mismo estándar.** Era la última parte con el formato anterior: Evaluar no explicaba nada si el resultado era sencillo ("RESULTADO: 14" a secas para `2+3*4`), Simplificar decía "Cancelación de factores comunes: x + 1" y Factorizar "Patrón identificado: Estructura (lineal)*(cuadrática) compatible con a^3 ± b^3 (verificación parcial)", sin ninguna cuenta. Ahora las tres empiezan por el resultado y siguen el formato estándar (**Regla**, **En este caso**, las cuentas, **Queda**):
  - **Evaluar**: la cuenta se lee tal como se escribió (con el módulo `ast` de Python, que conserva el orden y los paréntesis: el parser de SymPy reordena `1/3 + 1/6` como `1/6 + 1/3` y aplana los productos) y se resuelve **una operación por paso, en el orden de la jerarquía**, diciendo por qué toca ("está entre paréntesis", "las potencias van antes...", "entre las del mismo nivel, la de la izquierda") y cómo queda la cuenta. Cada operación tiene su regla y sus cuentas: suma y resta de fracciones con el mínimo común denominador ("1/3 = 2/6", "3/6 = 1/2"), producto y cociente de fracciones (inversa), regla de los signos ("más por menos da menos"), potencias desarrolladas (`(-2)^3 = (-2)*(-2)*(-2)`), exponentes negativos y fraccionarios, raíces exactas ("sqrt(16) = 4, porque 4^2 = 16") y no exactas ("8 = 2^2*2, así que sqrt(8) = 2*sqrt(2)"), valores exactos conocidos de funciones y, al final, la aproximación decimal. Dividir entre 0 da un error claro.
  - **Simplificar**: desarrollar paréntesis (propiedad distributiva, cuadrado de un binomio, suma por diferencia), agrupar términos semejantes con la cuenta de los coeficientes ("2*x + 5*x = (2 + 5)*x = 7*x"), sumar fracciones algebraicas con el mínimo común múltiplo de los denominadores (por qué se multiplica cada fracción), factorizar y cancelar diciendo para qué valores no vale, e identidades (`exp(log(x)) = x`, `log(exp(2*x)) = 2*x`). Antes, `2*(x - 3)` se desarrollaba sin decirlo, porque SymPy reparte el número al leer la expresión: ahora se parte de la expresión sin evaluar.
  - **Factorizar**: factor común (cada término dividido entre él), diferencia de cuadrados ("x^4 = (x^2)^2"), trinomio cuadrado perfecto (comprobando el término central), trinomio `x^2 + bx + c` ("dos números que multiplicados den 6 y sumados den -5: -3 y -2"), `ax^2 + bx + c` con el discriminante y las raíces (y cómo se reparte el coeficiente: "2*(x + 1/2) = 2*x + 1"), suma y diferencia de cubos, factor común por grupos y **Ruffini** (los candidatos descartados, `P(1) = 1 - 6 + 11 - 6 = 0` y la tabla columna a columna). Cada factor se vuelve a factorizar (`x^4 - 1` hasta `(x - 1)*(x + 1)*(x^2 + 1)`), un factor de grado 2 que no se descompone se justifica con su discriminante, y al final se comprueba multiplicando.
  - Verificación contra SymPy: Evaluar compara el valor de sus pasos con el exacto de SymPy; Simplificar, la expresión final con `simplify`; Factorizar, el producto (al expandirlo) con la expresión. Si no coinciden, se da el resultado de SymPy sin pasos y con un aviso. Los resultados mostrados no cambian.
  - Corregido de paso en `calculo/pasos.py`: al juntar sumas, un sumando que era a su vez una suma negativa se escribía sin paréntesis (`x - x + 1` en lugar de `x + (-x - 1)`).
  - Código: `pasos_aritmetica.py` (nuevo) con `ExplicadorEvaluar`, `ExplicadorSimplificar` y `ExplicadorFactorizar`; la inferencia de patrones anterior de `aritmetica.py` desaparece.
  - `tests/test_pasos_aritmetica.py`: 74 pruebas (56 expresiones de las tres operaciones con la estructura completa, las cuentas de cada caso y la verificación). Las pruebas que comparaban Evaluar con "RESULTADO: 4" exacto comparan la primera línea.
  - Ayuda (F1) y README.

### Corregido

- **Integrales por partes cíclicas que dejaban de resolverse en la misma sesión**: tras unas cuantas integrales, `∫ exp(x)*sin(x)` (o `exp(x)*cos(x)`) se quedaba sin método ("Sin regla conocida") hasta reiniciar la calculadora. SymPy limita a tres los usos de `sin`, `cos`, `exp`... como `u` de la integración por partes, para no dar vueltas sin fin, pero solo pone esa cuenta a cero en `manualintegrate()`, y la calculadora usa `integral_steps()` para obtener los pasos: la cuenta se acumulaba entre integrales. Ahora se pone a cero tras cada una. Apareció al probar las nuevas explicaciones de las integrales, cuyo resultado dependía del orden de las pruebas. `tests/test_calculo.py` integra cinco veces seguidas `exp(x)*sin(x)`.
- **Derivadas e integrales de logaritmos en otra base**: `log(x,10)` se derivaba como `1/x` (debe ser `1/(x*log(10))`), y su integral daba `x*log(x)/log(10) - x` (el término `-x` también va dividido entre `log(10)`); la integral definida y la derivada de orden N arrastraban el error. El parser no evalúa las expresiones (`evaluate=False`) y SymPy no deriva bien `log(x, 10)` sin evaluar: lo trataba como `log(x)`. Ahora derivadas e integrales evalúan la expresión antes de calcular (`doit()`, como ya hacía la aritmética), lo que de paso evita en los pasos formas como `3*x - 1*7`. Se descubrió al probar el nuevo paso a paso de las derivadas, que se negaba a explicar ese resultado porque no coincidía con el suyo. Pruebas en `tests/test_calculo.py`, `tests/test_integral_definida.py` y `tests/test_derivadas.py`.
- **Límites de la integral definida sin nombre**: con **Opciones → Mostrar el paso a paso** desactivado, y en la exportación (texto, Markdown y HTML), los límites aparecían como `inferior: 0` y `superior: 1`, con el nombre interno del parámetro y sin traducir. Ahora dicen **Límite inferior** / **Límite superior** (*Lower limit* / *Upper limit*). Apareció al juntar la integral definida, escrita antes de existir el modo "solo el resultado", con la versión 1.4.0. `tests/test_exportar.py` comprueba el resumen de una integral definida.
- **Pasos de integración sin nombre**: cuando SymPy encontraba varios caminos (`AlternativeRule`, por ejemplo `exp(-x)`, que se puede sustituir de dos formas) o una potencia escrita como fracción (`NestedPowRule`, `1/x^2`), la explicación decía "Paso Intermedio. Regla detectada: AlternativeRule". Ahora se explica el primer camino y `1/x^2` usa la regla de la potencia. Afecta también a la integral indefinida.

## [1.4.0] - 2026-10-10

Versión de opciones: la calculadora se actualiza sola desde las Releases de GitHub, se puede elegir entre ver el paso a paso o solo el resultado, y los textos en español se pueden editar en `locales/es.json` sin tocar el código.

### Añadido

- **Actualizaciones automáticas.** Al abrirse, la calculadora consulta la última Release de GitHub y, si hay una versión más nueva, muestra sus novedades y ofrece **Actualizar ahora**, **Omitir esta versión** o **Más tarde**. Al actualizar, descarga el instalador (diálogo de progreso con Cancelar), se cierra, lo instala en modo silencioso y se vuelve a abrir. Hasta ahora, cada usuario tenía que enterarse por su cuenta de que había una versión nueva, buscarla en GitHub e instalarla a mano.
  - `actualizador.py` (sin interfaz, probado sin red): consulta `releases/latest`, compara versiones numéricamente (`1.10.0` > `1.9.0`), elige el instalador por su nombre, lo descarga solo por https y comprueba su tamaño y el SHA-256 que publica GitHub; un instalador incompleto o alterado se borra y no se ejecuta nunca. Lo lanza con `os.startfile` porque es lo que permite el aviso de permisos de administrador (UAC); si se rechaza, la calculadora sigue abierta y lo explica.
  - **Ayuda → Buscar actualizaciones...** comprueba en cualquier momento e informa del resultado (al día, sin conexión...). La comprobación al abrir no dice nada si no hay versión nueva o no hay conexión, espera a que termine un cálculo en curso y no vuelve a ofrecer una versión omitida. **Opciones → Buscar actualizaciones al iniciar** la desactiva. En "Actualización disponible", Escape equivale a **Más tarde**, no a omitir.
  - Al ejecutar el código fuente no se busca al abrir, y desde el menú se abre la página de la Release en lugar de instalar.
  - `setup_script.iss`: con el parámetro `/ACTUALIZAR=1` vuelve a abrir la calculadora al terminar, como el usuario y no como administrador. Además, una instalación normal ofrece ahora la casilla "Ejecutar Calculadora Accesible" en la última página.
  - Requisitos para publicar (README, "Publicar una versión"): el repositorio debe ser público, la Release debe tener la etiqueta `vX.Y.Z` y el instalador adjunto con su nombre exacto, y no ser pre-release ni borrador. Las versiones ya instaladas (1.3.0 y anteriores) no tienen el actualizador: hay que instalar a mano la primera versión que lo incluya.
  - La autoprueba del ejecutable comprueba que incluye `ssl` y lee los certificados raíz de Windows, sin conectarse (16 casos).
  - `tests/test_actualizador.py`: 34 pruebas (versiones, respuesta de GitHub, descarga verificada, alterada, incompleta, cortada o cancelada, solo https, instalar y permiso rechazado, y que el nombre del instalador de `compilar.py` y el parámetro de `setup_script.iss` coinciden con los del actualizador). `tests/verificar_ui.py` recorre en la ventana real buscar (al día, sin conexión, al abrir), Más tarde, Omitir, descargar con progreso, instalar y cerrar, y el permiso rechazado: 86 comprobaciones.
  - Ayuda (F1): sección 11, en los dos idiomas.
- **Los textos en español están en `locales/es.json`**, igual que los del inglés en `en.json`, para corregir o mejorar la redacción (menús, diálogos, explicaciones paso a paso, errores) sin tocar el código. Antes el español no tenía catálogo: el texto que se mostraba era el del código, y cambiar una palabra exigía editar el `.py` correspondiente.
  - El texto del código sigue siendo la clave de todos los catálogos, así que `en.json` y las comparaciones internas (`N_`) no cambian. `es.json` empieza con el mismo texto que el código en todas sus entradas: nada cambia para el usuario hasta que se edite.
  - Un `es.json` ausente o con un error de formato no impide abrir la calculadora (se usan los textos del código). Un marcador mal escrito (`{valorr}`) tampoco interrumpe el cálculo: ese texto se muestra como en el código. Antes, `tr()` lanzaba `KeyError` si una traducción tenía un marcador inexistente.
  - El catálogo del español se carga ya al importar `i18n`. Sin eso, el proceso de cálculo (que empieza en español sin llamar a `establecer_idioma`) habría mostrado los textos del código en los resultados aunque la interfaz usara los de `es.json`.
  - **`catalogos.py`**: `python -X utf8 catalogos.py` añade a `es.json` los textos nuevos del código, quita los que ya no se usan sin tocar los editados, e informa de las traducciones que faltan o sobran en `en.json` (`--comprobar` solo informa). La extracción de textos de `tests/test_i18n.py` pasa a este módulo para compartirla.
  - Las pruebas, `tests/verificar_ui.py` y la autoprueba del ejecutable comparan con los textos del código: con la variable de entorno `CALCULADORA_TEXTOS_ORIGEN=1` no se carga `es.json`. Si no, mejorar una redacción haría fallar la suite y `compilar.py` se negaría a generar el instalador.
  - `tests/test_i18n.py`: `es.json` cubre todos los textos y conserva los marcadores; un `es.json` editado cambia el resultado mostrado; uno dañado, ausente o con un marcador mal escrito usa los textos del código.
  - README: sección "Editar los textos en español".
- **Paso a paso o solo el resultado** (menú **Opciones → Mostrar el paso a paso**, `Ctrl+Shift+P`). Sin el paso a paso, cada cálculo muestra solo el resultado, la operación y sus datos; las soluciones de un sistema y las filas de una matriz van una por línea, para leerlas con las flechas. Para quien ya conoce el método (o repasa muchos ejercicios), escuchar la explicación entera en cada cálculo era lento, aunque la primera línea fuera el resultado.
  - Es solo una forma de mostrarlo: el cálculo y su `ResultadoOperacion` no cambian, así que el historial, la exportación y **Copiar explicación completa** conservan siempre el paso a paso.
  - Al cambiar la opción, el resultado actual se vuelve a mostrar en el nuevo modo (el lector de pantalla lo lee), de modo que se puede consultar la explicación de un resultado sin recalcularlo. Si no hay resultado, un diálogo confirma el cambio.
  - `exportar.resumen()` genera el texto breve; la casilla del menú se actualiza también al usar el atajo.
  - `tests/test_exportar.py`: el resumen de los 14 tipos de resultado, en español y en inglés; `tests/verificar_ui.py`: 10 comprobaciones nuevas en la ventana real.
- **`configuracion.py`**: las preferencias (`%APPDATA%\CalculadoraAccesible\config.json`) se leen y guardan en un solo módulo, con su valor por defecto y sus valores válidos. Antes `i18n.py` leía y escribía el archivo solo para el idioma; ahora que hay más preferencias, cada una habría repetido ese código. Un `config.json` de versiones anteriores se sigue leyendo; uno dañado o con un valor no válido da los valores por defecto, y si no se puede escribir la calculadora sigue funcionando. `i18n.ruta_configuracion` se conserva. `tests/test_configuracion.py`: 10 pruebas.

### Corregido

- `tests/test_historial.py::test_guardar_historial` fallaba de vez en cuando: comparaba dos exportaciones cuyo pie lleva la hora al segundo, y si caían a ambos lados de un cambio de segundo no coincidían (detuvo una vez `compilar.py`). Ahora la prueba fija la hora.
- **`tests/verificar_ui.py`**: una lectura fallida del portapapeles lanzaba una excepción que cortaba la cadena de pasos, y el script se quedaba abierto sin decir dónde. Ahora espera el portapapeles hasta 2 segundos (si no puede leerlo, esa comprobación falla sin interrumpir las siguientes), y si se agota el tiempo muestra lo comprobado hasta ese momento y las ventanas que quedaron abiertas, y termina.


### Cambiado

- **Registro de operaciones** (`puente.REGISTRO`): cada operación se declara una sola vez, con su nombre, el método que la calcula, los datos que pide, su menú, su etiqueta y su atajo. Es el paso previo para añadir operaciones nuevas (la primera será la integral definida): antes, cada una exigía tocar a mano el diccionario `OPERACIONES`, el menú, un manejador propio en `main.py` y el verbo del diálogo de variable, y olvidar uno de ellos (por ejemplo, la clave en `OPERACIONES`) hacía que el historial la descartara al abrir la calculadora sin avisar.
  - `main.py` construye los menús Operaciones, Cálculo y Álgebra a partir del registro, y un solo manejador (`on_operacion`) pide los datos según el tipo (`PEDIR_DATOS`: expresión, líneas, expresión y variable, variable y orden, variable y tendencia) y ejecuta el método. Los nueve manejadores `on_simplificar`, `on_derivar`, etc. desaparecen.
  - Para el usuario no cambia nada: los menús, atajos, separadores y submenús son idénticos en los dos idiomas (se comprobó volcando la barra de menús antes y después).
  - `OPERACIONES` se mantiene, derivado del registro, para el historial y la exportación.
  - `tests/test_registro.py`: 24 pruebas (cada método existe y devuelve un resultado con la clave del registro, las descripciones solo usan marcadores que se rellenan, cada tipo de datos y menú existe en la interfaz, y ningún atajo se repite con los fijos de `main.py`); la suite tiene 1760.
  - `tests/verificar_ui.py`: un paso nuevo recorre todas las operaciones del registro con los diálogos simulados y comprueba el método, los argumentos y la descripción de cada una, y que cancelar un diálogo no calcula nada: 62 comprobaciones.
  - README: sección "Añadir una operación".

## [1.3.0] - 2026-10-05

Versión de historial y cálculo en segundo plano: las operaciones quedan en un historial que se conserva entre sesiones y se puede exportar completo, Cancelar detiene de verdad un cálculo largo, y los límites con raíces y funciones trigonométricas se explican con el método que corresponde.

### Añadido

- **Historial de operaciones** (menú **Historial**). Cada cálculo correcto se guarda mientras la calculadora está abierta (máximo 200; los errores no se guardan).
  - **Ver historial** (`Ctrl+H`): diálogo con una lista, la operación más reciente primero, con número, operación, entrada y resultado. Enter muestra la operación completa, que vuelve a ser el resultado actual (se puede copiar o exportar); **Usar entrada** la copia al cuadro de entrada para editarla; `Supr` la elimina; **Borrar todo** vacía el historial con confirmación.
  - **Exportar historial** (`Ctrl+Shift+E`): todas las operaciones en un solo documento, en los mismos 5 formatos. En HTML, cada operación es una `<section>` con su MathML y, si se calculó en otro idioma, su atributo `lang`, para que el lector de pantalla cambie de voz. En JSON, una lista `entries`.
  - **Borrar historial**, también desde el menú.
- `historial.py` (modelo sin interfaz, probado con pytest) y `ventana_historial.py` (diálogo).
- Pruebas:
  - `tests/test_historial.py`: modelo, numeración, límite de tamaño y exportación del historial en cada formato.
  - `tests/verificar_ui.py`: diálogo, Suprimir, Mostrar, Usar entrada y exportar todo en la ventana real; pasa de 35 a 45 comprobaciones.
  - La suite tiene 1675 pruebas.
- La ayuda (F1) tiene una sección 9 sobre el historial, en los dos idiomas.
- **El historial se conserva entre sesiones**: se guarda en `%APPDATA%\CalculadoraAccesible\historial.json` (junto a la preferencia de idioma) tras cada cálculo, al eliminar una operación y al borrarlo, y se recupera al abrir la calculadora. Antes se perdía al cerrarla, y un estudiante que vuelve a la calculadora al día siguiente tenía que rehacer los ejercicios para revisarlos.
  - Las operaciones recuperadas son completas: se pueden mostrar, reutilizar, copiar y exportar en LaTeX o MathML igual que las de la sesión. Para eso se guardan también los objetos SymPy (resultado, entrada interpretada y planteamiento) con `pickle`, reconstruyendo cada nodo **sin evaluar**: con la reconstrucción normal de SymPy, el planteamiento `1/6 + 1/3` volvería como `1/2` y la ecuación `y = y` de un sistema con infinitas soluciones como `True`. Se probó primero con `srepr`, pero no reproducía exactamente los árboles. Las integrales se reconstruyen con su constructor normal, que no calcula nada y sin evaluar añadiría un `1·` al integrando.
  - Un archivo dañado no impide abrir la calculadora: las entradas ilegibles se descartan, y si los objetos SymPy no se pueden leer (por ejemplo, tras actualizar SymPy) se conserva el texto de la operación. Si no se puede escribir el archivo, la calculadora sigue funcionando sin avisar, como con la preferencia de idioma.
  - `tests/test_historial.py`: 35 pruebas nuevas, entre ellas la reconstrucción exacta (`srepr` idéntico, mismo LaTeX y MathML) de 18 tipos de resultado; la suite tiene 1722. `tests/verificar_ui.py` usa ahora una carpeta `APPDATA` temporal, para no tocar el historial del usuario, y comprueba que el historial vuelve al abrir de nuevo (46 comprobaciones).

### Cambiado

- **Los cálculos se ejecutan en un proceso aparte** (`proceso_calculo.py`), no en un hilo de la propia calculadora. Es lo que permite que Cancelar detenga el cálculo de verdad (ver *Corregido*).
  - El proceso es persistente: se arranca al abrir la ventana (tarda menos de 1 segundo, sobre todo en importar SymPy) y atiende todos los cálculos; solo se reinicia al cancelar o si termina solo. Crear uno por cálculo añadiría ese segundo a cada operación.
  - Se envía el método, sus datos y el idioma actual, y el resultado vuelve completo (texto, valor, planteamiento) con el mismo pickle "sin evaluar" del historial, que pasa a `serializacion.py` para compartirlo. Con el pickle normal de SymPy, el planteamiento `1/6 + 1/3` llegaría como `1/2` y no se podría exportar como en un libro. `historial.py` conserva los nombres anteriores, para que los historiales ya guardados se sigan leyendo.
  - Si el proceso termina solo (por ejemplo, sin memoria), se muestra un error y el siguiente cálculo arranca otro proceso.
  - En el ejecutable, el proceso de cálculo es otra copia de `CalculadoraAccesible.exe`: `main.py` llama a `multiprocessing.freeze_support()` al empezar, para que esa copia solo calcule y no abra otra ventana. La autoprueba (`--autoprueba`) tiene un caso nuevo que calcula a través del proceso (15 casos), así que `compilar.py` comprueba que funciona en el ejecutable compilado.
  - `CalculadoraAccesible` acepta `nucleo=` (la clase del núcleo matemático) para las pruebas, y al cerrar la ventana se detiene el proceso de cálculo.
- `exportar.py` separa cada formato en el bloque de una operación y el documento que lo envuelve, para exportar un resultado o todo el historial con el mismo código. La exportación de un solo resultado no cambia; solo se añade al HTML un estilo que separa las secciones.
- **Los catálogos de wxWidgets salen de `IDIOMAS`**: añadir un idioma ya no exige tocar `setup.py` ni `main.py`. Antes `setup.py` copiaba a mano solo `wx_locale/es` y `main.py` elegía entre `wx.LANGUAGE_SPANISH` y `wx.LANGUAGE_ENGLISH`, así que un idioma nuevo habría mostrado los botones Aceptar/Cancelar en inglés sin que nada avisara.
  - `i18n.catalogos_wx()` da los idiomas que necesitan catálogo (todos menos el inglés, en el que wxWidgets escribe sus textos); `setup.py` copia uno por idioma y `main.py` busca el idioma con `wx.Locale.FindLanguageInfo(código)`.
  - El ejecutable incluye exactamente lo mismo que antes (`wx_locale/es`).
  - `tests/test_i18n.py`: 3 pruebas nuevas comprueban que wxWidgets reconoce cada idioma de `IDIOMAS` y trae su catálogo `wxstd.mo`.

### Corregido

- **Cancelar un cálculo lo detiene de verdad.** Antes, Cancelar solo dejaba de esperar el resultado: el cálculo seguía en un hilo usando el procesador hasta terminar (o indefinidamente, si SymPy no terminaba), porque Python no permite detener un hilo. Con varios cálculos cancelados, la calculadora y el equipo se volvían lentos. Ahora Cancelar termina el proceso de cálculo (tarda unas centésimas de segundo) y arranca otro limpio para el siguiente, que puede tardar hasta un segundo más en empezar.
  - `tests/test_proceso_calculo.py`: 8 pruebas (resultado completo, planteamiento sin evaluar, idioma, excepción del motor, que el proceso cancelado ya no existe, cancelar sin cálculo en curso, proceso que termina solo, cerrar), con el núcleo de pruebas `tests/nucleo_pruebas.py`; la suite tiene 1733 pruebas.
  - `tests/verificar_ui.py` usa ese núcleo (el cálculo ya no ocurre en el proceso de la ventana, así que no se puede sustituir un método desde la prueba) y comprueba además que el proceso cancelado ya no existe y que al cerrar la ventana termina el proceso de cálculo: 50 comprobaciones. Su arranque está ahora bajo `if __name__ == "__main__"`, porque el proceso de cálculo vuelve a importar el script principal.
- **Continuidad con raíces y potencias**: `sqrt(x^2+9)` cuando x→4 se resuelve ahora por *Continuidad por composición* (resultado 5) en vez de caer en el modo general. La estrategia ya sabía evaluar `u**c`, pero `puede_resolver()` solo aceptaba funciones como `sin` o `exp`, y `sqrt(u)` se representa como la potencia `u**(1/2)`. También se normaliza el exponente, porque el parser deja `1/3` sin evaluar y `(x^2+1)^(1/3)` no se reconocía como raíz cúbica.
  - Para no atribuir a la continuidad límites que no lo son, una potencia con exponente negativo se rechaza si el límite interno es 0 (por ejemplo `1/(x-1)^2` cuando x→1 sigue en el modo general).
  - `tests/test_limites.py`: 4 pruebas nuevas; la auditoría `tests_limites.py` sigue en 65/65.
- **Explicaciones de la estrategia trigonométrica**: un límite ya no se atribuye a un núcleo notable que no aparece como factor en la expresión. Antes bastaba con que hubiera un `sin(u)` o un `cos(u)` en cualquier parte, así que `cos(1/x)` cuando x→∞ se explicaba con `(1−cos u)/u²` y `exp(sin(x)/x)` cuando x→0 con `sin(u)/u`. Los valores eran correctos, pero la explicación no correspondía al método que usaría un estudiante. Ahora `sin(u)`, `tan(u)` o `(1−cos u)` deben ser un factor del numerador:
  - `cos(1/x)` y `exp(sin(x)/x)` se resuelven por *Continuidad por composición*.
  - `(sin(x)−x)/x³` pasa al modo general: el resultado −1/6 sale de la serie de Taylor, no de `sin(u)/u`.
  - Los casos con el núcleo como factor (`x·sin(1/x)` cuando x→∞, `sin²(x)/x²`, `2(1−cos x)/x²`) siguen usando la estrategia trigonométrica.
  - `tests/test_limites.py`: 6 pruebas nuevas (la suite tiene 1687); la auditoría `tests_limites.py` sigue en 65/65.

## [1.2.0] - 2026-10-05

Versión bilingüe: la calculadora completa en español e inglés, y los resultados se pueden copiar y exportar a HTML con fórmulas MathML accesibles, LaTeX, Markdown, JSON o texto plano.

### Añadido

- **Interfaz y resultados en inglés.** Nuevo menú **Idioma / Language** para cambiar entre español e inglés en cualquier momento: menús, etiquetas, diálogos, explicaciones paso a paso de todos los motores, mensajes de error, ayuda (F1) y archivos exportados.
  - La primera vez se elige según el idioma de Windows, y la elección se guarda en `%APPDATA%\CalculadoraAccesible\config.json`.
  - Los botones propios de wxWidgets (Aceptar/Cancelar en los diálogos) también se traducen. Antes salían en inglés incluso en la versión en español, porque el ejecutable no incluía el catálogo de wxWidgets.
  - En inglés se acepta `infinity` como infinito, en expresiones y en la tendencia de un límite.
- **Copiar resultados** (menú **Resultado**): el resultado en una línea (`Ctrl+Shift+C`), la explicación completa (`Ctrl+Shift+A`), en LaTeX (`Ctrl+Shift+L`) o en MathML (`Ctrl+Shift+M`). Un diálogo confirma lo copiado, para que el lector de pantalla lo anuncie.
- **Exportar resultados** (`Ctrl+E`) a **HTML con fórmulas MathML**, **texto plano**, **Markdown**, **documento LaTeX** y **JSON**.
  - El HTML es el formato más accesible: los lectores de pantalla pueden leer y explorar las fórmulas en el navegador.
  - LaTeX y MathML muestran el **planteamiento = resultado** como en un libro (por ejemplo `\int x e^{x}\, dx = (x-1)e^{x} + C`), con `≈` cuando el resultado es decimal.
- `i18n.py` (traducción), `exportar.py` (formatos) y `locales/` (`en.json` con unas 620 traducciones, `ayuda_es.txt` y `ayuda_en.txt`).
- Pruebas nuevas:
  - `tests/test_i18n.py`: cada texto marcado en el código tiene traducción con los mismos marcadores, no hay traducciones sin uso y 41 operaciones en inglés no dejan texto en español.
  - `tests/test_exportar.py`: los 5 formatos para 14 tipos de resultado, JSON válido, MathML como XML válido y LaTeX esperado.
  - La suite pasa de 188 a 1620 pruebas.
  - `tests/verificar_ui.py` comprueba también copiar (leyendo el portapapeles real), exportar y cambiar de idioma: 35 comprobaciones.
- La autoprueba del ejecutable incluye un caso en inglés, que comprueba que las traducciones están en el paquete.

### Cambiado

- **Fachada con resultados estructurados**: `puente.py` ofrece una API de objetos (`evaluar()`, `derivar()`, `limite()`…) que devuelve un `ResultadoOperacion` con el texto, el valor SymPy, el planteamiento sin evaluar, los parámetros y `es_error`. La API de texto anterior (`Evaluar()`, `Derivar()`…) se mantiene.
- **La interfaz detecta los errores con `es_error`** en lugar de mirar cómo empieza el texto. La detección anterior dependía de que cada mensaje empezara por "Error…", y eso no habría funcionado al traducir.
- Gauss-Jordan y los métodos clásicos devuelven también la solución como ecuaciones SymPy (`resolver()`); el enrutador de límites, el valor del límite (`calcular()`).
- La ayuda (F1) pasa de estar dentro del código a `locales/ayuda_<idioma>.txt`, con dos secciones nuevas: copiar/exportar e idioma.
- Las estrategias de integración se muestran con nombres en español ("Integración por partes", "Regla de la potencia"…). Antes aparecían los nombres internos de SymPy en inglés (`Parts`, `Power`, `ConstantTimes`).
- "OPERACIÓN: DERIVADA_ENECIMA" pasa a "OPERACIÓN: DERIVADA DE ORDEN N", y los métodos clásicos se muestran con tilde ("RESOLUCIÓN POR SUSTITUCIÓN").
- Menú y atajos: el nuevo menú **Resultado** usa `Alt+U` para no chocar con `Alt+E` (cuadro de entrada); el botón Borrar indica "Ctrl+Retroceso".

### Corregido

- **Copiar al portapapeles podía fallar sin avisar**: en Windows, el historial del portapapeles o el lector de pantalla lo ocupan un instante tras cada cambio. Ahora se reintenta, se comprueba que la copia funcionó y el texto sigue disponible aunque se cierre la calculadora.
- **El MathML de SymPy no era XML válido**: usaba entidades con nombre de HTML (`&pi;`, `&InvisibleTimes;`), que fallan al pegar en otros programas, y `<mfenced>`, que los navegadores actuales ya no dibujan. Ahora usa referencias numéricas y la forma de MathML Core.
- Se mantiene la salida en español: una batería de 148 operaciones da exactamente el mismo texto que la versión 1.1.0, salvo las mejoras indicadas arriba.

## [1.1.0] - 2026-10-05

Versión de calidad: corrige resultados matemáticos incorrectos (límites bilaterales, factorización), evita que la ventana se congele, añade 188 pruebas automáticas y reduce el instalador de 80 MB a 36 MB.

### Añadido

- **`compilar.py`**: un solo comando para todo el proceso de publicación: pruebas, ejecutable con cx_Freeze, **verificación del ejecutable compilado** e instalador con Inno Setup. Se detiene en el primer fallo y admite `--sin-pruebas`, `--sin-instalador` y `--salida`.
- **Modo `--autoprueba`** (`autoprueba.py`): `CalculadoraAccesible.exe --autoprueba informe.txt` calcula un caso de cada motor sin abrir la ventana y devuelve código 0/1. Sirve para comprobar que el empaquetado no dejó fuera ningún módulo, ya que SymPy carga módulos de forma dinámica. `tests/test_autoprueba.py` la ejecuta también desde el código fuente para que no quede desactualizada.
- **Sugerencias para funciones mal escritas**: `xsin(x)`, `xcos(2*x)` o `sinx` ya no se interpretan en silencio como productos de letras (`i·n·s·x·x`). Ahora dan un error que propone la corrección, por ejemplo "¿Quiso decir x*sin(x)?".
- Se acepta la notación `sin^2(x)` (antes daba error) y la entrada `Matrix([[1,2],[3,4]])` en Gauss-Jordan y en la inversa (antes era imposible porque el parser pasa todo a minúsculas).
- `tests/test_parser.py`: 36 pruebas de sintaxis, sugerencias y efecto de las variables reales. La suite llega a 187 pruebas.
- **Cálculos en segundo plano**: ningún cálculo bloquea ya la ventana. Si uno tarda más de 0,6 s, se abre el diálogo **"Calculando"**, que NVDA anuncia, con tiempo transcurrido y botón **Cancelar**. Mientras hay un cálculo en curso no se puede lanzar otro, y se avisa de ello antes de pedir variables u otros datos.
- **Menú para los sistemas 2×2 por método clásico**: submenú *Álgebra → Sistema 2×2 por método clásico* con Sustitución, Igualación y Reducción. El motor ya existía, pero no se podía usar desde la interfaz.
- Atajo **Ctrl+G** para resolver sistemas por Gauss-Jordan.
- `tests/verificar_ui.py`: verificación automática de la interfaz real (19 comprobaciones: segundo plano, diálogo "Calculando", cancelación, errores del hilo, menús y ayuda). Se ejecuta a mano porque abre la ventana.
- **Suite de pruebas `pytest`** en `tests/` (151 pruebas, se ejecuta en unos 3 segundos):
  - `test_aritmetica.py`: evaluar, simplificar y factorizar (incluido el reconocimiento de cada caso escolar).
  - `test_calculo.py`: derivadas por estrategia, derivada de orden N e integrales (comprueba que la derivada de la integral devuelve la función original).
  - `test_algebra.py`: Gauss-Jordan (solución única, infinitas soluciones, sistema sin solución, entrada matricial), métodos clásicos 2×2 e inversa por cofactores (formatos de entrada, matriz singular, matriz no cuadrada, límite de 4×4).
  - `test_limites.py`: los 65 casos de `tests_limites.py` como pruebas parametrizadas, más pruebas de regresión de límites bilaterales, laterales y formatos de tendencia.
  - `test_ui_errores.py`: comprueba que la interfaz reconoce como error el fallo de cada motor, y que resultados como "el límite no existe" o "el sistema no tiene solución" **no** se tratan como errores.
- `requirements-dev.txt` con las dependencias de desarrollo (`pytest`).
- Este `CHANGELOG.md`.
- Funciones compartidas `limite_seguro()`, `es_limite_evaluable()` y `es_punto_finito()` en `calculo/lim_estrategias/_base.py`.

### Cambiado

- **Ejecutable 3 veces más pequeño**: de 237 MB a 77 MB; **instalador de 80 MB a 36 MB**. cx_Freeze incluía librerías que SymPy importa de forma opcional si están instaladas en la máquina que compila: `llvmlite` (102 MB por sí sola), `numba`, `scipy`, `numpy`, `matplotlib`, `PIL` y `cryptography`, además de herramientas de desarrollo (`pip`, `setuptools`, `lief`…). Ahora se excluyen en `setup.py`, y la autoprueba del ejecutable confirma que no hacían falta.
- **Versión en un solo lugar** (`_version.py`): `compilar.py` se la pasa a Inno Setup (`/DMyAppVersion`), así que ya no se repite a mano en `setup_script.iss`.
- **Dependencias con versión fija**: `requirements.txt` (wxPython 4.2.2, sympy 1.13.3, mpmath 1.3.0) y `requirements-dev.txt` (más pytest 9.1.1 y cx_Freeze 8.5.1).
- `setup.py`: carpeta de salida fija (`build/CalculadoraAccesible`), que ya no depende de la versión de Python; ya no copia el código fuente `.py` junto al ejecutable (ya iba compilado dentro), y en su lugar incluye el CHANGELOG.
- `setup_script.iss`: las URL apuntan al repositorio real (`agus-romero96/calculadora_accesible`; antes `jansen-dev`) y la desinstalación muestra el icono de la aplicación. Se conserva el `AppId` exacto del instalador 1.0.0, para que las nuevas versiones lo actualicen en lugar de instalarse aparte.
- `guia_compilacion.txt` reescrita: explicaba cómo crear archivos que ya existen; ahora explica cómo compilar y publicar.
- **Las variables son números reales** (`Symbol(..., real=True)`). Con variables complejas, que era el comportamiento por defecto de SymPy:
  - la derivada de `abs(x)` era un `Piecewise` con `re(x)`, `im(x)` y `Derivative(re(x), x)`; ahora es `sign(x)`;
  - `sqrt(x^2)` no se simplificaba; ahora da `Abs(x)`;
  - `∫abs(x)` quedaba sin resolver; ahora se resuelve;
  - L'Hôpital sobre `abs(x)/x` mostraba `re(x)` e `im(x)`.

  Todos los módulos que crean una variable a partir de su nombre (calculo, limite, router, gauss) usan ahora `ParserMatematico.simbolo()`. Si no, la `x` que escribe el usuario en un diálogo sería distinta de la `x` del parser, y por ejemplo una derivada daría 0.
- `parser.py` pasa a llamarse **`parser_matematico.py`**, para no coincidir con el nombre de un antiguo módulo de la biblioteca estándar. Se actualizaron `puente.py`, `setup.py`, `guia_compilacion.txt` y el README.
- `continuidad.py` reutiliza los núcleos trigonométricos de `LimitesTrigNotables` en lugar de tener su propia copia: unas 100 líneas menos. Se verificó que los resultados de una batería de límites por composición son idénticos antes y después.
- **Ayuda (F1) actualizada**: lista todos los atajos (antes faltaban Ctrl+S, Ctrl+F, Ctrl+Mayús+D y Ctrl+M) y explica los límites laterales, la entrada de matrices y el diálogo "Calculando". También corrige la regla de multiplicación: decía que `2x` era incorrecto, pero se acepta. Ahora advierte del caso que sí falla: `xsin(x)` hay que escribirlo `x*sin(x)`.
- La interfaz ya no llama directamente a `core.calculo`: derivar e integrar pasan por la fachada `puente.py`, cuyos métodos `Derivar` e `Integrar` aceptan ahora la variable elegida.
- El diálogo de tendencia del límite explica el formato (`0`, `oo`, `-oo`, `0+`, `0-`).
- **Orden de las estrategias de límites** (`calculo/router.py`): ahora van de la más específica a la más general: trigonométricos notables → racionalización → comparación de grados → continuidad → simplificación. Antes "Simplificación y cancelación" iba primera y se atribuía casos que en realidad resolvía SymPy, de modo que la explicación mostrada no correspondía al método adecuado. La auditoría `tests_limites.py` pasa de **22/65 a 65/65**.
- **"Simplificación y cancelación" solo se aplica cuando corresponde**: la sustitución directa debe dar `0/0` en un punto finito y, tras cancelar, la sustitución debe dar un valor finito. Si no, deja paso a otra estrategia.
- Las cinco copias de `_limite_seguro` y las tres de `_es_limite_evaluable` repartidas por las estrategias y `limite.py` se sustituyen por una única implementación en `_base.py`.
- Los resultados de límites se escriben en un lenguaje más claro para el lector de pantalla: `+Infinito`, `-Infinito`, "No existe (los límites laterales no coinciden)" y "No existe (diverge a infinitos de distinto signo)", en lugar de `oo`, `-oo`, `zoo` o `nan`.
- El método del límite lateral calculado por SymPy pasa a llamarse "Modo General (límite lateral calculado con SymPy, dir=…)", igual que los demás casos de modo general.

### Corregido

- **Derivada de orden N**: un `except:` sin tipo hacía que cualquier error, incluida una expresión mal escrita, se mostrara como "El orden debe ser un número entero". Ahora solo ese caso da ese mensaje; el resto de errores se muestran tal cual.
- Los diálogos de texto de Derivada N y Límite se destruyen tras usarse (antes quedaban en memoria).
- **Límites bilaterales incorrectos.** `sympy.limit()` sin dirección calcula solo el límite **por la derecha**, así que la aplicación daba resultados matemáticamente falsos:
  - `lim abs(x)/x` cuando x→0 decía `1` (correcto: no existe, laterales −1 y 1).
  - `lim 1/x` cuando x→0 decía `+∞` (correcto: no existe, −∞ por la izquierda y +∞ por la derecha).
  - `lim sin(x)/x²` cuando x→0 decía `+∞` (correcto: no existe).

  Ahora, en puntos finitos sin dirección, se calcula el límite bilateral (`dir="+-"`).
- **Factorizar no detectaba polinomios irreducibles** (`x^2+1` aparecía como "Factor común") y mostraba pasos falsos como "Extracción de factor común: x**2 - 9" o expresiones como `x**2 - 1*9`. Causa: el parser no evalúa las expresiones (`evaluate=False`), así que las comparaciones del tipo "¿cambió algo?" siempre daban verdadero. Simplificar y Factorizar ahora normalizan la expresión con `.doit()`.
- **Factorizar con factor común numérico** (`2x²−18`, `3x²+6x+3`) no reconocía el caso escolar: comparaba el núcleo con la factorización que incluía la constante. Ahora reconoce "Diferencia de cuadrados", "Trinomio cuadrado perfecto", etc.
- **Factorizar fallaba con suma o diferencia de cubos** (`x^3-8`, `x^3+27`): la comprobación de diferencia de cuadrados suponía factores de dos términos y lanzaba una excepción que anulaba toda la operación.

### Eliminado

- `compilar.spec` (PyInstaller): el proceso real de publicación era cx_Freeze + Inno Setup, y PyInstaller ni siquiera estaba instalado. Con dos sistemas en paralelo, uno quedaba siempre desactualizado. Se puede recuperar del historial de git si hiciera falta.

### Primeros cambios de esta versión

#### Corregido — commit `7be2f58`

- Un límite con error de sintaxis o con la tendencia vacía lanzaba una excepción no capturada y la interfaz no mostraba nada. Ahora devuelve un mensaje de error.
- La tendencia `∞` producía el resultado incorrecto `1/∞`. Ahora acepta `∞`, `-∞` e `infinito`.
- Gauss-Jordan y los métodos clásicos descartaban en silencio el texto después de un segundo `=` (`x+y=1=2`). Ahora lo rechazan con un mensaje.
- La regla de la potencia mostraba siempre `x` aunque la variable fuera otra.
- El diálogo de error de la interfaz solo reconocía mensajes que empezaban exactamente por `Error`. Ahora reconoce todos los formatos de error de los motores.
- README reescrito con funcionalidades, atajos, sintaxis, instalación, compilación y arquitectura.

#### Cambiado — commit `6d3d987`

- Refactorización de los motores matemáticos: objetos de resultado inmutables, renderizado accesible separado del cálculo, parser común compartido y enrutador de límites con estrategias didácticas.

#### Eliminado — commit `9823725`

- Dejan de versionarse `Paquetes/` (librerías copiadas en el proyecto), `__pycache__/` y `.vscode/`. Se amplía `.gitignore` y se añaden al repositorio los archivos de versión, dependencias, compilación y la auditoría de límites.

## [1.0.0] - 2025-12-27

Primera versión publicada con instalador para Windows: evaluación, simplificación y factorización; derivadas, integrales y límites con explicación paso a paso; sistemas por Gauss-Jordan e inversa por cofactores; interfaz accesible para NVDA.

[Sin publicar]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.4.0...HEAD
[1.5.0]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/agus-romero96/calculadora_accesible/compare/9de0952...v1.1.0

---

## Pendiente (problemas conocidos)

- **Variables como reales**: es la convención adecuada para un curso de cálculo, pero los resultados con números complejos (por ejemplo, raíces de números negativos dentro de expresiones con variables) pueden diferir de los que daría SymPy por defecto.
- **`tests/verificar_ui.py` a veces no termina al cerrar la ventana** (en torno a 1 de cada 5 ejecuciones, también antes de los cambios de esta versión): todas las comprobaciones pasan, pero el bucle de eventos sigue vivo y el script acaba por tiempo agotado. El diagnóstico muestra la ventana principal y varios `DialogoHistorial` (del paso del historial) que siguen existiendo aunque se destruyeron. Forzar `ExitMainLoop()` tras cerrar lo evita, pero con NVDA en ejecución provoca una violación de acceso al salir, así que se descartó. No afecta a la calculadora: solo al script de verificación.
- **Traducción al inglés sin revisión nativa**: la escribió el desarrollador y no la ha revisado un hablante nativo de inglés ni un docente angloparlante (terminología de clase).
