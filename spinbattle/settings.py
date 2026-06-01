import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "spinbattle.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "spinbattle.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.CustomUser"

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

LANGUAGE_CODE = "ko"

LANGUAGES = [
    ("ko", "한국어"),
    ("ja", "日本語"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

USE_R2_STORAGE = os.getenv("USE_R2_STORAGE", "False").lower() in ("true", "1", "yes")

if USE_R2_STORAGE:
    INSTALLED_APPS.append("storages")
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
    R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")
    R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")

    if not R2_ACCOUNT_ID:
        raise ImproperlyConfigured("R2_ACCOUNT_ID가 설정되지 않았습니다.")
    if not R2_BUCKET_NAME:
        raise ImproperlyConfigured("R2_BUCKET_NAME이 설정되지 않았습니다.")

    AWS_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise ImproperlyConfigured("R2_ACCESS_KEY_ID 또는 R2_SECRET_ACCESS_KEY가 설정되지 않았습니다.")
    AWS_STORAGE_BUCKET_NAME = R2_BUCKET_NAME
    AWS_S3_REGION_NAME = "auto"
    if R2_ENDPOINT_URL:
        parsed = urlparse(R2_ENDPOINT_URL)
        if not parsed.scheme or not parsed.netloc:
            raise ImproperlyConfigured("R2_ENDPOINT_URL 형식이 올바르지 않습니다. 예: https://<accountid>.r2.cloudflarestorage.com")
        AWS_S3_ENDPOINT_URL = f"{parsed.scheme}://{parsed.netloc}"
    else:
        AWS_S3_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    AWS_S3_ADDRESSING_STYLE = "path"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "region_name": AWS_S3_REGION_NAME,
                "default_acl": AWS_DEFAULT_ACL,
                "querystring_auth": AWS_QUERYSTRING_AUTH,
                "file_overwrite": AWS_S3_FILE_OVERWRITE,
                "custom_domain": R2_PUBLIC_URL.replace("https://", "").replace("http://", "") if R2_PUBLIC_URL else None,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    if R2_PUBLIC_URL:
        MEDIA_URL = f"{R2_PUBLIC_URL.rstrip('/')}/"

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
