# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend
WORKDIR /fe
COPY web/frontend/package.json ./
RUN npm install
COPY web/frontend ./
RUN npm run build

FROM python:3.12-slim AS builder

ARG MARKDROP_ENGINE=full
ARG MARKDROP_EXTRAS=lite,litellm
ENV MARKDROP_ENGINE=${MARKDROP_ENGINE}
ENV MARKDROP_EXTRAS=${MARKDROP_EXTRAS}
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY markdrop ./markdrop
COPY web ./web

RUN pip install --no-cache-dir --upgrade pip \
    && sh web/docker-install.sh \
    && pip install --no-cache-dir -r web/requirements.txt

FROM python:3.12-slim

ARG MARKDROP_ENGINE=full
ARG MARKDROP_EXTRAS=lite,litellm
ENV MARKDROP_ENGINE=${MARKDROP_ENGINE}
ENV MARKDROP_EXTRAS=${MARKDROP_EXTRAS}
ENV MARKDROP_DATA_DIR=/data
ENV XDG_CONFIG_HOME=/data/config
ENV HF_HOME=/data/cache/hf
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OMP_NUM_THREADS=4
ENV PYTORCH_NUM_THREADS=4
ENV PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY markdrop ./markdrop
COPY web ./web
COPY --from=frontend /fe/dist ./web/static
RUN mkdir -p /data

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')"
CMD ["python", "-m", "web"]
