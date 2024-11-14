# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1


# Copy the requirements file into the container
COPY requirements.txt /app/

# Copy initialization scripts and data
COPY ./init_scripts/init_mongo.py /app/init_scripts/
COPY ./init_scripts/init_webhook_urls.py /app/init_scripts/
COPY ./init_data/languages.json /app/init_data/
COPY ./init_data/users.json /app/init_data/

# Copy utility scripts
COPY ./utils /app/utils
COPY ./utils_init/utils_init.py /app/utils_init/

# Copy credentials dile
COPY ./service_account_credentials/dialogflow-int-796518c92a4c.json /app/service_account_credentials
# Copy Dialogflow handler 
COPY ./dialogflow_cx_handler/dialogflowHandler.py /app/dialogflow_cx_handler


# Install system dependencies and pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmariadb-dev pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app file into the container
COPY app.py /app/

# Make port 5001 available to the world outside this container
EXPOSE 5000

# Define environment variable (not needed for FastAPI, optional to keep)
ENV APP_MODULE=app:app

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--log-level", "info"]
