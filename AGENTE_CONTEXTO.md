# Contexto del Sistema — Casa Pignatelli (para agentes AI)

## Qué es este proyecto
Sistema de gestión y venta del inventario de antigüedades de la familia Pignatelli
(Condominio Solaris, Costa Rica). ~551 artículos, herederos + compradores externos.

---

## Arquitectura de datos (3 fuentes sincronizadas)

| Fuente | Ubicación | Propósito |
|---|---|---|
| **Google Sheet** | ID: `1X6l9MeiFgXKRmVyRYBwsMnjwkWz971BsrBK3lbWJ-u4` | Fuente de verdad para precios y estados |
| **solaris_catalogo.json** | `Api_PG/data/solaris_catalogo.json` | Catálogo local, se sincroniza del Sheet |
| **estados.json** | Solo en servidor `/app/Api_PG/data/` | Estados dinámicos del panel (NO en git) |

**Regla crítica:** Sheet manda. Cualquier cambio va primero al Sheet, luego se sincroniza.

---

## Sistema de precios (MUY IMPORTANTE)

El Sheet tiene 3 columnas de precios:

| Columna | Nombre | Significado |
|---|---|---|
| **D** | `Precio USD` | **Precio de venta final al cliente** — lo que se muestra en la web |
| **E** | `Estimación Sotheby's` | Solo referencia informativa — NUNCA se modifica |
| **F** | `Mínimo` | **Precio que estableció Andrea (la abogada)** |

### Regla F → D (fundamental)
> **Si F tiene precio → D = F** (F siempre reemplaza D)
> Si F está vacío → se respeta lo que haya en D
> Si ambos vacíos → sin precio por ahora

### Excepciones en F (no son precios numéricos):
- `regalo`, `(regalo)`, `donada` → artículo es regalo, D queda vacío
- `parte del set` → precio lo maneja el artículo padre
- `$X c/u`, `$X cada una` → precio POR UNIDAD, D = cantidad × precio unit
  - La cantidad está en el nombre entre paréntesis: `(3)`, `(25)` o implícita: `Pareja` = 2

---

## Estructura del Sheet (INVENTARIO_MAESTRO, gid=963068179)

```
A: Artículo (código)    B: Nombre           C: Categoría
D: Precio USD           E: Estimación Sotheby's   F: Mínimo
G: Estado               H: Reservado/Comprador
I: Ref Sotheby's        J: Página           K: Notas
```

**NUNCA borrar columnas E ni F.**

---

## Nomenclatura de artículos

- Código = letra de categoría + número + sufijo: `136A`, `136AA`, `136AB`...
- `F` = Muebles, `G` = Cristalería, `C` = Cerámica, `D` = Decorativos
- `P` = Pinturas, `S` = Platería, `E` = Electrodomésticos, `U` = Utensilios
- `tipoEstructural: "SET"` = ítem de referencia, NO se vende directamente
- `tipoEstructural: "ARTICULO"` = artículo vendible

---

## Estados de artículos

| Estado | Significado |
|---|---|
| `Disponible` | Libre para vender |
| `Reservado` | Apartado para alguien |
| `Vendido` | Transacción completada |

### Herederos (no pagan, no necesitan precio):
Adriano Pignatelli, Diego Pignatelli, Fabrizia Pignatelli,
Margherita Pignatelli, Maria Cristina Pignatelli, Isabel Marin, Jerancy Alpizar

---

## Flujo de sincronización

```bash
# Script principal (corre todo automáticamente):
python Api_PG/scripts/sincronizar_catalogo.py

# Qué hace:
# 1. Lee Sheet (fuente de verdad)
# 2. Aplica regla F→D a todos los precios
# 3. Actualiza solaris_catalogo.json
# 4. Genera solaris_catalogo.html (solo backup estático)
# 5. git commit + push
# 6. En servidor: git checkout solaris_catalogo.json && git pull && restart
```

---

## Infraestructura del servidor

- **IP:** 24.199.89.36
- **Dominio:** catalogo.pignatelli.uk
- **Panel herederos:** `catalogo.pignatelli.uk/` (Flask, privado)
- **Catálogo público:** `catalogo.pignatelli.uk/publico` (dinámico, lee /api/catalogo)
- **Servicio:** systemd `pignatelli` (Flask en puerto 8090, nginx proxy)
- **Fotos:** `/app/Api_PG/images/fotos-Solaris-inventory/Todas las Fotos/`

### Subir fotos nuevas (siempre .jpg, código en MAYÚSCULAS):
```bash
# Convertir HEIC → JPG primero (iPhone)
# Luego copiar a AMBAS carpetas: Api_PG/images/ y Api_PG_Deploy/images/
# Subir al servidor:
tar -czf fotos.tar.gz -C "Api_PG_Deploy/images/fotos-Solaris-inventory/Todas las Fotos" [archivos]
scp fotos.tar.gz root@24.199.89.36:/tmp/
# En servidor:
cd "/app/Api_PG_Deploy/images/fotos-Solaris-inventory/Todas las Fotos" && tar -xzf /tmp/fotos.tar.gz
# También copiar a Api_PG/images/ (Flask sirve desde ahí):
cp [fotos] /app/Api_PG/images/fotos-Solaris-inventory/"Todas las Fotos"/
```

---

## Acceso a Google Sheets API

Credenciales en: `pignatelli-app/.env.local`
- `GOOGLE_SHEETS_ID` = ID del spreadsheet
- `GOOGLE_SERVICE_ACCOUNT_EMAIL`
- `GOOGLE_PRIVATE_KEY`

Tabs importantes:
- `INVENTARIO_MAESTRO` gid=963068179 — inventario principal
- `VENTAS` gid=1917449891 — ventas confirmadas (comprador, precio USD, precio CRC, fecha)

---

## Artículos con precio por unidad (F dice "c/u")
| Código | Qty | Precio unit | Total D |
|---|---|---|---|
| 11A | 2 (Pareja) | $75 | $150 |
| 46A | 3 | $10 | $30 |
| 249A | SET — dividido en 249AA/AB/AC | | |

---

## Errores comunes a evitar

1. **Nunca leer precios de un CSV viejo** para restaurar — siempre usar el Sheet en vivo
2. **Nunca borrar columnas E y F** del Sheet
3. **El sync script usa índices de columna por NOMBRE** — si el Sheet cambia de estructura, revisar el script
4. **estados.json NO va en git** — vive solo en el servidor
5. **Al hacer git pull en servidor**, siempre primero `git checkout Api_PG/data/solaris_catalogo.json`
6. **Fotos HEIC de iPhone** deben convertirse a JPG antes de subir
7. **Código en el nombre de foto debe ir en MAYÚSCULAS**: `143AD-1-nombre.jpg` no `143ad-1-nombre.jpg`