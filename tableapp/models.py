from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.conf import settings

# tableapp/models.py
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    password = models.CharField(max_length=128)  # ใช้ฟังก์ชัน set_password สำหรับ hashing

    def __str__(self):
        return self.username


class Table(models.Model):
    table_name = models.CharField(max_length=100)
    table_status = models.CharField(max_length=20, choices=[('ว่าง', 'ว่าง'), ('กำลังนั่ง', 'กำลังนั่ง'), ('จอง', 'จอง')])

    def __str__(self):
        return self.table_name

class Booking(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    booking_date = models.DateField(default='2024-01-01')
    booking_time = models.TimeField(default='12:00:00')
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)  # ทำให้ user สามารถเป็น NULL ได้

    def __str__(self):
        return f"Booking for {self.table} on {self.booking_date} at {self.booking_time}"


class MyModel(models.Model):
    event_name = models.CharField(max_length=200)
    event_datetime = models.DateTimeField()

    def __str__(self):
        return self.event_name

