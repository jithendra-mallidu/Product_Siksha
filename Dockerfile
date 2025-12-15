# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for psycopg2 compilation sometimes, though using binary helps)
# RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy backend code
COPY backend/ .

# Expose port (Cloud Run defaults to 8080)
ENV PORT 8080
EXPOSE 8080

# Command to run the application using Gunicorn
# app:app refers to module 'app.py' and callable 'app'
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
