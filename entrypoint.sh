#!/bin/sh
set -e

echo "⏳ Waiting for database..."
# เช็ก Postgres พร้อม (ต้องมี psycopg ติดตั้งแล้วจาก requirements.txt)
until python - <<'PY' >/dev/null 2>&1
import os, psycopg
try:
    psycopg.connect(
        host=os.getenv("DB_HOST","db"),
        port=int(os.getenv("POSTGRES_PORT","5432")),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )
except Exception as e:
    raise e
PY
do
  sleep 1
done
echo "✅ Database is ready."

# migrate
python manage.py migrate --noinput

# สร้าง superuser ถ้ายังไม่มี
# สร้าง superuser ถ้ายังไม่มี (ใช้ manage.py shell เพื่อให้ settings ถูกตั้งให้อัตโนมัติ)
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
e = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
p = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')
print('ensure superuser...')
User.objects.filter(username=u).exists() or User.objects.create_superuser(u, e, p)
print('done')
"


# run server
python manage.py runserver 0.0.0.0:8000
