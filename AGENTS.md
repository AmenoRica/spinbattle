# AGENTS.md — SpinBattle Project Guide

## Overview

SpinBattle is a web game where users upload images that become spinning tops (팽이) with auto-generated stats, types, and battle mechanics. Built with Django 5.x backend, Tailwind CSS (CDN) frontend, and pure JavaScript.

Language: **Korean** (all UI text, log messages, error messages are in Korean)

---

## Project Structure

```
spinbattle/
├── manage.py
├── requirements.txt
├── .env                          # SECRET_KEY, DEBUG (gitignored)
├── .gitignore
│
├── spinbattle/                   # Django project config
│   ├── settings.py               # Loads .env via python-dotenv
│   ├── urls.py                   # Root URL routing
│   ├── wsgi.py / asgi.py
│
├── weather/                    # Weather API (pure Python, no Django dependency)
│   ├── api.py                  # Open-Meteo integration (30-min cache)
│   └── cities.py               # 20 cities list
│
├── accounts/                     # ONLY Django app — users + spin images
│   ├── models.py                 # CustomUser (AbstractUser + bio + is_hidden), SpinImage
│   ├── views.py                  # All views (function-based)
│   ├── forms.py                  # 5 forms: creation, change, upload, rename, bulk upload
│   ├── admin.py                  # CustomUserAdmin + SpinImageAdmin + bulk upload action
│   ├── urls.py                   # All app URL patterns
│   ├── management/commands/      # migrate_media_to_r2 command
│   └── migrations/               # 8 migrations to date
│
├── battle/                       # Pure Python package — NOT a Django app
│   ├── engine.py                 # simulate() → list[dict] with text + effects
│   ├── rating.py                 # ELO rating: compute_new_ratings(), expected_score()
│   ├── stats.py                  # compute_stats(hash) → 6 stats, grades, colors
│   ├── types.py                  # 10 types, type advantages, image→type analysis
│   ├── weather.py                # Weather type/effect constants
│   ├── messages.py                # Battle messages (3 languages)
│   ├── events.py                 # Random event data
│   └── josa.py                   # Korean particle helper
│
├── templates/                    # Project-level templates directory
│   ├── base.html                 # Master layout (nav, footer, Tailwind CDN)
│   ├── home.html
│   ├── user_list.html
│   ├── ranking.html              # All spins ranked by battle_score
│   ├── spin_detail.html          # Hex stat radar + battle modal + city select
│   ├── battle_friendly.html      # STANDALONE — does NOT extend base.html
│   ├── accounts/                 # my_spins (profile + upload + spin list)
│   └── registration/             # login (Django auth)
│
├── static/js/                    # Vanilla JS (IIFE module pattern)
│   ├── battle-sound.js           # Web Audio API synthesizer
│   ├── battle-effects.js         # CSS animation controller
│   └── battle.js                 # BattleReplay: play/pause/skip/speed
│
└── media/                        # User uploads (gitignored)
```

---

## Key Architecture Decisions

- **Single Django app**: Only `accounts` is in `INSTALLED_APPS`. The `battle/` package is pure Python business logic with no Django dependency.
- **Custom User Model**: `AUTH_USER_MODEL = "accounts.CustomUser"` — always use this, never `auth.User`.
- **Templates at project root**: `TEMPLATES[0]['DIRS'] = [BASE_DIR / "templates"]`, not inside app directories.
- **Tailwind CDN only**: No build step, no `tailwind.config.js`, no `package.json`.
- **No JS framework**: All frontend is vanilla JS using IIFE revealing module pattern (`const Module = (() => { ... return {}; })()`).
- **Battle data via localStorage**: Battle sends POST → JSON response → `localStorage` → navigate to battle page → JS reads `localStorage` and replays. Both friendly and ranked battles use the same battle page.
- **ELO rating**: Standard ELO with K=32. Ranked battles update `wins`, `losses`, `battle_score` on both spins.
- **Matchmaking**: Ranked battles use score-proximity weighted random selection from all other users' spins.
- **Media storage**: Supports local media and Cloudflare R2 (S3-compatible) via `USE_R2_STORAGE` toggle.

---

## Models

### CustomUser (accounts/models.py)
- Extends `AbstractUser`
- Extra fields: `bio` (TextField, blank=True), `is_hidden` (BooleanField, default=False)

