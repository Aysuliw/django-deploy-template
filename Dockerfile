FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# collectstatic needs settings to load; the real key comes from the environment at runtime.
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput

# Never run the app as root: if it is ever compromised, the attacker gets this user, not the box.
RUN useradd --system --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "30", "--access-logfile", "-"]
