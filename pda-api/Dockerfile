FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY samples ./samples
COPY tests/fixtures/benchmark ./tests/fixtures/benchmark
RUN pip install --no-cache-dir -e .
ENV DATABASE_URL=sqlite+aiosqlite:////tmp/pda.db
EXPOSE 8000
CMD ["uvicorn", "pda_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
