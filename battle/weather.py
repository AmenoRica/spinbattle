WEATHER_TYPES = {
    "clear": {
        "name_ko": "쾌청",
        "name_ja": "晴れ",
        "name_en": "Clear",
        "icon_ko": "☀️",
        "icon_class": "weather-clear",
    },
    "rain": {
        "name_ko": "비",
        "name_ja": "雨",
        "name_en": "Rain",
        "icon_ko": "🌧️",
        "icon_class": "weather-rain",
    },
    "snow": {
        "name_ko": "눈",
        "name_ja": "雪",
        "name_en": "Snow",
        "icon_ko": "❄️",
        "icon_class": "weather-snow",
    },
    "normal": {
        "name_ko": "평범",
        "name_ja": "普通",
        "name_en": "Normal",
        "icon_ko": "⛅",
        "icon_class": "weather-normal",
    },
}

WEATHER_CHOICES = [(k, v["name_ko"]) for k, v in WEATHER_TYPES.items()]


def get_weather_name(weather_type, lang="ko"):
    t = WEATHER_TYPES.get(weather_type, WEATHER_TYPES["normal"])
    return t.get(f"name_{lang}", t.get("name_ko", ""))


def get_weather_icon(weather_type):
    t = WEATHER_TYPES.get(weather_type, WEATHER_TYPES["normal"])
    return t.get("icon_ko", "")


WEATHER_STAT_MODS = {
    "clear": {
        "fire": {"attack": 1.15},
        "electric": {"luck": 1.10},
    },
    "rain": {
        "water": {"speed_recover_bonus": 5.0},
        "fire": {"attack": 0.85},
    },
    "snow": {
        "ice": {"defense": 1.20},
        "fire": {"decel_mult": 1.5},
    },
    "normal": {},
}

WEATHER_CRIT_BONUS = {
    "clear": 0.03,
    "rain": 0.0,
    "snow": 0.0,
    "normal": 0.0,
}

WEATHER_EVENTS = {
    "clear": [],
    "rain": ["rain_influx"],
    "snow": ["snowstorm"],
    "normal": [],
}