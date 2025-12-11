# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database (if using SQLite)
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DB_DIR=/app/data

# Expose port (IBM Cloud will override this)
EXPOSE 8080

# Run the application
# IBM Cloud expects apps to listen on PORT environment variable
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
