FROM python:3.10-slim

# Cài đặt LibreOffice và fontconfig
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-dejavu \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục và copy TẤT CẢ font từ thư mục fonts/ local vào Docker
RUN mkdir -p /usr/share/fonts/truetype/mulish
COPY fonts/ /usr/share/fonts/truetype/mulish/

# Cập nhật cache font của hệ thống
RUN fc-cache -f -v

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]