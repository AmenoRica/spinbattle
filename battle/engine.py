import math

from .josa import JOSA
from .messages import MESSAGES
from .events import EVENT_DATA, EVENT_TEXT, ENDURE_THRESHOLD, WEATHER_EVENT_TEXT
from .stats import compute_stats
from .types import get_type_multiplier
from .weather import WEATHER_STAT_MODS, WEATHER_CRIT_BONUS, WEATHER_EVENTS

ACCEL_BASE_CHANCE = 0.15
ACCEL_LUCK_SCALE = 0.55
ACCEL_AMOUNT_FACTOR = 6.0

BASE_DAMAGE_ATTACK_SCALE = 0.18
BASE_DAMAGE_SPEED_SCALE = 0.02
DEFENSE_HALF = 35.0
DEFENSE_DECEL_FACTOR = 0.008

CRIT_BASE_CHANCE = 0.05
CRIT_LUCK_SCALE = 0.15
CRIT_BASE_MULTIPLIER = 1.5
CRIT_ACCEL_SCALE = 0.01

SPEED_PRIORITY_LUCK_RATIO = 0.3

BASE_DECEL = 4.0
DECEL_STAMINA_SCALE = 80.0
DECEL_TURN_GROWTH = 0.08

MAX_TURNS = 35

EVENT_BASE_CHANCE = 0.05
EVENT_LUCK_SCALE = 0.0025


def _build_positives():
    result = []
    for eid, eff, weight, val in [
        ("dragon_dance", "speed_recover_pct", 15, 0.15),
        ("sword_dance", "attack_buff", 15, 25),
        ("reflect", "defense_buff", 15, 25),
        ("oran_berry", "speed_recover_pct", 10, 0.20),
        ("focus_band", "endure", 5, ENDURE_THRESHOLD),
    ]:
        josa_map = {
            "dragon_dance": ("은", "는"),
            "sword_dance": ("은", "는"),
            "reflect": (None,),
            "oran_berry": ("이", "가"),
            "focus_band": ("이", "가"),
        }
        result.append({"id": eid, "weight": weight, "effect": eff, "value": val, "josa": josa_map[eid]})
    return result


def _build_negatives():
    result = []
    for eid, eff, weight, val in [
        ("wilt", "speed_loss_pct", 15, 0.15),
        ("confusion", "attack_debuff", 15, 20),
        ("poison", "speed_flat_loss", 10, 20),
        ("weathering", "defense_debuff", 5, 20),
    ]:
        josa_map = {
            "wilt": ("은", "는"),
            "confusion": ("이", "가"),
            "poison": ("이", "가"),
            "weathering": (None,),
        }
        result.append({"id": eid, "weight": weight, "effect": eff, "value": val, "josa": josa_map[eid]})
    return result


POSITIVE_EVENTS = _build_positives()
NEGATIVE_EVENTS = _build_negatives()

WEATHER_RAIN_INFLUX_CHANCE = 0.08
WEATHER_SNOWSTORM_CHANCE = 0.08
WEATHER_SNOWSTORM_PCT = 0.20


def _pick_event(events, rng):
    total = sum(e["weight"] for e in events)
    r = rng.uniform(0, total)
    acc = 0
    for e in events:
        acc += e["weight"]
        if r <= acc:
            return e
    return events[-1]


