# 1. Python'un resmi image'ını kullan
FROM python:3.9

# 2. Çalışma dizinini ayarla
WORKDIR /app

# 3. Bağımlılıkları yükle
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. Flask uygulamasını kopyala
COPY . .

# 5. Flask uygulamasını çalıştır
CMD ["python", "app.py"]
