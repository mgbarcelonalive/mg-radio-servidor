FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app/

RUN mkdir -p /app/musica /app/cunas && chmod -R 777 /app

ENV PORT=7860
EXPOSE 7860 8080

CMD ["python", "servidor_nube.py"]
