# backend/Dockerfile
FROM python:3.12-slim

# set a working dir; keep it simple and explicit
WORKDIR /app

# system deps needed for some wheels (psycopg2, cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# copy only requirements first for better caching
COPY backend/requirements.txt /app/requirements.txt

# upgrade pip and install packages preferring wheels where available
RUN python -m pip install --upgrade pip setuptools wheel \
 && python -m pip install --prefer-binary -r /app/requirements.txt

# copy app code
COPY backend /app

# expose port (Render will map $PORT)
ENV PORT 8000
EXPOSE 8000

# default command - use $PORT if Render sets it, fallback to 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
