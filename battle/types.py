import colorsys

from PIL import Image


SPIN_TYPES = {
    "fire": {"name_ko": "불꽃", "name_ja": "ほのお", "name_en": "Fire", "color": "#F08030"},
    "water": {"name_ko": "물", "name_ja": "みず", "name_en": "Water", "color": "#6890F0"},
    "grass": {"name_ko": "풀", "name_ja": "くさ", "name_en": "Grass", "color": "#78C850"},
    "electric": {"name_ko": "전기", "name_ja": "でんき", "name_en": "Electric", "color": "#F8D030"},
    "ice": {"name_ko": "얼음", "name_ja": "こおり", "name_en": "Ice", "color": "#98D8D8"},
    "steel": {"name_ko": "강철", "name_ja": "はがね", "name_en": "Steel", "color": "#B8B8D0"},
    "dragon": {"name_ko": "드래곤", "name_ja": "ドラゴン", "name_en": "Dragon", "color": "#7038F8"},
    "dark": {"name_ko": "악", "name_ja": "あく", "name_en": "Dark", "color": "#705848"},
    "psychic": {"name_ko": "에스퍼", "name_ja": "エスパー", "name_en": "Psychic", "color": "#F85888"},
    "fighting": {"name_ko": "격투", "name_ja": "かくとう", "name_en": "Fighting", "color": "#C03028"},
}

SPIN_TYPE_CHOICES = [(k, v["name_ko"]) for k, v in SPIN_TYPES.items()]


def get_type_name(type_key, lang="ko"):
    t = SPIN_TYPES.get(type_key, {})
    return t.get(f"name_{lang}", t.get("name_ko", ""))

# ============================================================
# 상성 테이블 — 공격자 속성 → 유리한 방어자 속성 목록
# 유리: 1.2배, 불리: 0.8배, 그 외: 1.0배
# ============================================================
ADVANTAGES = {
    "fire": ["grass", "ice"],
    "water": ["fire", "steel"],
    "grass": ["water", "electric"],
    "electric": ["water", "ice"],
    "ice": ["grass", "dragon"],
    "steel": ["ice", "dark"],
    "dragon": ["psychic", "electric"],
    "dark": ["psychic", "dragon"],
    "psychic": ["fighting", "fire"],
    "fighting": ["steel", "dark"],
}

ADVANTAGE_MULT = 1.2
DISADVANTAGE_MULT = 1 / ADVANTAGE_MULT


def get_type_multiplier(atk_type, def_type):
    if atk_type in ADVANTAGES and def_type in ADVANTAGES[atk_type]:
        return ADVANTAGE_MULT
    if def_type in ADVANTAGES and atk_type in ADVANTAGES[def_type]:
        return DISADVANTAGE_MULT
    return 1.0


def compute_type_from_image(image_field):
    try:
        img = Image.open(image_field).convert("RGB")
        img = img.resize((50, 50))
        pixels = list(img.getdata())
        n = len(pixels)
        avg_r = sum(p[0] for p in pixels) / n / 255
        avg_g = sum(p[1] for p in pixels) / n / 255
        avg_b = sum(p[2] for p in pixels) / n / 255
        image_field.seek(0)

        h, s, v = colorsys.rgb_to_hsv(avg_r, avg_g, avg_b)

        if v < 0.15:
            return "dark"

        if s < 0.06:
            return "ice" if v > 0.75 else "steel"

        hue = h * 360

        if hue < 15 or hue >= 340:
            return "fire"
        if hue < 40:
            return "fighting"
        if hue < 75:
            return "electric"
        if hue < 160:
            return "grass"
        if hue < 200:
            return "ice"
        if hue < 260:
            return "water"
        if hue < 300:
            return "dragon"
        return "psychic"
    except Exception:
        import random
        return random.choice(list(SPIN_TYPES.keys()))
