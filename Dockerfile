FROM python:3.12
WORKDIR /app

# copy requirements.txt ก่อน (เฉพาะไฟล์นี้)
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy ไฟล์อื่น ๆ เข้ามา
COPY . .

# เพิ่ม entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# ถ้าไม่ใช้ gunicorn และจะใช้ runserver ให้เปลี่ยน CMD แบบนี้
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
