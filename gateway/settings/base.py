from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
DEFAULT_ALLOWED_HOSTS = "localhost,127.0.0.1,web"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).split(",") if host.strip()]
for internal_host in ["web"]:
    if internal_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(internal_host)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mailer",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gateway.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "gateway.wsgi.application"

LANGUAGE_CODE = "es-ar"
TIME_ZONE = os.getenv("TZ", "America/Buenos_Aires")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_GATEWAY_CONFIG = os.getenv("EMAIL_GATEWAY_CONFIG", str(BASE_DIR / "config.yml"))
EMAIL_GATEWAY_API_KEY = os.getenv("EMAIL_GATEWAY_API_KEY", "")
EMAIL_GATEWAY_WORKER_SLEEP_SECONDS = float(os.getenv("EMAIL_GATEWAY_WORKER_SLEEP_SECONDS", "2"))
EMAIL_GATEWAY_INLINE_WORKER_ENABLED = os.getenv("EMAIL_GATEWAY_INLINE_WORKER_ENABLED", "true").lower() == "true"
EMAIL_GATEWAY_INLINE_WORKER_START_DELAY_SECONDS = float(os.getenv("EMAIL_GATEWAY_INLINE_WORKER_START_DELAY_SECONDS", "1"))
EMAIL_GATEWAY_BATCH_SIZE = int(os.getenv("EMAIL_GATEWAY_BATCH_SIZE", "10"))
EMAIL_GATEWAY_PROCESSING_TIMEOUT_SECONDS = int(os.getenv("EMAIL_GATEWAY_PROCESSING_TIMEOUT_SECONDS", "600"))
