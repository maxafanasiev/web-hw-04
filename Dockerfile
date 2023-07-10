FROM python:3.11.2
WORKDIR /app
COPY . .
VOLUME /app/storage
ENTRYPOINT ["python", "main.py"]