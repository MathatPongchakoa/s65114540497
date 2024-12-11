import os
from openpyxl import load_workbook
from django.conf import settings
from tableapp.models import CustomUser, Table, Booking
from datetime import datetime, time
from django.core.management.base import BaseCommand

from tableapp.models import CustomUser, Table, Booking, Menu  # Import Menu model

class Command(BaseCommand):
    help = 'Load data from Excel into CustomUser, Table, Booking, and Menu models'

    def handle(self, *args, **options):
        file_path = os.path.join(settings.BASE_DIR, 'tableapp', 'fixtures', 'data_ex.xlsx')

        # อ่านข้อมูลจาก Excel
        wb = load_workbook(file_path)

        # แผ่นงานสำหรับ CustomUser
        user_sheet = wb['CustomUser']
        for row in user_sheet.iter_rows(min_row=2, values_only=True):
            user_id, username, email, first_name, last_name, password = row
            if password and not isinstance(password, str):
                password = str(password)
            if password:
                user_instance, created = CustomUser.objects.get_or_create(
                    id=user_id,
                    defaults={
                        'username': username,
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                    }
                )
                if created:
                    user_instance.set_password(password)
                    user_instance.save()
                    self.stdout.write(f"Created user: {username}")
                else:
                    self.stdout.write(f"User already exists: {username}")
            else:
                self.stdout.write(f"Skipping user {username} due to missing password")

        # แผ่นงานสำหรับ Table
        table_sheet = wb['Table']
        for row in table_sheet.iter_rows(min_row=2, values_only=True):
            table_id, table_name, table_status = row
            table_instance, created = Table.objects.get_or_create(
                id=table_id,
                defaults={
                    'table_name': table_name,
                    'table_status': table_status,
                }
            )
            if created:
                self.stdout.write(f"Created table: {table_name}")
            else:
                self.stdout.write(f"Table already exists: {table_name}")
       
       # แผ่นงานสำหรับ Booking

        booking_sheet = wb['Booking']
        for row in booking_sheet.iter_rows(min_row=2, values_only=True):
            booking_id, table_id, booking_date, booking_time, user_id = row
            self.stdout.write(f"Processing Booking row: {row}")

            # ตรวจสอบวันที่
            try:
                booking_date = datetime.strptime(str(booking_date), '%Y/%m/%d').date()
            except ValueError as e:
                self.stdout.write(f"Invalid booking date format for booking ID {booking_id}. Skipping... Error: {e}")
                continue

            # ตรวจสอบเวลา
            try:
                if isinstance(booking_time, datetime):
                    booking_time = booking_time.time()
                elif isinstance(booking_time, time):
                    pass
                else:
                    booking_time = datetime.strptime(str(booking_time), '%H:%M:%S').time()
            except ValueError as e:
                self.stdout.write(f"Invalid booking time format for booking ID {booking_id}. Skipping... Error: {e}")
                continue

            # ค้นหา Table
            table = Table.objects.filter(id=table_id).first()
            if not table:
                self.stdout.write(f"Table ID {table_id} not found. Skipping booking.")
                continue

            # ตรวจสอบสถานะของโต๊ะ
            if table.table_status == 'ว่าง':
                self.stdout.write(f"Skipping booking ID {booking_id} because table {table.table_name} is available (ว่าง).")
                continue

            # ตรวจสอบว่ามีการจองอยู่แล้วหรือไม่
            existing_booking = Booking.objects.filter(
                table=table,
                booking_date=booking_date,
                booking_time=booking_time
            ).first()

            if existing_booking:
                self.stdout.write(f"Skipping booking ID {booking_id} because a booking already exists for table {table.table_name} at {booking_date} {booking_time}.")
                continue

            # ค้นหา User
            user = None
            if user_id:
                user = CustomUser.objects.filter(id=user_id).first()
                if not user:
                    self.stdout.write(f"User ID {user_id} not found. Skipping booking ID {booking_id}.")

            # สร้างข้อมูลการจอง
            booking_instance, created = Booking.objects.get_or_create(
                id=booking_id,
                defaults={
                    'table': table,
                    'booking_date': booking_date,
                    'booking_time': booking_time,
                    'user': user,
                }
            )
            if created:
                self.stdout.write(f"Created booking ID {booking_id} for table {table.table_name}")
            else:
                self.stdout.write(f"Booking ID {booking_id} already exists.")



        # แผ่นงานสำหรับ Menu
        menu_sheet = wb['Menu']
        for row in menu_sheet.iter_rows(min_row=2, values_only=True):
            print(f"Row data: {row}")
            _,food_name, price, image_url, category = row
            menu_instance, created = Menu.objects.get_or_create(
                food_name=food_name,
                defaults={
                    'price': price,
                    'image_url': image_url,
                    'category': category,
                }
            )
            if created:
                self.stdout.write(f"Created menu item: {food_name}")
            else:
                self.stdout.write(f"Menu item already exists: {food_name}")

        self.stdout.write(self.style.SUCCESS("Data loaded successfully!"))
