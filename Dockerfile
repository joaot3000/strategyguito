# Use Python 3.8 for better compatibility with aiohttp
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip wheel && \
    pip install -r requirements.txt --no-cache-dir

# Copy application code
COPY . .

# Run the bot
CMD ["python", "main.py"]
