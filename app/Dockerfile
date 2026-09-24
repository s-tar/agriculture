FROM python:3.14-alpine

WORKDIR /app

RUN apk add --no-cache --virtual .build-deps \
    build-base \
    libffi-dev \
    postgresql-dev \
    gcc \
    g++ \
    gcompat \
    python3-dev \
    musl-dev

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir && \
    apk del .build-deps

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
