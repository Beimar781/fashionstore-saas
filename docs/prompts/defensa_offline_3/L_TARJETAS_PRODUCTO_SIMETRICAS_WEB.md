# Prompt L — Tarjetas de producto simétricas y presentables (web)

Problema (captura del catálogo): las tarjetas de prenda tienen alturas de imagen distintas (la imagen cambia de alto según la foto), los títulos ocupan 1 o 2 líneas y empujan precio, categoría y colores a posiciones diferentes; la tarjeta «Camiseta Beige» queda con los colores cortados abajo. La cuadrícula se ve desigual.

Objetivo: todas las tarjetas del catálogo con **exactamente el mismo tamaño y la misma distribución interna**, sin romper responsive ni la versión sin conexión.

## Qué hacer
1. **Imagen con proporción fija.** Contenedor con `aspect-ratio: 4 / 5` (o 3 / 4) y `overflow: hidden`; la `<img>` con `width:100%; height:100%; object-fit: cover; object-position: center top` (que no se corte la cabeza/cuello de la prenda). Fondo neutro mientras carga y `loading="lazy"`; si la imagen falla, placeholder con el mismo tamaño.
2. **Tarjeta como columna de altura completa.** `display:flex; flex-direction:column; height:100%`; la cuadrícula con `display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 24px; align-items: stretch`. Mismo ancho para todas (no `auto`).
3. **Zona de texto de altura estable.**
   - Nombre: máximo 2 líneas con `line-clamp: 2` y `min-height` de 2 líneas (los de una línea no desalinean el resto); `title` con el nombre completo.
   - Categoría · marca: 1 línea con ellipsis.
   - Precio: siempre en la misma posición (usar `margin-top:auto` en el bloque inferior para anclar precio, colores y tallas abajo).
4. **Fila de colores y tallas con altura reservada.** Círculos de color de 16 px en una fila con `min-height` fija, máx. ~5 visibles y «+N» si hay más; «Tallas: S · M · L · XL» en una línea con ellipsis. Que nunca queden cortados ni dependan del alto de la imagen (corrige el caso de Camiseta Beige).
5. **Detalles de presentación.** Borde/sombra suave igual en todas, `border-radius` 14 px, hover con elevación leve y ligero zoom de imagen (sin cambiar el tamaño de la tarjeta), foco visible por teclado, tarjeta completa clicable.
6. **Etiquetas de estado coherentes** (Agotado, Poco stock, Sin conexión) como insignia en la esquina de la imagen, sin mover el contenido.
7. **Aplícalo a todas las vistas con tarjetas de producto**: catálogo del cliente, resultados de búsqueda, favoritos / «también te puede interesar», selector de prendas del POS y de Reservas si usan tarjetas. Extrae un único componente/estilo compartido (`product-card`) en vez de duplicar CSS.
8. **Responsive:** 4 columnas en escritorio ancho, 3 en laptop, 2 en tablet, 2 compactas en móvil (≥ 150 px); en móvil que el texto no se desborde.
9. **Estados de carga y vacíos:** skeleton con la misma proporción de tarjeta; «Sin resultados» centrado.
10. Mantén accesibilidad: `alt` con el nombre de la prenda, contraste suficiente, tamaños táctiles.

## Verificación
- Prueba con nombres largos («Camiseta Verde Oliva Estampada»), cortos, sin imagen, con 1 y con 6+ colores, y agotados: todas las tarjetas de una fila deben tener la misma altura y el precio alineado.
- Revisa 1440, 1024, 768 y 390 px de ancho.
- `npm run build` y tests web verdes; no toques backend ni lógica de carrito/inventario.
- Un commit, en español, a mi nombre, **sin co-autor**; sube a `correccion-pago` y `main`. Avísame al terminar para verificar en Railway.
