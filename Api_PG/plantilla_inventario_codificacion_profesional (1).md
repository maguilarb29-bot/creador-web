# 📊 Plantilla Maestra de Inventario y Codificación

Esta plantilla conserva el **orden original del Excel** y, al mismo tiempo, usa un **código estructurado** para organizar sets, sub-sets, items y fotos.

---

## ✅ REGLAS FINALES DEL SISTEMA

### 1. El número original se respeta siempre
- El número base mantiene la cronología original del inventario.
- No se renumera aunque cambie la clasificación.
- Ejemplos: 2, 55, 136, 139, 159, 178, 182.

### 2. Las letras organizan la estructura
- El número base identifica el grupo o registro original.
- Las letras indican set, sub-set o item derivado.
- Ejemplos:
  - 136I = set
  - 136IA = item derivado de 136I
  - 178A = set A dentro de 178
  - 178AA = item dentro de 178A

### 3. Las fotos siempre van al final con guion y número
- No se usa F.
- El formato correcto es:
  - 136IA-1
  - 136IA-2
  - 178AA-1
- Regla: **guion + número = foto**

### 4. Si algo nace de otro código, hereda el código padre
- Correcto:
  - 136I → 136IA
- Incorrecto:
  - 136G si en realidad nace de 136I

### 5. Si se vende junto, lleva un solo código
- Ejemplos:
  - 139A = par de cuadros
  - 55 = set de cuatro paneles
  - 159D = ramequines (set de cuatro)

### 6. Si se vende separado, se divide
- Ejemplo:
  - 159A, 159B, 159C...

### 7. La descripción no debe empezar con números
- Incorrecto:
  - 4 ramequines blancos
  - 1 par de grabados
- Correcto:
  - Ramequines de cerámica blanca (set de cuatro)
  - Par de grabados orientalistas enmarcados

### 8. La categoría no es necesaria dentro del código
- La categoría puede manejarse por carpeta o en una columna aparte.
- Ejemplo:
  - Código: 159D
  - Categoría: Cerámica

---

## 🧾 COLUMNAS RECOMENDADAS EN EXCEL

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA | FOTO/ARCHIVO | ESTADO | NOTAS |
|---|---|---|---|---|---|---|---|---|

### Tipos sugeridos
- GRUPO
- SET
- SUBSET
- ITEM
- FOTO
- REF

### Unidad de venta sugerida
- Individual
- Par
- Set
- Lote

---

# 🔹 EJEMPLOS YA DEFINIDOS

## 1) Caso 2: grupo con varios artículos independientes

### Lógica
- 2 es el grupo original.
- 2A, 2B, 2C, 2D son artículos distintos que salen del mismo grupo.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA |
|---|---|---|---|---|---|
| 2 | 2 | - | GRUPO | Conjunto mixto de porcelana china floral con sopera, jarras y jarrones | Lote |
| 2 | 2A | 2 | ITEM | Jarras de porcelana china floral con grullas y nubes (un par) | Par |
| 2 | 2B | 2 | ITEM | Jarrones chinos de porcelana floral con aves (set de tres) | Set |
| 2 | 2C | 2 | ITEM | Sopera china de porcelana floral policromada con escenas figurativas | Individual |
| 2 | 2D | 2 | ITEM | Pieza individual adicional del grupo 2 | Individual |

---

## 2) Caso 55: un solo artículo con varias partes, vendido junto

### Lógica
- 55 es el artículo real.
- Las cuatro fotos muestran sus partes, pero el precio es por el conjunto.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA |
|---|---|---|---|---|---|
| 55 | 55 | - | ITEM | Paneles de madera tallada con escenas chinas (set de cuatro) | Set |
| 55 | 55-1 | 55 | FOTO | Vista del panel uno | - |
| 55 | 55-2 | 55 | FOTO | Vista del panel dos | - |
| 55 | 55-3 | 55 | FOTO | Vista del panel tres | - |
| 55 | 55-4 | 55 | FOTO | Vista del panel cuatro | - |

---

## 3) Caso 80: tres cuadros de amanecer, un solo item con tres fotos

