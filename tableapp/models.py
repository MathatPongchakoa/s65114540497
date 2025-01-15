from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.conf import settings
from datetime import time
from datetime import timedelta
from django.utils.timezone import now
from django.utils import timezone
from background_task import background
from django.db.models import Index

# tableapp/models.py
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    password = models.CharField(max_length=128)  # ใช้ฟังก์ชัน set_password สำหรับ hashing

    def __str__(self):
        return self.username

from django.db import models

class Zone(models.Model):
    name = models.CharField(max_length=100)  # ชื่อโซน เช่น "ในร้าน", "นอกร้าน"
    description = models.TextField(blank=True, null=True)  # คำอธิบายเพิ่มเติมเกี่ยวกับโซน
    image = models.ImageField(upload_to='zone_images/', blank=True, null=True)  # รูปภาพประกอบโซน (ถ้ามี)

    def __str__(self):
        return self.name



class Table(models.Model):
    table_name = models.CharField(max_length=100)
    table_status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'ว่าง'),
            ('occupied', 'กำลังนั่ง'),
            ('booked', 'จอง')
        ],
        default='available'
    )
    seating_capacity = models.IntegerField(default=4)  # จำนวนคนที่รองรับได้
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)  # เชื่อมกับ Zone

    def __str__(self):
        return f"{self.table_name} ({self.seating_capacity} คน, {self.zone.name if self.zone else 'ไม่ระบุโซน'})"




class Booking(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    booking_date = models.DateField(default=now)
    booking_time = models.TimeField(default='12:00:00')  # เวลาจองเริ่มต้น
    booking_end_time = models.TimeField(default='13:00:00')  # เวลาสิ้นสุดการจอง
    user = models.ForeignKey('CustomUser', null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'รอยืนยัน'),
            ('occupied', 'มีคนนั่ง'),
            ('cancelled', 'ยกเลิก')
        ],
        default='pending'
    )

    def __str__(self):
        return f"Booking for {self.table} on {self.booking_date} from {self.booking_time} to {self.booking_end_time}"

    def save(self, *args, **kwargs):
        # ตรวจสอบสถานะการจองและอัปเดตสถานะของโต๊ะ
        if self.status == 'pending':
            self.table.table_status = 'booked'
        elif self.status == 'occupied':
            self.table.table_status = 'occupied'
        elif self.status == 'cancelled':
            self.table.table_status = 'available'

        # บันทึกสถานะของโต๊ะ
        self.table.save()

        # บันทึกสถานะการจอง
        super().save(*args, **kwargs)

    

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="ชื่อประเภทอาหาร")

    def __str__(self):
        return self.name


class Menu(models.Model):
    food_name = models.CharField(max_length=100, verbose_name="ชื่ออาหาร")  # ชื่ออาหาร
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="ราคาอาหาร")  # ราคาอาหาร
    image = models.ImageField(upload_to="menu_images/",blank=True, null=True)  # ใช้ ImageField
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="ประเภทอาหาร")

    def __str__(self):
        return f"{self.food_name} - {self.category.name}"


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.menu.food_name} - {self.quantity} pcs"


User = get_user_model()

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ชื่อผู้ใช้
    table_name = models.CharField(max_length=100)  # ชื่อโต๊ะ
    booking_start = models.DateTimeField()  # เวลาเริ่มต้นการจอง
    booking_end = models.DateTimeField()  # เวลาสิ้นสุดการจอง
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # ยอดรวม
    created_at = models.DateTimeField(auto_now_add=True)  # วันที่สั่งซื้อ

    def __str__(self):
        return f"Order by {self.user.username} for table {self.table_name}"



