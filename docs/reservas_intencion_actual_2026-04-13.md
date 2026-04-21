# Reservas e Intencion Actual 2026-04-13

## Regla de trabajo

Este documento no redefine la codificacion.
Sirve para interpretar la intencion actual de reservas y hold del Excel base usando el inventario ya desglosado.

## Aclaraciones confirmadas

- El Excel de herederos funciona como base de intencion, no como estructura final.
- Rasmi Sanchez, Nuria Alpizar y Alejandro Aguilar no deben tratarse como herederos.
  Son clientes con apartados o reservas.
- `130` ya no se interpreta como el numero viejo del Excel.
  Su desglose actual relevante es:
  - `134A-1`
  - `134B-1`
  Ambos quedan en estado `HOLD UNTIL SALE`.
- `13A-1` representa un item que se vende como set de 3 unidades, aunque solo tenga una foto.
- `136` ya fue desglosado y debe leerse solo con la estructura nueva.
- `138A-1` y `138A-2` ya fueron resueltos con sus propios numeros de item y no deben volver a colgar de `136`.

## Implicaciones operativas

- La carpeta `Reservas Herederos` debe poblarse solo con reservas de herederos reales.
- Los apartados de clientes conviene separarlos conceptualmente de herederos, aunque luego puedan vivir en una carpeta auxiliar distinta.
- Los casos `HOLD UNTIL SALE` no equivalen automaticamente a reserva heredero.
  Deben tratarse como bloqueo comercial temporal.

## Casos confirmados para interpretar con cuidado

- `134A-1` y `134B-1`: hold hasta venta final.
- `13A-1`: un solo item, set de tres unidades.
- `136`: usar solo desglose nuevo.
- `138A-1`, `138A-2`: items ya independientes.

## Pendiente siguiente

Construir una tabla limpia con tres tipos:

- `heredero`
- `cliente`
- `hold_until_sale`

y convertir cada entrada a codigo actual antes de copiar fotos.
