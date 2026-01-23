import re
from typing import List, Dict


PRICE_PATTERN = re.compile(r"(?i)([$€£]?\d+[\d,.]*|\d+[\d,.]*\s?(?:usd|eur|rs|aed|sar|inr))")
HEADING_PATTERN = re.compile(r"^#{1,6}\s*(.+)$")


def parse_menu_from_markdown(markdown: str) -> List[Dict[str, str]]:
    """Heuristically extract potential menu items from markdown page content.

    Strategy:
    1. Identify sections whose heading contains keywords: menu, dishes, food, meals.
    2. Collect lines under those headings until next heading.
    3. Additionally scan all lines for price patterns combined with text.
    4. Normalize and deduplicate items.
    Returns list of dicts: {name, price(optional), source_line}.
    """
    if not markdown:
        return []

    lines = [l.strip() for l in markdown.splitlines() if l.strip()]
    menu_sections: List[str] = []
    current_collect: List[str] = []
    in_menu_section = False
    menu_keywords = {"menu", "dishes", "food", "meals", "entrees", "starters"}

    for line in lines:
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            title = heading_match.group(1).lower()
            if any(k in title for k in menu_keywords):
                # start new menu section
                if current_collect:
                    menu_sections.extend(current_collect)
                    current_collect = []
                in_menu_section = True
                continue
            else:
                if in_menu_section and current_collect:
                    menu_sections.extend(current_collect)
                in_menu_section = False
                current_collect = []
                continue
        else:
            if in_menu_section:
                # stop if line looks like a divider
                if set(line) <= {"-", "_", "*"} and len(line) > 3:
                    in_menu_section = False
                else:
                    current_collect.append(line)

    # Flush last collected section
    if in_menu_section and current_collect:
        menu_sections.extend(current_collect)

    # Fallback: if no explicit menu section found, scan all lines with prices
    candidate_lines = menu_sections if menu_sections else lines

    items: List[Dict[str, str]] = []
    seen_names = set()

    for line in candidate_lines:
        price_match = PRICE_PATTERN.search(line)
        # Skip lines that are too short or purely numeric
        if len(line) < 3 or line.isdigit():
            continue
        # Extract name by removing price part
        price = price_match.group(0) if price_match else ""
        name_part = line
        if price:
            name_part = PRICE_PATTERN.sub("", line).strip(" -:|\t")
        # Basic cleanup
        name_part = re.sub(r"\s{2,}", " ", name_part).strip()
        if not name_part:
            continue
        # Heuristic: ignore lines that look like paragraphs (> 120 chars)
        if len(line) > 120:
            continue
        # Avoid duplicates
        key = (name_part.lower(), price.lower())
        if key in seen_names:
            continue
        seen_names.add(key)
        # Accept if price present OR looks like an item (contains word + maybe colon)
        if price or re.search(r"[A-Za-z].*[A-Za-z]", name_part):
            items.append({"name": name_part, "price": price, "source_line": line})

    return items[:50]  # cap to 50 items to avoid bloat


__all__ = ["parse_menu_from_markdown"]
