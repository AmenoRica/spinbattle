import math
import random as _random

from .stats import compute_stats
from .types import get_type_multiplier


def _josa(name, josa_pair):
    """한국어 조사 자동 선택. josa_pair: ('은','는'), ('이','가'), ('을','를')"""
    has_final = (ord(name[-1]) - 0xAC00) % 28 != 0
    return name + (josa_pair[0] if has_final else josa_pair[1])


# ============================================================
# 밸런스 조정용 상수 — 값을 변경하여 게임 밸런스를 조절할 수 있습니다
# ============================================================

# 가속 이벤트
ACCEL_BASE_CHANCE = 0.15           # 가속 이벤트 기본 발동 확률
ACCEL_LUCK_SCALE = 0.55            # 행운 100일 때 추가 확률 (총 70%)
ACCEL_AMOUNT_FACTOR = 5.0          # 가속량 = 이 값 * √(acceleration)

# 데미지
BASE_DAMAGE_DIVISOR = 500.0        # 기본 데미지 = (speed * attack) / 이 값
DEFENSE_HALF = 100.0               # 방어 감소율 = defense / (defense + 이 값)

# 크리티컬
CRIT_BASE_CHANCE = 0.05            # 크리티컬 기본 확률
CRIT_LUCK_SCALE = 0.30             # 행운 100일 때 추가 크리티컬 확률 (총 35%)
CRIT_BASE_MULTIPLIER = 1.5         # 크리티컬 기본 배율
CRIT_ACCEL_SCALE = 1 / 200.0       # 가속도당 크리티컬 배율 증가분

# 선공 판정
SPEED_PRIORITY_LUCK_RATIO = 0.5    # 선공 행운 보정 범위 (luck * 이 값)

# 감속
BASE_DECEL = 3.0                   # 턴당 기본 감속량
DECEL_STAMINA_SCALE = 100.0        # 감속 = BASE_DECEL * (이 값 / stamina)
DECEL_TURN_GROWTH = 0.08           # 턴당 감속 증가율 (턴 N: 1 + (N-1) * 이 값)

# 턴 제한
MAX_TURNS = 25                     # 최대 턴 수

# 랜덤 이벤트
EVENT_BASE_CHANCE = 0.05           # 랜덤 이벤트 기본 발생 확률
EVENT_LUCK_SCALE = 0.0025          # 행운 1당 이벤트 확률 증가분

# 기합의머리띠
ENDURE_THRESHOLD = 10              # 기합의머리띠 발동 시 남는 속도


# ============================================================
# 랜덤 이벤트 정의
# ============================================================

POSITIVE_EVENTS = [
    {
        "weight": 15,
        "name": "용의춤",
        "message": "{name_josa} 용의춤을 추었다! 몸에서 열기가 피어오른다!",
        "josa": ("은", "는"),
        "effect": "speed_recover_pct",
        "value": 0.15,
        "log": "속도 {old} → {new}",
        "float_text": "속도↑",
    },
    {
        "weight": 15,
        "name": "칼춤",
        "message": "{name_josa} 칼춤을 추었다! 공격의 기운이 치솟는다!",
        "josa": ("은", "는"),
        "effect": "attack_buff",
        "value": 25,
        "log": "이번 턴 공격력 +{value}",
        "float_text": "공격↑",
    },
    {
        "weight": 15,
        "name": "리플렉터",
        "message": "{name}의 앞에 빛의 벽이 나타났다!",
        "josa": None,
        "effect": "defense_buff",
        "value": 25,
        "log": "이번 턴 방어력 +{value}",
        "float_text": "방어↑",
    },
    {
        "weight": 10,
        "name": "체리열매",
        "message": "{name_josa} 체리열매를 먹었다! 회전이 안정되었다!",
        "josa": ("이", "가"),
        "effect": "speed_recover_pct",
        "value": 0.20,
        "log": "속도 {old} → {new}",
        "float_text": "회복!",
    },
    {
        "weight": 5,
        "name": "기합의머리띠",
        "message": "{name_josa} 기합의머리띠를 발동했다! 절대로 멈추지 않는다!",
        "josa": ("이", "가"),
        "effect": "endure",
        "value": ENDURE_THRESHOLD,
        "log": "속도가 0이 되어도 한 번 버틴다!",
        "float_text": "인내!",
    },
]

