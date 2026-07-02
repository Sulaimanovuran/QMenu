"""Генерация человекочитаемых slug'ов (транслитерация кириллицы + уникальность)."""
import re

# кириллица -> латиница для slug (упрощённая таблица)
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(text: str) -> str:
    """Строит базовый slug: транслит -> нижний регистр -> дефисы."""
    text = (text or "").strip().lower()
    out = []
    for ch in text:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum():
            out.append(ch)
        else:
            out.append("-")
    slug = re.sub(r"-+", "-", "".join(out)).strip("-")
    return slug or "item"


async def unique_slug(model, base_text: str, *, exclude_id: int | None = None) -> str:
    """Возвращает slug, уникальный в рамках таблицы model (добавляет -2, -3, ...)."""
    base = slugify(base_text)
    candidate = base
    i = 2
    while True:
        qs = model.filter(slug=candidate)
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if not await qs.exists():
            return candidate
        candidate = f"{base}-{i}"
        i += 1
