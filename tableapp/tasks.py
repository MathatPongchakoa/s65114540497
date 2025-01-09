from celery import shared_task
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from .models import Booking,Order

@shared_task
def check_booking_status():
    # เวลาปัจจุบัน
    current_time = datetime.now()
    
    # ตรวจสอบ Booking ที่เป็น 'pending' และเกินเวลา
    pending_bookings = Booking.objects.filter(
        status="pending",
        booking_time__lt=current_time.time(),
        booking_date=current_time.date()
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
                message=f"การจองโต๊ะ {booking.table.table_name} ถูกยกเลิกเนื่องจากไม่มีการยืนยันภายในเวลาที่กำหนด",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.user.email],
            )

    # ตรวจสอบ Booking ที่เป็น 'occupied' และหมดเวลา
    occupied_bookings = Booking.objects.filter(
        status="occupied",
        booking_end_time__lte=current_time.time(),
        booking_date=current_time.date()
    )
    for booking in occupied_bookings:
        booking.status = "completed"  # หรือสถานะอื่นที่เหมาะสม เช่น 'completed'

    # ตรวจสอบว่ามี Booking อื่น ๆ ที่ยังไม่หมดเวลา
        active_bookings = Booking.objects.filter(
            table=booking.table,
            status__in=["pending", "occupied"],
            booking_date=current_time.date()
        ).exclude(id=booking.id)

        if not active_bookings.exists():
            # หากไม่มี Booking อื่นที่ยังใช้งานอยู่ ให้ตั้งสถานะโต๊ะเป็น 'available'
            booking.table.table_status = "available"
        else:
            # หากมี Booking อื่นที่ยังรออยู่ ให้ตั้งสถานะโต๊ะเป็น 'booked'
            booking.table.table_status = "booked"
        
        booking.table.save()
        booking.save()

        # คุณสามารถเพิ่มการแจ้งเตือนหรือการจัดการเพิ่มเติมได้ เช่น การส่งอีเมลแจ้งเตือน


@shared_task
def delete_cancelled_bookings():
    cancelled_bookings = Booking.objects.filter(status="cancelled")
    
    # ลบออเดอร์ที่เกี่ยวข้องกับ Booking ที่ถูกยกเลิกก่อนลบ Booking
    for booking in cancelled_bookings:
        Order.objects.filter(table_name=booking.table.table_name, user=booking.user).delete()
    
    cancelled_bookings.delete()