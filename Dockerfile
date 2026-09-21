FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code-only changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (see .dockerignore for exclusions).
COPY . .

# Cloud Run sets $PORT (defaults to 8080) and expects the container to listen
# on it. gunicorn serves app.py's exposed Flask instance ("server").
ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 0 app:server
