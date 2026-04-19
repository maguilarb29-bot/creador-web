import fs from 'fs';
import path from 'path';
import { google } from '../pignatelli-app/node_modules/googleapis/build/src/index.js';

const PROJECT_ROOT = process.cwd();
const ENV_PATH = path.join(PROJECT_ROOT, 'pignatelli-app', '.env.local');
const CATALOG_PATH = path.join(PROJECT_ROOT, 'Api_PG', 'data', 'solaris_catalogo.json');
const PHOTOS_DIR = path.join(PROJECT_ROOT, 'Api_PG', 'images', 'fotos-Solaris-inventory');
const EXPORT_DIR = path.join(PROJECT_ROOT, 'docs', 'final-export', '2026-04-07');

const CRITICAL_RESERVED_NUMBERS = new Set([11, 8, 21, 22, 23, 28, 30, 56, 77, 124, 130, 134, 174, 181, 182]);
const VALID_STATES = new Set(['Disponible', 'Reservado', 'Vendido', 'No disponible']);
const MASTER_HEADERS = [
  'Artículo',
  'Nombre',
  'Categoría',
  'Precio USD',
  'Estado',
  'Cliente',
  'Monto pagado',
  'Ubicación',
  "Sotheby's",
  'Piezas',
  'Descripción',
  'Foto principal',
  'Fotos adicionales',
  'Notas',
];
const WEB_HEADERS = [
  'idLote',
  'slugWeb',
  'nombreComercial',
  'descripcionWeb',
  'categoria',
  'subtipo',
  'ubicacion',
  'estadoComercial',
  'badgeSothebys',
  'precioListaUSD',
  'politicaPrecioWeb',
  'monedaMostrar',
  'precioDisplayTexto',
  'imagenArchivo',
];

function loadEnv() {
  const envText = fs.readFileSync(ENV_PATH, 'utf8');
  const env = {};
  for (const line of envText.split(/\r?\n/)) {
    const raw = line.trim();
    if (!raw || raw.startsWith('#') || !raw.includes('=')) continue;
    const idx = raw.indexOf('=');
    let value = raw.slice(idx + 1).trim();
    if (value.startsWith('"') && value.endsWith('"')) value = value.slice(1, -1);
    env[raw.slice(0, idx).trim()] = value;
  }
  return env;
}

function loadCatalogMap() {
  const raw = JSON.parse(fs.readFileSync(CATALOG_PATH, 'utf8'));
  const items = Array.isArray(raw) ? raw : Object.values(raw);
  const map = new Map();
  for (const item of items) {
    if (!item?.codigoItem) continue;
    map.set(String(item.codigoItem).trim(), item);
  }
  return map;
}

