import math
import random

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from battle.engine import simulate
from battle.stats import compute_stats, get_grade, get_grade_color, STAT_NAMES, STAT_KEYS
from battle.types import SPIN_TYPES

from .forms import CustomUserChangeForm, CustomUserCreationForm, SpinImageForm, SpinImageRenameForm
from .models import CustomUser, SpinImage


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
def upload_image(request):
    if request.method == "POST":
        form = SpinImageForm(request.POST, request.FILES)
        if form.is_valid():
            spin_image = form.save(commit=False)
            spin_image.user = request.user
            try:
                spin_image.full_clean()
                spin_image.save()
                return redirect("upload_image")
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
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
    users = CustomUser.objects.prefetch_related(
        Prefetch("spin_images", queryset=SpinImage.objects.order_by("-uploaded_at"))
    ).annotate(
        total_score=Coalesce(Sum("spin_images__battle_score"), 0)
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
    stats = compute_stats(spin_image.hash)
    stat_detail = []
    for key in STAT_KEYS:
        value = stats[key]
        stat_detail.append({
            "key": key,
            "name": STAT_NAMES[key],
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
        labels.append({"x": f"{lx:.1f}", "y": f"{ly:.1f}", "name": STAT_NAMES[key], "value": stats[key]})

    spin_type_info = SPIN_TYPES.get(spin_image.spin_type, {})

    return render(request, "spin_detail.html", {
        "spin_image": spin_image,
        "stat_detail": stat_detail,
        "total": total,
        "grid_rings": grid_rings,
        "stat_polygon": stat_polygon,
        "spokes": spokes,
        "labels": labels,
        "spin_type_name": spin_type_info.get("name", ""),
        "spin_type_color": spin_type_info.get("color", "#888"),
    })


@login_required
def friendly_battle(request):
    my_pk = request.POST.get("my_spin")
    opp_pk = request.POST.get("opponent_spin")
    my_spin = get_object_or_404(SpinImage, pk=my_pk, user=request.user)
    opp_spin = get_object_or_404(SpinImage, pk=opp_pk)

    rng = random.Random()
    log = simulate(my_spin.hash, opp_spin.hash, rng, my_spin.name, opp_spin.name, my_spin.spin_type, opp_spin.spin_type)

    return JsonResponse({
        "spin_a": {
            "name": my_spin.name,
            "image_url": my_spin.image.url,
            "spin_type": my_spin.spin_type,
            "spin_type_name": SPIN_TYPES.get(my_spin.spin_type, {}).get("name", ""),
            "spin_type_color": SPIN_TYPES.get(my_spin.spin_type, {}).get("color", "#888"),
        },
        "spin_b": {
            "name": opp_spin.name,
            "image_url": opp_spin.image.url,
            "spin_type": opp_spin.spin_type,
            "spin_type_name": SPIN_TYPES.get(opp_spin.spin_type, {}).get("name", ""),
            "spin_type_color": SPIN_TYPES.get(opp_spin.spin_type, {}).get("color", "#888"),
        },
        "log": log,
    })
