# Registro de cambios

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/). La versión actual está en `_version.py`.

## [Sin publicar]

(Nada todavía.)

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

[Sin publicar]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/agus-romero96/calculadora_accesible/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/agus-romero96/calculadora_accesible/compare/9de0952...v1.1.0

---

## Pendiente (problemas conocidos)

- **Variables como reales**: es la convención adecuada para un curso de cálculo, pero los resultados con números complejos (por ejemplo, raíces de números negativos dentro de expresiones con variables) pueden diferir de los que daría SymPy por defecto.
- **Traducción al inglés sin revisión nativa**: la escribió el desarrollador y no la ha revisado un hablante nativo de inglés ni un docente angloparlante (terminología de clase).
