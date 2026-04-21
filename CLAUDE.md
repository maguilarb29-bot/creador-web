# Casa Pignatelli — Instrucciones para agentes AI

## Qué es este proyecto
Sistema de gestión y venta del inventario de antigüedades de la familia Pignatelli (Condominio Solaris, Costa Rica). Gestiona ~524 artículos, permite a herederos reservar piezas y a compradores externos adquirirlas, con trazabilidad de transacciones y facturación.

## Stack actual (abril 2026)
- **Backend:** Flask/Python (`Api_PG/server.py`)
- **Frontend:** HTML + JS vanilla (`Api_PG/panel_herederos.html`) — una sola página con tabs
- **Datos:** JSON files en `Api_PG/data/`
- **Fotos:** `Api_PG/images/fotos-Solaris-inventory/Todas las Fotos/`
- **Deploy:** DigitalOcean VPS Ubuntu 24.04 — `catalogo.pignatelli.uk` (HTTPS)
- **Git:** https://github.com/maguilarb29-bot/creador-web

## Archivos clave
| Archivo | Propósito |
|---|---|
| `Api_PG/server.py` | Servidor Flask, endpoints API, lógica de reservas/ventas |
| `Api_PG/panel_herederos.html` | UI completa (catálogo, transacciones, facturación) |
| `Api_PG/data/solaris_catalogo.json` | Catálogo de 524 artículos (datos estáticos) |
| `Api_PG/data/transacciones.json` | Historial de reservas y ventas |
| `Api_PG/data/estados.json` | Estados dinámicos por artículo — NO está en git |
| `Api_PG/data/contadores.json` | Contador de facturas consecutivas — NO está en git |
| `Api_PG/data/reservas_excel_entregable_2026-04-13.json` | Lista de herederos y asignaciones |

## Infraestructura del servidor
- **IP:** 24.199.89.36
- **Dominio:** catalogo.pignatelli.uk (HTTPS via certbot/Let's Encrypt)
- **Servicio:** systemd `pignatelli` (auto-restart)
- **Proxy:** nginx → puerto 8090 (Flask)
- **Backups:** cron diario → `/app/backups/`
- **Acceso SSH:** `ssh root@24.199.89.36`

## Workflow de actualización
```bash
# Desde el PC (terminal):
git add <archivos> && git commit -m "mensaje" && git push

# En la consola de DigitalOcean:
cd /app && git checkout Api_PG/data/solaris_catalogo.json && git pull && systemctl restart pignatelli
```

IMPORTANTE: El `git checkout` descarta cambios locales del catálogo en el servidor.
Los estados dinámicos están en `estados.json` (no afectado por git) — las reservas son seguras.

## Modelo de datos del catálogo

### Tipos de ítem
- `tipoEstructural: "SET"` — Grupo de referencia. Badge "REFERENCIA". No se vende directamente.
- `tipoEstructural: "ARTICULO"` — Artículo vendible individual.

### Campos por ítem
```json
{
  "codigoItem": "90A",
  "codigoPadre": "",
  "numItem": 90,
  "tipoEstructural": "SET",
  "categoria": "Ceramica",
  "nombreES": "Nombre del artículo",
  "fotos": ["90A-1-slug-nombre.jpg"],
  "estado": "Disponible",
  "reservadoPara": "",
  "precioUSD": null,
  "cantidad": 1,
  "tieneSothebys": false,
  "estimacionSothebys": ""
}
```

### Estados dinámicos (estados.json — solo en servidor, nunca en git)
```json
{
  "14A": {"estado": "Reservado", "reservadoPara": "Fabrizia Pignatelli", "confirmadoHeredero": false}
}
```

## Herederos registrados
Adriano Pignatelli, Diego Pignatelli, Fabrizia Pignatelli, Isabel Marin, Jerancy Alpizar.
Si el comprador NO está en esta lista → es Cliente externo.

## Facturación
- Borrador/preview: etiqueta tipo (RESERVA/VENTA), sin número consecutivo
- Factura confirmada: etiqueta "FACTURA" + número FAC-0010, FAC-0011... (contador en contadores.json, inicio 9)
- Herederos: muestra columna Valoración Sotheby's
- Clientes externos: oculta Sotheby's salvo que el ítem tenga valoración

## Nomenclatura de fotos
`[CODIGO]-[N]-[slug-nombre-espanol].jpg`
Ejemplo: `90A-1-juego-de-cuatro-jarrones-chinos-de-porcelana.jpg`

## Reglas críticas
1. NO modificar `estados.json` ni `contadores.json` via git — son archivos exclusivos del servidor
2. El catálogo JSON tiene solo datos estáticos — los estados se gestionan vía estados.json
3. Las fotos se suben via `scp`, no via git (Api_PG/images/ está en .gitignore)
4. El sitio está en producción — cuidado al modificar cualquier cosa
5. Antes de git pull en el servidor, siempre hacer `git checkout Api_PG/data/solaris_catalogo.json`
