FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# The SQLite database lives in /app/instance — mount a volume here in production
RUN mkdir -p /app/instance

EXPOSE 5000

# Gunicorn + eventlet worker (single worker required by Flask-SocketIO)
CMD ["gunicorn", \
     "--worker-class", "eventlet", \
     "--workers", "1", \
     "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
