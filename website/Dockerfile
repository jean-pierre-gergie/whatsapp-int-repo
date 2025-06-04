FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1



# Install necessary system dependencies
RUN set -eux; \
    apt-get update; \
    # upgrade EVERYTHING first
    apt-get dist-upgrade -y --no-install-recommends; \
    # then install the few build deps you really need
    apt-get install -y --no-install-recommends gcc libmariadb-dev pkg-config; \
    # minimise the image
    apt-get autoremove -y; \
    apt-get clean; rm -rf /var/lib/apt/lists/*

# RUN groupadd -r appuser && useradd -r -g appuser appuser
# USER appuser

# Install Python dependencies
COPY . /app/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Expose Flask app port
EXPOSE 1313

# Ensure environment variables are loaded dynamically
CMD ["gunicorn", "--bind", "0.0.0.0:1313", "run:app"]
