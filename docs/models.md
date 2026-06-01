# SpinBattle 모델 구조 및 데이터 흐름

## 1. 데이터베이스 모델

### CustomUser (`accounts/models.py`)

`AbstractUser`를 상속하는 커스텀 유저 모델.

| 필드 | 타입 | 설명 |
|---|---|---|
| `username` | CharField | Django 기본 제공 — 로그인 ID |
| `password` | CharField | Django 기본 제공 — 해시된 비밀번호 |
| `email` | EmailField | Django 기본 제공 |
| `bio` | TextField | 자기소개 (선택) |

---

### SpinImage (`accounts/models.py`)

사용자가 업로드한 팽이 이미지. 업로드 시 `hash`와 `spin_type`이 자동 계산됨.

| 필드 | 타입 | 설명 |
|---|---|---|
| `user` | FK → CustomUser | 소유자 (`related_name="spin_images"`) |
| `name` | CharField(30) | 팽이 이름 (사용자 입력) |
| `image` | ImageField | 업로드된 이미지 (`spins/%Y/%m/%d/`) |
| `hash` | CharField(64, unique) | 이미지 바이트의 SHA-256 해시 (자동 생성, 수정 불가) |
| `spin_type` | CharField(10) | 이미지 색상 분석으로 결정된 타입 (자동 생성, 수정 불가) |
| `wins` | PositiveIntegerField | 랭크 대전 승리 수 (기본값 0) |
| `losses` | PositiveIntegerField | 랭크 대전 패배 수 (기본값 0) |
| `battle_score` | IntegerField | ELO 랭킹 점수 (기본값 1000) |
| `uploaded_at` | DateTimeField | 업로드 시각 (auto_now_add) |

**제약 조건:**
- 사용자당 최대 3개 (`MAX_PER_USER = 3`)
- 이미지 크기 최대 5MB (`MAX_SIZE_BYTES = 5 * 1024 * 1024`)
- `hash`는 unique — 같은 이미지 중복 업로드 불가

**`save()` 자동 처리:**
1. `hash`가 없으면 이미지 바이트를 SHA-256 해시하여 저장
2. `spin_type`가 없으면 `battle.types.compute_type_from_image()`로 색상 분석 후 저장

**`clean()` 검증:**
1. 이미지 크기 > 5MB → ValidationError
2. 사용자당 업로드 수 ≥ 3 → ValidationError

---

## 2. 스탯 시스템 (`battle/stats.py`)

이미지의 SHA-256 해시를 6등분하여 각 스탯 값을 도출한다.

### 스탯 종류

| 스탯 | 한국어 | 범위 | 설명 |
|---|---|---|---|
| speed | 초기 속도 | 10–100 | 팽이의 초기 회전 속도 |
| acceleration | 가속도 | 10–100 | 회전 가속도 |
| luck | 행운 | 10–100 | 특수한 효과가 일어날 확률 |
| stamina | 지구력 | 10–100 | 회전 지속 시간 |
| attack | 공격력 | 10–100 | 충돌 시 데미지 |
| defense | 방어력 | 10–100 | 충돌 시 피해 감소 |

### 계산 방식

```
hash = SHA-256(이미지 바이트)  # 64자리 16진수 문자열
chunk_size = 64 // 6 = 10  # 각 스탯에 10자리 할당

for i, key in enumerate(STAT_KEYS):
    chunk = hash[i*10 : (i+1)*10]    # 10자리 16진수
    value = int(chunk, 16)           # 정수 변환
    stat = 10 + (value % 91)         # [10, 100] 범위 매핑
```

**특징:** 같은 이미지 → 같은 해시 → 같은 스탯. 이미지가 다르면 스탯도 다름.

### 등급 시스템

| 등급 | 최소값 |
|---|---|
| S+ | 93 |
| S | 86 |
| S- | 79 |
| A+ | 72 |
| A | 65 |
| A- | 58 |
| B+ | 51 |
| B | 44 |
| B- | 37 |
| C+ | 30 |
| C | 23 |
| C- | 10 |

**등급 색상:** S=금색(`#fbbf24`), A=빨강(`#ef4444`), B=파랑(`#3b82f6`), C=회색(`#6b7280`)

---

## 3. 타입 시스템 (`battle/types.py`)

### 10가지 타입

| 키 | 한국어 | 색상 |
|---|---|---|
| fire | 불꽃 | `#F08030` |
| water | 물 | `#6890F0` |
| grass | 풀 | `#78C850` |
| electric | 전기 | `#F8D030` |
| ice | 얼음 | `#98D8D8` |
| steel | 강철 | `#B8B8D0` |
| dragon | 드래곤 | `#7038F8` |
| dark | 악 | `#705848` |
| psychic | 에스퍼 | `#F85888` |
| fighting | 격투 | `#C03028` |

### 타입 판정 로직

이미지를 50×50으로 축소 후 평균 RGB → HSV 변환:

