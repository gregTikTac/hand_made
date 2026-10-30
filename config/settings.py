"""
Django settings — магазин PDF-мастер-классов.
Большинство значений берутся из переменных окружения (.env).
"""

from pathlib import Path

from dotenv import load_dotenv

from config.env import env

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SITE_NAME = env("SITE_NAME", default="Петелька")
ADMIN_URL = env("ADMIN_URL", default="admin/")

# Contact links (moved to SiteSettings in stage 7). Empty value = link is hidden.
SUPPORT_URL = env("SUPPORT_URL", default="")
VK_URL = env("VK_URL", default="")
TELEGRAM_URL = env("TELEGRAM_URL", default="")
INSTAGRAM_URL = env("INSTAGRAM_URL", default="")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "storages",
    "django_celery_beat",
    "import_export",
    # project apps
    "core",
    "catalog",
    "orders",
    "payments",
    "delivery",
    "promo",
    "pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db_url("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# Private files (purchased PDFs) are never served directly: only via presigned URLs / views.
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

# Two storages (see ARCHITECTURE: public bucket for photos, private bucket for PDFs):
#   "default" — public media (product photos), "private" — PDF files.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(PRIVATE_MEDIA_ROOT)},
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
if STORAGE_BACKEND == "s3":
    _s3_common = {
        "access_key": env("AWS_ACCESS_KEY_ID"),
        "secret_key": env("AWS_SECRET_ACCESS_KEY"),
        "region_name": env("AWS_S3_REGION_NAME", default="ru-central1"),
        "endpoint_url": env("AWS_S3_ENDPOINT_URL"),
        "signature_version": "s3v4",
        "file_overwrite": False,
    }
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": env("AWS_STORAGE_BUCKET_NAME"),
            "custom_domain": env("AWS_S3_CUSTOM_DOMAIN", default="") or None,
            "querystring_auth": False,
            "default_acl": "public-read",
        },
    }
    STORAGES["private"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": env("AWS_PRIVATE_BUCKET_NAME"),
            "endpoint_url": env("AWS_PRIVATE_ENDPOINT_URL") or env("AWS_S3_ENDPOINT_URL"),
            "querystring_auth": True,
            "querystring_expire": env.int("PRIVATE_URL_EXPIRE_SECONDS", default=300),
            "default_acl": "private",
        },
    }

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="dev@example.com")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = f"/{ADMIN_URL}"

# django-unfold admin theme (ADR-0001)
UNFOLD = {
    "SITE_TITLE": SITE_NAME,
    "SITE_HEADER": f"{SITE_NAME} — админка",
}
