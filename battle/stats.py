STAT_NAMES = {
    "speed": "초기 속도",
    "acceleration": "가속도",
    "luck": "행운",
    "stamina": "지구력",
    "attack": "공격력",
    "defense": "방어력",
}

STAT_DESCRIPTIONS = {
    "speed": "팽이의 초기 회전 속도",
    "acceleration": "회전 가속도",
    "luck": "특수한 효과가 일어날 확률",
    "stamina": "회전 지속 시간",
    "attack": "충돌 시 데미지",
    "defense": "충돌 시 피해 감소",
}

STAT_KEYS = list(STAT_NAMES.keys())

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
