# Registro de cambios

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/). La versión actual está en `_version.py`.

## [Sin publicar]

### Añadido

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

### Cambios anteriores (ya en el historial de git)

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

---

## Pendiente (problemas conocidos)

- **Símbolos complejos**: el parser crea variables sin la suposición de ser reales, así que algunos pasos muestran `re(x)` e `im(x)`; por ejemplo, al aplicar L'Hôpital a `abs(x)/x`. El resultado es correcto, pero la explicación es confusa.
- **Parser**:
  - `xsin(x)` se interpreta en silencio como `i·n·s·x·x` (separa las letras al multiplicar sin `*`). Debería avisar o reconocer el nombre de la función.
  - Convierte todo a minúsculas, así que la entrada `Matrix(...)` no funciona.
  - Su nombre (`parser.py`) coincide con el de un antiguo módulo de la biblioteca estándar.
- **Cancelar un cálculo** no lo detiene: el hilo sigue usando el procesador hasta terminar, porque Python no permite detener un hilo. Para detenerlo de verdad habría que ejecutar los cálculos en un proceso aparte.
- **Interfaz**: falta un historial de operaciones y una forma rápida de copiar solo la línea del resultado.
- **Prueba con NVDA real**: el diálogo "Calculando" y el nuevo submenú se verificaron de forma automática (`tests/verificar_ui.py`), pero no todavía con el lector de pantalla. El botón Cancelar del diálogo tampoco se ha pulsado físicamente: la prueba invoca directamente la función que ejecuta.
- **Empaquetado**: hay dos sistemas en paralelo (cx_Freeze y PyInstaller), la versión está duplicada en `setup_script.iss` y `requirements.txt` no fija versiones.
