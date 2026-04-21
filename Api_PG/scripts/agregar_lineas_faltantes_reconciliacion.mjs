import { readFileSync, writeFileSync } from 'fs';
import { createRequire } from 'module';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = resolve(__dirname, '..', '..');
const APP_ROOT = resolve(ROOT, 'pignatelli-app');
const require = createRequire(resolve(APP_ROOT, 'package.json'));
const { google } = require('googleapis');
const ENV_PATH = resolve(APP_ROOT, '.env.local');
const SERVICE_ACCOUNT_PATH = resolve(APP_ROOT, 'lib', 'service-account.json');
const CATALOG_PATH = resolve(ROOT, 'Api_PG', 'data', 'solaris_catalogo.json');
const OUTPUT_LOG = resolve(ROOT, 'docs', 'missing_lines_apply_log_2026-04-08.json');

function loadEnv(path) {
  const env = {};
  const lines = readFileSync(path, 'utf8').split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [k, ...rest] = line.split('=');
    let v = rest.join('=').trim();
    if (v.startsWith('"') && v.endsWith('"')) v = v.slice(1, -1);
    env[k.trim()] = v;
  }
  return env;
}

function slugToTitleish(filename) {
  return filename
    .replace(/\.[^.]+$/, '')
    .replace(/^[A-Z]\d+[A-Z]*-?/i, '')
    .replace(/-/g, ' ')
    .trim();
}

function toCatalogArray(raw) {
  return Array.isArray(raw) ? raw : Object.values(raw);
}

function getSheetsClient() {
  const env = loadEnv(ENV_PATH);
  const credentials = JSON.parse(readFileSync(SERVICE_ACCOUNT_PATH, 'utf8'));
  const auth = new google.auth.GoogleAuth({
    credentials,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });
  return {
    auth,
    spreadsheetId: env.GOOGLE_SHEETS_ID,
  };
}

function fetchMap(rows) {
  const map = new Map();
  rows.forEach((row, idx) => {
    const code = String(row[0] || '').trim().toUpperCase();
    if (code) map.set(code, idx);
  });
  return map;
}

function ensureWidth(row, width) {
  const copy = [...row];
  while (copy.length < width) copy.push('');
  return copy.slice(0, width);
}

function insertAfterCode(rows, anchorCode, newRows) {
  const idx = rows.findIndex((row, i) => i > 0 && String(row[0] || '').trim().toUpperCase() === anchorCode);
  const insertAt = idx >= 0 ? idx + 1 : rows.length;
  rows.splice(insertAt, 0, ...newRows);
  return insertAt;
}

function findCatalogItem(items, code) {
  return items.find((item) => String(item.codigoItem || '').toUpperCase() === code) || null;
}

function extractPhotoForCode(parent, code) {
  const codeLower = code.toLowerCase();
  const parentPhotos = Array.isArray(parent?.fotos) ? parent.fotos : [];
  return parentPhotos.find((photo) => photo.toLowerCase().startsWith(codeLower)) || '';
}

function makeInventoryRowFromParent({ parentRow, code, name, reservationName, photo, notes }) {
  const row = ensureWidth(parentRow, 14);
  row[0] = code;
  if (name) row[1] = name;
  row[4] = reservationName ? 'Reservado' : row[4] || 'Disponible';
  row[5] = reservationName || '';
  row[6] = '';
  row[11] = photo || row[11] || '';
  row[12] = '';
  row[13] = notes || row[13] || '';
  return row;
}

function makeReservationRow({ code, name, reservedFor, priceUsd, photo }) {
  return [
    code,
    name || '',
    'Reservado',
    'Reservado',
    reservedFor || '',
    priceUsd === null || priceUsd === undefined ? '' : priceUsd,
    '',
    photo || '',
  ];
}

function parseNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') return value;
  const normalized = String(value).replace(/[^\d,.-]/g, '').replace(/\.(?=\d{3}\b)/g, '').replace(',', '.');
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

