# ---- Builder: install dependencies into an isolated prefix ----
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime: slim image, non-root numeric user ----
FROM python:3.11-slim

# Numeric UID so Kubernetes' runAsNonRoot can verify the user without a lookup
# (a named USER is rejected with CreateContainerConfigError under runAsNonRoot).
RUN groupadd --system --gid 10001 appgroup \
    && useradd --system --uid 10001 --gid 10001 --no-create-home appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