NEGATIVE_EVENTS = [
    {
        "weight": 15,
        "name": "풀죽음",
        "message": "{name_josa} 풀이 죽었다... 의욕이 사라졌다.",
        "josa": ("은", "는"),
        "effect": "speed_loss_pct",
        "value": 0.15,
        "log": "속도 {old} → {new}",
        "float_text": "속도↓",
    },
    {
        "weight": 15,
        "name": "혼란",
        "message": "{name_josa} 혼란에 빠졌다! 제대로 공격할 수 없다!",
        "josa": ("이", "가"),
        "effect": "attack_debuff",
        "value": 20,
        "log": "이번 턴 공격력 -{value}",
        "float_text": "혼란!",
    },
    {
        "weight": 10,
        "name": "독",
        "message": "{name_josa} 독에 걸렸다! 회전이 서서히 갉아먹힌다...",
        "josa": ("이", "가"),
        "effect": "speed_flat_loss",
        "value": 20,
        "log": "속도 {old} → {new}",
        "float_text": "독!",
    },
    {
        "weight": 5,
        "name": "풍화",
        "message": "{name}의 표면이 바스러지기 시작했다!",
        "josa": None,
        "effect": "defense_debuff",
        "value": 20,
        "log": "이번 턴 방어력 -{value}",
        "float_text": "방어↓",
    },
]


def _pick_event(events, rng):
    total = sum(e["weight"] for e in events)
    r = rng.uniform(0, total)
    acc = 0
    for e in events:
        acc += e["weight"]
        if r <= acc:
            return e
    return events[-1]


def _apply_event(spin, event, side, log_entries):
    name = spin["name"]
    name_josa = _josa(name, event["josa"]) if event.get("josa") else name
    msg = event["message"].format(name=name, name_josa=name_josa)

    eff = event["effect"]
    val = event["value"]
    detail = ""
    effects = []

    is_positive = event in POSITIVE_EVENTS
    fx_type = "event_positive" if is_positive else "event_negative"

    if eff == "speed_recover_pct":
        old = spin["speed"]
        spin["speed"] = min(spin["speed"] + spin["speed"] * val, spin["speed"] * 2)
        detail = event["log"].format(old=f"{old:.1f}", new=f"{spin['speed']:.1f}")
    elif eff == "speed_loss_pct":
        old = spin["speed"]
        spin["speed"] = max(spin["speed"] - spin["speed"] * val, 0)
        detail = event["log"].format(old=f"{old:.1f}", new=f"{spin['speed']:.1f}")
    elif eff == "speed_flat_loss":
        old = spin["speed"]
        spin["speed"] = max(spin["speed"] - val, 0)
        detail = event["log"].format(old=f"{old:.1f}", new=f"{spin['speed']:.1f}")
    elif eff == "attack_buff":
        spin["attack_mod"] += val
        detail = event["log"].format(value=val)
    elif eff == "attack_debuff":
        spin["attack_mod"] -= val
        detail = event["log"].format(value=val)
    elif eff == "defense_buff":
        spin["defense_mod"] += val
        detail = event["log"].format(value=val)
    elif eff == "defense_debuff":
        spin["defense_mod"] -= val
        detail = event["log"].format(value=val)
    elif eff == "endure":
        spin["endure"] = True
        detail = event["log"]

    effects.append({
        "type": fx_type,
        "target": side,
        "event_name": event["name"],
        "float_text": event.get("float_text", ""),
    })

    log_entries.append({"text": msg, "effects": effects})
    if detail:
        log_entries.append({"text": detail, "effects": []})


