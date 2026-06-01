ENDURE_THRESHOLD = 10

WEATHER_EVENT_TEXT = {
    "ko": {
        "rain_influx": {
            "name": "빗물 유입",
            "message": "🌧️ 빗물이 {name_josa} {name}의 회전에 스며들었다! 속도가 소폭 회복되었다!",
            "log": "속도 {old} → {new}",
            "float_text": "빗물 회복!",
        },
        "snowstorm": {
            "name": "눈보라",
            "message": "❄️ 눈보라가 몰아쳤다! {name_josa} {name}의 회전이 크게 둔해졌다!",
            "log": "속도 {old} → {new}",
            "float_text": "눈보라!",
        },
    },
    "ja": {
        "rain_influx": {
            "name": "雨水浸入",
            "message": "🌧️ 雨水が{name_josa}{name}の回転に染み込んだ！速度が少し回復した！",
            "log": "速度 {old} → {new}",
            "float_text": "雨水回復!",
        },
        "snowstorm": {
            "name": "ブリザード",
            "message": "❄️ ブリザードが吹き荒れた！{name_josa}{name}の回転が大きく鈍った！",
            "log": "速度 {old} → {new}",
            "float_text": "ブリザード!",
        },
    },
    "en": {
        "rain_influx": {
            "name": "Rain Influx",
            "message": "🌧️ Rainwater seeped into {name}'s rotation! Speed recovered slightly!",
            "log": "Speed {old} → {new}",
            "float_text": "Rain Heal!",
        },
        "snowstorm": {
            "name": "Snowstorm",
            "message": "❄️ A blizzard swept through! {name}'s rotation slowed significantly!",
            "log": "Speed {old} → {new}",
            "float_text": "Blizzard!",
        },
    },
}

EVENT_DATA = [
    ("dragon_dance", "speed_recover_pct", 15, 0.15, ("은", "는"), ("は",), ("",)),
    ("sword_dance", "attack_buff", 25, 25, ("은", "는"), ("は",), ("",)),
    ("reflect", "defense_buff", 15, 25, (None,), (None,), (None,)),
    ("oran_berry", "speed_recover_pct", 10, 0.20, ("이", "가"), ("は",), ("",)),
    ("focus_band", "endure", 5, ENDURE_THRESHOLD, ("이", "가"), ("は",), ("",)),
    ("wilt", "speed_loss_pct", 15, 0.15, ("은", "는"), ("は",), ("",)),
    ("confusion", "attack_debuff", 15, 20, ("이", "가"), ("は",), ("",)),
    ("poison", "speed_flat_loss", 10, 20, ("이", "가"), ("は",), ("",)),
    ("weathering", "defense_debuff", 5, 20, (None,), (None,), (None,)),
]

