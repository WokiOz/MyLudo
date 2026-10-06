# Étape 1 : compilation du frontend, sur l'architecture de la machine de build
# car le résultat est du HTML/JS identique pour toutes les architectures
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Étape 2 : backend Python qui sert l'API et le frontend
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir . && mkdir -p /data
COPY --from=frontend /build/dist ./static
VOLUME ["/data"]
EXPOSE 6018
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:6018/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6018"]
