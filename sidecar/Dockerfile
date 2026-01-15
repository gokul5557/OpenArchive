FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow/Tesseract if needed (optional for simulation)
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables will be overridden by docker-compose
ENV PYTHONUNBUFFERED=1

CMD ["python", "agent.py"]
