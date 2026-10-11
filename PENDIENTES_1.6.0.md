# Pendientes para la versión 1.6.0

Lista oficial de funciones de la versión, todas con el estándar del paso a paso: **Regla**, **En este caso**, cada cuenta intermedia y **Queda**; el resultado primero, comprobado contra SymPy, y legible con NVDA. Cada una se registra en `puente.REGISTRO`, con sus textos en `locales/es.json` y `locales/en.json`, su ayuda (F1), sus pruebas y su entrada en `CHANGELOG.md`.

Una tarea terminada se tacha (`~~...~~`) y se anota el commit.

## Plan

1. ~~**Integral definida**~~ — **completada** (publicada en la 1.5.0, `Ctrl+Shift+I`).
2. ~~**Ecuaciones e inecuaciones de una variable**~~ — **completada** (`Ctrl+R`; commits `c14a7f4`, `4014307`, `0064de1`; redacción aprobada con NVDA).
3. ~~**Recta tangente y normal**~~ — **completada** (`Ctrl+T`; commit `84ecf99`).
4. ~~**Puntos críticos, extremos locales e intervalos de crecimiento** (menú **Cálculo**)~~ — **completada** (`Ctrl+Shift+X`, `calculo/extremos.py`; commit `1befd9e`)
   - ~~Puntos críticos: donde `f'(x) = 0` (dentro del dominio).~~
   - ~~Intervalos de crecimiento y decrecimiento con el signo de `f'(x)` en cada intervalo (criterio de la primera derivada).~~
   - ~~Máximos y mínimos locales, con el criterio de la segunda derivada cuando decide (`f''(x₀) ≠ 0`), y el valor `f(x₀)` de cada extremo.~~
   - Queda fuera: puntos críticos donde `f'(x)` no existe pero `f(x)` sí (picos). `x^(2/3)` da un mensaje claro; `abs(x)` lo resuelve SymPy sin pasos. Se pueden añadir si hace falta.
5. ~~**Polinomio de Taylor alrededor de un punto**~~ — **completada** (menú **Cálculo**, `Ctrl+Shift+T`, `calculo/taylor.py`)
   - ~~Orden `n` y punto `x₀`.~~
   - ~~Cada derivada `f⁽ᵏ⁾(x)`, su valor en `x₀` y cada término `f⁽ᵏ⁾(x₀)/k! · (x - x₀)ᵏ`.~~
6. **Determinante de una matriz por cofactores** (operación independiente en **Álgebra**)
   - Expansión por cofactores con cada menor, su signo y sus cuentas.
7. **Derivada implícita** (con respecto a `x` de una ecuación `F(x, y) = 0`)
   - Derivar los dos lados tratando `y` como función de `x` (regla de la cadena: `dy/dx`), y despejar `dy/dx`.

## Antes de publicar la 1.6.0

- Fusionar la rama con `main`.
- Compilar el ejecutable con `compilar.py` (autoprueba del `.exe`).
