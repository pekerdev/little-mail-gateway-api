import os

from .base import *  # noqa: F403


DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "mail_gateway"),
        "USER": os.getenv("POSTGRES_USER", "mail_gateway"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "mail_gateway"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
