# Comprobación manual pendiente: fase 6.5A

Las pruebas automáticas verifican contratos de datos y despacho con diálogos sustituidos, además de crear los formularios nativos y comprobar nombres, botón predeterminado e inserción con selección. No certifican anuncios de lectores de pantalla ni navegación real. Ejecutar estas comprobaciones en Windows con NVDA y JAWS, en español e inglés, y registrar versión del lector, resultado e incidencias.

- Abrir «Nuevo cálculo guiado» desde el botón y desde Operaciones usando teclado. Recorrer las tres opciones con flechas y comprobar que se anuncian nombre y descripción.
- Abrir cada formulario: el foco inicial debe estar en ecuación o función. Recorrer con Tab y Mayús+Tab; comprobar etiquetas, nombres, orden, selector de dirección y botones sin utilizar ratón.
- Insertar cada plantilla al final, en medio y sobre una selección. Comprobar que vuelve el foco a la expresión y queda seleccionado el contenido editable. Editar numerador, denominador, radicando, base y exponente y revisar la expresión con flechas.
- Resolver `2*x + 3 = 7`; derivar `x^2 + 3*x` respecto de `x`; calcular `sin(x)/x` en `0`. No deben aparecer preguntas adicionales por los mismos datos. Comprobar historial y exportación de los resultados.
- Calcular `1/x` en `0` con las tres direcciones. Introducir `0+` en tendencia: debe pedir corregir el valor sin cerrar el formulario. Para infinito, usar Bilateral; el núcleo determina el sentido por el signo del infinito.
- Dejar cada campo obligatorio vacío y pulsar Calcular: comprobar un único aviso y foco en el campo correspondiente. Introducir `xsin(x)` y comprobar que se conserva el mensaje del parser.
- Pulsar Enter desde los campos: debe calcular. En los botones de inserción, Enter debe insertar. Escape, Cancelar y cierre de ventana deben cancelar sin iniciar cálculo. Al salir de los diálogos debe restaurarse el foco al control de origen; tras un resultado, se conserva el foco de resultados existente.
- Iniciar un cálculo lento y cancelarlo en el diálogo de progreso existente; comprobar que se puede hacer otro cálculo. Intentar abrir el modo guiado mientras se calcula y comprobar el aviso de operación en curso.
- Verificar editor libre, Ctrl+Enter, Ctrl+Retroceso, Ctrl+D, Ctrl+L, Ctrl+R, ayuda, preferencias, historial y exportación.
- Comprobar que no hay anuncios repetitivos durante la edición ni texto cortado con escalado de pantalla de 150 % y 200 %.

El prototipo usa la notación del parser existente y plantillas con valores de ejemplo editables. No interpreta lenguaje natural ni modifica la presentación de resultados. Las ecuaciones siguen el alcance del motor existente.
