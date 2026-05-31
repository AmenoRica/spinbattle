STAT_NAMES = {
    "ko": {
        "speed": "초기 속도",
        "acceleration": "가속도",
        "luck": "행운",
        "stamina": "지구력",
        "attack": "공격력",
        "defense": "방어력",
    },
    "ja": {
        "speed": "初速",
        "acceleration": "加速",
        "luck": "運",
        "stamina": "耐久",
        "attack": "攻撃",
        "defense": "防御",
    },
    "en": {
        "speed": "Speed",
        "acceleration": "Accel",
        "luck": "Luck",
        "stamina": "Stamina",
        "attack": "Attack",
        "defense": "Defense",
    },
}

STAT_KEYS = list(STAT_NAMES["ko"].keys())

STAT_DESCRIPTIONS = {
    "ko": {
        "speed": "팽이의 초기 회전 속도",
        "acceleration": "회전 가속도",
        "luck": "특수한 효과가 일어날 확률",
        "stamina": "회전 지속 시간",
        "attack": "충돌 시 데미지",
        "defense": "충돌 시 피해 감소",
    },
    "ja": {
        "speed": "コマの初期回転速度",
        "acceleration": "回転の加速",
        "luck": "特殊効果が発生する確率",
        "stamina": "回転の持続時間",
        "attack": "衝突時のダメージ",
        "defense": "衝突時の被害軽減",
    },
    "en": {
        "speed": "Initial spin speed",
        "acceleration": "Spin acceleration",
        "luck": "Chance of special effects",
        "stamina": "Spin duration",
        "attack": "Collision damage",
        "defense": "Damage reduction",
    },
}

GRADES = [
    (93, "S+"),
    (86, "S"),
    (79, "S-"),
    (72, "A+"),
    (65, "A"),
    (58, "A-"),
    (51, "B+"),
    (44, "B"),
    (37, "B-"),
    (30, "C+"),
    (23, "C"),
    (10, "C-"),
]


def get_stat_names(lang="ko"):
    return STAT_NAMES.get(lang, STAT_NAMES["ko"])


def get_grade(value):
    for threshold, grade in GRADES:
        if value >= threshold:
            return grade
    return "C-"


def get_grade_color(grade):
    if grade.startswith("S"):
        return "#fbbf24"
    if grade.startswith("A"):
        return "#ef4444"
    if grade.startswith("B"):
        return "#3b82f6"
    return "#6b7280"


def compute_stats(hash_str):
    chunk_size = len(hash_str) // len(STAT_KEYS)
    stats = {}
    for i, key in enumerate(STAT_KEYS):
        chunk = hash_str[i * chunk_size : (i + 1) * chunk_size]
        value = int(chunk, 16)
        mapped = 10 + (value % 91)
        stats[key] = mapped
    return stats