def simulate(hash_a, hash_b, rng, name_a="A", name_b="B", type_a=None, type_b=None):
    stats_a = compute_stats(hash_a)
    stats_b = compute_stats(hash_b)

    def make_spin(stats, name, spin_type):
        return {
            "name": name,
            "speed": float(stats["speed"]),
            "max_speed": float(stats["speed"]) * 2,
            "attack": stats["attack"],
            "defense": stats["defense"],
            "stamina": stats["stamina"],
            "acceleration": stats["acceleration"],
            "luck": stats["luck"],
            "spin_type": spin_type,
            "attack_mod": 0,
            "defense_mod": 0,
            "endure": False,
            "endured": False,
        }

    a = make_spin(stats_a, name_a, type_a)
    b = make_spin(stats_b, name_b, type_b)

    log_entries = []

    log_entries.append({
        "text": "━━━ 전투 시작 ━━━",
        "effects": [{"type": "battle_start", "stats_a": dict(stats_a), "stats_b": dict(stats_b)}],
    })
    log_entries.append({
        "text": (
            f"{a['name']}(속도 {a['speed']:.0f} 공격 {a['attack']} 방어 {a['defense']} "
            f"지구력 {a['stamina']} 가속 {a['acceleration']} 행운 {a['luck']})"
        ),
        "effects": [],
    })
    log_entries.append({
        "text": (
            f"{b['name']}(속도 {b['speed']:.0f} 공격 {b['attack']} 방어 {b['defense']} "
            f"지구력 {b['stamina']} 가속 {b['acceleration']} 행운 {b['luck']})"
        ),
        "effects": [],
    })
    log_entries.append({"text": "", "effects": []})

    winner = None

    for turn in range(1, MAX_TURNS + 1):
        a["attack_mod"] = 0
        a["defense_mod"] = 0
        b["attack_mod"] = 0
        b["defense_mod"] = 0

        log_entries.append({
            "text": "─────────────────",
            "effects": [],
        })
        log_entries.append({
            "text": f"턴 {turn}",
            "effects": [{"type": "turn_start", "turn": turn}],
        })
        log_entries.append({"text": "", "effects": []})

        # 1. 가속 이벤트
        for spin, side in [(a, "a"), (b, "b")]:
            chance = ACCEL_BASE_CHANCE + ACCEL_LUCK_SCALE * (spin["luck"] / 100)
            if rng.random() < chance:
                old_speed = spin["speed"]
                boost = ACCEL_AMOUNT_FACTOR * math.sqrt(spin["acceleration"])
                spin["speed"] += boost
                if spin["speed"] > spin["max_speed"]:
                    spin["max_speed"] = spin["speed"]
                log_entries.append({
                    "text": (
                        f"{_josa(spin['name'], ('은', '는'))} 가속 이벤트 발동! 회전이 가속된다! "
                        f"속도 {old_speed:.1f} → {spin['speed']:.1f}"
                    ),
                    "effects": [{"type": "accel", "target": side, "old_speed": round(old_speed, 1), "new_speed": round(spin["speed"], 1)}],
                })
            else:
                log_entries.append({
                    "text": f"{_josa(spin['name'], ('은', '는'))} 가속에 실패했다. 아쉬운 타이밍이었다.",
                    "effects": [{"type": "accel_fail", "target": side}],
                })

        log_entries.append({"text": "", "effects": []})

        # 2. 선공 판정
        prio_a = a["speed"] + rng.uniform(-a["luck"] * SPEED_PRIORITY_LUCK_RATIO, a["luck"] * SPEED_PRIORITY_LUCK_RATIO)
        prio_b = b["speed"] + rng.uniform(-b["luck"] * SPEED_PRIORITY_LUCK_RATIO, b["luck"] * SPEED_PRIORITY_LUCK_RATIO)

        if prio_a >= prio_b:
            first, second, first_side, second_side = a, b, "a", "b"
            log_entries.append({"text": f"선공: {a['name']}!", "effects": [{"type": "first_strike", "target": "a"}]})
        else:
            first, second, first_side, second_side = b, a, "b", "a"
            log_entries.append({"text": f"선공: {b['name']}!", "effects": [{"type": "first_strike", "target": "b"}]})

        # 3. 공격 페이즈
        def do_attack(attacker, defender, atk_side, def_side):
            atk = max(attacker["attack"] + attacker["attack_mod"], 1)
            def_val = max(defender["defense"] + defender["defense_mod"], 0)

            base_damage = (attacker["speed"] * atk) / BASE_DAMAGE_DIVISOR

            is_crit = rng.random() < (CRIT_BASE_CHANCE + CRIT_LUCK_SCALE * (attacker["luck"] / 100))
            multiplier = 1.0
            if is_crit:
                multiplier = CRIT_BASE_MULTIPLIER + attacker["acceleration"] * CRIT_ACCEL_SCALE
                base_damage *= multiplier

            type_mult = get_type_multiplier(attacker.get("spin_type"), defender.get("spin_type"))

            reduction = def_val / (def_val + DEFENSE_HALF)
            final_damage = base_damage * (1 - reduction) * type_mult
            final_damage = max(final_damage, 0)

            old_speed = defender["speed"]
            defender["speed"] -= final_damage

            crit_text = ""
            if is_crit:
                crit_text = f" 크리티컬 히트!! 데미지가 {multiplier:.1f}배 증폭되었다!"

            type_text = ""
            if type_mult > 1.0:
                type_text = " 속성 상성 유리!"
            elif type_mult < 1.0:
                type_text = " 속성 상성 불리..."

            log_entries.append({
                "text": (
                    f"{attacker['name']}의 돌진! {final_damage:.1f} 데미지!{crit_text}{type_text} "
                    f"({_josa(defender['name'], ('은', '는'))} 속도 {old_speed:.1f} → {max(defender['speed'], 0):.1f})"
                ),
                "effects": [{
                    "type": "attack",
                    "attacker": atk_side,
                    "defender": def_side,
                    "damage": round(final_damage, 1),
                    "crit": is_crit,
                    "crit_mult": round(multiplier, 1) if is_crit else None,
                    "type_mult": round(type_mult, 2),
                }],
            })

            if defender["speed"] <= 0 and defender["endure"] and not defender["endured"]:
                defender["speed"] = ENDURE_THRESHOLD
                defender["endured"] = True
                log_entries.append({
                    "text": f"{_josa(defender['name'], ('이', '가'))} 기합의머리띠로 버텼다! 속도 0 → {ENDURE_THRESHOLD}!",
                    "effects": [{"type": "endure", "target": def_side, "old_speed": 0, "new_speed": ENDURE_THRESHOLD}],
                })

            if defender["speed"] < 0:
                defender["speed"] = 0

        do_attack(first, second, first_side, second_side)
        if second["speed"] > 0:
            do_attack(second, first, second_side, first_side)
        else:
            log_entries.append({
                "text": f"{_josa(second['name'], ('은', '는'))} 속도가 0이 되었다! 반격할 수 없다!",
                "effects": [{"type": "counter_fail", "target": second_side}],
            })

        log_entries.append({"text": "", "effects": []})

        # 속도 0 체크
        if a["speed"] <= 0 and b["speed"] <= 0:
            log_entries.append({"text": "두 팽이가 동시에 멈추었다!", "effects": [{"type": "stop_both"}]})
            winner = "draw"
            break
        if a["speed"] <= 0:
            log_entries.append({"text": f"{_josa(a['name'], ('이', '가'))} 속도가 0이 되었다! 회전이 멈추었다!", "effects": [{"type": "stop", "target": "a"}]})
            winner = "b"
            break
        if b["speed"] <= 0:
            log_entries.append({"text": f"{_josa(b['name'], ('이', '가'))} 속도가 0이 되었다! 회전이 멈추었다!", "effects": [{"type": "stop", "target": "b"}]})
            winner = "a"
            break

        # 4. 랜덤 이벤트
        for spin, side in [(a, "a"), (b, "b")]:
            chance = EVENT_BASE_CHANCE + spin["luck"] * EVENT_LUCK_SCALE
            if rng.random() < chance:
                positive_weight = spin["luck"]
                negative_weight = 100 - spin["luck"]
                if rng.uniform(0, positive_weight + negative_weight) < positive_weight:
                    event = _pick_event(POSITIVE_EVENTS, rng)
                else:
                    event = _pick_event(NEGATIVE_EVENTS, rng)
                _apply_event(spin, event, side, log_entries)

        # 이벤트 후 속도 재체크
        if a["speed"] <= 0 and not (a["endure"] and not a["endured"]):
            log_entries.append({"text": f"{_josa(a['name'], ('이', '가'))} 속도가 0이 되었다! 회전이 멈추었다!", "effects": [{"type": "stop", "target": "a"}]})
            winner = "b"
            break
        if b["speed"] <= 0 and not (b["endure"] and not b["endured"]):
            log_entries.append({"text": f"{_josa(b['name'], ('이', '가'))} 속도가 0이 되었다! 회전이 멈추었다!", "effects": [{"type": "stop", "target": "b"}]})
            winner = "a"
            break

        # 기합의머리띠 발동 (이벤트로 받은 경우)
        for spin, side in [(a, "a"), (b, "b")]:
            if spin["speed"] <= 0 and spin["endure"] and not spin["endured"]:
                spin["speed"] = ENDURE_THRESHOLD
                spin["endured"] = True
                log_entries.append({
                    "text": f"{_josa(spin['name'], ('이', '가'))} 기합의머리띠로 버텼다! 속도 0 → {ENDURE_THRESHOLD}!",
                    "effects": [{"type": "endure", "target": side, "old_speed": 0, "new_speed": ENDURE_THRESHOLD}],
                })

        # 5. 턴 종료 감속
        growth = 1 + (turn - 1) * DECEL_TURN_GROWTH

        old_a = a["speed"]
        old_b = b["speed"]
        a["speed"] = max(a["speed"] - BASE_DECEL * (DECEL_STAMINA_SCALE / a["stamina"]) * growth, 0)
        b["speed"] = max(b["speed"] - BASE_DECEL * (DECEL_STAMINA_SCALE / b["stamina"]) * growth, 0)

        log_entries.append({
            "text": (
                f"턴 종료 감속 — {a['name']} 속도 {old_a:.1f} → {a['speed']:.1f}, "
                f"{b['name']} 속도 {old_b:.1f} → {b['speed']:.1f}"
            ),
            "effects": [{"type": "decel", "turn": turn, "a_old": round(old_a, 1), "a_new": round(a["speed"], 1), "b_old": round(old_b, 1), "b_new": round(b["speed"], 1)}],
        })

        # 감속 후 체크
        if a["speed"] <= 0 and b["speed"] <= 0:
            log_entries.append({"text": "두 팽이가 동시에 멈추었다!", "effects": [{"type": "stop_both"}]})
            winner = "draw"
            break
        if a["speed"] <= 0:
            log_entries.append({"text": f"{_josa(a['name'], ('이', '가'))} 회전이 멈추었다!", "effects": [{"type": "stop", "target": "a"}]})
            winner = "b"
            break
        if b["speed"] <= 0:
            log_entries.append({"text": f"{_josa(b['name'], ('이', '가'))} 회전이 멈추었다!", "effects": [{"type": "stop", "target": "b"}]})
            winner = "a"
            break

    log_entries.append({"text": "─────────────────", "effects": []})
    log_entries.append({"text": "", "effects": []})

    if winner == "draw":
        log_entries.append({
            "text": f"━━━ 전투 종료 ━━━\n{MAX_TURNS}턴이 경과했다! 승부가 나지 않았다... 무승부!",
            "effects": [{"type": "battle_end", "winner": "draw", "turns": turn}],
        })
    elif turn == MAX_TURNS and winner is None:
        winner = "draw"
        log_entries.append({
            "text": f"━━━ 전투 종료 ━━━\n{MAX_TURNS}턴이 경과했다! 승부가 나지 않았다... 무승부!",
            "effects": [{"type": "battle_end", "winner": "draw", "turns": turn}],
        })
    else:
        winner_name = a["name"] if winner == "a" else b["name"]
        log_entries.append({
            "text": f"━━━ 전투 종료 ━━━\n승자: {winner_name}! ({turn}턴 만에 승리)",
            "effects": [{"type": "battle_end", "winner": winner, "turns": turn}],
        })

    return log_entries


def simulate_text(hash_a, hash_b, rng, name_a="A", name_b="B"):
    entries = simulate(hash_a, hash_b, rng, name_a, name_b)
    return "\n".join(e["text"] for e in entries)
