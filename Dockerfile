FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libegl1 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "program.py"]
# to run the container, use the following command in the terminal:
# docker compose up --build -d