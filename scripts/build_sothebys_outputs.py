from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "docs" / "referencia_sothebys_pignatelli.csv"
JSON_PATH = ROOT / "docs" / "referencia_sothebys_pignatelli.json"
JSON_INDEXED_PATH = ROOT / "docs" / "referencia_sothebys_pignatelli_indexed.json"
DOCX_PATH = ROOT / "docs" / "referencia_sothebys_pignatelli.docx"


def read_rows() -> list[dict[str, str]]:
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_json(rows: list[dict[str, str]]) -> None:
    manual_values = []
    sothebys_refs = []
    indexed: dict[str, dict] = {}

    for row in rows:
        item = {
            "codigo_pignatelli": row["codigo_pignatelli"],
            "referencia_sothebys": row["referencia_sothebys"] or None,
            "pagina_sothebys": int(row["pagina_sothebys"]) if row["pagina_sothebys"] else None,
            "descripcion_es": row["descripcion_es"],
            "valoracion_usd": row["valoracion_usd"],
            "notas": row["notas"] or None,
            "fuente": row["fuente"],
        }
        if row["fuente"] == "Manual usuario":
            manual_values.append(item)
        else:
            sothebys_refs.append(item)
        indexed[row["codigo_pignatelli"]] = {
            "codigo": row["codigo_pignatelli"],
            "descripcion_es": row["descripcion_es"],
            "valoracion_usd": row["valoracion_usd"],
            "referencia_sothebys": row["referencia_sothebys"] or None,
            "pagina_sothebys": int(row["pagina_sothebys"]) if row["pagina_sothebys"] else None,
            "notas": row["notas"] or None,
            "fuente": row["fuente"],
        }

    payload = {
        "titulo": "Referencia Sotheby's vs Catalogo Pignatelli",
        "origen": "Consolidado manual + PDF de valoracion Sotheby's 18 January 2016",
        "manual_values": manual_values,
        "sothebys_references": sothebys_refs,
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    JSON_INDEXED_PATH.write_text(
        json.dumps(
            {
                "titulo": "Referencia Sotheby's vs Catalogo Pignatelli",
                "lookup_by_codigo": indexed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def paragraphs_to_xml(paragraphs: list[str]) -> str:
    xml_parts = []
    for text in paragraphs:
        safe = escape(text)
        xml_parts.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">"
            + safe
            + "</w:t></w:r></w:p>"
        )
    return "".join(xml_parts)


def build_docx(rows: list[dict[str, str]]) -> None:
    paragraphs = [
        "Referencia Sotheby's vs Catalogo Pignatelli",
        "",
        "Valores manuales confirmados",
    ]

    for row in rows:
        if row["fuente"] == "Manual usuario":
            paragraphs.append(
                f"{row['codigo_pignatelli']}: {row['descripcion_es']} | {row['valoracion_usd']}"
            )

    paragraphs.append("")
    paragraphs.append("Referencias Sotheby's")

    for row in rows:
        if row["fuente"] == "Sotheby's":
            ref = row["referencia_sothebys"]
            page = row["pagina_sothebys"]
            notes = f" | Notas: {row['notas']}" if row["notas"] else ""
            paragraphs.append(
                f"{row['codigo_pignatelli']} | Ref. {ref} | Pag. {page} | {row['descripcion_es']} | {row['valoracion_usd']}{notes}"
            )

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

    core = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Referencia Sotheby's vs Catalogo Pignatelli</dc:title>
  <dc:creator>Codex</dc:creator>
</cp:coreProperties>"""

    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>"""

    document = (
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14">
<w:body>"""
        + paragraphs_to_xml(paragraphs)
        + """<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>"""
    )

    with zipfile.ZipFile(DOCX_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("docProps/core.xml", core)
        zf.writestr("docProps/app.xml", app)
        zf.writestr("word/document.xml", document)


def main() -> int:
    rows = read_rows()
    build_json(rows)
    build_docx(rows)
    print(JSON_PATH)
    print(JSON_INDEXED_PATH)
    print(DOCX_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