function countSothebys(rows) {
  return rows.filter((row) => {
    const v = String(row[8] || '').trim().toLowerCase();
    return v && v !== 'no' && v !== 'sin valoración' && v !== 'sin valoracion';
  }).length;
}

const additions = [
  {
    code: 'G44AA',
    anchorCode: 'G44A',
    parentCode: 'G44A',
    reservedFor: 'Diego Pignatelli',
    sameItemNote: 'Relacionado manualmente con G44A como mismo item; linea propia conservada por codigo.',
  },
  {
    code: 'G44AB',
    anchorCode: 'G44AA',
    parentCode: 'G44A',
    reservedFor: 'Adriano Pignatelli',
    sameItemNote: 'Relacionado visualmente con el bloque G44; reservado segun definicion manual posterior.',
  },
  {
    code: 'P139B',
    anchorCode: 'P139',
    parentCode: 'P139',
    reservedFor: 'Rasmi Sanchez',
    sameItemNote: 'Linea agregada por codigo definido en reservas; archivo fisico pendiente de normalizacion frente a P139a.',
    forcePhotoFromParent: 'P139a-2-prints-of-catfish-in-water.jpg',
  },
  {
    code: 'G150E',
    anchorCode: 'G150',
    parentCode: 'G150',
    reservedFor: 'Rasmi Sanchez',
    sameItemNote: 'Subcodigo fisico existente; linea propia agregada segun regla canonica por codigo.',
  },
  {
    code: 'P93A',
    anchorCode: 'P93',
    parentCode: 'P93',
    reservedFor: 'Rasmi Sanchez',
    sameItemNote: 'Cuadro floral individual del bloque P93.',
  },
  {
    code: 'P93B',
    anchorCode: 'P93A',
    parentCode: 'P93',
    reservedFor: 'Rasmi Sanchez',
    sameItemNote: 'Cuadro floral individual del bloque P93.',
  },
  {
    code: 'P93C',
    anchorCode: 'P93B',
    parentCode: 'P93',
    reservedFor: 'Rasmi Sanchez',
    sameItemNote: 'Cuadro floral individual del bloque P93.',
  },
  {
    code: 'S309A',
    anchorCode: 'S309',
    parentCode: 'S309',
    reservedFor: 'Diego Pignatelli',
    sameItemNote: 'S309A y S309B definidos manualmente como un mismo item; lineas propias conservadas por codigo.',
  },
  {
    code: 'S309B',
    anchorCode: 'S309A',
    parentCode: 'S309',
    reservedFor: 'Diego Pignatelli',
    sameItemNote: 'S309A y S309B definidos manualmente como un mismo item; lineas propias conservadas por codigo.',
  },
  {
    code: 'U356A',
    anchorCode: 'U356',
    parentCode: 'U356',
    reservedFor: 'Fabrizia Pignatelli',
    sameItemNote: 'Relacionado manualmente con U356 como mismo item; linea propia conservada por codigo.',
  },
];