def _apply_event(spin, event, side, log_entries, lang):
    msgs = MESSAGES.get(lang, MESSAGES["ko"])
    evt = EVENT_TEXT.get(lang, EVENT_TEXT["ko"]).get(event["id"], {})
    josa_fn = JOSA.get(lang, JOSA["ko"])

    name = spin["name"]
    josa_pair = event["josa"]
    if josa_pair[0] is not None:
        name_josa = josa_fn(name, josa_pair)
    else:
        name_josa = name

    msg_template = evt.get("message", event["id"])
    msg = msg_template.replace("{name}", name).replace("{name_josa}", name_josa)

    eff = event["effect"]
    val = event["value"]
    detail = ""
    effects = []

    is_positive = event in POSITIVE_EVENTS
    fx_type = "event_positive" if is_positive else "event_negative"

    if eff == "speed_recover_pct":
        old = spin["speed"]
        spin["speed"] = min(spin["speed"] + spin["speed"] * val, spin["speed"] * 2)
        detail = evt.get("log", "").replace("{old}", f"{old:.1f}").replace("{new}", f"{spin['speed']:.1f}")
    elif eff == "speed_loss_pct":
        old = spin["speed"]
        spin["speed"] = max(spin["speed"] - spin["speed"] * val, 0)
        detail = evt.get("log", "").replace("{old}", f"{old:.1f}").replace("{new}", f"{spin['speed']:.1f}")
    elif eff == "speed_flat_loss":
        old = spin["speed"]
        spin["speed"] = max(spin["speed"] - val, 0)
        detail = evt.get("log", "").replace("{old}", f"{old:.1f}").replace("{new}", f"{spin['speed']:.1f}")
    elif eff == "attack_buff":
        spin["attack_mod"] += val
        detail = evt.get("log", "").replace("{value}", str(int(val)))
    elif eff == "attack_debuff":
        spin["attack_mod"] -= val
        detail = evt.get("log", "").replace("{value}", str(int(val)))
    elif eff == "defense_buff":
        spin["defense_mod"] += val
        detail = evt.get("log", "").replace("{value}", str(int(val)))
    elif eff == "defense_debuff":
        spin["defense_mod"] -= val
        detail = evt.get("log", "").replace("{value}", str(int(val)))
    elif eff == "endure":
        spin["endure"] = True
        detail = evt.get("log", event["id"])

    effects.append({
        "type": fx_type,
        "target": side,
        "event_name": event["id"],
        "float_text": evt.get("float_text", ""),
    })

    log_entries.append({"text": msg, "effects": effects})
    if detail:
        log_entries.append({"text": detail, "effects": []})


