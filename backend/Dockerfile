FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN addgroup --system app && adduser --system --ingroup app --home /home/app app

ENV HOME=/home/app \
    HF_HOME=/home/app/.cache/huggingface \
    TORCH_HOME=/home/app/.cache/torch

RUN mkdir -p /home/app/.cache /app/backend/documents /app/backend/app/doc_processing/doc \
    && chown -R app:app /home/app /app

COPY --chown=app:app backend ./backend
COPY --chown=app:app alembic.ini ./alembic.ini

USER app

EXPOSE 8000

# Apply schema migrations before starting the API.
CMD ["sh", "-c", "alembic -c /app/alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]