async function main() {
  const { auth, spreadsheetId } = getSheetsClient();
  const sheets = google.sheets({ version: 'v4', auth: await auth.getClient() });

  const [invRes, resRes] = await Promise.all([
    sheets.spreadsheets.values.get({
      spreadsheetId,
      range: 'INVENTARIO_MAESTRO!A1:N800',
      valueRenderOption: 'UNFORMATTED_VALUE',
    }),
    sheets.spreadsheets.values.get({
      spreadsheetId,
      range: 'RESERVAS!A1:H300',
      valueRenderOption: 'UNFORMATTED_VALUE',
    }),
  ]);

  const inventoryRows = (invRes.data.values || []).map((row) => ensureWidth(row, 14));
  const reservationRows = (resRes.data.values || []).map((row) => ensureWidth(row, 8));
  const catalogItems = toCatalogArray(JSON.parse(readFileSync(CATALOG_PATH, 'utf8')));

  const log = {
    generatedAt: new Date().toISOString(),
    inventoryAppended: [],
    reservationsAppended: [],
    skipped: [],
  };

  const inventoryMap = fetchMap(inventoryRows);
  const reservationMap = fetchMap(reservationRows);

  for (const addition of additions) {
    const code = addition.code.toUpperCase();
    const parentCode = addition.parentCode.toUpperCase();

    if (!inventoryMap.has(parentCode)) {
      log.skipped.push({ code, reason: `Parent inventory row ${parentCode} not found` });
      continue;
    }

    const parentInvRow = inventoryRows[inventoryMap.get(parentCode)];
    const catalogParent = findCatalogItem(catalogItems, parentCode);
    const photo =
      addition.forcePhotoFromParent ||
      extractPhotoForCode(catalogParent, code) ||
      extractPhotoForCode(catalogParent, addition.code) ||
      '';

    let name = catalogParent?.nombreES || slugToTitleish(photo) || parentInvRow[1] || '';
    if (['P93A', 'P93B', 'P93C'].includes(code)) name = 'Pintura jardín floral impresionista';
    if (code === 'P139B') name = 'Par de grabados de bagres en el agua';
    if (code === 'G150E') name = 'Miscelánea de cristalería con garrafas, cuencos, platos y copas';
    if (code === 'G44AA' || code === 'G44AB') name = 'Cristalería con borde dorado, flautas y copas multicolor';
    if (code === 'S309A') name = 'Juego de 12 servilleteros de plata';
    if (code === 'S309B') name = 'Conjunto de figuras de animales de plata';
    if (code === 'U356A') name = 'Estuche de almacenamiento vintage';

    if (!inventoryMap.has(code)) {
      const newInvRow = makeInventoryRowFromParent({
        parentRow: parentInvRow,
        code,
        name,
        reservationName: addition.reservedFor,
        photo,
        notes: addition.sameItemNote,
      });
      insertAfterCode(inventoryRows, addition.anchorCode.toUpperCase(), [newInvRow]);
      log.inventoryAppended.push({ code, anchor: addition.anchorCode, photo, reservedFor: addition.reservedFor });
      inventoryMap.clear?.();
    } else {
      log.skipped.push({ code, reason: 'Already exists in INVENTARIO_MAESTRO' });
    }

    if (!reservationMap.has(code)) {
      const priceUsd =
        parentInvRow[3] === undefined || parentInvRow[3] === null || parentInvRow[3] === '' ? '' : parentInvRow[3];
      const newResRow = makeReservationRow({
        code,
        name,
        reservedFor: addition.reservedFor,
        priceUsd,
        photo,
      });
      insertAfterCode(reservationRows, addition.anchorCode.toUpperCase(), [newResRow]);
      log.reservationsAppended.push({ code, anchor: addition.anchorCode, photo, reservedFor: addition.reservedFor });
      reservationMap.clear?.();
    } else {
      log.skipped.push({ code, reason: 'Already exists in RESERVAS' });
    }

    // Refresh maps after structural change.
    for (const [map, rows] of [
      [inventoryMap, inventoryRows],
      [reservationMap, reservationRows],
    ]) {
      map.clear();
      fetchMap(rows).forEach((v, k) => map.set(k, v));
    }
  }

  await sheets.spreadsheets.values.batchUpdate({
    spreadsheetId,
    requestBody: {
      valueInputOption: 'USER_ENTERED',
      data: [
        {
          range: `INVENTARIO_MAESTRO!A1:N${inventoryRows.length}`,
          values: inventoryRows,
        },
        {
          range: `RESERVAS!A1:H${reservationRows.length}`,
          values: reservationRows,
        },
      ],
    },
  });

  const [webRes, salesRes] = await Promise.all([
    sheets.spreadsheets.values.get({
      spreadsheetId,
      range: 'CATALOGO_WEB!A1:N800',
      valueRenderOption: 'UNFORMATTED_VALUE',
    }),
    sheets.spreadsheets.values.get({
      spreadsheetId,
      range: 'VENTAS!A1:H200',
      valueRenderOption: 'UNFORMATTED_VALUE',
    }),
  ]);

  const inventoryData = inventoryRows.slice(1).filter((row) => String(row[0] || '').trim());
  const visibleWeb = (webRes.data.values || []).slice(1).filter((row) => String(row[0] || '').trim()).length;
  const salesData = (salesRes.data.values || []).slice(1).filter((row) => String(row[0] || '').trim());
  const states = {
    Disponible: inventoryData.filter((row) => String(row[4] || '').trim() === 'Disponible').length,
    Reservado: inventoryData.filter((row) => String(row[4] || '').trim() === 'Reservado').length,
    Vendido: inventoryData.filter((row) => String(row[4] || '').trim() === 'Vendido').length,
    'No disponible': inventoryData.filter((row) => String(row[4] || '').trim() === 'No disponible').length,
  };
  const listedUsd = inventoryData.reduce((sum, row) => sum + (parseNumber(row[3]) || 0), 0);
  const soldUsd = salesData.reduce((sum, row) => sum + (parseNumber(row[3]) || 0), 0);
  const categoryOrder = [
    'Decorativos y Arte',
    'Muebles',
    'Cristalería',
    'Cuadros y Grabados',
    'Platería',
    'Porcelana y Cerámica',
    'Electrodomésticos',
    'Utensilios',
  ];
  const categoryCounts = new Map(categoryOrder.map((name) => [name, 0]));
  for (const row of inventoryData) {
    const key = String(row[2] || '').trim();
    if (!key) continue;
    categoryCounts.set(key, (categoryCounts.get(key) || 0) + 1);
  }
  const categoryRows = Array.from(categoryCounts.entries()).filter(([, n]) => n > 0);

  const summaryUpdates = [
    { range: 'RESUMEN!A3:B3', values: [['Métrica', 'Valor']] },
    { range: 'RESUMEN!D3:E3', values: [['Estado', 'Cantidad']] },
    { range: 'RESUMEN!B4', values: [[inventoryData.length]] },
    { range: 'RESUMEN!B5', values: [[states.Disponible]] },
    { range: 'RESUMEN!B6', values: [[states.Reservado]] },
    { range: 'RESUMEN!B7', values: [[states.Vendido]] },
    { range: 'RESUMEN!B8', values: [[visibleWeb]] },
    { range: 'RESUMEN!B9', values: [[countSothebys(inventoryData)]] },
    { range: 'RESUMEN!B10', values: [[listedUsd]] },
    { range: 'RESUMEN!B11', values: [[soldUsd]] },
    { range: 'RESUMEN!E4', values: [[states.Disponible]] },
    { range: 'RESUMEN!E5', values: [[states.Reservado]] },
    { range: 'RESUMEN!E6', values: [[states.Vendido]] },
    { range: 'RESUMEN!E7', values: [[states['No disponible']]] },
    { range: 'RESUMEN!A13:B13', values: [['Categoría web', 'Cantidad']] },
    { range: 'RESUMEN!D13:E13', values: [['Categoría web', 'Cantidad']] },
  ];

  if (categoryRows.length) {
    summaryUpdates.push({ range: `RESUMEN!A14:B${13 + categoryRows.length}`, values: categoryRows });
    summaryUpdates.push({ range: `RESUMEN!D14:E${13 + categoryRows.length}`, values: categoryRows });
  }

  await sheets.spreadsheets.values.clear({
    spreadsheetId,
    range: 'RESUMEN!A12:B25',
    requestBody: {},
  });
  await sheets.spreadsheets.values.clear({
    spreadsheetId,
    range: 'RESUMEN!D11:E25',
    requestBody: {},
  });
  await sheets.spreadsheets.values.batchUpdate({
    spreadsheetId,
    requestBody: {
      valueInputOption: 'USER_ENTERED',
      data: summaryUpdates,
    },
  });

  writeFileSync(OUTPUT_LOG, JSON.stringify(log, null, 2), 'utf8');
  console.log(JSON.stringify(log, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
