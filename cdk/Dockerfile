FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY python-brain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY python-brain/ .

EXPOSE 5001

CMD ["python", "app.py"]

