**Especificación Oficial de Codificación**

Versión: `2026-04-09`

Propósito:
- definir la gramática oficial del código de inventario
- separar identidad de artículo y numeración de fotos
- dejar una base única para Excel, JSON, API y web

**Idea Central**

La jerarquía se expresa por herencia directa del código.

Reglas:
- el número original se conserva
- las letras organizan sets, subsets e items
- las fotos siempre van al final con guion y número
- no se usa `F` en el sufijo de fotos

**Formato General**

```text
[Numero][estructura de letras]
[Codigo]-[numero de foto]
```

Ejemplos:
- `136`
- `136I`
- `136IA`
- `136IAA`
- `136IA-1`
- `178AA-1`
- `182A-2`

**Niveles**

**Nivel 1: Grupo**

Ejemplo:
- `136`
- `178`

Significado:
- contenedor principal
- raíz del árbol

**Nivel 2: Set**

Ejemplo:
- `136A`
- `136C`
- `136I`
- `178A`
- `178B`

Significado:
- hijo directo del grupo
- primer nivel operativo interno

**Nivel 3: Subset**

Ejemplo:
- `136CA`
- `136CB`
- `136IA`

Significado:
- subdivisión de un set

**Nivel 4: Item**

Ejemplo:
- `136CAA`
- `136CAB`
- `136CBA`
- `178AA`
- `178BB`

Significado:
- artículo real individual

**Nivel 5: Foto**

Ejemplo:
- `136CAA-1`
- `136CAA-2`
- `178AA-1`
- `182A-2`

Significado:
- foto del artículo
- no crea una nueva identidad de inventario

**Reglas Oficiales**

1. Si nace de algo, hereda todo el código del padre y agrega una letra.
2. No se saltan niveles.
3. Las fotos nunca cambian el código base del artículo.
4. `REF` es una función visual o documental, no un artículo.
5. Si un código viejo se reclasifica, el código viejo deja de ser activo.
6. Si un artículo tiene varias fotos, se usa `-1`, `-2`, `-3`.
7. No crear letras al mismo nivel si la relación real es de dependencia.
8. Se divide en `A/B/C` cuando cambia la lógica de venta, no cuando cambia la foto.

**Ejemplos Reales**

**Jerarquía 136**

```text
136
|-- 136C
|   |-- 136CA
|   |   |-- 136CAA
|   |   |   |-- 136CAA-1
|   |   |   `-- 136CAA-2
|   |   `-- 136CAB
|   `-- 136CB
|       |-- 136CBA
|       `-- 136CBB
`-- 136I
    `-- 136IA
```

**Jerarquía 178**

```text
178
|-- 178A
|   |-- 178AA
|   |-- 178AB
|   |-- 178AC
|   |-- 178AD
|   |-- 178AE
|   `-- 178AF
`-- 178B
    |-- 178BA
    `-- 178BB
```

**Artículo con fotos**

```text
182A
|-- 182A-1
`-- 182A-2
```

**Casos de Venta**

- si se vende junto: un solo código de item
  - `80A` = tríptico
  - `139A` = par
  - `182A` = par
  - `159D` = set de cuatro ramequines

- si se vende separado: se divide
  - `159A`, `159B`, `159C`
  - `178AA`, `178AB`, `178AC`

**Casos Prohibidos**

- crear un hijo sin heredar el código del padre
- usar una foto como si fuera artículo
- mezclar `GRUPO` y `ITEM` en el mismo nodo sin aclaración estructural
- seguir usando un código eliminado como si siguiera activo
- usar prefijos de categoría dentro del código nuevo
- usar `-F1`, `-F2` en la foto nueva

**Frase Oficial**

Cada nivel agrega una letra, cada foto agrega `-1`, `-2`, `-3`.
