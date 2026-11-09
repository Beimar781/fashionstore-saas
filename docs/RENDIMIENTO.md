# Decisiones de rendimiento (RNF09)

Cuatro decisiones de consulta y almacenamiento, justificadas y listas para pasar al Word. Los índices se verifican en `backend/tests/test_r9_indices.py`
(con `EXPLAIN`, apagando el recorrido completo de la tabla para comprobar que cada consulta crítica tiene un índice utilizable).

## 1. Todo índice empieza por `empresa_id` (aislamiento y rendimiento a la vez)
La base es compartida y cada consulta filtra por empresa. Los índices compuestos llevan `empresa_id` primero (`ix_pedidos_pagados (empresa_id, sucursal_id, canal, pagado_en)`,
`ix_existencias_sucursal (empresa_id, sucursal_id, variante_id)`, `ix_bitacora_empresa (empresa_id, creado_en DESC)`…). Así la misma columna que garantiza el aislamiento lógico
acota el recorrido: una empresa pequeña no paga el costo de las demás.
**Alternativa descartada:** una base o un esquema por empresa (más aislamiento, pero migraciones y conexiones por tenant; el enunciado pide una base compartida).

## 2. Índice parcial para las ventas pagadas
Los reportes solo miran pedidos `PAGADO`, que son una fracción de la tabla (carritos y pedidos por pagar no cuentan). `ix_pedidos_pagados` es un índice **parcial**
(`WHERE estado = 'PAGADO'`): más pequeño, más rápido de mantener y con el orden justo para «ventas por sucursal y fecha».
Los conflictos de sincronización usan la misma idea (`ix_operaciones_offline_conflicto WHERE estado = 'EN_CONFLICTO'`): el Encargado solo consulta lo que está en conflicto.

## 3. Paginación y límites en lo que crece
El catálogo (`GET /catalogo/productos` y `/catalogo/buscar`, `tamano` hasta 50), la bitácora (`pagina` y `tamano`), el inventario por sucursal (`GET /reportes/inventario`, hasta 200 por página)
y los movimientos de inventario devuelven páginas con el total; nunca la tabla completa. Los reportes tienen un periodo máximo de 366 días y el reporte generativo limita el detalle de ventas
(`limite_detalle`) y el ranking (`limite_ranking`). La exportación a Excel o PDF es lo único que recorre todo el periodo, y por eso el inventario exportado se acota a 5000 filas.
**Por qué:** una consulta sin límite crece con los datos de la empresa y degrada a todas las demás en una base compartida.

## 4. Cálculo en la base y descarga acotada al cliente
Los totales de los reportes (ventas netas, por canal, por sucursal, ranking) se calculan con `SUM`/`COUNT`/`GROUP BY` en PostgreSQL, no en Python: se transfieren pocas filas agregadas.
En el cliente, el catálogo descargado para trabajar sin conexión (CU-37) es **solo el subconjunto autorizado** (productos activos, variantes, stock de las sucursales del usuario) y se guarda
en IndexedDB y SQLite; las imágenes van al caché del Service Worker o del dispositivo. Así las consultas diarias del Cajero no salen al servidor y la descarga completa se repite solo
si los datos tienen más de 6 horas (actualización automática).
