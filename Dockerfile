# Stage 1: Build stage with all dependencies
FROM python:3.10-slim AS builder

# Set non-interactive frontend for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for building wheels and for whisper/torch
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg build-essential && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up a virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements and install them into the virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final, lightweight stage
FROM python:3.10-slim

# Set non-interactive frontend for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install ffmpeg which is a runtime dependency
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code
COPY main.py .

# Activate the virtual environment and run the application
ENV PATH="/opt/venv/bin:$PATH"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
