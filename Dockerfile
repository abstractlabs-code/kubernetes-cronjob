FROM python:3.14.0a3-alpine3.20

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


WORKDIR /app

COPY requirements.txt .
COPY pod-observability-check.py .

RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    py3-pip \
    build-base && \
    pip install --no-cache-dir -r requirements.txt



CMD ["python", "pod-observability-check.py"]