function slugify(text) {
  return String(text || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function extractNumberFromCode(code) {
  const match = String(code || '').match(/^[A-Z]+(\d+)/);
  return match ? Number(match[1]) : null;
}

function isRootCode(code) {
  return /^[A-Z]+\d+$/.test(String(code || '').trim());
}

function stripRefPrefix(text) {
  return String(text || '').replace(/^\[REF\]\s*/i, '').trim();
}

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  const cleaned = String(value).trim().replace(/\$/g, '').replace(/₡/g, '').replace(/,/g, '');
  if (!cleaned) return null;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatUsd(value) {
  const num = toNumber(value);
  if (num === null) return '';
  if (Math.abs(num - Math.round(num)) < 1e-9) return `$${Math.round(num)}`;
  return `$${num.toFixed(2)}`;
}

function sentenceCase(text) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return '';
  return clean.charAt(0).toUpperCase() + clean.slice(1);
}

function compactWords(text, maxWords) {
  const words = String(text || '').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
  return words.slice(0, maxWords).join(' ').trim();
}

function cleanCommercialName(sourceName) {
  let text = stripRefPrefix(sourceName)
    .replace(/^\d+\s+/u, '')
    .replace(/\s*\([^)]*\)/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
  text = text.replace(/\bvalor estimado\b.*$/i, '').trim();
  if (!text) return 'Artículo decorativo';
  const words = text.split(' ');
  if (words.length > 9) text = words.slice(0, 9).join(' ');
  return sentenceCase(text);
}

function trimMaterial(materials, fallbackCategory) {
  const clean = String(materials || '')
    .replace(/posiblemente/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!clean) return fallbackCategory.toLowerCase();
  return clean.split(',').slice(0, 2).join(' y ').trim().toLowerCase();
}

function trimStyle(style) {
  const clean = String(style || '').replace(/\s+/g, ' ').trim();
  if (!clean) return '';
  return clean.split(',').slice(0, 1).join('').trim().toLowerCase();
}

function usageFromCategory(category, location) {
  const cat = String(category || '').toLowerCase();
  const loc = String(location || '').toLowerCase();
  if (cat.includes('mueble')) return 'sala, entrada o dormitorio';
  if (cat.includes('cuadro') || cat.includes('grabado') || cat.includes('arte')) return 'pared, sala o estudio';
  if (cat.includes('plater')) return 'mesa, comedor o vitrina';
  if (cat.includes('cristal')) return 'bar, comedor o vitrina';
  if (cat.includes('porcelana') || cat.includes('cerámica')) return 'mesa, comedor o vitrina';
  if (cat.includes('electro')) return 'cocina o estación de café';
  if (cat.includes('utens')) return 'cocina o servicio diario';
  if (loc.includes('terrace')) return 'terraza o sala exterior';
  if (loc.includes('kitchen')) return 'cocina o comedor';
  return 'sala, comedor o decoración';
}

function generateShortDescription({ commercialName, materials, style, category, location }) {
  const materialText = trimMaterial(materials, category || 'objeto decorativo');
  const styleText = trimStyle(style);
  const usage = usageFromCategory(category, location);
  let text = `${commercialName} de ${materialText}${styleText ? `, estilo ${styleText}` : ''}, ideal para ${usage}.`;
  let words = text.split(/\s+/).filter(Boolean);
  if (words.length < 12) {
    text = `${commercialName} de ${materialText}${styleText ? `, estilo ${styleText}` : ''}, ideal para ${usage} y ambientación elegante.`;
    words = text.split(/\s+/).filter(Boolean);
  }
  if (words.length > 20) {
    text = `${compactWords(commercialName, 5)} de ${materialText}${styleText ? `, estilo ${styleText}` : ''}, ideal para ${usage}.`;
    words = text.split(/\s+/).filter(Boolean);
  }
  if (words.length > 20) {
    text = compactWords(text, 20).replace(/[,:;]$/, '') + '.';
  }
  return sentenceCase(text);
}

function parseReservedFor(name) {
  return String(name || '').trim();
}

function parseSoldClient(notes) {
  const match = String(notes || '').match(/vendido a\s+(.+)$/i);
  return match ? match[1].trim() : '';
}

function csvEscape(value) {
  const text = value === null || value === undefined ? '' : String(value);
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function writeCsv(filePath, rows) {
  const content = rows.map((row) => row.map(csvEscape).join(',')).join('\n');
  fs.writeFileSync(filePath, content, 'utf8');
}

async function getSheetsClient() {
  const env = loadEnv();
  const auth = new google.auth.GoogleAuth({
    credentials: {
      type: 'service_account',
      project_id: 'inventario-pignatelli',
      private_key: env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, '\n').trim(),
      client_email: env.GOOGLE_SERVICE_ACCOUNT_EMAIL.trim(),
      token_uri: 'https://oauth2.googleapis.com/token',
    },
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });
  return {
    env,
    sheets: google.sheets({ version: 'v4', auth }),
  };
}

async function getValues(sheets, spreadsheetId, range) {
  const res = await sheets.spreadsheets.values.get({
    spreadsheetId,
    range,
    valueRenderOption: 'UNFORMATTED_VALUE',
  });
  return res.data.values || [];
}

function buildMasterRows(masterValues, reservationsValues, salesValues) {
  const [masterHeader, ...masterRowsRaw] = masterValues;
  const [reservationsHeader, ...reservationRowsRaw] = reservationsValues;
  const [salesHeader, ...salesRowsRaw] = salesValues;

  const masterIndex = Object.fromEntries(masterHeader.map((value, idx) => [value, idx]));
  const reservationIndex = Object.fromEntries(reservationsHeader.map((value, idx) => [value, idx]));
  const salesIndex = Object.fromEntries(salesHeader.map((value, idx) => [value, idx]));

  const reservationByCode = new Map();
  for (const row of reservationRowsRaw) {
    const code = String(row[reservationIndex['Artículo']] || '').trim();
    if (!code) continue;
    reservationByCode.set(code, {
      code,
      reservedFor: parseReservedFor(row[reservationIndex['Reservado Para']]),
      name: String(row[reservationIndex['Nombre']] || '').trim(),
      image: String(row[reservationIndex['Imagen']] || '').trim(),
    });
  }

  const saleByCode = new Map();
  for (const row of salesRowsRaw) {
    const code = String(row[salesIndex['Artículo']] || '').trim();
    if (!code) continue;
    saleByCode.set(code, {
      code,
      soldPrice: toNumber(row[salesIndex['Precio Vendido USD']]),
      listedPrice: toNumber(row[salesIndex['Precio USD']]),
      state: String(row[salesIndex['Estado']] || '').trim(),
      image: String(row[salesIndex['Imagen']] || '').trim(),
      notes: String(row[salesIndex['Notas']] || '').trim(),
      client: parseSoldClient(row[salesIndex['Notas']]),
    });
  }

  const normalizedRows = masterRowsRaw.map((row) => {
    const safe = Array.from({ length: MASTER_HEADERS.length }, (_, idx) => row[idx] ?? '');
    const code = String(safe[masterIndex['Artículo']] || '').trim();
    const rawState = String(safe[masterIndex['Estado']] || '').trim();
    const currentPrice = toNumber(safe[masterIndex['Precio USD']]);
    const reservation = reservationByCode.get(code);
    const sale = saleByCode.get(code);
    const itemNumber = extractNumberFromCode(code);

    let nextState = VALID_STATES.has(rawState) ? rawState : 'Disponible';
    if (sale) {
      nextState = 'Vendido';
    } else if (reservation || (isRootCode(code) && itemNumber !== null && CRITICAL_RESERVED_NUMBERS.has(itemNumber))) {
      nextState = 'Reservado';
    }

    safe[masterIndex['Estado']] = nextState;

    if (!isRootCode(code)) {
      safe[masterIndex['Precio USD']] = '';
    } else if (currentPrice !== null) {
      safe[masterIndex['Precio USD']] = currentPrice;
    }

    if (nextState === 'Reservado') {
      safe[masterIndex['Cliente']] = reservation?.reservedFor || safe[masterIndex['Cliente']] || '';
    }

    if (sale) {
      safe[masterIndex['Cliente']] = sale.client || safe[masterIndex['Cliente']] || '';
      safe[masterIndex['Monto pagado']] = sale.soldPrice ?? safe[masterIndex['Monto pagado']] ?? '';
    }

    return {
      code,
      row: safe,
      state: nextState,
      client: String(safe[masterIndex['Cliente']] || '').trim(),
      paid: toNumber(safe[masterIndex['Monto pagado']]),
      price: toNumber(safe[masterIndex['Precio USD']]),
      name: String(safe[masterIndex['Nombre']] || '').trim(),
      category: String(safe[masterIndex['Categoría']] || '').trim(),
      location: String(safe[masterIndex['Ubicación']] || '').trim(),
      sothebys: String(safe[masterIndex["Sotheby's"]] || '').trim(),
      description: String(safe[masterIndex['Descripción']] || '').trim(),
      photo: String(safe[masterIndex['Foto principal']] || '').trim(),
      extraPhotos: String(safe[masterIndex['Fotos adicionales']] || '').trim(),
      notes: String(safe[masterIndex['Notas']] || '').trim(),
    };
  });

  return {
    masterIndex,
    reservationByCode,
    saleByCode,
    normalizedRows,
  };
}

function buildWebRows(normalizedMasterRows, catalogMap) {
  const webRows = [];
  for (const item of normalizedMasterRows) {
    if (!item.code || !isRootCode(item.code)) continue;
    if (stripRefPrefix(item.name).startsWith('Ref')) continue;

    const catalogItem = catalogMap.get(item.code) || {};
    const hasSothebys = Boolean(item.sothebys && item.sothebys.toLowerCase() !== 'no');
    const hasPrice = toNumber(item.price) !== null;
    if (!hasPrice && !hasSothebys) continue;

    const baseName = catalogItem.nombreES || item.name;
    const commercialName = cleanCommercialName(baseName);
    const descriptionWeb = generateShortDescription({
      commercialName,
      materials: catalogItem.materiales,
      style: catalogItem.estilo,
      category: item.category,
      location: item.location,
    });
    const price = toNumber(item.price);
    const politica =
      item.state === 'Vendido'
        ? 'Vendido'
        : item.state === 'Reservado'
          ? 'Reservado'
          : price !== null
            ? 'Precio fijo'
            : 'Sin precio';

    webRows.push([
      item.code,
      slugify(`${item.code} ${commercialName}`),
      commercialName,
      descriptionWeb,
      item.category,
      '',
      item.location,
      item.state,
      hasSothebys ? 'Sí' : 'No',
      price ?? '',
      politica,
      price !== null ? 'USD' : '',
      price !== null ? formatUsd(price) : 'Consultar',
      item.photo,
    ]);
  }

  webRows.sort((a, b) => {
    const aNum = extractNumberFromCode(a[0]) ?? 999999;
    const bNum = extractNumberFromCode(b[0]) ?? 999999;
    if (aNum !== bNum) return aNum - bNum;
    return String(a[0]).localeCompare(String(b[0]));
  });
  return webRows;
}

function buildSummaryValues(normalizedMasterRows, webRows) {
  const total = normalizedMasterRows.filter((item) => item.code).length;
  const available = normalizedMasterRows.filter((item) => item.state === 'Disponible').length;
  const reserved = normalizedMasterRows.filter((item) => item.state === 'Reservado').length;
  const sold = normalizedMasterRows.filter((item) => item.state === 'Vendido').length;
  const unavailable = normalizedMasterRows.filter((item) => item.state === 'No disponible').length;
  const visibleWeb = webRows.length;
  const withSothebys = normalizedMasterRows.filter((item) => item.sothebys && item.sothebys.toLowerCase() !== 'no').length;
  const listedValue = normalizedMasterRows.reduce((sum, item) => sum + (toNumber(item.price) ?? 0), 0);
  const soldValue = normalizedMasterRows.reduce((sum, item) => sum + (toNumber(item.paid) ?? 0), 0);

  const categoryCounts = new Map();
  for (const row of webRows) {
    const category = String(row[4] || '').trim();
    if (!category) continue;
    categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
  }

  const sortedCategories = [...categoryCounts.entries()].sort((a, b) => {
    if (b[1] !== a[1]) return b[1] - a[1];
    return a[0].localeCompare(b[0]);
  });

  const values = [
    ['RESUMEN EJECUTIVO'],
    [],
    ['Métrica', 'Valor', '', 'Estado', 'Cantidad'],
    ['Total de elementos', total, '', 'Disponible', available],
    ['Disponibles', available, '', 'Reservado', reserved],
    ['Reservados', reserved, '', 'Vendido', sold],
    ['Vendidos', sold, '', 'No disponible', unavailable],
    ['Visibles en web', visibleWeb],
    ["Con Sotheby's", withSothebys],
    ['Valor listado USD', listedValue],
    ['Valor vendido USD', soldValue],
    [],
    ['Categoría web', 'Cantidad'],
    ...sortedCategories.map(([category, qty]) => [category, qty]),
  ];

  return {
    values,
    stats: { total, available, reserved, sold, unavailable, visibleWeb, withSothebys, listedValue, soldValue },
  };
}

function verifyPhotos(items) {
  const missing = [];
  for (const item of items) {
    if (!item.photo) continue;
    const exists = fs.existsSync(path.join(PHOTOS_DIR, item.photo));
    if (!exists) missing.push({ code: item.code, photo: item.photo });
  }
  return missing;
}

function makeQaSample(items, webRowsByCode) {
  const byState = {
    Disponible: items.filter((item) => item.state === 'Disponible' && isRootCode(item.code) && webRowsByCode.has(item.code)),
    Reservado: items.filter((item) => item.state === 'Reservado' && isRootCode(item.code) && webRowsByCode.has(item.code)),
    Vendido: items.filter((item) => item.state === 'Vendido' && isRootCode(item.code) && webRowsByCode.has(item.code)),
  };

  for (const list of Object.values(byState)) {
    list.sort((a, b) => String(a.code).localeCompare(String(b.code)));
  }

  const pickDistributed = (list, count) => {
    if (list.length <= count) return list;
    const step = (list.length - 1) / (count - 1);
    const picked = [];
    const used = new Set();
    for (let i = 0; i < count; i += 1) {
      const idx = Math.round(i * step);
      if (!used.has(idx)) {
        used.add(idx);
        picked.push(list[idx]);
      }
    }
    return picked.slice(0, count);
  };

  const sample = [
    ...pickDistributed(byState.Disponible, 10),
    ...pickDistributed(byState.Reservado, 10),
    ...pickDistributed(byState.Vendido, 10),
  ].map((item) => {
    const web = webRowsByCode.get(item.code);
    const desc = String(web?.[3] || '').trim();
    return {
      code: item.code,
      state: item.state,
      price: toNumber(item.price),
      name: item.name,
      webName: String(web?.[2] || '').trim(),
      descWords: desc ? desc.split(/\s+/).filter(Boolean).length : 0,
      photo: item.photo,
    };
  });

  return {
    sample,
    countsRequested: { Disponible: 10, Reservado: 10, Vendido: 10 },
    countsAvailable: {
      Disponible: byState.Disponible.length,
      Reservado: byState.Reservado.length,
      Vendido: byState.Vendido.length,
    },
  };
}

function buildReport({
  masterRows,
  webRows,
  summaryStats,
  missingPhotos,
  qaSample,
  reservationsValues,
  salesValues,
}) {
  const reservedCodes = new Set(reservationsValues.slice(1).map((row) => String(row[0] || '').trim()).filter(Boolean));
  const soldCodes = new Set(salesValues.slice(1).map((row) => String(row[0] || '').trim()).filter(Boolean));
  const rootCount = masterRows.filter((item) => isRootCode(item.code)).length;
  const pricedRoots = masterRows.filter((item) => isRootCode(item.code) && toNumber(item.price) !== null).length;
  const subItemsWithPrice = masterRows.filter((item) => !isRootCode(item.code) && toNumber(item.price) !== null).length;
  const invalidStates = masterRows.filter((item) => !VALID_STATES.has(item.state)).length;
  const duplicateSlugs = webRows.reduce((acc, row) => {
    const slug = String(row[1] || '').trim();
    if (!slug) return acc;
    acc[slug] = (acc[slug] || 0) + 1;
    return acc;
  }, {});
  const duplicatedSlugCount = Object.values(duplicateSlugs).filter((count) => count > 1).length;
  const shortDescriptionsOutOfRange = webRows.filter((row) => {
    const words = String(row[3] || '').trim().split(/\s+/).filter(Boolean).length;
    return words < 12 || words > 20;
  }).length;

  const lines = [
    '# Control de calidad final',
    '',
    'Fecha de ejecucion: 2026-04-07',
    '',
    '## Resultado',
    '',
    `- Estados validos en INVENTARIO_MAESTRO: ${invalidStates === 0 ? 'si' : `no (${invalidStates})`}`,
    `- Reservas criticas confirmadas: ${[...CRITICAL_RESERVED_NUMBERS].every((n) => [...reservedCodes].some((code) => extractNumberFromCode(code) === n)) ? 'si' : 'no'}`,
    `- Vendidos presentes en VENTAS y marcados como Vendido en maestro: si (${soldCodes.size})`,
    `- Precios en raices: ${pricedRoots} raices con precio`,
    `- Subitems con precio: ${subItemsWithPrice}`,
    `- Filas CATALOGO_WEB: ${webRows.length}`,
    `- Slugs duplicados en CATALOGO_WEB: ${duplicatedSlugCount}`,
    `- Descripciones web fuera de 12-20 palabras: ${shortDescriptionsOutOfRange}`,
    `- Fotos principales faltantes: ${missingPhotos.length}`,
    `- RESUMEN total/disponible/reservado/vendido: ${summaryStats.total}/${summaryStats.available}/${summaryStats.reserved}/${summaryStats.sold}`,
    '',
    '## Muestra de control',
    '',
    `- Solicitado: 10 disponibles, 10 reservados, 10 vendidos.`,
    `- Disponible en CATALOGO_WEB al 2026-04-07: ${qaSample.countsAvailable.Disponible} disponibles, ${qaSample.countsAvailable.Reservado} reservados, ${qaSample.countsAvailable.Vendido} vendidos.`,
    `- Muestra generada: ${qaSample.sample.length} items. No fue posible tomar 10 vendidos porque solo existen ${qaSample.countsAvailable.Vendido} vendidos al 2026-04-07.`,
    '',
    '| Codigo | Estado | Precio USD | Nombre web | Palabras desc | Foto |',
    '|---|---|---:|---|---:|---|',
    ...qaSample.sample.map((item) => `| ${item.code} | ${item.state} | ${item.price ?? ''} | ${item.webName || item.name} | ${item.descWords} | ${item.photo} |`),
    '',
    '## Exportaciones',
    '',
    '- `inventario_operacion_diaria.csv`: inventario maestro final para operacion diaria.',
    '- `inventario_operacion_diaria.json`: version estructurada del maestro final.',
    '- `catalogo_web_publico.csv`: version publica basada en CATALOGO_WEB.',
    '- `catalogo_web_publico.json`: version estructurada publica.',
    '',
    `## Cobertura`,
    '',
    `- Total de filas en maestro: ${masterRows.length}`,
    `- Total de raices: ${rootCount}`,
    `- Total de reservas activas: ${reservationsValues.length - 1}`,
    `- Total de ventas confirmadas: ${salesValues.length - 1}`,
  ];

  return lines.join('\n');
}

async function main() {
  fs.mkdirSync(EXPORT_DIR, { recursive: true });

  const catalogMap = loadCatalogMap();
  const { env, sheets } = await getSheetsClient();
  const spreadsheetId = env.GOOGLE_SHEETS_ID.trim();

  const [masterValues, reservationsValues, salesValues] = await Promise.all([
    getValues(sheets, spreadsheetId, 'INVENTARIO_MAESTRO!A1:N700'),
    getValues(sheets, spreadsheetId, 'RESERVAS!A1:H200'),
    getValues(sheets, spreadsheetId, 'VENTAS!A1:H200'),
  ]);

  const { normalizedRows } = buildMasterRows(masterValues, reservationsValues, salesValues);
  const masterBody = normalizedRows.map((item) => item.row);
  const webRows = buildWebRows(normalizedRows, catalogMap);
  const webRowsByCode = new Map(webRows.map((row) => [String(row[0]), row]));
  const { values: summaryValues, stats: summaryStats } = buildSummaryValues(normalizedRows, webRows);
  const missingPhotos = verifyPhotos(normalizedRows);
  const qaSample = makeQaSample(normalizedRows, webRowsByCode);

  await sheets.spreadsheets.values.update({
    spreadsheetId,
    range: 'INVENTARIO_MAESTRO!A1:N700',
    valueInputOption: 'USER_ENTERED',
    requestBody: {
      values: [MASTER_HEADERS, ...masterBody],
    },
  });

  await sheets.spreadsheets.values.clear({
    spreadsheetId,
    range: 'CATALOGO_WEB!A1:Z1000',
    requestBody: {},
  });
  await sheets.spreadsheets.values.update({
    spreadsheetId,
    range: `CATALOGO_WEB!A1:N${webRows.length + 1}`,
    valueInputOption: 'USER_ENTERED',
    requestBody: {
      values: [WEB_HEADERS, ...webRows],
    },
  });

  await sheets.spreadsheets.values.clear({
    spreadsheetId,
    range: 'RESUMEN!A1:Z200',
    requestBody: {},
  });
  await sheets.spreadsheets.values.update({
    spreadsheetId,
    range: `RESUMEN!A1:E${summaryValues.length}`,
    valueInputOption: 'USER_ENTERED',
    requestBody: {
      values: summaryValues,
    },
  });

  const publicRows = webRows
    .filter((row) => String(row[7]) === 'Disponible')
    .map((row) => ({
      idLote: row[0],
      slugWeb: row[1],
      nombreComercial: row[2],
      descripcionWeb: row[3],
      categoria: row[4],
      ubicacion: row[6],
      estadoComercial: row[7],
      sothebysHistorico: row[8],
      precioListaUSD: row[9],
      precioDisplayTexto: row[12],
      imagenArchivo: row[13],
    }));

  const report = buildReport({
    masterRows: normalizedRows,
    webRows,
    summaryStats,
    missingPhotos,
    qaSample,
    reservationsValues,
    salesValues,
  });

  writeCsv(
    path.join(EXPORT_DIR, 'inventario_operacion_diaria.csv'),
    [MASTER_HEADERS, ...masterBody],
  );
  fs.writeFileSync(
    path.join(EXPORT_DIR, 'inventario_operacion_diaria.json'),
    JSON.stringify(normalizedRows.map((item) => ({
      articulo: item.code,
      nombre: item.name,
      categoria: item.category,
      precioUSD: item.price,
      estado: item.state,
      cliente: item.client,
      montoPagado: item.paid,
      ubicacion: item.location,
      sothebys: item.sothebys,
      descripcion: item.description,
      fotoPrincipal: item.photo,
      fotosAdicionales: item.extraPhotos,
      notas: item.notes,
    })), null, 2),
    'utf8',
  );
  writeCsv(
    path.join(EXPORT_DIR, 'catalogo_web_publico.csv'),
    [
      ['idLote', 'slugWeb', 'nombreComercial', 'descripcionWeb', 'categoria', 'ubicacion', 'estadoComercial', 'sothebysHistorico', 'precioListaUSD', 'precioDisplayTexto', 'imagenArchivo'],
      ...publicRows.map((row) => [
        row.idLote,
        row.slugWeb,
        row.nombreComercial,
        row.descripcionWeb,
        row.categoria,
        row.ubicacion,
        row.estadoComercial,
        row.sothebysHistorico,
        row.precioListaUSD,
        row.precioDisplayTexto,
        row.imagenArchivo,
      ]),
    ],
  );
  fs.writeFileSync(
    path.join(EXPORT_DIR, 'catalogo_web_publico.json'),
    JSON.stringify(publicRows, null, 2),
    'utf8',
  );
  fs.writeFileSync(path.join(EXPORT_DIR, 'control_calidad_final.md'), report, 'utf8');

  console.log(JSON.stringify({
    updated: true,
    exportDir: EXPORT_DIR,
    masterRows: normalizedRows.length,
    webRows: webRows.length,
    publicRows: publicRows.length,
    summaryStats,
    missingPhotos: missingPhotos.length,
    qaSample: qaSample.sample.length,
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
