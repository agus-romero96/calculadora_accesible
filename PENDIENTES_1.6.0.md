# Pendientes para la versión 1.6.0

Hoja de ruta de cinco funciones nuevas, todas con el estándar del paso a paso: **Regla**, **En este caso**, cada cuenta intermedia y **Queda**; el resultado primero, comprobado contra SymPy, y legible con NVDA. Cada una se registra en `puente.REGISTRO`, con sus textos en `locales/es.json` y `locales/en.json`, su ayuda (F1), sus pruebas y su entrada en `CHANGELOG.md`.

Una tarea terminada se tacha (`~~...~~`) y se anota el commit.

Ya hecho en esta rama (antes del plan): resolver ecuaciones e inecuaciones de una variable (commits `c14a7f4`, `4014307`, `0064de1`; redacción aprobada con NVDA).

## Plan

1. ~~**Recta tangente y recta normal a una curva en un punto** (menú **Cálculo**)~~ — **hecho** (`Ctrl+T`, `calculo/rectas.py`; pendiente de commit)
   - ~~Evaluar `f(x₀)` (el punto de tangencia), con sus cuentas.~~
   - ~~Derivar `f'(x)`, con el paso a paso de **Derivar**.~~
   - ~~Pendiente de la tangente: `m = f'(x₀)`.~~
   - ~~Pendiente de la normal: `m_n = -1/m` (casos `m = 0` y tangente vertical).~~
   - ~~Ecuación punto-pendiente `y - y₀ = m(x - x₀)` y su forma explícita, para las dos rectas.~~

2. **Extremos locales y puntos de inflexión** (menú **Cálculo**)
   - Puntos críticos con `f'(x) = 0`.
   - Criterio de la primera derivada o de la segunda para máximos y mínimos.
   - Concavidad y puntos de inflexión con `f''(x) = 0`.

3. **Operaciones con matrices** (menú **Álgebra**)
   - Suma y resta, elemento a elemento.
   - Producto matricial, fila por columna, con la aritmética intermedia.
   - Matriz transpuesta.

4. **División larga de polinomios** (menú **Álgebra** u **Operaciones**)
   - Algoritmo de la galera: cada término del cociente, cada resta y cada término que se baja.
   - Cociente y resto explícitos, y comprobación `dividendo = divisor · cociente + resto`.

5. **Trigonometría analítica** (menú nuevo o en **Álgebra**)
   - Resolución de triángulos.
   - Ley de senos y ley de cosenos, paso a paso.

## Antes de publicar la 1.6.0

- Fusionar la rama con `main`.
- Compilar el ejecutable con `compilar.py` (autoprueba del `.exe`).
