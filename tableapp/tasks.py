from celery import shared_task
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from .models import Booking,Order

@shared_task
def check_booking_status():
    fifteen_minutes_ago = datetime.now() - timedelta(minutes=1)
    pending_bookings = Booking.objects.filter(
        status="pending",
        booking_time__lt=fifteen_minutes_ago.time(),
        booking_date=datetime.now().date()
    )
    for booking in pending_bookings:
        booking.status = "cancelled"
        booking.save()
        
        # ลบออเดอร์ที่เกี่ยวข้องกับ Booking ที่ถูกยกเลิก
        Order.objects.filter(table_name=booking.table.table_name, user=booking.user).delete()

        # ส่งอีเมลแจ้งเตือนผู้ใช้
        if booking.user and booking.user.email:
            send_mail(
                subject="การจองของคุณถูกยกเลิก",
                message=f"การจองโต๊ะ {booking.table.table_name} ถูกยกเลิกเนื่องจากไม่มีการยืนยันภายใน 15 นาที",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.user.email],
            )

@shared_task
def delete_cancelled_bookings():
    cancelled_bookings = Booking.objects.filter(status="cancelled")
    
    # ลบออเดอร์ที่เกี่ยวข้องกับ Booking ที่ถูกยกเลิกก่อนลบ Booking
    for booking in cancelled_bookings:
        Order.objects.filter(table_name=booking.table.table_name, user=booking.user).delete()
    
    cancelled_bookings.delete()