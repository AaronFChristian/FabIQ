# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install hatchling && pip install --no-cache-dir -e .

# ── Production stage ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS production
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ src/

# Non-root user for security
RUN useradd --create-home --shell /bin/bash fabiq
USER fabiq

EXPOSE 8000
CMD ["uvicorn", "fabiq.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
