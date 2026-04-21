from __future__ import annotations

import json
import re
from pathlib import Path


PRICE_RE = re.compile(r"\$?\s*([0-9IlOSSBZ.,xX<>]+)\s*[-•]\s*\$?\s*([0-9IlOSSBZ.,xX<>]+)")
DIM_RE = re.compile(r"\b\d+[0-9.,&oO]*\s*cm\b", re.IGNORECASE)

TECHNIQUE_HINTS = (
    "oil on",
    "pastel",
    "watercolour",
    "red chalk",
    "pen and brown ink",
    "bronze",
    "porcelain",
    "silver",
    "glass",
    "giltwood",
    "mahogany",
    "marble",
    "silk",
    "wool",
    "canvas",
)


def fix_money_token(token: str) -> int | None:
    cleaned = token.upper()
    cleaned = cleaned.replace("O", "0").replace("I", "1").replace("L", "1")
    cleaned = cleaned.replace("S", "5").replace("B", "8").replace("Z", "2")
    cleaned = cleaned.replace("X", "0").replace("<", "").replace(">", "")
    digits = re.sub(r"[^0-9]", "", cleaned)
    return int(digits) if digits else None


def parse_price(line: str) -> tuple[int | None, int | None]:
    match = PRICE_RE.search(line)
    if not match:
        one = re.findall(r"\$[0-9,.\-]+", line)
        if len(one) == 1:
            value = fix_money_token(one[0])
            return value, value
        return None, None
    return fix_money_token(match.group(1)), fix_money_token(match.group(2))


def is_header(line: str) -> bool:
    return "I" in line and any(
        key in line.lower()
        for key in ("floor", "bedroom", "room", "stairs", "hall", "salon", "study", "bathroom")
    )


def is_footer(line: str) -> bool:
    low = line.lower()
    return (
        "sotheby" in low
        or "valuation" in low
        or "18 january 2016" in low
        or low.startswith("57 chester")
    )


def looks_like_code(line: str) -> bool:
    s = re.sub(r"[^A-Za-z0-9]", "", line)
    return 4 <= len(s) <= 6 and any(ch.isdigit() for ch in s) and any(ch.isalpha() for ch in s)


def looks_like_number(line: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}", line.strip()))


def looks_like_start(line: str, nxt: str | None) -> bool:
    low = line.lower()
    if "century" in low or "school" in low or "circle of" in low or "follower of" in low:
        return True
    if nxt and nxt.isupper() and len(nxt) > 8:
        return True
    return False


def split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    saw_price = False

    for idx, line in enumerate(lines):
        nxt = lines[idx + 1] if idx + 1 < len(lines) else None
        if current and saw_price and looks_like_start(line, nxt):
            blocks.append(current)
            current = [line]
            saw_price = False
            continue

        current.append(line)
        if "$" in line or " - " in line or "•" in line:
            pmin, pmax = parse_price(line)
            if pmin or pmax:
                saw_price = True

    if current:
        blocks.append(current)
    return blocks


def parse_block(block: list[str]) -> dict:
    artist = block[0] if block else None
    title_lines: list[str] = []
    desc_lines: list[str] = []
    technique = None
    dimensions = None
    price_min = None
    price_max = None
    mode = "desc"

    for line in block[1:]:
        stripped = line.strip()
        low = stripped.lower()
        pmin, pmax = parse_price(stripped)
        if pmin or pmax:
            price_min, price_max = pmin, pmax
            continue

        if any(h in low for h in TECHNIQUE_HINTS) and technique is None:
            technique = stripped
            mode = "desc"
            continue

        if DIM_RE.search(stripped):
            dimensions = stripped
            continue

        if stripped.isupper() and len(stripped) > 4 and technique is None and not desc_lines:
            title_lines.append(stripped)
            mode = "title"
            continue

        if mode == "title" and stripped.isupper() and len(stripped) > 2:
            title_lines.append(stripped)
            continue

        desc_lines.append(stripped)

    return {
        "artista_escuela": artist,
        "titulo": " ".join(title_lines) if title_lines else None,
        "descripcion": " ".join(desc_lines) if desc_lines else None,
        "tecnica": technique,
        "dimensiones": dimensions,
        "precio_min": price_min,
        "precio_max": price_max,
    }


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    ocr_path = base_dir / "data" / "sothebys_ocr_pages.json"
    out_path = base_dir / "data" / "sothebys_inventory_best_effort.json"

    data = json.loads(ocr_path.read_text(encoding="utf-8-sig"))

    metadata = {
        "propietarios": "Prince and Princess Pignatelli",
        "direccion": "57 Chester Square, London SW1W 9EA",
        "fecha_valoracion": "18 January 2016",
        "numero_valoracion": "70265243",
    }

    items = []
    next_number = 1

    for page in data:
        page_no = page["page"]
        if page_no < 6 or page_no > 110:
            continue

        raw_lines = [ln.strip() for ln in page["lines"] if ln and ln.strip()]
        header_idx = next((i for i, ln in enumerate(raw_lines) if is_header(ln)), None)
        if header_idx is None:
            continue

        pre = raw_lines[:header_idx]
        content = [ln for ln in raw_lines[header_idx + 1 :] if not is_footer(ln)]
        category_location = raw_lines[header_idx].replace("Puntings", "Paintings").replace("Paintirzs", "Paintings")
        if " I " in category_location:
            categoria, ubicacion = [part.strip() for part in category_location.split(" I ", 1)]
        else:
            categoria, ubicacion = category_location, None

        numbers = [int(ln) for ln in pre if looks_like_number(ln)]
        codes = [re.sub(r"[^A-Za-z0-9]", "", ln) for ln in pre if looks_like_code(ln)]

        blocks = split_blocks(content)
        for idx, block in enumerate(blocks):
            parsed = parse_block(block)
            number = numbers[idx] if idx < len(numbers) else next_number
            code = codes[idx] if idx < len(codes) else None
            items.append(
                {
                    "numero": number,
                    "codigo_lote": code,
                    "categoria": categoria,
                    "ubicacion": ubicacion,
                    **parsed,
                    "source_page": page_no,
                }
            )
            next_number = max(next_number, number + 1)

    result = {
        "metadata": metadata,
        "items": items,
    }

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {out_path} with {len(items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
