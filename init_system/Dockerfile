FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy data and code into the container
COPY ./init_data /app/init_data
COPY ./utils /app/utils
COPY ./logger /app/logger
COPY ./requirements.txt /app/
COPY ./init_system.py /app/

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmariadb-dev pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Define the default command
CMD ["python", "init_system.py"]




