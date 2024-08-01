FROM python:3.9-slim



RUN apt-get update && apt-get install -y \
    pkg-config \
    libmariadb-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT 8080
ENV PYTHONUNBUFFERED True

EXPOSE 8080

CMD ["python", "app.py"]
