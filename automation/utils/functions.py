import re
from typing import Tuple, Optional


def extract_postal_code_and_city(address_text: str) -> Tuple[str, str] | Tuple[None, None]:
    pattern = r"(\d{5})\s+([A-Z\s]+)(?: CEDEX)?"

    match = re.search(pattern, address_text.strip().upper())

    if match:
        postal_code = match.group(1)
        city_name = match.group(2).strip()
        if city_name.endswith(" CEDEX"):
            city_name = city_name[:-6].strip()

        return postal_code, city_name
    else:
        return None, None


def xpath_of_text(text: str):
    return f"//span[contains(text(), '{text}')]/following-sibling::span[1]"


def _read_done_set(path: str = 'done.txt') -> set[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return set(l.strip() for l in f if l.strip())
    except FileNotFoundError:
        return set()