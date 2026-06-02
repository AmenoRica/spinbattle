#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
URL_TARGET="http://127.0.0.1:${PORT}"
FORCE_HOST_SUFFIX=".trycloudflare.com"
FORCE_CSRF_ORIGIN="https://*.trycloudflare.com"

cd "$ROOT_DIR"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared가 설치되어 있지 않습니다."
  echo "macOS: brew install cloudflare/cloudflare/cloudflared"
  exit 1
fi

append_csv_if_missing() {
  local csv="$1"
  local value="$2"
  if [ -z "$csv" ]; then
    echo "$value"
    return
  fi
  case ",$csv," in
    *",$value,"*) echo "$csv" ;;
    *) echo "$csv,$value" ;;
  esac
}

export DEBUG=False
export ALLOWED_HOSTS="$(append_csv_if_missing "${ALLOWED_HOSTS:-127.0.0.1,localhost}" "$FORCE_HOST_SUFFIX")"
export CSRF_TRUSTED_ORIGINS="$(append_csv_if_missing "${CSRF_TRUSTED_ORIGINS:-http://127.0.0.1:${PORT},http://localhost:${PORT}}" "$FORCE_CSRF_ORIGIN")"

python manage.py check >/dev/null

ISSUE_TEMP_ADMIN_PASSWORD="${ISSUE_TEMP_ADMIN_PASSWORD:-1}"
if [ "$ISSUE_TEMP_ADMIN_PASSWORD" = "1" ]; then
  ADMIN_USERNAME="${ADMIN_USERNAME:-}"
  TEMP_ADMIN_PASSWORD="$(python -c "import secrets,string; chars=string.ascii_letters+string.digits+'!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(20)))")"
  ADMIN_RESET_RESULT="$(TEMP_ADMIN_PASSWORD="$TEMP_ADMIN_PASSWORD" ADMIN_USERNAME="$ADMIN_USERNAME" python manage.py shell -c "import os; from django.contrib.auth import get_user_model; U=get_user_model(); username=(os.environ.get('ADMIN_USERNAME') or '').strip(); user=None; user = U.objects.filter(username=username, is_superuser=True).first() if username else U.objects.filter(is_superuser=True).order_by('id').first(); print('NO_SUPERUSER' if user is None else user.username); user.set_password(os.environ['TEMP_ADMIN_PASSWORD']) if user else None; user.save(update_fields=['password']) if user else None" | tr -d '\r\n')"
  if [ "$ADMIN_RESET_RESULT" = "NO_SUPERUSER" ]; then
    echo "슈퍼유저가 없어 임시 비밀번호를 발급하지 않았습니다. 필요하면 createsuperuser를 먼저 실행하세요."
  else
    echo "임시 관리자 비밀번호 발급: username=${ADMIN_RESET_RESULT} password=${TEMP_ADMIN_PASSWORD}"
  fi
fi

python manage.py runserver "${HOST}:${PORT}" --noreload &
DJANGO_PID=$!

cleanup() {
  if kill -0 "$DJANGO_PID" >/dev/null 2>&1; then
    kill "$DJANGO_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

sleep 1
echo "Django 서버: http://127.0.0.1:${PORT}"
echo "터널 URL은 아래 cloudflared 출력에서 확인하세요."
cloudflared tunnel --url "$URL_TARGET"
