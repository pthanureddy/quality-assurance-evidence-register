FROM python:3.12-slim

WORKDIR /app
RUN useradd --create-home appuser

COPY pyproject.toml ./
COPY src ./src
COPY data ./data
RUN pip install --no-cache-dir .

USER appuser
CMD ["qa-register", "generate", "--input", "data/sample_quality_records.json", "--output", "/tmp/quality-export"]
