import re
from collections import defaultdict

CATEGORY_ORDER = [
    "produce",
    "dairy",
    "meat & seafood",
    "bakery",
    "frozen",
    "pantry",
    "drinks",
    "condiments",
    "snacks",
    "leftovers",
    "other",
]

DIET_BANNED_CATEGORIES = {
    "vegetarian": {"meat & seafood"},
    "vegan": {"meat & seafood", "dairy"},
}

DIET_BANNED_KEYWORDS = {
    "vegetarian": {
        "chicken", "beef", "pork", "bacon", "sausage", "turkey", "lamb",
        "fish", "salmon", "tuna", "shrimp", "prawn", "anchovy", "ham",
        "steak", "mince", "meatball", "pepperoni", "chorizo", "duck",
        "crab", "lobster", "scallop", "sardine", "gelatine", "gelatin",
    },
    "vegan": {
        "chicken", "beef", "pork", "bacon", "sausage", "turkey", "lamb",
        "fish", "salmon", "tuna", "shrimp", "prawn", "anchovy", "ham",
        "steak", "mince", "meatball", "pepperoni", "chorizo", "duck",
        "crab", "lobster", "scallop", "sardine", "gelatine", "gelatin",
        "cheese", "yoghurt", "yogurt", "butter", "cream",
        "egg", "eggs", "honey", "whey", "casein", "mozzarella", "cheddar",
        "kefir", "ice cream",
    },
}

_STOPWORDS = {"a", "an", "the", "some", "of", "fresh", "extra", "free", "range"}


def normalize(name):
    words = re.findall(r"[a-z0-9']+", name.lower())
    kept = [w for w in words if w not in _STOPWORDS]
    return " ".join(kept) if kept else name.lower().strip()


def _word_sets(a, b):
    return set(a.split()), set(b.split())


def matches_pantry(item_name, pantry_entry):
    a, b = normalize(item_name), normalize(pantry_entry)
    if not a or not b:
        return False
    if a == b:
        return True
    if re.search(rf"\b{re.escape(b)}\b", a) or re.search(rf"\b{re.escape(a)}\b", b):
        return True
    aw, bw = _word_sets(a, b)
    if not aw or not bw:
        return False
    overlap = aw & bw
    if not overlap:
        return False
    return overlap == aw or overlap == bw


def load_pantry(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                entries.append(line)
    return entries


def is_banned(item, diet):
    if diet not in DIET_BANNED_CATEGORIES:
        return False
    if item.get("category", "").lower() in DIET_BANNED_CATEGORIES[diet]:
        return True
    words = set(normalize(item["name"]).split())
    return bool(words & DIET_BANNED_KEYWORDS[diet])


def build_list(inventory, pantry=None, diet="any"):
    pantry = pantry or []
    have, need = [], []
    for item in inventory:
        if is_banned(item, diet):
            continue
        if any(matches_pantry(item["name"], entry) for entry in pantry):
            have.append(item)
        else:
            need.append(item)
    return {"have": have, "need": need}


def group(items):
    grouped = defaultdict(list)
    for item in items:
        grouped[item.get("category", "other").lower()].append(item)
    ordered = []
    for cat in CATEGORY_ORDER + sorted(set(grouped) - set(CATEGORY_ORDER)):
        if cat in grouped:
            ordered.append((cat, grouped[cat]))
    return ordered


def render_text(result):
    lines = []
    need = result["need"]
    have = result["have"]
    if need:
        lines.append("GROCERY LIST")
        lines.append("=" * 40)
        for cat, items in group(need):
            lines.append("")
            lines.append(cat.upper())
            lines.append("-" * len(cat))
            for it in items:
                qty = f"  ({it['quantity']})" if it["quantity"] else ""
                lines.append(f"  [ ] {it['name']}{qty}")
    else:
        lines.append("GROCERY LIST")
        lines.append("=" * 40)
        lines.append("")
        lines.append("Nothing needed - you are fully stocked. Nap time.")
    if have:
        lines.append("")
        lines.append("ALREADY AT HOME (skipped)")
        lines.append("-" * 26)
        for it in have:
            lines.append(f"  {it['name']}")
    return "\n".join(lines)


def render_markdown(result):
    lines = ["# Grocery List", ""]
    need = result["need"]
    if need:
        for cat, items in group(need):
            lines.append(f"## {cat.capitalize()}")
            lines.append("")
            for it in items:
                qty = f" ({it['quantity']})" if it["quantity"] else ""
                lines.append(f"- [ ] {it['name']}{qty}")
            lines.append("")
    else:
        lines.append("Nothing needed - you are fully stocked. Nap time.")
        lines.append("")
    if result["have"]:
        lines.append("<details><summary>Already at home</summary>")
        lines.append("")
        for it in result["have"]:
            lines.append(f"- {it['name']}")
        lines.append("")
        lines.append("</details>")
    return "\n".join(lines)
