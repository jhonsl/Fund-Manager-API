# syntax=docker/dockerfile:1

# ---- Stage 1: builder ----
# Installs dependencies into an isolated venv so the final image stays small.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Create a virtualenv we can copy wholesale into the final stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only what's needed to resolve dependencies first (better layer caching).
COPY pyproject.toml README.md ./
COPY app ./app

# Install the project (runtime deps only; dev tools excluded).
RUN pip install --upgrade pip && pip install .

# ---- Stage 2: runtime ----
# Slim final image with just the venv + source, running as a non-root user.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root user for security.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Bring the prepared venv and application code from the builder.
COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8080

# Production-style start command (no --reload). Dev hot-reload is provided by
# docker-compose via a mounted volume + command override.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
