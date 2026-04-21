import fs from "fs";

const filePath = "C:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG/scripts/generar_catalogo_html.py";
let source = fs.readFileSync(filePath, "utf8");

source = source.replace(
  '        page_txt = f" · Pag. {pag_s}" if pag_s else ""',
  '        page_txt = f" - Pag. {pag_s}" if pag_s else ""'
);
source = source.replace(
  '        est_txt = f" · {est_s}" if est_s else ""',
  '        est_txt = f" - {est_s}" if est_s else ""'
);
source = source.replace(
  '        page_txt = f" Â· Pag. {pag_s}" if pag_s else ""',
  '        page_txt = f" - Pag. {pag_s}" if pag_s else ""'
);
source = source.replace(
  '        est_txt = f" Â· {est_s}" if est_s else ""',
  '        est_txt = f" - {est_s}" if est_s else ""'
);

fs.writeFileSync(filePath, source, "utf8");
console.log("Separadores de generar_catalogo_html.py normalizados");
