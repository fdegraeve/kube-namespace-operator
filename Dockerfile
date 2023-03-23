FROM python:3.11-alpine

WORKDIR /operator
RUN apk --no-cache add build-base 
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD kopf run --standalone --liveness=http://0.0.0.0:8080/healthz handlers.py
