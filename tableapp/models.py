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
    zone = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True, blank=True)  # เชื่อมกับ Zone

    # ✅ เพิ่มฟิลด์ตำแหน่ง x, y สำหรับการลากโต๊ะ
    x_position = models.IntegerField(default=100)  # ตำแหน่ง x เริ่มต้น
    y_position = models.IntegerField(default=100)  # ตำแหน่ง y เริ่มต้น

    def save(self, *args, **kwargs):
        """ ถ้าเพิ่มโต๊ะใหม่และไม่มีค่า x, y ให้กำหนดอัตโนมัติ """
        if self.x_position == 100 and self.y_position == 100:
            last_table = Table.objects.order_by('-id').first()
            if last_table:
                self.x_position = last_table.x_position + 200
                self.y_position = last_table.y_position
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.table_name} ({self.seating_capacity} คน, {self.zone.name if self.zone else 'ไม่ระบุโซน'})"




class Booking(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    booking_date = models.DateField(default=now)
    booking_time = models.TimeField(default='12:00:00')  # เวลาจองเริ่มต้น
    booking_end_time = models.TimeField(default='13:00:00')  # เวลาสิ้นสุดการจอง
    user = models.ForeignKey('CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='bookings')
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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    table = models.ForeignKey('Table', on_delete=models.SET_NULL, null=True, blank=True)

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
    STATUS_CHOICES = [
        ('pending', 'รอยืนยัน'),
        ('in_progress', 'กำลังเตรียม'),
        ('served', 'เสิร์ฟแล้ว'),
        ('completed', 'สำเร็จ'),
        ('cancelled', 'ยกเลิก'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ เชื่อมกับ Booking โดยตรง
    table_name = models.CharField(max_length=100)
    booking_start = models.DateTimeField()
    booking_end = models.DateTimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.get_status_display()}"




class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)  # เปลี่ยนเป็น ForeignKey
    price = models.DecimalField(max_digits=6, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.menu.food_name} (x{self.quantity})"  # ดึงชื่อเมนูจาก ForeignKey
    

class Promotion(models.Model):
    PROMO_TYPE_CHOICES = [
        ('percent', 'ลดเป็น %'),
        ('fixed_price', 'กำหนดราคาตายตัว'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อโปรโมชัน")
    discount_type = models.CharField(max_length=20, choices=PROMO_TYPE_CHOICES, verbose_name="ประเภทส่วนลด")
    discount_value = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="มูลค่าส่วนลด")  # เช่น 10% หรือ 50 บาท
    start_time = models.DateTimeField(verbose_name="เริ่มโปรโมชัน")
    end_time = models.DateTimeField(verbose_name="สิ้นสุดโปรโมชัน")
    is_active = models.BooleanField(default=True, verbose_name="โปรโมชันยังใช้งานอยู่")

    def __str__(self):
        return f"{self.name} ({self.get_discount_type_display()} {self.discount_value})"

class PromotionMenu(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="promotion_menus")
    menu = models.ForeignKey('Menu', on_delete=models.CASCADE, related_name="menu_promotions")

    def __str__(self):
        return f"{self.promotion.name} - {self.menu.food_name}"


