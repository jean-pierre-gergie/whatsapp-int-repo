FROM python:3.13.5-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1

# Copy all files to the container
COPY . /app/

# Install system dependencies and Python requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmariadb-dev pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port for Flask
EXPOSE 5001

# Command to run the Flask app
CMD ["python", "app.py"]