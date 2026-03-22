# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./

RUN python - <<'PY' > /tmp/requirements.txt
from pathlib import Path
import tomllib

data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
for dependency in data["project"]["dependencies"]:
    print(dependency)
PY

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    python -m pip install -r /tmp/requirements.txt

COPY app ./app
COPY scripts ./scripts

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-deps .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
