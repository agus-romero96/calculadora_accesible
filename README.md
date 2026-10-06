# Calculadora Accesible (Jansen Calculator)

Calculadora científica y simbólica de escritorio diseñada **para usarse con lector de pantalla** (NVDA, JAWS) y solo con teclado. No se limita a dar el resultado: explica **paso a paso** cómo se llega a él, en texto plano y ordenado para que se pueda leer línea por línea.

Está construida con **Python + wxPython** (interfaz nativa y accesible en Windows) y **SymPy** (motor de matemática simbólica).

Disponible en **español e inglés** (interfaz, explicaciones y ayuda). Los resultados se pueden **copiar** y **exportar** a HTML con fórmulas MathML accesibles, LaTeX, Markdown, JSON o texto plano, y quedan en un **historial** que se conserva entre sesiones.

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Accesibilidad](#accesibilidad)
- [Atajos de teclado](#atajos-de-teclado)
- [Cómo escribir expresiones](#cómo-escribir-expresiones)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Compilar el ejecutable e instalador](#compilar-el-ejecutable-e-instalador)
- [Arquitectura](#arquitectura)
- [Traducir a otro idioma](#traducir-a-otro-idioma)
- [Pruebas](#pruebas)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Licencia](#licencia)

---

## Funcionalidades

### Aritmética y álgebra básica (menú **Operaciones**)

| Operación | Qué hace |
|---|---|
| **Evaluar** | Calcula expresiones numéricas. Si el resultado es entero o una fracción simple, lo muestra directamente; si es irracional (por ejemplo `2*pi` o `sqrt(2)`), muestra el valor exacto **y** una aproximación decimal. Rechaza expresiones con variables y sugiere usar *Simplificar*. |
| **Simplificar** | Reduce expresiones algebraicas. Informa la estrategia usada: agrupación por potencias (`collect`), cancelación de factores en fracciones (`cancel`) o simplificación general. |
| **Factorizar** | Factoriza polinomios sobre los racionales y **reconoce el caso escolar** solo cuando puede verificarlo: factor común, trinomio cuadrado perfecto, cubo perfecto, diferencia de cuadrados, suma/diferencia de cubos, trinomio `x²+bx+c` y `ax²+bx+c`. Avisa si el polinomio es irreducible. |

### Cálculo (menú **Cálculo**)

| Operación | Qué hace |
|---|---|
| **Derivar** | Deriva y explica qué regla aplica: constante, linealidad, constante por función, producto, cociente, potencia, potencia negativa, regla de la cadena, exponencial `a^u(x)` y potencia general `u(x)^v(x)` (derivación logarítmica). También lista las reglas secundarias usadas en los subtérminos. |
| **Derivada de orden N** | Calcula derivadas sucesivas mostrando cada derivada intermedia. Simplifica cada pocos pasos para que el resultado no crezca sin control. |
| **Integrar** | Integral indefinida (con `+ C`). Cuando es posible, muestra los pasos: extracción de constante, linealidad, sustitución `u`, integración por partes e integrales inmediatas. Avisa si no existe solución cerrada o si aparecen funciones especiales (`erf`, `Ei`, `Si`, …). |
| **Límite** | Calcula límites en un punto, en `±∞` y **laterales** (`2+`, `2-`). Un enrutador elige la estrategia didáctica más adecuada (ver abajo) y, si ninguna aplica, recurre a un motor general con diagnóstico de indeterminación (`0/0`, `∞/∞`, `k/0`), L'Hôpital validado, límites laterales y clasificación del comportamiento (función continua, discontinuidad evitable, de salto, asíntota vertical u horizontal). |

**Estrategias de límites** (`calculo/lim_estrategias/`):

1. **Simplificación y cancelación**: `together` + `cancel` + factorización.
2. **Límites trigonométricos notables**: extrae núcleos `sin(u)/u → 1`, `tan(u)/u → 1` y `(1−cos u)/u² → 1/2`.
3. **Racionalización**: multiplica por el conjugado en binomios con raíz cuadrada.
4. **Continuidad por composición**: `lim f(g(x)) = f(lim g(x))`, comprobando el dominio de `f` (log, sqrt, asin, acos, …).
5. **Comparación de grados**: cocientes de polinomios cuando `x → ±∞`, incluido el signo de la divergencia.

### Álgebra lineal (menú **Álgebra**)

| Operación | Qué hace |
|---|---|
| **Sistemas (Gauss-Jordan)** | Resuelve sistemas lineales de cualquier tamaño, escritos como ecuaciones (una por línea) o como matriz aumentada `[[1,1,10],[1,-1,2]]`. Muestra cada operación de fila (intercambio, normalización, eliminación) con la matriz resultante, y prefiere pivotes `1` o `-1` para evitar fracciones. Diagnostica con el teorema de Rouché-Frobenius: solución **única**, **infinitas** (con parametrización y grados de libertad) o **sin solución**. |
| **Sistema 2×2 por método clásico** | Resuelve sistemas de dos ecuaciones con dos incógnitas por **sustitución**, **igualación** o **reducción** (submenú *Álgebra → Sistema 2×2 por método clásico*), explicando cada paso como en clase: despeje, sustitución, eliminación y comprobación final. Detecta sistemas incompatibles e indeterminados. |
| **Matriz inversa (cofactores)** | Calcula la inversa por el método de la adjunta, para matrices de hasta 4×4: determinante por expansión de la fila 1, ejemplo detallado del cofactor C₁₁, matriz de cofactores, adjunta e inversa final. Detecta matrices singulares y no cuadradas. |

> Atajo inteligente: si en la entrada escribe **varias líneas que contienen `=`** y pulsa **Ctrl+Enter**, la calculadora detecta que es un sistema y lo resuelve por Gauss-Jordan automáticamente.

### Copiar y exportar resultados (menú **Resultado**)

| Opción | Qué hace |
|---|---|
| **Copiar resultado** | Copia solo el resultado en una línea: `x = 6, y = 4`, `(x - 1)*exp(x) + C`… |
| **Copiar explicación completa** | Copia todo el informe paso a paso. |
| **Copiar como LaTeX** | Copia el planteamiento y el resultado como en un libro: `\int x e^{x}\, dx = \left(x - 1\right) e^{x} + C`. |
| **Copiar como MathML** | Lo mismo en MathML (XML válido), para pegarlo en editores de ecuaciones o páginas web. |
| **Exportar a archivo** | Guarda el resultado en el formato elegido en el diálogo *Guardar*. |

Formatos de exportación:

- **HTML con fórmulas MathML** (recomendado): una página accesible que se abre en cualquier navegador. Los lectores de pantalla (NVDA con MathCAT, JAWS) pueden leer **y explorar** las fórmulas término a término.
- **Texto plano**: el informe tal cual.
- **Markdown**: con la fórmula en `$$…$$`, ideal para apuntes o GitHub.
- **Documento LaTeX**: listo para compilar con XeLaTeX o LuaLaTeX.
- **JSON**: datos estructurados (entrada, parámetros, resultado en texto/SymPy/LaTeX y explicación), con claves en inglés para que sea igual en todos los idiomas.

Tras copiar, un diálogo confirma lo que se copió, para que el lector de pantalla lo anuncie.

### Historial de operaciones (menú **Historial**)

Cada cálculo correcto se guarda en el historial (hasta 200 operaciones). El historial se conserva al cerrar la calculadora, en `%APPDATA%\CalculadoraAccesible\historial.json`, junto a la preferencia de idioma; **Historial → Borrar historial** lo vacía también en disco.

- **Ver historial** (`Ctrl+H`): una lista con la operación más reciente primero, por ejemplo *"3. Integral indefinida: x*exp(x) → (x - 1)*exp(x) + C"*.
  - `Enter` (**Mostrar**): vuelve a mostrar la explicación completa, que pasa a ser el resultado actual y se puede copiar o exportar.
  - **Usar entrada** (`Alt+U`): copia la expresión al cuadro de entrada para modificarla y calcular de nuevo.
  - `Suprimir`: elimina esa operación. **Borrar todo** vacía el historial (pide confirmación).
  - `Esc`: cierra la lista.
- **Exportar historial** (`Ctrl+Shift+E`): todas las operaciones en un solo documento, en cualquiera de los formatos de exportación. En HTML, cada operación es una sección con su fórmula MathML; si se calcularon en idiomas distintos, cada sección indica su idioma para que el lector de pantalla use la voz adecuada.

### Idioma

El menú **Idioma / Language** cambia toda la calculadora entre **español** e **inglés**: menús, diálogos, explicaciones paso a paso, mensajes de error, ayuda (F1) y archivos exportados. La primera vez se elige según el idioma de Windows, y la elección se recuerda (en `%APPDATA%\CalculadoraAccesible\config.json`). En inglés también se acepta `infinity` como infinito.

---

## Accesibilidad

- **Solo teclado**: todas las funciones tienen menú con letra de acceso (`Alt`) y la mayoría tiene atajo directo.
- **Resultado primero**: en derivadas, integrales y límites, la primera línea es siempre `RESULTADO: …`, para no tener que escuchar todo el desarrollo.
- **Gestión del foco**: al calcular, el foco pasa al cuadro de resultados y el cursor vuelve al inicio, listo para leer con las flechas. Si hay un error, el foco vuelve a la entrada.
- **Texto plano estructurado**: secciones numeradas, viñetas y matrices fila por fila (`[ 1, 2 | 3 ]`), sin depender de imágenes ni de notación visual.
- **Diálogos de desambiguación**: si una expresión tiene varias variables (`x*y`), se pregunta respecto a cuál derivar o integrar en una lista navegable con flechas.
- **Ayuda integrada (F1)**: un manual pensado para lectores de pantalla se muestra en el cuadro de resultados.
- **La ventana nunca se congela**: los cálculos se ejecutan en un proceso aparte. Si uno tarda más de medio segundo, se abre el diálogo **"Calculando"** (NVDA lo anuncia), que muestra el tiempo transcurrido y tiene un botón **Cancelar** que detiene el cálculo de inmediato y libera el procesador.
- **Fórmulas accesibles fuera de la calculadora**: la exportación a HTML con MathML permite leer y explorar las fórmulas con el lector de pantalla en el navegador.
- **Ejecutable sin consola**: la versión compilada no abre una ventana de consola que interfiera con NVDA.

---

## Atajos de teclado

| Atajo | Acción |
|---|---|
| `Ctrl+Enter` | Evaluar (o resolver sistema si hay varias líneas con `=`) |
| `Ctrl+S` | Simplificar |
| `Ctrl+F` | Factorizar |
| `Ctrl+D` | Derivar |
| `Ctrl+Shift+D` | Derivada de orden N |
| `Ctrl+I` | Integrar |
| `Ctrl+L` | Límite |
| `Ctrl+G` | Resolver sistema por Gauss-Jordan |
| `Ctrl+M` | Matriz inversa por cofactores |
| `Ctrl+Retroceso` | Borrar entrada y resultados |
| `Ctrl+Shift+C` | Copiar el resultado |
| `Ctrl+Shift+A` | Copiar la explicación completa |
| `Ctrl+Shift+L` | Copiar el resultado en LaTeX |
| `Ctrl+Shift+M` | Copiar el resultado en MathML |
| `Ctrl+E` | Exportar el resultado a un archivo |
| `Ctrl+H` | Ver el historial de operaciones |
| `Ctrl+Shift+E` | Exportar todo el historial |
| `F1` | Ayuda |
| `Alt` | Barra de menús (Operaciones, Cálculo, Álgebra, Resultado, Historial, Idioma, Ayuda) |
| `Alt+E` / `Alt+R` | Ir al cuadro de entrada / de resultados |

---

## Cómo escribir expresiones

| Concepto | Sintaxis | Ejemplo |
|---|---|---|
| Multiplicación | `*`, o el número pegado a una letra o paréntesis | `3*x^2`, `2x`, `3sin(x)`, `2(x+1)` |
| Potencia | `^` o `**` | `x^3`, `x**3`, `sin^2(x)` |
| Raíz cuadrada | `sqrt()` | `sqrt(x+1)` |
| Trigonométricas | `sin`, `cos`, `tan`, `asin`, … | `sin(2*x)` |
| Logaritmo natural | `ln()` o `log()` | `ln(x)` |
| Logaritmo base 10 | `log10()` | `log10(100)` |
| Valor absoluto | `abs()` | `abs(x)/x` |
| Constantes | `pi`, `e` | `e^(2*x)` |
| Infinito | `oo`, `inf` o `infinito` (en la tendencia de un límite también `∞`) | límite hacia `oo` o `-oo` |

- **Entre una variable y una función use siempre `*`**: `x*sin(x)`. Si escribe `xsin(x)` o se olvida los paréntesis (`sinx`), la calculadora da un error con la corrección sugerida ("¿Quiso decir x*sin(x)?").
- Las variables se tratan como **números reales**: por ejemplo, la derivada de `abs(x)` es `sign(x)` y `sqrt(x^2)` se simplifica a `Abs(x)`.
- La entrada **no distingue mayúsculas de minúsculas** (todo se convierte a minúsculas).
- Los paréntesis deben estar balanceados.
- **Límites laterales**: en el diálogo *Tendencia*, escriba el punto seguido de `+` o `-` (`0+`, `4-`).
- **Matrices** para la inversa: una fila por línea, con números separados por espacios o comas, o bien en formato `[[1,2],[3,4]]` o `Matrix([[1,2],[3,4]])`. Se aceptan fracciones y raíces (`1/2`, `sqrt(2)`).

---

## Ejemplos de uso

**Derivar**: escriba `x^2*sin(x)` y pulse `Ctrl+D`.
```
RESULTADO: x*(x*cos(x) + 2*sin(x))
==============================
OPERACIÓN: DERIVADA
...
Estrategia Principal: Regla del Producto
```

**Límite**: escriba `(sqrt(1+x)-1)/x`, pulse `Ctrl+L`, variable `x`, tendencia `0`. Resultado: `1/2`.

**Sistema de ecuaciones**: escriba en dos líneas y pulse `Ctrl+Enter`:
```
x + y = 10
x - y = 2
```
Resultado: `x = 6`, `y = 4`, con cada operación de fila explicada.

**Matriz inversa**: escriba y pulse `Ctrl+M`:
```
1 2
3 4
```

---

## Instalación y ejecución

Requisitos: **Python 3.12** (probado con 3.12.10) en Windows.

```bash
git clone <url-del-repositorio>
cd calculadora_accesible
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Dependencias (con versión fija en `requirements.txt`): `wxPython` 4.2.2, `sympy` 1.13.3 y `mpmath` 1.3.0. Para desarrollar (pruebas y compilación): `pip install -r requirements-dev.txt`.

---

## Compilar el ejecutable e instalador

Requisitos: las dependencias de desarrollo (`pip install -r requirements-dev.txt`, incluye cx_Freeze) y, para el instalador, [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```bash
python compilar.py
```

Un solo comando hace todo y se detiene en el primer fallo:

1. Ejecuta las pruebas.
2. Compila el ejecutable con **cx_Freeze** en `build\CalculadoraAccesible\` (unos 77 MB).
3. **Verifica el ejecutable compilado**: lo ejecuta con `--autoprueba`, que calcula un caso de cada motor sin abrir la ventana. Así se detecta si al empaquetado le falta algún módulo.
4. Genera el instalador en español con **Inno Setup**: `Output\setup-calculadora-accesible-v<versión>.exe` (unos 36 MB).

Opciones: `--sin-pruebas`, `--sin-instalador` y `--salida CARPETA`.

La versión se define **solo** en `_version.py`; el título de la ventana, el ejecutable y el instalador la toman de ahí. Los detalles están en [`guia_compilacion.txt`](guia_compilacion.txt).

---

## Arquitectura

```
main.py                 Interfaz wxPython (ventana, menús, atajos, diálogos)
  │
proceso_calculo.py      Proceso de cálculo aparte (multiprocessing): se detiene al cancelar
serializacion.py        pickle de objetos SymPy sin evaluar (historial y proceso de cálculo)
  │
puente.py               Fachada: CoreMatematico orquesta los motores y devuelve
  │                     ResultadoOperacion (texto + valor SymPy + planteamiento)
exportar.py             Copiar/exportar (un resultado o el historial): texto, Markdown,
                        LaTeX, HTML+MathML, JSON
historial.py            Historial de operaciones y su archivo (modelo, sin interfaz)
ventana_historial.py    Diálogo accesible del historial
i18n.py                 Traducción: tr(), N_(), idioma guardado y detectado
locales/                en.json (catálogo inglés) y ayuda_es.txt / ayuda_en.txt
  │
parser_matematico.py    ParserMatematico: parser único compartido (SymPy parse_expr)
  │
├── aritmetica.py               Evaluar / Simplificar / Factorizar
├── algebra/
│   ├── gauss_logic.py          Gauss-Jordan paso a paso
│   ├── matrix_logic.py         Inversa por cofactores
│   └── classic_systems.py      Sustitución, igualación, reducción (2x2)
└── calculo/
    ├── calculo.py              Derivadas, derivada N, integrales
    ├── router.py               Enrutador de estrategias de límites
    ├── limite.py               Motor general de límites (fallback)
    └── lim_estrategias/        Estrategias didácticas (patrón Strategy)
        ├── _base.py
        ├── simplificacion.py
        ├── trigonometria.py
        ├── racionalizacion.py
        ├── continuidad.py
        └── infinito.py

autoprueba.py           Prueba del núcleo para el ejecutable compilado (--autoprueba)
_version.py             Versión de la aplicación (única fuente)
compilar.py             Pruebas + ejecutable + autoprueba + instalador
setup.py                Configuración de cx_Freeze
setup_script.iss        Instalador (Inno Setup)
tests/                  Suite de pytest (+ verificar_ui.py, prueba manual de la interfaz)
```

Principios de diseño:

- **Inyección de dependencias**: todos los motores reciben el mismo `ParserMatematico`, así que la sintaxis es la misma en todo el programa.
- **DTOs inmutables** (`@dataclass(frozen=True)`): cada motor devuelve un objeto de resultado (`ResultadoAritmetica`, `ResultadoCalculo`, `ResultadoGauss`, …) y un método `renderizar` lo convierte en texto accesible. La lógica matemática y la presentación están separadas.
- **"La verdad la da SymPy"**: el resultado final siempre se calcula con SymPy; la explicación pedagógica se añade aparte y solo se muestra un patrón (por ejemplo, "diferencia de cuadrados") cuando se puede verificar.
- **Patrón Strategy en límites**: cada técnica implementa `puede_resolver()` y `resolver()`. El enrutador las prueba en orden y la primera que llega a una conclusión gana.
- **Traducción**: el código está escrito en español, y cada texto visible pasa por `tr("…")`, que busca su traducción en `locales/<idioma>.json`. Los textos que además funcionan como identificadores (nombres de estrategia que se comparan en el código) se marcan con `N_("…")` y se traducen solo al mostrarlos.
- **Resultado estructurado**: la interfaz trabaja con `ResultadoOperacion` (texto, valor SymPy, planteamiento sin evaluar y `es_error`), lo que permite exportar `planteamiento = resultado` y detectar errores sin mirar el texto.

---

## Traducir a otro idioma

1. Copie `locales/en.json` como `locales/<código>.json` (por ejemplo `fr.json`) y traduzca los **valores**. Las claves son el texto original en español y no se modifican; los marcadores entre llaves (`{variable}`) deben conservarse.
2. Cree `locales/ayuda_<código>.txt` con la ayuda (F1) traducida.
3. Añada el idioma a `IDIOMAS` en `i18n.py` (y, si quiere que se elija automáticamente, ajuste `detectar_idioma_sistema()`).
4. Ejecute las pruebas: `tests/test_i18n.py` comprueba que el catálogo cubra **todos** los textos del programa y que los marcadores coincidan.

---

## Pruebas

El proyecto tiene una suite de **pytest** en `tests/` (más de 1600 pruebas, unos 15 segundos) que cubre el parser, todos los motores, la exportación, la traducción (cada texto del programa tiene traducción, y los resultados en inglés no dejan texto en español) y la detección de errores en la interfaz (sin abrir ventanas).

```bash
pip install -r requirements-dev.txt
python -X utf8 -m pytest tests
```

`tests_limites.py` es además un script de auditoría independiente con 65 casos de límites (trigonométricos, racionalización, infinito y fallback). Para cada caso comprueba el **valor** y la **estrategia** usada, e imprime un informe detallado:

```bash
python -X utf8 tests_limites.py
```

Para verificar la interfaz (abre la ventana real unos segundos y comprueba el cálculo en segundo plano, que cancelar detiene el proceso de cálculo, los menús, copiar, exportar, el historial, el cambio de idioma y la ayuda):

```bash
python -X utf8 tests/verificar_ui.py
```

Estado actual: todas las pruebas pasan y la auditoría da 65/65.

Los cambios del proyecto se documentan en [`CHANGELOG.md`](CHANGELOG.md).

---

## Limitaciones conocidas

- Los métodos clásicos (sustitución, igualación, reducción) solo admiten sistemas 2×2. Para otros tamaños, use Gauss-Jordan.
- La inversa por cofactores está limitada a 4×4 (para matrices mayores, use Gauss-Jordan).

---

## Licencia

Distribuido bajo la licencia **MIT**. Ver [`LICENSE`](LICENSE).
