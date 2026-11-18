FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --system --user-group lazycut \
    && mkdir /app/data /app/exports /app/music /clips \
    && chown lazycut:lazycut /app/data /app/exports

COPY backend/ backend/
COPY presets/ presets/
COPY vibes/ vibes/

USER lazycut
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
