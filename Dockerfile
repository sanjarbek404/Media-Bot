FROM python:3.10-slim

# Install ffmpeg and curl (for deno install)
RUN apt-get update && \
    apt-get install -y ffmpeg curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Deno JS runtime (required by yt-dlp for YouTube challenge solving)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR="/root/.deno"
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --upgrade

# Copy project files
COPY . .

# Run the bot
CMD ["python", "main.py"]
