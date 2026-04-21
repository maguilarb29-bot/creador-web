**Diccionario Maestro del Inventario**

Versión: `2026-04-09`

Propósito:
- fijar la estructura oficial de `INVENTARIO_MAESTRO`
- separar `ORDEN ORIGINAL` de `CODIGO`
- dejar una base clara para Excel, JSON, API y web

**Principios**

- `ORDEN ORIGINAL` conserva el número histórico del inventario.
- `CODIGO` expresa la jerarquía real de venta y estructura.
- un registro solo puede cumplir una función principal: `GRUPO`, `SET`, `SUBSET`, `ITEM`, `FOTO` o `REF`
- las fotos no cambian la identidad del artículo
- el código organiza; el nombre vende
- si falta un dato, queda vacío

**Columnas Oficiales**

| Columna | Uso | Regla |
|---|---|---|
| `ORDEN ORIGINAL` | Número histórico base | No se modifica. |
| `CODIGO` | Código estructural oficial | Sin prefijo de categoría. Ej. `136IA`, `178AA`, `159D`. |
| `PADRE` | Nodo del que nace el registro | Vacío solo en nodos raíz. |
| `TIPO` | Función estructural principal | `GRUPO`, `SET`, `SUBSET`, `ITEM`, `FOTO`, `REF`. |
| `NOMBRE` | Nombre comercial o editorial | En español. No empieza con números. |
| `UNIDAD DE VENTA` | Forma comercial de venta | `Individual`, `Par`, `Set`, `Lote`. |
| `FOTO/ARCHIVO` | Archivo físico asociado | Las fotos llevan `-1`, `-2`, `-3`. |
| `ESTADO` | Estado operativo | `Disponible`, `Reservado`, `Vendido`, `No disponible`. |
| `NOTAS` | Aclaraciones operativas | Breves, útiles y en español. |

**Semántica Operativa**

| Tipo | Significado | Se vende |
|---|---|---|
| `GRUPO` | Contenedor raíz del orden original | No por defecto |
| `SET` | Conjunto identificado como unidad o rama principal | Depende de la lógica de venta |
| `SUBSET` | Subgrupo intermedio dentro de un set | No por defecto |
| `ITEM` | Artículo real vendible | Sí |
| `FOTO` | Vista de un artículo o set | No |
| `REF` | Referencia visual o documental | No |

**Reglas de Codificación**

- formato base del código: `[Numero][estructura de letras]`
- formato de foto: `[Codigo]-[numero]`
- ejemplo:
  - `136` = grupo
  - `136I` = set
  - `136IA` = item o subset derivado
  - `136IA-1` = foto 1
- regla de oro: si nace de algo, hereda el código del padre y agrega una letra

**Reglas Editoriales**

- el nombre nunca debe empezar con números
- la cantidad se expresa en texto natural cuando haga falta
- ejemplos correctos:
  - `Par de grabados orientalistas enmarcados`
  - `Ramequines de cerámica blanca (set de cuatro)`
  - `Azucareros de cerámica blanca con relieve floral`

**Ejemplos Reales**

**Caso 136**

| ORDEN ORIGINAL | CODIGO | PADRE | TIPO | lectura |
|---|---|---|---|---|
| `136` | `136` |  | `GRUPO` | grupo principal |
| `136` | `136C` | `136` | `SET` | set dentro del grupo |
| `136` | `136CA` | `136C` | `SUBSET` | subset dentro de `136C` |
| `136` | `136CAA` | `136CA` | `ITEM` | item real |
| `136` | `136CAA-1` | `136CAA` | `FOTO` | foto 1 del item |

**Caso 178**

| ORDEN ORIGINAL | CODIGO | PADRE | TIPO | lectura |
|---|---|---|---|---|
| `178` | `178` |  | `GRUPO` | grupo principal |
| `178` | `178A` | `178` | `SET` | set A |
| `178` | `178AA` | `178A` | `ITEM` | item del set A |
| `178` | `178B` | `178` | `SET` | set B |
| `178` | `178BB` | `178B` | `ITEM` | item del set B |

**Caso 182**

| ORDEN ORIGINAL | CODIGO | PADRE | TIPO | lectura |
|---|---|---|---|---|
| `182` | `182A` | `182` | `ITEM` | artículo real |
| `182` | `182A-1` | `182A` | `FOTO` | foto principal |
| `182` | `182A-2` | `182A` | `FOTO` | foto adicional |

**Reglas de Validación**

1. Un código no debe mezclar ser padre y foto a la vez.
2. Si un nodo tiene hijos reales, su relación debe quedar explícita en `PADRE`.
3. Si una foto es solo apoyo visual, no crea una línea de inventario nueva.
4. Si se vende junto, mantiene un solo código de item.
5. Si se vende separado, se abre en subcódigos.

**Frase Oficial**

Cada hijo hereda el código del padre; cada foto agrega `-1`, `-2`, `-3`.
