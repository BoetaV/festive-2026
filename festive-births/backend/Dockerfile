FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

ENV PORT=8000 HOST=0.0.0.0
EXPOSE 8000
# Apply migrations, then serve. Railway injects $PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host ${HOST} --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