### Lógica
- Son tres cuadros físicos.
- Se venden juntos como un solo item.
- No se dividen en A, B y C porque la lógica de venta es unitaria.
- Las tres imágenes se manejan como fotos del mismo item.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA |
|---|---|---|---|---|---|
| 80 | 80A | 80 | ITEM | Cuadros de amanecer con paisaje montañoso abstracto (tríptico) | Set |
| 80 | 80A-1 | 80A | FOTO | Vista uno del tríptico | - |
| 80 | 80A-2 | 80A | FOTO | Vista dos del tríptico | - |
| 80 | 80A-3 | 80A | FOTO | Vista tres del tríptico | - |

---

## 4) Caso 139: dos cuadros físicos, un solo item tipo par

### Lógica
- Son dos cuadros, pero se venden juntos.
- Por eso solo llevan un código de item.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA |
|---|---|---|---|---|---|
| 139 | 139A | 139 | ITEM | Par de grabados de bagres en el agua | Par |
| 139 | 139A-1 | 139A | FOTO | Vista uno del par | - |
| 139 | 139A-2 | 139A | FOTO | Vista dos del par | - |

---

## 4) Caso 182: dos grabados, un solo item tipo par

### Lógica
- Igual que el caso 139: son dos piezas físicas, pero un solo item de venta.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA |
|---|---|---|---|---|---|
| 182 | 182A | 182 | ITEM | Par de grabados orientalistas enmarcados con escenas en terrazas chinas | Par |
| 182 | 182A-1 | 182A | FOTO | Vista uno del par | - |
| 182 | 182A-2 | 182A | FOTO | Vista dos del par | - |

---

## 5) Caso 178: un grupo con dos sets distintos, y cada set tiene items individuales

### Lógica
- 178 es el grupo original.
- 178A y 178B son dos sets distintos.
- Dentro de cada set, los artículos se venden individualmente.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA |
|---|---|---|---|---|---|
| 178 | 178A | 178 | SET | Platería fina decorativa (set A) | Set |
| 178 | 178A-1 | 178A | FOTO | Vista de referencia del set A | - |
| 178 | 178AA | 178A | ITEM | Azucarero de plata con borde festoneado | Individual |
| 178 | 178AB | 178A | ITEM | Lechera de plata | Individual |
| 178 | 178AC | 178A | ITEM | Bandeja de plata con galería calada | Individual |
| 178 | 178AD | 178A | ITEM | Bandeja de plata calada con asas | Individual |
| 178 | 178AE | 178A | ITEM | Cafetera de plata antigua | Individual |
| 178 | 178AF | 178A | ITEM | Cubilete de plata victoriano grabado con iniciales | Individual |
| 178 | 178B | 178 | SET | Platería decorativa y cristal tallado (set B) | Set |
| 178 | 178B-1 | 178B | FOTO | Vista de referencia del set B | - |
| 178 | 178BA | 178B | ITEM | Ponchera de plata con acanaladuras | Individual |
| 178 | 178BB | 178B | ITEM | Calentador de platos con salseras y quemadores | Individual |

---

## 6) Caso 159: lote mixto que sí se divide por lógica de venta

### Lógica
- 159 era un conjunto mezclado.
- Se divide porque cada grupo sí puede venderse por separado.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA |
|---|---|---|---|---|---|
| 159 | 159A | 159 | ITEM | Azucareros individuales de cerámica blanca con relieve floral | Set |
| 159 | 159A-1 | 159A | FOTO | Vista del grupo 159A | - |
| 159 | 159B | 159 | ITEM | Taza y platillo de espresso Illy de cerámica blanca | Individual |
| 159 | 159B-1 | 159B | FOTO | Vista del item 159B | - |
| 159 | 159C | 159 | ITEM | Azucareros de cerámica con motivos frutales y florales | Set |
| 159 | 159C-1 | 159C | FOTO | Vista del grupo 159C | - |
| 159 | 159D | 159 | ITEM | Ramequines cerámicos blancos con textura (set de cuatro) | Set |
| 159 | 159D-1 | 159D | FOTO | Vista del item 159D | - |
| 159 | 159E | 159 | ITEM | Cuencos cerámicos blancos en forma de corazón (set) | Set |
| 159 | 159E-1 | 159E | FOTO | Vista del item 159E | - |
| 159 | 159F | 159 | ITEM | Fuentes individuales de cerámica blanca con bordes ondulados | Set |
| 159 | 159F-1 | 159F | FOTO | Vista del item 159F | - |
| 159 | 159G | 159 | ITEM | Azucareros de cerámica blanca (un par) | Par |
| 159 | 159G-1 | 159G | FOTO | Vista del item 159G | - |

