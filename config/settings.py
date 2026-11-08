"""Settings from environment variables only. Safe defaults when DEBUG is off."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=""):
    return os.environ.get(name, default).strip()


def env_bool(name, default=False):
    return env(name, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [v.strip() for v in env(name, default).split(",") if v.strip()]


DEBUG = env_bool("DEBUG")
SECRET_KEY = env("SECRET_KEY") or ("dev-only-not-secret" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required when DEBUG is off")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = env("TIME_ZONE", "UTC")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "app"),
        "USER": env("DB_USER", "app"),
        "PASSWORD": env("DB_PASSWORD", "app"),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "55434"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # nginx serves this directory

# ---- Behind nginx, over HTTPS ---------------------------------------------------
if not DEBUG:
    # nginx terminates TLS and sets X-Forwarded-Proto. Only trust it because
    # gunicorn is reachable from nginx alone (see docker-compose.yml).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]  # checked over plain HTTP inside the network
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = env_bool("HSTS_PRELOAD", False)
    if not SECURE_HSTS_PRELOAD:
        # Preload is hard to undo, so it stays a deliberate choice, not a default.
        SILENCED_SYSTEM_CHECKS = ["security.W021"]
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# ---- Errors: Sentry and/or Telegram ---------------------------------------------
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", "0")),
        send_default_pii=False,
    )

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
        "telegram": {"class": "core.alerts.TelegramHandler", "level": "ERROR"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"handlers": ["console", "telegram"], "level": "ERROR", "propagate": False},
        "app": {"handlers": ["console", "telegram"], "level": "INFO", "propagate": False},
    },
}
