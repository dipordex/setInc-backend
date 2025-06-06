FROM python:3.8-slim-buster

# Environment configuration
ENV TZ=Europe/London \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    gcc \
    g++ \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /src

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Optional cleanup: remove compilers and dev headers
RUN apt-get purge -y gcc g++ \
 && apt-get autoremove -y

# Install Gunicorn (ensure it's listed in requirements.txt if you prefer)
RUN pip install --no-cache-dir gunicorn

# Copy application source
COPY . .

# Entrypoint for signal forwarding and process reaping
ENTRYPOINT ["tini", "--"]

# Default command
CMD ["bash", "run.sh"]
