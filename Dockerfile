FROM python:3.11-slim

# Установка системных зависимостей для аудио (ffmpeg, libsndfile1), сборки (build-essential) и Postgres (libpq-dev)
RUN apt-get update && \
    apt-get install -y ffmpeg git libsndfile1 build-essential libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем только requirements.txt и torch/torchaudio, если они в отдельном файле
COPY requirements.txt ./

# Установка Torch и Torchaudio только для CPU перед requirements, чтобы избежать дефолтных GPU
RUN pip install --timeout=600 torch==2.2.2+cpu torchaudio==2.2.2+cpu --index-url https://download.pytorch.org/whl/cpu
# Установка зависимостей проекта
RUN pip install -r requirements.txt

# Копируем остальной код проекта
COPY . .

# Run migrations on container start then start the bot
CMD sh -c "python -m migrations.create_tables && python main.py"

