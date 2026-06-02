import hashlib
import math
import random
import time

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import get_language, gettext as _
from django.utils import timezone

from battle.engine import simulate
from battle.rating import compute_new_ratings
from battle.stats import compute_stats, get_grade, get_grade_color, get_stat_names, STAT_KEYS
from battle.types import SPIN_TYPES, compute_type_from_image, get_type_name
from battle.weather import get_weather_name, get_weather_icon

from weather.cities import random_city, CITIES
from weather.api import get_weather_for_city

from .forms import CustomUserChangeForm, CustomUserCreationForm, SpinImageForm, SpinImageRenameForm
from .models import CustomUser, SpinImage


def rng_choice(queryset, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    acc = 0
    for obj, w in zip(queryset, weights):
        acc += w
        if r <= acc:
            return obj
    return queryset.last()


PLACEMENT_ROUNDS = 10
IP_UPLOAD_DAILY_LIMIT = 100
IP_UPLOAD_BLOCK_SECONDS = 86400


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "unknown").strip()


def _upload_limit_info(ip):
    blocked_key = f"upload_block:{ip}"
    blocked_until = cache.get(blocked_key)
    if blocked_until:
        return True, max(int(blocked_until - time.time()), 1)
    day_key = timezone.localdate().isoformat()
    count_key = f"upload_count:{ip}:{day_key}"
    uploaded_count = int(cache.get(count_key, 0))
    return uploaded_count >= IP_UPLOAD_DAILY_LIMIT, 0


def _increase_upload_count(ip):
    day_key = timezone.localdate().isoformat()
    count_key = f"upload_count:{ip}:{day_key}"
    added = cache.add(count_key, 1, timeout=IP_UPLOAD_BLOCK_SECONDS)
    if added:
        uploaded_count = 1
    else:
        try:
            uploaded_count = cache.incr(count_key)
        except ValueError:
            cache.set(count_key, 1, timeout=IP_UPLOAD_BLOCK_SECONDS)
            uploaded_count = 1
    if uploaded_count >= IP_UPLOAD_DAILY_LIMIT:
        blocked_until = time.time() + IP_UPLOAD_BLOCK_SECONDS
        cache.set(f"upload_block:{ip}", blocked_until, timeout=IP_UPLOAD_BLOCK_SECONDS)


