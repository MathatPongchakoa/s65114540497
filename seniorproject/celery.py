from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import schedule, crontab  # เพิ่ม crontab สำหรับการกำหนดเวลา

# ตั้งค่า default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seniorproject.settings')

# สร้าง instance Celery
app = Celery('seniorproject')

# โหลด settings จาก Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# โหลด tasks จาก apps ทั้งหมด
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# กำหนด Schedule ให้ทำงานทุก 1 นาที
app.conf.beat_schedule = {
    'check-booking-status-every-1-minute': {
        'task': 'tableapp.tasks.check_booking_status',  # Path ไปยัง Task
        'schedule': schedule(60.0),  # ทำงานทุก 60 วินาที
    },
    'delete-cancelled-bookings-every-1-minute': {
        'task': 'tableapp.tasks.delete_cancelled_bookings',
        'schedule': schedule(60.0),  # ทำงานทุก 60 วินาที
    },
}

# Optional: ตั้ง Timezone
app.conf.timezone = 'UTC'  # หรือ 'Asia/Bangkok'
