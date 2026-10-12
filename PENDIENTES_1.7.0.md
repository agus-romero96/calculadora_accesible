# Pendientes para la versión 1.7.0

Lista oficial (aprobada el 2026-10-11: los 14 métodos, una sola operación y este orden). Ecuaciones diferenciales ordinarias (EDO), con el estándar del paso a paso: **Regla**, **En este caso**, cada cuenta intermedia y **Queda**; el resultado primero, comprobado contra SymPy (sustituyendo la solución en la ecuación), y legible con NVDA. Cada operación se registra en `puente.REGISTRO`, con sus textos en `locales/es.json` y `locales/en.json`, su ayuda (F1), sus pruebas y su entrada en `CHANGELOG.md`.

Una tarea terminada se tacha (`~~...~~`) y se anota el commit.

## Diseño común

- **Una sola operación, "Ecuación diferencial"** (menú **Cálculo**), que reconoce el tipo y elige el método, igual que **Integrar** elige entre partes, sustitución o fracciones parciales. El primer paso dice siempre qué tipo de ecuación es y por qué (por ejemplo: "Es lineal de primer orden: se puede escribir y' + P(x)*y = Q(x)").
- **Entrada**: `y' + 2*y = x`, `y'' - 3*y' + 2*y = exp(x)`, también `dy/dx`. Variable independiente `x` y función `y` por defecto.
- **Condiciones iniciales opcionales** (`y(0) = 1, y'(0) = 0`): si se dan, se resuelve el problema de valor inicial y se hallan las constantes con sus cuentas.
- **Solución general** con constantes `C1`, `C2`...; si la solución queda implícita y no se puede despejar `y`, se da en forma implícita y se dice.
- Lo que quede fuera de los métodos de la lista se resuelve con SymPy sin pasos, con un aviso, como en las demás operaciones. No existe un método general para todas las EDO no lineales: "todos los casos" son los de un curso de ecuaciones diferenciales.
- Las integrales de cada método usan el paso a paso de **Integrar** (incluidas fracciones parciales y sustitución trigonométrica).

## Plan

### Primer orden

1. ~~**Variables separables** — separar, integrar los dos lados, despejar `y`. Incluye las reducibles a separables `y' = f(a*x + b*y + c)` (cambio `u = a*x + b*y + c`).~~ — **completada** (menú **Cálculo**, `Ctrl+Shift+R`, `calculo/edo.py`; commit `860c095`)
   - Con la base común: lectura de `y'`/`dy/dx` y condiciones, planteamiento, despeje de `y` función a función con la constante renombrada, soluciones constantes, condición inicial y comprobación.
2. ~~**Lineales de primer orden** — forma `y' + P(x)*y = Q(x)`, factor integrante `e^(∫P dx)`, multiplicar e integrar.~~ — **completada** (`MotorEdo._lineal`; el factor integrante se llama `m(x)`, sin letra griega; commit `68c3e88`)
3. ~~**Homogéneas** — `y' = f(y/x)`, cambio `y = u*x`, y la separable que resulta.~~ — **completada** (`MotorEdo._homogenea`; commit `9ce5c9e`)
4. ~~**Exactas** — comprobar `∂M/∂y = ∂N/∂x`, hallar la función potencial. Si no es exacta, **factor integrante** que dependa solo de `x` o solo de `y`.~~ — **completada** (`MotorEdo._exacta`; entrada también en forma diferencial, `M dx + N dy = 0`; commit `a4f8e27`)
5. ~~**Bernoulli** — `y' + P(x)*y = Q(x)*y^n`, cambio `v = y^(1-n)` y la lineal que resulta.~~ — **completada** (`MotorEdo._bernoulli`; commit `904248d`)
6. **Riccati** (si se da una solución particular) y **Clairaut** / **reducibles de orden** (`F(x, y', y'') = 0` sin `y`, o sin `x`).

### Orden superior, lineales

7. ~~**Coeficientes constantes, homogéneas** (orden `n`) — ecuación característica, sus raíces (con los pasos de **Resolver ecuación**) y la solución según sean reales distintas, repetidas o complejas conjugadas.~~ — **completada** (`_OrdenSuperior` en `calculo/edo.py`; con las condiciones iniciales de orden `n`; commit `a73240e`)
8. ~~**No homogéneas: coeficientes indeterminados** — la forma de la solución particular según `g(x)` (polinomios, exponenciales, senos y cosenos, sus productos), la corrección por `x^k` si coincide con la homogénea, y el sistema de coeficientes.~~ — **completada** (`_OrdenSuperior.particular`; el sistema, por sustitución con sus pasos; commit `a73240e`)
9. ~~**No homogéneas: variación de parámetros** — el wronskiano (con los pasos del **Determinante**), `u1'`, `u2'` y sus integrales.~~ — **completada** (`_OrdenSuperior.variacion`, orden 2; el wronskiano 2x2 con su cuenta)
10. ~~**Cauchy-Euler** — `a*x^2*y'' + b*x*y' + c*y = 0` (y no homogéneas), con `y = x^m` y la ecuación indicial.~~ — **completada** (`_OrdenSuperior.indicial`; se usa `x^r`; las no homogéneas, por variación de parámetros)
11. **Reducción de orden** — con una solución `y1` conocida, `y2 = u*y1`.

### Otros métodos

12. **Transformada de Laplace** para problemas de valor inicial — transformar cada término (tabla con su regla), despejar `Y(s)`, fracciones parciales y transformada inversa. Incluye escalón unitario y delta.
13. **Sistemas lineales de primer orden** con coeficientes constantes `X' = A*X` — valores y vectores propios; casos de raíces distintas, repetidas y complejas.
14. **Series de potencias** alrededor de un punto ordinario — la recurrencia de los coeficientes y los primeros términos. (Frobenius en un punto singular regular, si da tiempo.)

## Orden propuesto

1 → 2 → 3 → 4 → 5 primero (comparten "separar e integrar"), después 7 → 8 → 9 → 10 → 11, y al final 12, 13, 14 y 6, que son los más largos o menos usados.

## Antes de publicar la 1.7.0

- Fusionar la rama con `main`.
- Compilar el ejecutable con `compilar.py` (autoprueba del `.exe`, con un caso de ecuación diferencial).
