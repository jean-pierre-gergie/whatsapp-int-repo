FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1

# Copy application files
COPY . /app/

# Install necessary system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmariadb-dev pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask app port
EXPOSE 1313

# Ensure environment variables are loaded dynamically
CMD ["gunicorn", "--bind", "0.0.0.0:1313", "run:app"]
