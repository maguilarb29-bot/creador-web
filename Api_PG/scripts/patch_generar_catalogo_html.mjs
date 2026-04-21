import fs from "fs";

const filePath = "C:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG/scripts/generar_catalogo_html.py";
let source = fs.readFileSync(filePath, "utf8");

const normalized = source.replaceAll("\r\n", "\n");

const targetRegex = /    soth_ref = ""\n    if soth and ref_s:\n        soth_ref = f'<div class="ref-s">[\s\S]*?<\/div>'\n\n    precio_html\s+= f'<div class="precio">\{precio\}<\/div>' if precio else ""/;

if (!targetRegex.test(normalized)) {
  throw new Error("No encontre el bloque principal de Sotheby's en generar_catalogo_html.py");
}

source = normalized.replace(
  targetRegex,
  `    soth_ref = ""
    if soth and ref_s:
        lot_txt = f"Lote {ref_s}" if ref_s else ""
        page_txt = f" · Pag. {pag_s}" if pag_s else ""
        est_txt = f" · {est_s}" if est_s else ""
        soth_ref = f'<div class="ref-s"><span class="ref-label">Valoracion Sotheby\\'s:</span> {lot_txt}{page_txt}{est_txt}</div>'

    precio_html = ""
    if precio:
        precio_label = "Precio comercial" if soth else "Precio"
        precio_html = f'<div class="precio"><span class="precio-label">{precio_label}:</span> {precio}</div>'`
);

source = source.replace(
  ".precio{{color:#8b6914;font-weight:700;font-size:.9rem;margin-bottom:4px}}",
  ".precio{{color:#8b6914;font-weight:700;font-size:.9rem;margin-bottom:4px}}\r\n.precio-label{{color:#6d5733;font-weight:600}}"
);

source = source.replace(
  ".ref-s{{font-size:.72rem;color:#8b6914;margin-top:6px;font-style:italic}}",
  ".ref-s{{font-size:.72rem;color:#8b6914;margin-top:6px;line-height:1.4}}\r\n.ref-label{{font-weight:700}}"
);

fs.writeFileSync(filePath, source, "utf8");
console.log("generar_catalogo_html.py actualizado");