---

## 7) Caso 136: grupo complejo con sets, sub-sets, migraciones y items derivados

### Lógica general
- 136 es contenedor principal.
- Se conserva el número original.
- Las letras organizan la jerarquía real.
- 136B deja de usarse porque pasó a 133.
- 136G deja de usarse como nivel propio porque en realidad nace de 136I.

### Mapa general
```text
136
├── 136A
├── 136B ❌ migrado a 133
├── 136C
│   ├── 136CA
│   └── 136CB
├── 136D
├── 136E
├── 136F
├── 136G ❌ reclasificado
├── 136H
│   └── 136HA
└── 136I
    └── 136IA
```

### Tabla maestra del 136

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA | NOTAS |
|---|---|---|---|---|---|---|
| 136 | 136 | - | GRUPO | Conjunto general de vajillas mixtas y cristalería | Lote | Contenedor principal |
| 136 | 136A | 136 | SET | Juego mixto de platos llanos, de postre y cargadores (set A) | Set | Contiene varios subgrupos |
| 136 | 136B | 136 | REF | Código descontinuado | - | Migrado a 133 |
| 136 | 136C | 136 | SET | Juego mixto de platos llanos, de postre y cargadores (set C) | Set | Tiene derivados |
| 136 | 136CA | 136C | SUBSET | Subgrupo A del set 136C | Set | Activo |
| 136 | 136CB | 136C | SUBSET | Subgrupo B del set 136C | Set | Activo |
| 136 | 136D | 136 | SET | Juego mixto de platos llanos, de postre y cargadores (set D) | Set | Aún sin fotos de items |
| 136 | 136E | 136 | SET | Juego mixto de platos llanos, de postre y cargadores (set E) | Set | Aún sin fotos de items |
| 136 | 136F | 136 | SET | Vajilla mixta cerámica botánica verde y cristalería tradicional | Set | Activo |
| 136 | 136G | 136 | REF | Código descontinuado | - | Se reclasificó como 136IA |
| 136 | 136H | 136 | SET | Juego de platos mixtos, cargadores, llanos y auxiliares | Set | Activo |
| 136 | 136HA | 136H | ITEM | Vajilla mixta botánica verde y cristalería | Individual / Set | Derivado de 136H |
| 136 | 136I | 136 | SET | Juego mixto de platos llanos, de postre y cargadores (set I) | Set | Activo |
| 136 | 136IA | 136I | ITEM | Platos cerámicos clásicos con borde festoneado y ribete dorado | Individual / Set | Antes se había confundido con 136G |
| 136 | 136IA-1 | 136IA | FOTO | Vista uno del item 136IA | - | |

---

## 8) Caso 133: absorbió el antiguo 136B

### Lógica
- 136B no se elimina del historial, pero deja de usarse como código activo.
- Su contenido pasa a 133 para respetar el orden original del Excel y la lógica real del inventario.

| ORDEN ORIGINAL | CÓDIGO | PADRE | TIPO | NOMBRE | UNIDAD DE VENTA | NOTAS |
|---|---|---|---|---|---|---|
| 133 | 133 | - | GRUPO / SET | Registro recuperado desde el antiguo 136B | Según clasificación final | Mantiene cronología original |

---

# 🔹 REGLAS PARA DECIDIR CUÁNDO DIVIDIR EN A/B

## Sí se divide cuando:
- cambia la lógica de venta
- son productos distintos
- pueden venderse por separado
- tienen diferente uso, valor o estilo

## No se divide cuando:
- es un set claro
- es un par inseparable
- son piezas que dependen una de otra
- la separación solo existe por foto, no por venta

### Regla maestra
**Se divide cuando cambia la lógica de venta, no cuando cambia la foto.**

---

# 🔹 RESUMEN OPERATIVO

- Número base = orden histórico original
- Letras = estructura real del inventario
- Guion + número = foto
- Si se vende junto = un solo código
- Si se vende separado = se divide
- Descripción natural, sin comenzar con números
- Categoría fuera del código

---

# 🎯 RESULTADO

✔ Inventario rastreable
✔ Respeta el Excel original
✔ Permite mover archivos físicos sin perder lógica
✔ Sirve para catálogo, web y control interno
✔ Evita renombrar todo otra vez

