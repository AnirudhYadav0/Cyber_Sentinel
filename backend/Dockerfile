# Multi-stage hardened production Dockerfile for CyberSentinel API
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final minimal runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Create unprivileged system user for SOC security
RUN groupadd -r socuser && useradd -r -g socuser -s /sbin/nologin socuser

# Copy installed python wheels from builder
COPY --from=builder /root/.local /home/socuser/.local
ENV PATH=/home/socuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy backend application source code
COPY --chown=socuser:socuser app/ /app/app/

USER socuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
