# Build from the repository root: docker build -f csd-api/Dockerfile -t csd-api .
FROM python:3.11-slim
WORKDIR /app
COPY csd-core /app/csd-core
COPY csd-api /app/csd-api
RUN pip install --no-cache-dir /app/csd-core /app/csd-api
ENV CSD_DATABASE_URL=sqlite:////data/csd.db
RUN mkdir /data && useradd --system csd && chown csd /data
USER csd
EXPOSE 8000
CMD ["uvicorn", "csd_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
