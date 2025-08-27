FROM python:3.12
WORKDIR /app

COPY . .
RUN pip install -r requirements.txt

# เตรียม entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# ใช้เป็น ENTRYPOINT (ไม่โดน command ใน compose ทับ)
ENTRYPOINT ["/entrypoint.sh"]

# คำสั่งเริ่มต้น (ยังแก้ได้จาก docker-compose ผ่าน 'command')
CMD ["gunicorn","seniorproject.wsgi:application","--bind","0.0.0.0:10497"]