### SpinImage (accounts/models.py)
- `user` → FK to CustomUser (related_name=`spin_images`)
- `name` → CharField(max_length=30, required)
- `image` → ImageField(upload_to="spins/%Y/%m/%d/", 5MB limit)
- `hash` → CharField(64, unique, editable=False) — SHA-256 of image bytes, auto-computed on save
- `spin_type` → CharField(10, editable=False) — auto-computed from image color analysis
- `wins`, `losses` → PositiveIntegerField(default=0) — updated by ranked battles
- `battle_score` → IntegerField(default=1000) — ELO rating, updated by ranked battles
- Constants: `MAX_PER_USER = 5`, `MAX_SIZE_BYTES = 5MB`
- `save()` auto-computes `hash` and `spin_type` if not set
- `clean()` validates image size and per-user count limit

---

## Battle System (battle/ package)

### Stats (battle/stats.py)
- 6 stats derived from SHA-256 hash: speed, acceleration, luck, stamina, attack, defense
- `compute_stats(hash_str)` → dict with values in range [10, 100]
- Grade system: S+/S/S- → A+/A/A- → B+/B/B- → C+/C/C-
- Grade colors: S=gold(#fbbf24), A=red(#ef4444), B=blue(#3b82f6), C=gray(#6b7280)

### Types (battle/types.py)
- 10 types: fire, water, grass, electric, ice, steel, dragon, dark, psychic, fighting
- Each type has Korean `name` and `color` (hex)
- `compute_type_from_image(image_field)` — analyzes average RGB → HSV → maps hue to type
- `get_type_multiplier(atk_type, def_type)` — returns 1.2 (advantage), ~0.833 (disadvantage), or 1.0

### Engine (battle/engine.py)
- `simulate(hash_a, hash_b, rng, name_a, name_b, type_a=None, type_b=None)` → `list[dict]`
- Each entry: `{"text": "Korean log line", "effects": [{type, target, ...}]}`
- **RNG must be passed in** — `random.Random` instance for reproducibility
- `simulate_text()` — convenience wrapper returning plain text log

### Rating (battle/rating.py)
- `expected_score(rating_a, rating_b)` → float [0, 1]
- `compute_new_ratings(rating_a, rating_b, result)` → (new_a, new_b)
- `result`: `"a"` (A wins), `"b"` (B wins), `"draw"` — standard ELO with K=32

**Turn order:**
1. Acceleration event (luck-scaled probability)
2. Speed priority check: `speed × 0.6 + attack × 0.25 + defense × 0.15 ± luck × 0.3`
3. Attack phase (first striker → counter-attack if alive)
4. Speed ≤ 0 check
5. Random events (positive/negative, luck-weighted)
6. Weather events (rain influx, snowstorm)
7. End-of-turn deceleration (stamina-scaled, growing with turn number, defense reduces)

**Damage formula:**
```
base_damage = attack × 0.18 + speed × 0.02
initial_speed = speed + defense × 0.4
defense_reduction = defense / (defense + 35)
priority = speed × 0.6 + attack × 0.25 + defense × 0.15 ± luck × 0.3
decel = 4.0 × (80 / stamina) × growth × defense_factor
defense_factor = max(1 - defense × 0.008, 0.3)
growth = 1 + (turn - 1) × 0.08
Turns 26-30: decel × 2; Turns 31+: decel × 4 (cumulative: ×2 then ×2)
Max turns: 35
```

**All balance constants** are at the top of `engine.py` with comments — easy to tune.

**Korean particle helper:** `_josa(name, ("은","는"))` auto-selects correct particle based on final consonant.

---

## URL Names

| Pattern | Name | Notes |
|---|---|---|
| `/` | `home` | TemplateView |
| `/accounts/signup/` | `signup` | Custom registration view |
| `/accounts/login/` | `login` | Django built-in auth |
| `/accounts/logout/` | `logout` | Django built-in auth |
| `/accounts/my-spins/` | `my_spins` | Login required, profile + upload + spin list |
| `/accounts/my-spins/preview/` | `upload_preview` | POST JSON, stat preview before upload |
| `/accounts/images/<pk>/delete/` | `delete_image` | POST only, owner only |
| `/accounts/images/<pk>/rename/` | `rename_image` | POST only, owner only |
| `/accounts/users/` | `user_list` | Public, sorted by total score |
| `/accounts/ranking/` | `ranking` | Public, all spins ranked by battle_score |
| `/accounts/spins/<pk>/` | `spin_detail` | Public, hex radar + battle + city select |
| `/accounts/friendly-battle/` | `friendly_battle` | POST, JSON, supports city param |
| `/accounts/ranked-battle/` | `ranked_battle` | POST, JSON, updates ELO |
| `/battle/` | `battle_friendly` | TemplateView, reads localStorage (both modes) |
| `/admin/` | — | Django admin |

---

## Frontend Patterns

### Templates
- All pages except `battle_friendly.html` extend `base.html`
- `base.html` provides: nav bar (auth-aware), `{% block title %}`, `{% block content %}`, footer
- Dark theme: `bg-gray-900` body, `bg-gray-800` cards, `text-indigo-400` accents
- Battle page is standalone (custom CSS animations, full-screen layout)

### JavaScript Modules (load order matters)
1. `battle-sound.js` — `BattleSound` IIFE: Web Audio API, toggle on/off
2. `battle-effects.js` — `BattleEffects` IIFE: DOM animations (spin speed, sparks, slashes, float text, wobble)
3. `battle.js` — `BattleReplay` IIFE: playback controller (init/play/pause/skip/restart/setSpeed), auto-acceleration, weather countdown

### Battle Page Flow
1. `spin_detail.html`: "친선 대전" or "랭크 대전" button → select spin → POST via fetch → JSON → localStorage → navigate to `/battle/`
2. `battle_friendly.html`: On DOMContentLoaded, read `localStorage('battle_data')`, init `BattleReplay`
3. Ranked battles: JSON includes `mode: "ranked"`, `old_score`, `new_score` per spin — shown on battle end
4. Friendly battles: city selector on `spin_detail.html` modal, POST includes `city` param
5. Spin discs rotate via CSS `animation: spin var(--spin-duration) linear infinite` — speed adjusted by changing `--spin-duration`
6. Stop animation: `wobbleStop` keyframe (wobble → tilt → grayscale)
7. Log auto-scrolls: `el.scrollTop = el.scrollHeight` after each line
8. Auto-acceleration: replay speed increases as entries progress (1 + currentIndex/80, max 3x)
9. Default playback speed: 5x; available speeds: 1x, 3x, 5x, 10x, 15x

---

## Conventions

- **Models**: snake_case fields, FK as singular (`user`), related_name as plural (`spin_images`)
- **Views**: Function-based only. Login-required views use `@login_required` decorator.
- **Forms**: ModelForm for all model forms. Widget customization in `Meta.widgets`.
- **URLs**: kebab-case paths (`friendly-battle/`), snake_case names (`friendly_battle`)
- **Templates**: `accounts/<page>.html` for account pages, root-level for project pages
- **Korean text**: All user-facing text is Korean. Use `_josa()` helper for correct particles.
- **No comments in code**: Do not add comments unless explicitly asked.
- **No tests yet**: `accounts/tests.py` is empty. When adding tests, use Django's `TestCase`.
- **No REST framework**: Use `JsonResponse` directly for any API endpoints.
- **Placement matches**: New spins automatically play 10 ranked placement matches (`PLACEMENT_ROUNDS = 10` in `accounts/views.py`). Results shown via JS modal on upload.
- **Static file cache busting**: When modifying any file in `static/js/` or `static/css/`, you **MUST** increment the version number in the corresponding `{% static %}` tag in the template that references it.
- **File deletion policy**: Never delete files with `rm`/`unlink`/destructive git checkout. If deletion is required, move targets to Trash only (for example `mv <path> ~/.Trash/` on macOS).

---

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python manage.py migrate
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# R2 migration
python manage.py migrate_media_to_r2 --dry-run
python manage.py migrate_media_to_r2

# Type computation for existing images (manual)
python -c "
import django; import os
os.environ['DJANGO_SETTINGS_MODULE']='spinbattle.settings'; django.setup()
from accounts.models import SpinImage
from battle.types import compute_type_from_image
for si in SpinImage.objects.all():
    si.spin_type = compute_type_from_image(si.image)
    SpinImage.objects.filter(pk=si.pk).update(spin_type=si.spin_type)
"
```

---

## Known Gaps

- No tests
- R2 key/endpoint provisioning issues may temporarily block uploads until Cloudflare side recovers
