FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Create volume mount point for persistent SQLite database
RUN mkdir -p /app/data

VOLUME ["/app/data"]

CMD ["python", "main.py"]
