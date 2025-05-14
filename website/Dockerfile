FROM python:3.13.2-slim

# Set the working directory in the container
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1


COPY . /app/

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmariadb-dev pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 1313

ENV FLASK_APP=app.py

CMD ["bash", "-c", "python run.py"]