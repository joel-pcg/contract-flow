FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including WeasyPrint requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \ 
    libpq-dev \
    # WeasyPrint dependencies
    libglib2.0-dev \
    libgirepository1.0-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/* 

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" ]