def simulate(hash_a, hash_b, rng, name_a="A", name_b="B", type_a=None, type_b=None, lang="ko", weather=None, city_name=None):
    msgs = MESSAGES.get(lang, MESSAGES["ko"])
    josa_fn = JOSA.get(lang, JOSA["ko"])

    if lang == "ko":
        topic = ("은", "는")
        subject = ("이", "가")
    elif lang == "ja":
        topic = ("", "は")
        subject = ("", "が")
    else:
        topic = ("", " ")
        subject = ("", " ")

    stats_a = compute_stats(hash_a)
    stats_b = compute_stats(hash_b)

    def make_spin(stats, name, spin_type):
        initial_speed = float(stats["speed"]) + float(stats["defense"]) * 0.4
        return {
            "name": name,
            "speed": initial_speed,
            "max_speed": initial_speed * 2,
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

    weather_mods = WEATHER_STAT_MODS.get(weather or "normal", {})
    weather_crit_bonus = WEATHER_CRIT_BONUS.get(weather or "normal", 0.0)
    weather_event_ids = WEATHER_EVENTS.get(weather or "normal", [])

    log_entries = []

    log_entries.append({
        "text": msgs["battle_start"],
        "effects": [{"type": "battle_start", "stats_a": dict(stats_a), "stats_b": dict(stats_b)}],
    })
    for spin_data in [a, b]:
        log_entries.append({
            "text": msgs["stat_line"].format(
                name=spin_data["name"],
                speed=spin_data["speed"],
                attack=spin_data["attack"],
                defense=spin_data["defense"],
                stamina=spin_data["stamina"],
                acceleration=spin_data["acceleration"],
                luck=spin_data["luck"],
            ),
            "effects": [],
        })
    log_entries.append({"text": "", "effects": []})

    if weather and weather != "normal":
        from .weather import get_weather_name
        weather_name = get_weather_name(weather, lang)
        city_display = city_name or ""
        log_entries.append({
            "text": msgs.get("weather_announce", "").format(city=city_display, weather_name=weather_name),
            "effects": [{"type": "weather_announce", "weather": weather, "city": city_display, "weather_name": weather_name}],
        })

        for spin, side in [(a, "a"), (b, "b")]:
            spin_type = spin.get("spin_type")
            type_mods = weather_mods.get(spin_type, {})
            for mod_key, mod_val in type_mods.items():
                effect_key = f"weather_effect_{weather}_{spin_type}"
                if mod_key == "attack":
                    spin["attack"] = int(spin["attack"] * mod_val)
                    log_entries.append({
                        "text": msgs.get(effect_key, ""),
                        "effects": [{"type": "weather_effect", "target": side, "weather": weather, "stat": "attack"}],
                    })
                elif mod_key == "defense":
                    spin["defense"] = int(spin["defense"] * mod_val)
                    log_entries.append({
                        "text": msgs.get(effect_key, ""),
                        "effects": [{"type": "weather_effect", "target": side, "weather": weather, "stat": "defense"}],
                    })
                elif mod_key == "luck":
                    spin["luck"] = int(spin["luck"] * mod_val)
                    log_entries.append({
                        "text": msgs.get(effect_key, ""),
                        "effects": [{"type": "weather_effect", "target": side, "weather": weather, "stat": "luck"}],
                    })
                elif mod_key == "speed_recover_bonus":
                    spin["speed_recover_bonus"] = mod_val
                    log_entries.append({
                        "text": msgs.get(effect_key, ""),
                        "effects": [{"type": "weather_effect", "target": side, "weather": weather, "stat": "speed_recover"}],
                    })
                elif mod_key == "decel_mult":
                    spin["decel_mult"] = mod_val
                    log_entries.append({
                        "text": msgs.get(effect_key, ""),
                        "effects": [{"type": "weather_effect", "target": side, "weather": weather, "stat": "decel"}],
                    })

        if weather == "clear":
            log_entries.append({
                "text": msgs.get("weather_effect_clear_crit", ""),
                "effects": [{"type": "weather_effect", "target": "both", "weather": weather, "stat": "crit"}],
            })

        log_entries.append({"text": "", "effects": []})

    winner = None

    for turn in range(1, MAX_TURNS + 1):
        a["attack_mod"] = 0
        a["defense_mod"] = 0
        b["attack_mod"] = 0
        b["defense_mod"] = 0

        log_entries.append({"text": msgs["separator"], "effects": []})
        log_entries.append({
            "text": msgs["turn"].format(turn=turn),
            "effects": [{"type": "turn_start", "turn": turn}],
        })
        log_entries.append({"text": "", "effects": []})

        for spin, side in [(a, "a"), (b, "b")]:
            chance = ACCEL_BASE_CHANCE + ACCEL_LUCK_SCALE * (spin["luck"] / 100)
            if rng.random() < chance:
                old_speed = spin["speed"]
                boost = ACCEL_AMOUNT_FACTOR * math.sqrt(spin["acceleration"])
                if "speed_recover_bonus" in spin:
                    boost += spin["speed_recover_bonus"]
                spin["speed"] += boost
                if spin["speed"] > spin["max_speed"]:
                    spin["max_speed"] = spin["speed"]
                log_entries.append({
                    "text": msgs["accel_success"].format(
                        name_josa=josa_fn(spin["name"], topic),
                        name=spin["name"],
                        old=old_speed,
                        new=spin["speed"],
                    ),
                    "effects": [{"type": "accel", "target": side, "old_speed": round(old_speed, 1), "new_speed": round(spin["speed"], 1)}],
                })
            else:
                log_entries.append({
                    "text": msgs["accel_fail"].format(
                        name_josa=josa_fn(spin["name"], topic),
                        name=spin["name"],
                    ),
                    "effects": [{"type": "accel_fail", "target": side}],
                })

        log_entries.append({"text": "", "effects": []})

        prio_a = a["speed"] * 0.6 + a["attack"] * 0.25 + a["defense"] * 0.15 + rng.uniform(-a["luck"] * SPEED_PRIORITY_LUCK_RATIO, a["luck"] * SPEED_PRIORITY_LUCK_RATIO)
        prio_b = b["speed"] * 0.6 + b["attack"] * 0.25 + b["defense"] * 0.15 + rng.uniform(-b["luck"] * SPEED_PRIORITY_LUCK_RATIO, b["luck"] * SPEED_PRIORITY_LUCK_RATIO)

        if prio_a >= prio_b:
            first, second, first_side, second_side = a, b, "a", "b"
            log_entries.append({"text": msgs["first_strike"].format(name=a["name"]), "effects": [{"type": "first_strike", "target": "a"}]})
        else:
            first, second, first_side, second_side = b, a, "b", "a"
            log_entries.append({"text": msgs["first_strike"].format(name=b["name"]), "effects": [{"type": "first_strike", "target": "b"}]})

        def do_attack(attacker, defender, atk_side, def_side):
            atk = max(attacker["attack"] + attacker["attack_mod"], 1)
            def_val = max(defender["defense"] + defender["defense_mod"], 0)

            base_damage = atk * BASE_DAMAGE_ATTACK_SCALE + attacker["speed"] * BASE_DAMAGE_SPEED_SCALE

            is_crit = rng.random() < (CRIT_BASE_CHANCE + CRIT_LUCK_SCALE * (attacker["luck"] / 100) + weather_crit_bonus)
            multiplier = 1.0
            if is_crit:
                multiplier = CRIT_BASE_MULTIPLIER + attacker["acceleration"] * CRIT_ACCEL_SCALE
                base_damage *= multiplier

            type_mult = get_type_multiplier(attacker.get("spin_type"), defender.get("spin_type"))

            reduction = def_val / (def_val + DEFENSE_HALF)
            final_damage = max(base_damage * (1 - reduction), 0.5) * type_mult
            final_damage = max(final_damage, 0)

            old_speed = defender["speed"]
            defender["speed"] -= final_damage

            crit_text = ""
            if is_crit:
                crit_text = msgs["crit_suffix"].format(mult=multiplier)

            type_text = ""
            if type_mult > 1.0:
                type_text = msgs["type_advantage"]
            elif type_mult < 1.0:
                type_text = msgs["type_disadvantage"]

            defender_josa = josa_fn(defender["name"], topic)

            log_entries.append({
                "text": msgs["attack"].format(
                    attacker=attacker["name"],
                    damage=final_damage,
                    crit_text=crit_text,
                    type_text=type_text,
                    defender_josa=defender_josa,
                    old=old_speed,
                    new=max(defender["speed"], 0),
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
                endure_name = josa_fn(defender["name"], subject)
                log_entries.append({
                    "text": msgs["endure_attack"].format(
                        name_josa=endure_name,
                        name=defender["name"],
                        threshold=ENDURE_THRESHOLD,
                    ),
                    "effects": [{"type": "endure", "target": def_side, "old_speed": 0, "new_speed": ENDURE_THRESHOLD}],
                })

            if defender["speed"] < 0:
                defender["speed"] = 0

        do_attack(first, second, first_side, second_side)
        if second["speed"] > 0:
            do_attack(second, first, second_side, first_side)
        else:
            second_josa = josa_fn(second["name"], topic)
            log_entries.append({
                "text": msgs["counter_fail"].format(
                    name_josa=second_josa,
                    name=second["name"],
                ),
                "effects": [{"type": "counter_fail", "target": second_side}],
            })

        log_entries.append({"text": "", "effects": []})

        if a["speed"] <= 0 and b["speed"] <= 0:
            log_entries.append({"text": msgs["stop_both"], "effects": [{"type": "stop_both"}]})
            winner = "draw"
            break
        if a["speed"] <= 0:
            a_josa = josa_fn(a["name"], subject)
            log_entries.append({"text": msgs["stop_one"].format(name_josa=a_josa, name=a["name"]), "effects": [{"type": "stop", "target": "a"}]})
            winner = "b"
            break
        if b["speed"] <= 0:
            b_josa = josa_fn(b["name"], subject)
            log_entries.append({"text": msgs["stop_one"].format(name_josa=b_josa, name=b["name"]), "effects": [{"type": "stop", "target": "b"}]})
            winner = "a"
            break

        for spin, side in [(a, "a"), (b, "b")]:
            chance = EVENT_BASE_CHANCE + spin["luck"] * EVENT_LUCK_SCALE
            if rng.random() < chance:
                positive_weight = spin["luck"]
                negative_weight = 100 - spin["luck"]
                if rng.uniform(0, positive_weight + negative_weight) < positive_weight:
                    event = _pick_event(POSITIVE_EVENTS, rng)
                else:
                    event = _pick_event(NEGATIVE_EVENTS, rng)
                _apply_event(spin, event, side, log_entries, lang)

        if weather == "rain" and weather_event_ids:
            for spin, side in [(a, "a"), (b, "b")]:
                if rng.random() < WEATHER_RAIN_INFLUX_CHANCE:
                    evt_text = WEATHER_EVENT_TEXT.get(lang, WEATHER_EVENT_TEXT["ko"]).get("rain_influx", {})
                    old_speed = spin["speed"]
                    bonus = spin.get("speed_recover_bonus", 0)
                    spin["speed"] = min(spin["speed"] + 5.0 + bonus, spin["speed"] * 2)
                    name = spin["name"]
                    josa_pair = ("은", "는") if lang == "ko" else (("は",) if lang == "ja" else ("",))
                    name_josa = josa_fn(name, josa_pair) if josa_pair[0] else name
                    msg_template = evt_text.get("message", "rain_influx")
                    msg = msg_template.replace("{name_josa}", name_josa).replace("{name}", name)
                    detail_template = evt_text.get("log", "")
                    detail = detail_template.replace("{old}", f"{old_speed:.1f}").replace("{new}", f"{spin['speed']:.1f}")
                    log_entries.append({"text": msg, "effects": [{"type": "weather_event", "target": side, "weather": "rain", "event_name": "rain_influx", "float_text": evt_text.get("float_text", "")}]})
                    if detail:
                        log_entries.append({"text": detail, "effects": []})

        if weather == "snow" and weather_event_ids:
            for spin, side in [(a, "a"), (b, "b")]:
                if rng.random() < WEATHER_SNOWSTORM_CHANCE:
                    evt_text = WEATHER_EVENT_TEXT.get(lang, WEATHER_EVENT_TEXT["ko"]).get("snowstorm", {})
                    old_speed = spin["speed"]
                    spin["speed"] = max(spin["speed"] - spin["speed"] * WEATHER_SNOWSTORM_PCT, 0)
                    name = spin["name"]
                    josa_pair = ("은", "는") if lang == "ko" else (("は",) if lang == "ja" else ("",))
                    name_josa = josa_fn(name, josa_pair) if josa_pair[0] else name
                    msg_template = evt_text.get("message", "snowstorm")
                    msg = msg_template.replace("{name_josa}", name_josa).replace("{name}", name)
                    detail_template = evt_text.get("log", "")
                    detail = detail_template.replace("{old}", f"{old_speed:.1f}").replace("{new}", f"{spin['speed']:.1f}")
                    log_entries.append({"text": msg, "effects": [{"type": "weather_event", "target": side, "weather": "snow", "event_name": "snowstorm", "float_text": evt_text.get("float_text", "")}]})
                    if detail:
                        log_entries.append({"text": detail, "effects": []})

        if a["speed"] <= 0 and not (a["endure"] and not a["endured"]):
            a_josa = josa_fn(a["name"], subject)
            log_entries.append({"text": msgs["stop_one"].format(name_josa=a_josa, name=a["name"]), "effects": [{"type": "stop", "target": "a"}]})
            winner = "b"
            break
        if b["speed"] <= 0 and not (b["endure"] and not b["endured"]):
            b_josa = josa_fn(b["name"], subject)
            log_entries.append({"text": msgs["stop_one"].format(name_josa=b_josa, name=b["name"]), "effects": [{"type": "stop", "target": "b"}]})
            winner = "a"
            break

        for spin, side in [(a, "a"), (b, "b")]:
            if spin["speed"] <= 0 and spin["endure"] and not spin["endured"]:
                spin["speed"] = ENDURE_THRESHOLD
                spin["endured"] = True
                endure_name = josa_fn(spin["name"], subject)
                log_entries.append({
                    "text": msgs["endure_attack"].format(
                        name_josa=endure_name,
                        name=spin["name"],
                        threshold=ENDURE_THRESHOLD,
                    ),
                    "effects": [{"type": "endure", "target": side, "old_speed": 0, "new_speed": ENDURE_THRESHOLD}],
                })

        growth = 1 + (turn - 1) * DECEL_TURN_GROWTH

        old_a = a["speed"]
        old_b = b["speed"]
        decel_a = BASE_DECEL * (DECEL_STAMINA_SCALE / a["stamina"]) * growth * a.get("decel_mult", 1.0) * max(1.0 - a["defense"] * DEFENSE_DECEL_FACTOR, 0.3)
        decel_b = BASE_DECEL * (DECEL_STAMINA_SCALE / b["stamina"]) * growth * b.get("decel_mult", 1.0) * max(1.0 - b["defense"] * DEFENSE_DECEL_FACTOR, 0.3)
        if turn >= 26:
            decel_a *= 2
            decel_b *= 2
        if turn >= 31:
            decel_a *= 2
            decel_b *= 2
        a["speed"] = max(a["speed"] - decel_a, 0)
        b["speed"] = max(b["speed"] - decel_b, 0)

        log_entries.append({
            "text": msgs["decel"].format(
                name_a=a["name"], old_a=old_a, new_a=a["speed"],
                name_b=b["name"], old_b=old_b, new_b=b["speed"],
            ),
            "effects": [{"type": "decel", "turn": turn, "a_old": round(old_a, 1), "a_new": round(a["speed"], 1), "b_old": round(old_b, 1), "b_new": round(b["speed"], 1)}],
        })

        if a["speed"] <= 0 and b["speed"] <= 0:
            log_entries.append({"text": msgs["stop_both"], "effects": [{"type": "stop_both"}]})
            winner = "draw"
            break
        if a["speed"] <= 0:
            a_josa = josa_fn(a["name"], subject)
            log_entries.append({"text": msgs["stop_decel"].format(name_josa=a_josa, name=a["name"]), "effects": [{"type": "stop", "target": "a"}]})
            winner = "b"
            break
        if b["speed"] <= 0:
            b_josa = josa_fn(b["name"], subject)
            log_entries.append({"text": msgs["stop_decel"].format(name_josa=b_josa, name=b["name"]), "effects": [{"type": "stop", "target": "b"}]})
            winner = "a"
            break

    log_entries.append({"text": msgs["separator"], "effects": []})
    log_entries.append({"text": "", "effects": []})

    final_turn = turn if turn else MAX_TURNS

    if winner == "draw":
        log_entries.append({
            "text": msgs["battle_end_draw"].format(turns=final_turn),
            "effects": [{"type": "battle_end", "winner": "draw", "turns": final_turn}],
        })
    elif turn == MAX_TURNS and winner is None:
        winner = "draw"
        log_entries.append({
            "text": msgs["battle_end_draw"].format(turns=MAX_TURNS),
            "effects": [{"type": "battle_end", "winner": "draw", "turns": MAX_TURNS}],
        })
    else:
        winner_name = a["name"] if winner == "a" else b["name"]
        log_entries.append({
            "text": msgs["battle_end_win"].format(winner=winner_name, turns=turn),
            "effects": [{"type": "battle_end", "winner": winner, "turns": turn}],
        })

    return log_entries


def simulate_text(hash_a, hash_b, rng, name_a="A", name_b="B", lang="ko", weather=None, city_name=None):
    entries = simulate(hash_a, hash_b, rng, name_a, name_b, lang=lang, weather=weather, city_name=city_name)
    return "\n".join(e["text"] for e in entries)