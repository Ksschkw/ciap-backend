# Use the official Python slim image for a smaller footprint
FROM python:3.11-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# gcc and libpq-dev are needed for building psycopg2 and other C-extensions
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir keeps the image size down by not caching the downloaded wheels
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create a non-root user and switch to it for security (Industry standard practice)
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE ${PORT}

# Command to run the application
# We use $PORT so platforms like Render or Heroku can inject their dynamically assigned port
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
