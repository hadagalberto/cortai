FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg com libass (legendas), libglib para o opencv-headless
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg libglib2.0-0 ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# work/ e out/ sao volumes; o resto e imagem
VOLUME ["/app/work", "/app/out"]

EXPOSE 8787

CMD ["python", "cortai.py", "run"]