1. 명도(V) < 0.15 → **dark**
2. 채도(S) < 0.06 → 명도 > 0.75이면 **ice**, 아니면 **steel**
3. 색상(H) 기반 매핑:
   - 0–15°, 340–360° → fire
   - 15–40° → fighting
   - 40–75° → electric
   - 75–160° → grass
   - 160–200° → ice
   - 200–260° → water
   - 260–300° → dragon
   - 300–340° → psychic

### 상성 시스템

유리한 속성에 대해 **1.2배**, 불리한 속성에 대해 **0.833배** (`1/1.2`), 나머지 **1.0배**.

```
fire      → grass, ice 에 유리
water     → fire, steel 에 유리
grass     → water, electric 에 유리
electric  → water, ice 에 유리
ice       → grass, dragon 에 유리
steel     → ice, dark 에 유리
dragon    → psychic, electric 에 유리
dark      → psychic, dragon 에 유리
psychic   → fighting, fire 에 유리
fighting  → steel, dark 에 유리
```

반대로, 방어자가 공격자에게 유리한 속성이면 공격자는 불리(0.833배) 처리.

---

## 4. 대전 엔진 (`battle/engine.py`)

### 시뮬레이션 흐름

`simulate(hash_a, hash_b, rng, name_a, name_b, type_a, type_b, lang)` → `list[dict]`

각 항목: `{"text": "한국어 로그", "effects": [{type, target, ...}]}`

### 턴 구조 (최대 25턴)

1. **가속 이벤트** — 각 팽이마다 `15% + luck * 0.55%` 확률로 가속 성공
   - 성공 시: `speed += 5.0 × √(acceleration)`
   - `max_speed` 갱신
2. **속도 우선권** — `speed ± luck × 0.5` 랜덤 범위로 선공 결정
3. **공격 페이즈** — 선공 → 후공 순서
   - 선공 팽이가 후공 팽이를 공격
   - 후공 팽이가 살아있으면 반격
4. **속도 ≤ 0 확인** — 팽이가 멈추면 즉시 승패 판정
5. **랜덤 이벤트** — `5% + luck × 0.25%` 확률로 발생
   - 행운이 높을수록 긍정 이벤트 확률 ↑
   - 긍정 이벤트: dragon_dance(속도 회복), sword_dance(공격 증가), reflect(방어 증가), oran_berry(속도 회복), focus_band(버티기)
   - 부정 이벤트: wilt(속도 감소), confusion(공격 감소), poison(속도 감소), weathering(방어 감소)
6. **감속** — 매 턴마다 속도 감소
   - `감속량 = 3.0 × (100 / stamina) × (1 + (turn-1) × 0.08)`
   - 지구력이 높을수록 감속량 ↓, 턴이 지날수록 감속량 ↑

### 데미지 공식

```
base_damage = (speed × attack) / 500.0
crit_multiplier = 1.5 + acceleration / 200  (치명타 시)
type_multiplier = 1.2 / 0.833 / 1.0         (상성에 따라)
defense_reduction = defense / (defense + 100)
final_damage = base_damage × crit_multiplier × type_multiplier × (1 - defense_reduction)
```

### 치명타

- 발생 확률: `5% + luck × 0.30%`
- 치명타 배율: `1.5 + acceleration / 200`

### 버티기 (Endure)

- focus_band 이벤트로 발동
- 속도가 0 이하가 되면 `ENDURE_THRESHOLD`까지 복구
- 1회 대전에서 1회만 발동 가능

---

## 5. ELO 레이팅 (`battle/rating.py`)

표준 ELO 시스템, K-팩터 = 32.

```
E_A = 1 / (1 + 10^((R_B - R_A) / 400))

A 승리: S_A = 1.0, S_B = 0.0
B 승리: S_A = 0.0, S_B = 1.0
무승부: S_A = 0.5, S_B = 0.5

R'_A = R_A + 32 × (S_A - E_A)
R'_B = R_B + 32 × (S_B - E_B)
```

랭크 대전 종료 시 `SpinImage.battle_score`, `wins`, `losses` 업데이트.

---

## 6. 전체 데이터 흐름

```
이미지 업로드
    │
    ▼
SpinImage.save()
    ├── hash = SHA-256(이미지 바이트)
    ├── spin_type = compute_type_from_image(image)
    │       └── 평균 RGB → HSV → 색상 기반 타입 판정
    └── 저장
    │
    ▼
대전 요청 (POST)
    │
    ▼
simulate(hash_a, hash_b, rng, name_a, name_b, type_a, type_b)
    ├── compute_stats(hash_a) → 스탯 A
    ├── compute_stats(hash_b) → 스탯 B
    └── 턴 시뮬레이션 → log_entries 반환
    │
    ▼
localStorage(JSON) → /battle/ 페이지에서 BattleReplay 재생
    │
    ▼ (랭크 대전인 경우)
compute_new_ratings(score_a, score_b, result)
    └── SpinImage.battle_score, wins, losses 업데이트
```