from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from tableapp.models import Booking
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "จัดการ Task การจอง เช่น ตรวจสอบการจองหรือการลบการจองที่ถูกยกเลิก"

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=['check_booking_status', 'delete_cancelled_bookings'],
            help='ระบุ Task ที่ต้องการรัน: check_booking_status หรือ delete_cancelled_bookings'
        )

    def handle(self, *args, **options):
        task = options['task']

        if task == 'check_booking_status':
            self.check_booking_status()
        elif task == 'delete_cancelled_bookings':
            self.delete_cancelled_bookings()
        else:
            self.stdout.write(self.style.ERROR("กรุณาระบุ Task ที่ถูกต้อง"))

    def check_booking_status(self):
        """ ตรวจสอบการจองและยกเลิกหากไม่ยืนยันภายใน 15 นาที """
        fifteen_minutes_ago = datetime.now() - timedelta(minutes=15)
        pending_bookings = Booking.objects.filter(
            status="pending",
            booking_time__lt=fifteen_minutes_ago.time(),
            booking_date=datetime.now().date()
        )

        for booking in pending_bookings:
            booking.status = "cancelled"
            booking.save()

            # ส่งอีเมลแจ้งเตือนผู้ใช้
            if booking.user and booking.user.email:
                send_mail(
                    subject="การจองของคุณถูกยกเลิก",
                    message=f"การจองโต๊ะ {booking.table.table_name} ของคุณเมื่อ {booking.booking_date} เวลา {booking.booking_time} ถูกยกเลิกเนื่องจากไม่มีการยืนยันภายใน 15 นาที",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[booking.user.email],
                )
                self.stdout.write(f"แจ้งเตือนอีเมลไปยัง {booking.user.email}")

        self.stdout.write(self.style.SUCCESS("ตรวจสอบการจองเสร็จสิ้น!"))

    def delete_cancelled_bookings(self):
        """ ลบการจองที่ถูกยกเลิก """
        cancelled_bookings = Booking.objects.filter(status="cancelled")
        count = cancelled_bookings.count()

        if count > 0:
            cancelled_bookings.delete()
            self.stdout.write(self.style.SUCCESS(f"ลบการจองที่ถูกยกเลิกแล้ว {count} รายการ"))
        else:
            self.stdout.write("ไม่พบการจองที่ถูกยกเลิก")
