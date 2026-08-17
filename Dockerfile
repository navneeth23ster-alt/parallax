FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# refresh data on container start, then serve
CMD ["sh", "-c", "python -m parallax run || true; uvicorn parallax.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
