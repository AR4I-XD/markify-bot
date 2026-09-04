# Multi-stage / lightweight Python build for Markify Bot
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user with UID 1000 (standard for Hugging Face Spaces)
RUN useradd -m -u 1000 user && \
    mkdir -p /app/data/logos

# Copy source code and assets
COPY src/ ./src/
COPY assets/ ./assets/

# Grant ownership of /app to user 1000
RUN chown -R user:user /app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

EXPOSE 7860

# Command to run bot
CMD ["python", "-m", "src.main"]
