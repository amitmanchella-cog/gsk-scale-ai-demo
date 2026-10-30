# Field Force Navigator (UC4, S5.1): one image serving the API (/api), the built SPA (/) and /health on port 8000.
# Build from the repo root so the curated tables can be baked in:
#   docker build -f apps/navigator/Dockerfile -t navigator .
#   docker run --rm -p 8000:8000 navigator
# Base images can be swapped (e.g. a registry mirror) with --build-arg NODE_IMAGE=... / PYTHON_IMAGE=...
ARG NODE_IMAGE=node:20-alpine
ARG PYTHON_IMAGE=python:3.11-slim

FROM ${NODE_IMAGE} AS web
WORKDIR /web
COPY apps/navigator/frontend/package*.json ./
RUN npm ci
COPY apps/navigator/frontend ./
RUN npm run build

FROM ${PYTHON_IMAGE}
# Mirror the repo layout so app/data.py's package-relative default (<repo root>/data) resolves to /srv/data.
WORKDIR /srv/apps/navigator/backend
COPY apps/navigator/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/navigator/backend/app ./app
COPY data/*.parquet /srv/data/
COPY --from=web /web/dist /srv/static
ENV NAVIGATOR_DATA_DIR=/srv/data NAVIGATOR_STATIC_DIR=/srv/static PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
