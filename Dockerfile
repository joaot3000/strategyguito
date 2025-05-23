FROM python:3.9-slim  # Explicitly using Python 3.9

# Install system dependencies
RUN apt-get update && \
    apt-get install -y gcc python3-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
