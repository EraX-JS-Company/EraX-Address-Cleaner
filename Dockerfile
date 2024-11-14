FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \ 
    redis-server \
    && rm -rf /var/lib/apt/lists/*

COPY app.py .
COPY utils.py .
COPY run_app.sh .
COPY requirements.txt .
COPY prepare.sh .
COPY openssl/ ./openssl/
COPY config/ ./config/
COPY media/ ./media/
COPY prompt/ ./prompt/

RUN bash prepare.sh

RUN chmod +x run_app.sh

EXPOSE 7015

CMD ["bash", "run_app.sh"]