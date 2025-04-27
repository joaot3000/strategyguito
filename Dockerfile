FROM python:3.10-slim  # Python 3.10 recommended for best compatibility

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
