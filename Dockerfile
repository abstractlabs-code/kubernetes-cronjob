FROM python:3.14.0a3-alpine3.20

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    py3-pip \
    build-base && \
    addgroup -S appgroup && adduser -S appuser -G appgroup

USER appuser

WORKDIR /app

COPY requirements.txt .
COPY pod-observability-check.py .
RUN pip install --no-cache-dir -r requirements.txt



ENTRYPOINT ["python", "pod-observability-check.py"]
