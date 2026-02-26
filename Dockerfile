# ──────────────────────────────────────────────────────────
# Stage 1 – builder: install dependencies into a wheel cache
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile psycopg2 (binary wheel so usually none needed,
# but kept here for reference if switching to the C extension)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ──────────────────────────────────────────────────────────
# Stage 2 – runtime: lean production image
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=pigw.settings.prod

WORKDIR /app

# Install compiled wheels from builder stage (no network needed)
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links /wheels /wheels/*.whl \
    && rm -rf /wheels

# Add gunicorn (not in wheels to keep image small; slim extra)
RUN pip install --no-cache-dir gunicorn

# Copy application source
COPY pigw/ /app/

# Collect static files into STATIC_ROOT
RUN DJANGO_SETTINGS_MODULE=pigw.settings.prod \
    DJANGO_SECRET_KEY=placeholder \
    FERNET_KEY=placeholder-32-bytes-for-collectstatic== \
    POSTGRES_DB=placeholder \
    POSTGRES_USER=placeholder \
    POSTGRES_PASSWORD=placeholder \
    python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

# 4 workers handles ~8 concurrent requests on a 2-core container
CMD ["gunicorn", "pigw.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "30", \
     "--access-logfile", "-"]
