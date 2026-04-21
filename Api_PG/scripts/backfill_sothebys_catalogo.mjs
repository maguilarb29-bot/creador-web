import fs from "fs";
import path from "path";

const projectRoot = "C:/Users/Alejandro/Documents/Proyecto Pignatelli";
const currentPath = path.join(projectRoot, "Api_PG/data/solaris_catalogo.json");
const legacyPath = path.join(
  projectRoot,
  "Api_PG/data/_legacy_logica_vieja/solaris_catalogo.json.bak-2026-04-13-editorial-clean"
);

const current = JSON.parse(fs.readFileSync(currentPath, "utf8"));
const legacy = JSON.parse(fs.readFileSync(legacyPath, "utf8"));

const currentItems = Array.isArray(current) ? current : Object.values(current);
const legacyItems = Array.isArray(legacy) ? legacy : Object.values(legacy);

const legacyByCode = new Map(
  legacyItems
    .filter((item) => item && item.codigoItem)
    .map((item) => [item.codigoItem, item])
);

let updated = 0;

for (const item of currentItems) {
  if (!item || !item.codigoItem || !item.tieneSothebys) continue;

  const legacyItem = legacyByCode.get(item.codigoItem);
  if (!legacyItem) continue;

  let changed = false;
  for (const field of [
    "refSothebys",
    "paginaSothebys",
    "estimacionSothebys",
    "descripcionSothebys",
  ]) {
    const currentValue = item[field];
    const legacyValue = legacyItem[field];
    if ((!currentValue || currentValue === "") && legacyValue) {
      item[field] = legacyValue;
      changed = true;
    }
  }

  if (changed) {
    updated += 1;
    console.log(
      `${item.codigoItem}: lote ${item.refSothebys || "-"} | pag ${item.paginaSothebys || "-"} | ${item.estimacionSothebys || "-"}`
    );
  }
}

fs.writeFileSync(currentPath, JSON.stringify(currentItems, null, 2) + "\n", "utf8");
console.log(`Backfill Sotheby's aplicado: ${updated} items`);
