FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install -r requirements.txt

COPY backend /app/backend
COPY pg_an /app/pg_an

WORKDIR /app/backend

CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5000", "app:app"]
