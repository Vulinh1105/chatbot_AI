FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

ARG REQUIREMENTS_FILE=requirements.backend-api.txt
COPY ${REQUIREMENTS_FILE} ./requirements.txt
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt

ARG ENABLE_DOCUMENTS=0
ENV ENABLE_DOCUMENTS=$ENABLE_DOCUMENTS

RUN addgroup --system app && adduser --system --ingroup app app

COPY --chown=app:app backend ./backend
COPY --chown=app:app alembic.ini ./alembic.ini

USER app

EXPOSE 8000

# Apply schema migrations before starting the API.
CMD ["sh", "-c", "alembic -c /app/alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
