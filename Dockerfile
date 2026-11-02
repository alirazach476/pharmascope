FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY configs ./configs
COPY scripts ./scripts

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .

ENV PHARMASCOPE_DATA_ROOT=/app/data
ENV PHARMASCOPE_CONFIG_DIR=/app/configs
ENV DUCKDB_PATH=/app/data/metadata/pharmascope.duckdb

EXPOSE 8000 8501

CMD ["uvicorn", "pharmascope.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