def _run_placement(spin_image):
    candidate_list = list(SpinImage.objects.exclude(pk=spin_image.pk))
    if not candidate_list:
        return []
    rng = random.Random()
    weather = "normal"
    results = []
    my_score = spin_image.battle_score
    my_wins = spin_image.wins
    my_losses = spin_image.losses
    opp_state = {
        c.pk: {"score": c.battle_score, "wins": c.wins, "losses": c.losses}
        for c in candidate_list
    }
    for i in range(PLACEMENT_ROUNDS):
        weights = [1.0 / (1.0 + abs(opp_state[c.pk]["score"] - my_score) / 200.0) for c in candidate_list]
        opp = rng_choice(candidate_list, weights)
        log = simulate(spin_image.hash, opp.hash, rng, spin_image.name, opp.name, spin_image.spin_type, opp.spin_type, lang="ko", weather=weather, city_name="")

        last_effect = None
        for entry in log:
            for eff in entry.get("effects", []):
                if eff.get("type") == "battle_end":
                    last_effect = eff
        winner = last_effect.get("winner", "draw") if last_effect else "draw"

        old_a = my_score
        old_b = opp_state[opp.pk]["score"]

        win_a, loss_a = (1, 0) if winner == "a" else (0, 1) if winner == "b" else (0, 0)
        win_b, loss_b = (0, 1) if winner == "a" else (1, 0) if winner == "b" else (0, 0)

        new_a, new_b = compute_new_ratings(old_a, old_b, winner)
        SpinImage.objects.filter(pk=spin_image.pk).update(
            wins=my_wins + win_a, losses=my_losses + loss_a, battle_score=new_a
        )
        SpinImage.objects.filter(pk=opp.pk).update(
            wins=opp_state[opp.pk]["wins"] + win_b, losses=opp_state[opp.pk]["losses"] + loss_b, battle_score=new_b
        )
        my_score = new_a
        my_wins += win_a
        my_losses += loss_a
        opp_state[opp.pk]["score"] = new_b
        opp_state[opp.pk]["wins"] += win_b
        opp_state[opp.pk]["losses"] += loss_b

        results.append({
            "round": i + 1,
            "opp_name": opp.name,
            "opp_type": opp.spin_type,
            "result": "win" if winner == "a" else "loss" if winner == "b" else "draw",
            "old_score": old_a,
            "new_score": new_a,
        })
    spin_image.battle_score = my_score
    spin_image.wins = my_wins
    spin_image.losses = my_losses
    return results


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def my_spins(request):
    profile_form = CustomUserChangeForm(instance=request.user)
    upload_form = SpinImageForm()
    spin_images = request.user.spin_images.order_by("-battle_score")

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            profile_form = CustomUserChangeForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                return redirect("my_spins")

        elif form_type == "upload":
            client_ip = _client_ip(request)
            is_blocked, remain_seconds = _upload_limit_info(client_ip)
            if is_blocked:
                remain_hours = max(1, math.ceil(remain_seconds / 3600)) if remain_seconds else 24
                upload_form.add_error("image", _("업로드 한도를 초과했습니다. 약 %(hours)s시간 뒤 다시 시도해주세요.") % {"hours": remain_hours})
                return render(request, "accounts/my_spins.html", {"profile_form": profile_form, "form": upload_form, "spin_images": spin_images})
            upload_form = SpinImageForm(request.POST, request.FILES)
            if upload_form.is_valid():
                spin_image = upload_form.save(commit=False)
                spin_image.user = request.user
                try:
                    spin_image.full_clean()
                except ValidationError as e:
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            upload_form.add_error(field, error)
                    return render(request, "accounts/my_spins.html", {"profile_form": profile_form, "form": upload_form, "spin_images": spin_images})

                if spin_image.image:
                    spin_image.image.seek(0)
                    file_hash = hashlib.sha256(spin_image.image.read()).hexdigest()
                    spin_image.image.seek(0)
                    if SpinImage.objects.filter(hash=file_hash).exists():
                        upload_form.add_error("image", _("이미 같은 이미지를 업로드한 유저가 있습니다!"))
                        return render(request, "accounts/my_spins.html", {"profile_form": profile_form, "form": upload_form, "spin_images": spin_images})

                spin_image.save()
                _increase_upload_count(client_ip)
                placement_results = _run_placement(spin_image)
                return JsonResponse({
                    "placement_spin_name": spin_image.name,
                    "placement_results": placement_results,
                })

    return render(request, "accounts/my_spins.html", {"profile_form": profile_form, "form": upload_form, "spin_images": spin_images})


