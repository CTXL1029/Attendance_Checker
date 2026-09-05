FROM python:3.10-slim

# Cài đặt LibreOffice và font chữ hệ thống
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-dejavu \
    wget \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Tải và cài đặt Font Mulish từ Google Fonts
RUN mkdir -p /usr/share/fonts/truetype/mulish \
    && wget -O /usr/share/fonts/truetype/mulish/Mulish.ttf https://github.com/google/fonts/raw/main/ofl/mulish/Mulish-VariableFont_wght.ttf \
    && fc-cache -f -v

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]