EVENT_TEXT = {
    "ko": {
        "dragon_dance": {
            "name": "용의춤",
            "message": "{name_josa} 용의춤을 추었다! 몸에서 열기가 피어오른다!",
            "log": "속도 {old} → {new}",
            "float_text": "속도↑",
        },
        "sword_dance": {
            "name": "칼춤",
            "message": "{name_josa} 칼춤을 추었다! 공격의 기운이 치솟는다!",
            "log": "이번 턴 공격력 +{value}",
            "float_text": "공격↑",
        },
        "reflect": {
            "name": "리플렉터",
            "message": "{name}의 앞에 빛의 벽이 나타났다!",
            "log": "이번 턴 방어력 +{value}",
            "float_text": "방어↑",
        },
        "oran_berry": {
            "name": "체리열매",
            "message": "{name_josa} 체리열매를 먹었다! 회전이 안정되었다!",
            "log": "속도 {old} → {new}",
            "float_text": "회복!",
        },
        "focus_band": {
            "name": "기합의머리띠",
            "message": "{name_josa} 기합의머리띠를 발동했다! 절대로 멈추지 않는다!",
            "log": "속도가 0이 되어도 한 번 버틴다!",
            "float_text": "인내!",
        },
        "wilt": {
            "name": "풀죽음",
            "message": "{name_josa} 풀이 죽었다... 의욕이 사라졌다.",
            "log": "속도 {old} → {new}",
            "float_text": "속도↓",
        },
        "confusion": {
            "name": "혼란",
            "message": "{name_josa} 혼란에 빠졌다! 제대로 공격할 수 없다!",
            "log": "이번 턴 공격력 -{value}",
            "float_text": "혼란!",
        },
        "poison": {
            "name": "독",
            "message": "{name_josa} 독에 걸렸다! 회전이 서서히 갉아먹힌다...",
            "log": "속도 {old} → {new}",
            "float_text": "독!",
        },
        "weathering": {
            "name": "풍화",
            "message": "{name}의 표면이 바스러지기 시작했다!",
            "log": "이번 턴 방어력 -{value}",
            "float_text": "방어↓",
        },
    },
    "ja": {
        "dragon_dance": {
            "name": "りゅうのまい",
            "message": "{name_josa}りゅうのまいを踊った！体から熱気が立ち上る！",
            "log": "速度 {old} → {new}",
            "float_text": "速度↑",
        },
        "sword_dance": {
            "name": "つるぎのまい",
            "message": "{name_josa}つるぎのまいを踊った！攻撃の気迫が高まる！",
            "log": "このターン攻撃力 +{value}",
            "float_text": "攻撃↑",
        },
        "reflect": {
            "name": "リフレクター",
            "message": "{name}の前に光の壁が現れた！",
            "log": "このターン防御力 +{value}",
            "float_text": "防御↑",
        },
        "oran_berry": {
            "name": "オボンのみ",
            "message": "{name_josa}オボンのみを食べた！回転が安定した！",
            "log": "速度 {old} → {new}",
            "float_text": "回復!",
        },
        "focus_band": {
            "name": "きあいのハチマキ",
            "message": "{name_josa}きあいのハチマキが発動した！絶対に止まらない！",
            "log": "速度が0になっても一度耐える！",
            "float_text": "根性!",
        },
        "wilt": {
            "name": "しおれ",
            "message": "{name_josa}しおれてしまった…やる気が消えた。",
            "log": "速度 {old} → {new}",
            "float_text": "速度↓",
        },
        "confusion": {
            "name": "こんらん",
            "message": "{name_josa}こんらんした！うまく攻撃できない！",
            "log": "このターン攻撃力 -{value}",
            "float_text": "こんらん!",
        },
        "poison": {
            "name": "どく",
            "message": "{name_josa}どく状態になった！回転が徐々に削られていく…",
            "log": "速度 {old} → {new}",
            "float_text": "どく!",
        },
        "weathering": {
            "name": "ふか",
            "message": "{name}の表面が崩れ始めた！",
            "log": "このターン防御力 -{value}",
            "float_text": "防御↓",
        },
    },
    "en": {
        "dragon_dance": {
            "name": "Dragon Dance",
            "message": "{name_josa}used Dragon Dance! Heat rises from the body!",
            "log": "Speed {old} → {new}",
            "float_text": "Speed↑",
        },
        "sword_dance": {
            "name": "Swords Dance",
            "message": "{name_josa}used Swords Dance! Attack power surges!",
            "log": "This turn Attack +{value}",
            "float_text": "Atk↑",
        },
        "reflect": {
            "name": "Reflect",
            "message": "A wall of light appeared before {name}!",
            "log": "This turn Defense +{value}",
            "float_text": "Def↑",
        },
        "oran_berry": {
            "name": "Oran Berry",
            "message": "{name_josa}ate an Oran Berry! Rotation stabilized!",
            "log": "Speed {old} → {new}",
            "float_text": "Heal!",
        },
        "focus_band": {
            "name": "Focus Band",
            "message": "{name_josa}Focus Band activated! Absolutely won't stop!",
            "log": "Will endure once even at 0 speed!",
            "float_text": "Endure!",
        },
        "wilt": {
            "name": "Wither",
            "message": "{name_josa}withered away... Motivation vanished.",
            "log": "Speed {old} → {new}",
            "float_text": "Speed↓",
        },
        "confusion": {
            "name": "Confusion",
            "message": "{name_josa}became confused! Can't attack properly!",
            "log": "This turn Attack -{value}",
            "float_text": "Confuse!",
        },
        "poison": {
            "name": "Poison",
            "message": "{name_josa}was poisoned! Rotation slowly wears away...",
            "log": "Speed {old} → {new}",
            "float_text": "Poison!",
        },
        "weathering": {
            "name": "Weathering",
            "message": "{name}'s surface started crumbling!",
            "log": "This turn Defense -{value}",
            "float_text": "Def↓",
        },
    },
}