@login_required
def upload_preview(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    form = SpinImageForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = {}
        for field, errs in form.errors.items():
            errors[field] = errs
        return JsonResponse({"error": errors}, status=400)

    spin_image = form.save(commit=False)
    spin_image.user = request.user
    try:
        spin_image.full_clean()
    except ValidationError as e:
        errors = {}
        for field, errs in e.message_dict.items():
            errors[field] = errs
        return JsonResponse({"error": errors}, status=400)

    spin_image.image.seek(0)
    spin_image.hash = hashlib.sha256(spin_image.image.read()).hexdigest()
    spin_image.image.seek(0)
    spin_image.spin_type = compute_type_from_image(spin_image.image)
    spin_image.image.seek(0)

    existing_count = SpinImage.objects.filter(user=request.user).count()
    if existing_count >= SpinImage.MAX_PER_USER:
        return JsonResponse({"error": {"image": [_("이미지는 최대 %(count)s개까지 업로드할 수 있습니다.") % {"count": SpinImage.MAX_PER_USER}]}}, status=400)

    if SpinImage.objects.filter(hash=spin_image.hash).exists():
        return JsonResponse({"error": {"image": [_("이미 같은 이미지를 업로드한 유저가 있습니다!")]}}, status=400)

    lang = get_language() or "ko"
    stats = compute_stats(spin_image.hash)
    stat_names = get_stat_names(lang)
    stat_detail = []
    for key in STAT_KEYS:
        value = stats[key]
        grade = get_grade(value)
        stat_detail.append({
            "key": key,
            "name": stat_names[key],
            "value": value,
            "grade": grade,
            "grade_color": get_grade_color(grade),
        })

    type_info = SPIN_TYPES.get(spin_image.spin_type, {})
    type_name = get_type_name(spin_image.spin_type, lang)

    return JsonResponse({
        "name": spin_image.name,
        "spin_type": spin_image.spin_type,
        "spin_type_name": type_name,
        "spin_type_color": type_info.get("color", "#888"),
        "stats": stat_detail,
        "total": sum(stats.values()),
    })


@login_required
def delete_image(request, pk):
    spin_image = get_object_or_404(SpinImage, pk=pk, user=request.user)
    if request.method == "POST":
        spin_image.delete()
    return redirect("my_spins")


@login_required
def rename_image(request, pk):
    spin_image = get_object_or_404(SpinImage, pk=pk, user=request.user)
    if request.method == "POST":
        form = SpinImageRenameForm(request.POST, instance=spin_image)
        if form.is_valid():
            form.save()
    return redirect("spin_detail", pk=spin_image.pk)


def user_list(request):
    users = CustomUser.objects.filter(is_hidden=False).prefetch_related(
        Prefetch("spin_images", queryset=SpinImage.objects.order_by("-uploaded_at"))
    ).annotate(
        total_score=Coalesce(Sum("spin_images__battle_score"), 0),
        total_wins=Coalesce(Sum("spin_images__wins"), 0),
        total_losses=Coalesce(Sum("spin_images__losses"), 0),
        spin_count=Count("spin_images"),
    )
    for u in users:
        u.total_score += (SpinImage.MAX_PER_USER - u.spin_count) * 700
    users = sorted(users, key=lambda u: u.total_score, reverse=True)
    return render(request, "user_list.html", {"users": users})


def ranking(request):
    spins = SpinImage.objects.select_related("user").order_by("-battle_score")
    lang = get_language() or "ko"
    stat_keys_order = ["speed", "acceleration", "luck", "stamina", "attack", "defense"]
    spin_data = []
    for s in spins:
        stats = compute_stats(s.hash)
        grades = [(k, get_grade(stats[k]), get_grade_color(get_grade(stats[k]))) for k in stat_keys_order]
        type_info = SPIN_TYPES.get(s.spin_type, {})
        spin_data.append({
            "spin": s,
            "grades": grades,
            "type_name": get_type_name(s.spin_type, lang),
            "type_color": type_info.get("color", "#888"),
        })
    return render(request, "ranking.html", {"spin_data": spin_data, "stat_keys": stat_keys_order})


def _hex_point(cx, cy, r, i):
    angle = math.radians(-90 + i * 60)
    return (cx + r * math.cos(angle), cy + r * math.sin(angle))


def _hex_points_str(cx, cy, r):
    parts = []
    for i in range(6):
        x, y = _hex_point(cx, cy, r, i)
        parts.append(f"{x:.1f},{y:.1f}")
    return " ".join(parts)


def spin_detail(request, pk):
    spin_image = get_object_or_404(SpinImage, pk=pk)
    lang = get_language() or "ko"
    stats = compute_stats(spin_image.hash)
    stat_names = get_stat_names(lang)
    stat_detail = []
    for key in STAT_KEYS:
        value = stats[key]
        stat_detail.append({
            "key": key,
            "name": stat_names[key],
            "value": value,
            "grade": get_grade(value),
            "grade_color": get_grade_color(get_grade(value)),
        })
    total = sum(stats.values())

    cx, cy, max_r = 150, 150, 110
    grid_rings = [_hex_points_str(cx, cy, max_r * p) for p in (0.25, 0.5, 0.75, 1.0)]
    stat_values = [stats[k] / 100.0 for k in STAT_KEYS]
    stat_parts = []
    for i in range(6):
        x, y = _hex_point(cx, cy, max_r * stat_values[i], i)
        stat_parts.append(f"{x:.1f},{y:.1f}")
    stat_polygon = " ".join(stat_parts)

    spokes = []
    for i in range(6):
        x, y = _hex_point(cx, cy, max_r, i)
        spokes.append({"x2": f"{x:.1f}", "y2": f"{y:.1f}"})

    labels = []
    for i, key in enumerate(STAT_KEYS):
        lx, ly = _hex_point(cx, cy, max_r + 22, i)
        labels.append({"x": f"{lx:.1f}", "y": f"{ly:.1f}", "name": stat_names[key], "value": stats[key]})

    spin_type_info = SPIN_TYPES.get(spin_image.spin_type, {})
    type_name = get_type_name(spin_image.spin_type, lang)

    total_battles = spin_image.wins + spin_image.losses
    winrate = round(spin_image.wins / total_battles * 100) if total_battles > 0 else None

    return render(request, "spin_detail.html", {
        "spin_image": spin_image,
        "stat_detail": stat_detail,
        "total": total,
        "grid_rings": grid_rings,
        "stat_polygon": stat_polygon,
        "spokes": spokes,
        "labels": labels,
        "spin_type_name": type_name,
        "spin_type_color": spin_type_info.get("color", "#888"),
        "winrate": winrate,
        "cities": CITIES,
    })


def _spin_json(spin, lang):
    return {
        "name": spin.name,
        "image_url": spin.image.url,
        "spin_type": spin.spin_type,
        "spin_type_name": get_type_name(spin.spin_type, lang),
        "spin_type_color": SPIN_TYPES.get(spin.spin_type, {}).get("color", "#888"),
    }


def _build_battle_json(my_spin, opp_spin, log, mode, lang, old_score_a=None, new_score_a=None, old_score_b=None, new_score_b=None, weather=None, city=None):
    spin_a = _spin_json(my_spin, lang)
    spin_b = _spin_json(opp_spin, lang)
    result = {
        "mode": mode,
        "spin_a": spin_a,
        "spin_b": spin_b,
        "log": log,
    }
    if weather:
        result["weather"] = weather
        result["weather_name"] = get_weather_name(weather, lang)
        result["weather_icon"] = get_weather_icon(weather)
    if city:
        result["city"] = city
    if mode == "ranked":
        spin_a["old_score"] = old_score_a
        spin_a["new_score"] = new_score_a
        spin_b["old_score"] = old_score_b
        spin_b["new_score"] = new_score_b
        result["winner"] = "a" if new_score_a > old_score_a else ("b" if new_score_b > old_score_b else "draw")
    return result


@login_required
def friendly_battle(request):
    my_pk = request.POST.get("my_spin")
    opp_pk = request.POST.get("opponent_spin")
    city_key = request.POST.get("city", "")
    my_spin = get_object_or_404(SpinImage, pk=my_pk, user=request.user)
    opp_spin = get_object_or_404(SpinImage, pk=opp_pk)

    if my_spin.pk == opp_spin.pk:
        return JsonResponse({"error": "같은 팽이끼리는 대전할 수 없습니다."}, status=400)

    lang = get_language() or "ko"
    rng = random.Random()
    if city_key:
        city = next((c for c in CITIES if c["key"] == city_key), None)
        if city is None:
            city = random_city(rng)
    else:
        city = random_city(rng)
    weather = get_weather_for_city(city)
    city_name = city.get(f"name_{lang}", city.get("name_ko", ""))
    log = simulate(my_spin.hash, opp_spin.hash, rng, my_spin.name, opp_spin.name, my_spin.spin_type, opp_spin.spin_type, lang=lang, weather=weather, city_name=city_name)

    return JsonResponse(_build_battle_json(my_spin, opp_spin, log, "friendly", lang, weather=weather, city=city_name))


@login_required
def ranked_battle(request):
    my_pk = request.POST.get("my_spin")
    my_spin = get_object_or_404(SpinImage, pk=my_pk, user=request.user)

    candidates = SpinImage.objects.exclude(user=request.user)
    if not candidates.exists():
        return JsonResponse({"error": "대전 가능한 상대가 없습니다."}, status=400)

    weights = []
    for c in candidates:
        diff = abs(c.battle_score - my_spin.battle_score)
        weights.append(1.0 / (1.0 + diff / 200.0))

    opp_spin = rng_choice(candidates, weights)

    lang = get_language() or "ko"
    rng = random.Random()
    city = random_city(rng)
    weather = get_weather_for_city(city)
    city_name = city.get(f"name_{lang}", city.get("name_ko", ""))
    log = simulate(my_spin.hash, opp_spin.hash, rng, my_spin.name, opp_spin.name, my_spin.spin_type, opp_spin.spin_type, lang=lang, weather=weather, city_name=city_name)

    last_effect = None
    for entry in log:
        for eff in entry.get("effects", []):
            if eff.get("type") == "battle_end":
                last_effect = eff
    winner = last_effect.get("winner", "draw") if last_effect else "draw"

    old_score_a = my_spin.battle_score
    old_score_b = opp_spin.battle_score

    if winner == "a":
        my_spin.wins += 1
        opp_spin.losses += 1
    elif winner == "b":
        my_spin.losses += 1
        opp_spin.wins += 1

    new_a, new_b = compute_new_ratings(old_score_a, old_score_b, winner)
    my_spin.battle_score = new_a
    opp_spin.battle_score = new_b
    SpinImage.objects.filter(pk=my_spin.pk).update(
        wins=my_spin.wins, losses=my_spin.losses, battle_score=new_a
    )
    SpinImage.objects.filter(pk=opp_spin.pk).update(
        wins=opp_spin.wins, losses=opp_spin.losses, battle_score=new_b
    )

    return JsonResponse(_build_battle_json(my_spin, opp_spin, log, "ranked", lang, old_score_a, new_a, old_score_b, new_b, weather=weather, city=city_name))
