import hashlib
import math
import random

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import get_language, gettext as _

from battle.engine import simulate
from battle.rating import compute_new_ratings
from battle.stats import compute_stats, get_grade, get_grade_color, get_stat_names, STAT_KEYS
from battle.types import SPIN_TYPES, compute_type_from_image, get_type_name
from battle.weather import get_weather_name, get_weather_icon

from weather.cities import random_city
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
def profile(request):
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = CustomUserChangeForm(instance=request.user)
    spin_images = request.user.spin_images.all()
    return render(request, "accounts/profile.html", {"form": form, "spin_images": spin_images})


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
def upload_image(request):
    if request.method == "POST":
        form = SpinImageForm(request.POST, request.FILES)
        if form.is_valid():
            spin_image = form.save(commit=False)
            spin_image.user = request.user
            try:
                spin_image.full_clean()
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
                return render(request, "accounts/upload.html", {"form": form, "spin_images": request.user.spin_images.all()})

            if spin_image.image:
                spin_image.image.seek(0)
                file_hash = hashlib.sha256(spin_image.image.read()).hexdigest()
                spin_image.image.seek(0)
                if SpinImage.objects.filter(hash=file_hash).exists():
                    form.add_error("image", _("이미 같은 이미지를 업로드한 유저가 있습니다!"))
                    return render(request, "accounts/upload.html", {"form": form, "spin_images": request.user.spin_images.all()})

            spin_image.save()
            return redirect("upload_image")
    else:
        form = SpinImageForm()
    spin_images = request.user.spin_images.all()
    return render(request, "accounts/upload.html", {"form": form, "spin_images": spin_images})


@login_required
def delete_image(request, pk):
    spin_image = get_object_or_404(SpinImage, pk=pk, user=request.user)
    if request.method == "POST":
        spin_image.delete()
    return redirect("upload_image")


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
    ).order_by("-total_score")
    return render(request, "user_list.html", {"users": users})


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
    my_spin = get_object_or_404(SpinImage, pk=my_pk, user=request.user)
    opp_spin = get_object_or_404(SpinImage, pk=opp_pk)

    if my_spin.pk == opp_spin.pk:
        return JsonResponse({"error": "같은 팽이끼리는 대전할 수 없습니다."}, status=400)

    lang = get_language() or "ko"
    rng = random.Random()
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
