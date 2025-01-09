import os
from openpyxl import load_workbook
from django.conf import settings
from tableapp.models import *
from datetime import datetime
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Load data from Excel into CustomUser, Table, Booking, Category, and Menu models'

    def handle(self, *args, **options):
        file_path = os.path.join(settings.BASE_DIR, 'tableapp', 'fixtures', 'data_ex.xlsx')

        # อ่านข้อมูลจาก Excel
        wb = load_workbook(file_path)

        # แผ่นงานสำหรับ CustomUser
        if 'CustomUser' in wb.sheetnames:
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

        # แผ่นงานสำหรับ Zone
        if 'Zone' in wb.sheetnames:
            zone_sheet = wb['Zone']
            for row in zone_sheet.iter_rows(min_row=2, values_only=True):
                # ตรวจสอบจำนวนค่าที่อ่านได้
                if len(row) < 4:
                    self.stdout.write(f"Skipping row in Zone sheet due to insufficient columns: {row}")
                    continue

                zone_id, name, description, image = row  # อ่านคอลัมน์ id, name, description, image

                # สร้างหรืออัปเดต Zone
                zone_instance, created = Zone.objects.get_or_create(
                    id=zone_id,
                    defaults={
                        'name': name,
                        'description': description,
                        'image': image,  # เพิ่มภาพในฟิลด์ image
                    }
                )
                if created:
                    self.stdout.write(f"Created zone: {name}")
                else:
                    # อัปเดตข้อมูลโซนถ้าจำเป็น
                    zone_instance.name = name
                    zone_instance.description = description
                    if image:  # ถ้ามีข้อมูลภาพใหม่
                        zone_instance.image = image
                    zone_instance.save()
                    self.stdout.write(f"Updated zone: {name}")

        # แผ่นงานสำหรับ Table
        if 'Table' in wb.sheetnames:
            table_sheet = wb['Table']
            for row in table_sheet.iter_rows(min_row=2, values_only=True):
                table_id, table_name, table_status, zone_id = row  # เพิ่มการอ่าน zone_id

                # ตรวจสอบว่าค่า table_status ถูกต้อง
                valid_statuses = ['available', 'occupied', 'booked']
                if table_status not in valid_statuses:
                    self.stdout.write(f"Invalid table status '{table_status}' for table {table_name}. Skipping...")
                    continue

                # ค้นหา Zone ด้วย zone_id
                zone = None
                if zone_id:
                    zone = Zone.objects.filter(id=zone_id).first()
                    if not zone:
                        self.stdout.write(f"Zone ID {zone_id} not found for table {table_name}. Skipping...")
                        continue

                # สร้างหรืออัปเดต Table
                table_instance, created = Table.objects.get_or_create(
                    id=table_id,
                    defaults={
                        'table_name': table_name,
                        'table_status': table_status,
                        'zone': zone,  # เพิ่ม zone ในการสร้าง
                    }
                )
                if created:
                    self.stdout.write(f"Created table: {table_name} in zone {zone.name if zone else 'N/A'}")
                else:
                    # อัปเดต zone ถ้ามีการเปลี่ยนแปลง
                    table_instance.zone = zone
                    table_instance.table_status = table_status
                    table_instance.save()
                    self.stdout.write(f"Updated table: {table_name} in zone {zone.name if zone else 'N/A'}")

        # แผ่นงานสำหรับ Booking
        if 'Booking' in wb.sheetnames:
            booking_sheet = wb['Booking']
            for row in booking_sheet.iter_rows(min_row=2, values_only=True):
                booking_id, table_id, booking_date, booking_time, booking_end_time, user_id, status = row

                # ตรวจสอบวันที่
                try:
                    booking_date = datetime.strptime(str(booking_date), '%Y-%m-%d').date()
                except ValueError as e:
                    self.stdout.write(f"Invalid booking date format for booking ID {booking_id}. Skipping... Error: {e}")
                    continue

                # ตรวจสอบเวลา
                try:
                    booking_time = datetime.strptime(str(booking_time), '%H:%M:%S').time()
                    booking_end_time = datetime.strptime(str(booking_end_time), '%H:%M:%S').time()
                except ValueError as e:
                    self.stdout.write(f"Invalid booking time format for booking ID {booking_id}. Skipping... Error: {e}")
                    continue

                # ค้นหา Table
                table = Table.objects.filter(id=table_id).first()
                if not table:
                    self.stdout.write(f"Table ID {table_id} not found. Skipping booking.")
                    continue

                # ค้นหา User
                user = None
                if user_id:
                    user = CustomUser.objects.filter(id=user_id).first()
                    if not user:
                        self.stdout.write(f"User ID {user_id} not found. Skipping booking ID {booking_id}.")

                # ตรวจสอบสถานะ booking
                valid_statuses = ['pending', 'occupied', 'cancelled']
                if status not in valid_statuses:
                    self.stdout.write(f"Invalid booking status '{status}' for booking ID {booking_id}. Skipping...")
                    continue

                # สร้างข้อมูลการจอง
                booking_instance, created = Booking.objects.get_or_create(
                    id=booking_id,
                    defaults={
                        'table': table,
                        'booking_date': booking_date,
                        'booking_time': booking_time,
                        'booking_end_time': booking_end_time,
                        'user': user,
                        'status': status,
                    }
                )
                if created:
                    self.stdout.write(f"Created booking ID {booking_id} for table {table.table_name}")
                else:
                    self.stdout.write(f"Booking ID {booking_id} already exists.")

        # แผ่นงานสำหรับ Category
        if 'Category' in wb.sheetnames:
            category_sheet = wb['Category']
            for row in category_sheet.iter_rows(min_row=2, values_only=True):
                name = row[1]
                category_instance, created = Category.objects.get_or_create(name=name)
                if created:
                    self.stdout.write(f"Created category: {name}")
                else:
                    self.stdout.write(f"Category already exists: {name}")

        # แผ่นงานสำหรับ Menu
        if 'Menu' in wb.sheetnames:
            menu_sheet = wb['Menu']
            for row in menu_sheet.iter_rows(min_row=2, values_only=True):
                # ข้ามคอลัมน์แรก (id)
                food_name, price, image_url, category_name = row[1:5]  # ดึง category_name จากคอลัมน์ใน Excel

                # ค้นหา Category ด้วยชื่อ (name)
                category = Category.objects.filter(name=category_name).first()
                if not category:
                    self.stdout.write(f"Category '{category_name}' not found. Skipping menu item '{food_name}'.")
                    continue

                # สร้างเมนู
                menu_instance, created = Menu.objects.get_or_create(
                    food_name=food_name,
                    defaults={
                        'price': price,
                        'image_url': image_url,
                        'category': category,  # ใช้ ForeignKey ที่สัมพันธ์กับ Category
                    }
                )
                if created:
                    self.stdout.write(f"Created menu item: {food_name}")
                else:
                    self.stdout.write(f"Menu item already exists: {food_name}")

        self.stdout.write(self.style.SUCCESS("Data loaded successfully!"))
