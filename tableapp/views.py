from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import *
from datetime import datetime
from .forms import CustomUserCreationForm
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import update_session_auth_hash

def table_status_view(request):
    table_data = Table.objects.all()
    has_booking = Booking.objects.filter(user=request.user).exists() if request.user.is_authenticated else False
    for table in table_data:
        booking = Booking.objects.filter(table=table).first()
        if booking and booking.user:
            table.user = booking.user
        else:
            table.user = None
    return render(request, 'table_status.html', {'table_data': table_data, 'has_booking': has_booking})

@login_required(login_url='login')
def booking_view(request, table_name):
    if request.method == 'POST':
        # รับค่าจากฟอร์ม
        datetime_str = request.POST.get('datetime')

        # ตรวจสอบว่ามีค่าของ datetime_str
        if datetime_str:
            booking_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            booking_date = booking_datetime.date()
            booking_time = booking_datetime.time()
        else:
            return render(request, 'booking.html', {'table_name': table_name, 'error': 'กรุณาระบุวันที่และเวลา'})

        # ค้นหาโต๊ะ
        table = Table.objects.filter(table_name=table_name).first()
        if not table:
            return render(request, 'booking.html', {'table_name': table_name, 'error': 'โต๊ะนี้ไม่มีอยู่ในระบบ'})

        # ตรวจสอบว่าผู้ใช้งานมีการจองโต๊ะอยู่แล้วหรือไม่
        if Booking.objects.filter(user=request.user).exists():
            return render(request, 'booking.html', {'table_name': table_name, 'error': 'คุณได้จองโต๊ะไปแล้ว'})

        # เปลี่ยนสถานะโต๊ะและบันทึกข้อมูลการจอง
        table.table_status = 'จอง'
        table.save()

        booking = Booking.objects.create(
            table=table,
            booking_date=booking_date,
            booking_time=booking_time,
            user=request.user
        )
        booking.save()

        return redirect('success')

    return render(request, 'booking.html', {'table_name': table_name})

@login_required(login_url='login')
def cancel_booking_view(request):
    if request.method == 'POST':
        table_id = request.POST.get('table_id')
        # ตรวจสอบว่าการจองนั้นเป็นของผู้ใช้ที่ล็อกอินอยู่
        booking = Booking.objects.filter(table_id=table_id, user=request.user).first()
        if booking:
            table = booking.table
            print(f"Before Cancel: Table {table.table_name} Status = {table.table_status}")
            table.table_status = 'ว่าง'
            table.save()
            print(f"After Cancel: Table {table.table_name} Status = {table.table_status}")
            booking.delete()


        return redirect('table_status')



# ฟังก์ชันแสดงหน้า success (จองโต๊ะสำเร็จ)
def success_view(request):
    return render(request, 'success.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('table_status')
            else:
                # เพิ่มการ debug ที่นี่
                print(f"Authentication failed for user: {username}")
                return render(request, 'login.html', {'error': 'Invalid username or password'})
        else:
            return render(request, 'login.html', {'error': 'Both fields are required.'})

    return render(request, 'login.html')

def logout_view(request):
    return redirect('login')  

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # ตรวจสอบความถูกต้องของข้อมูล
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'register.html')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'register.html')

        # สร้างผู้ใช้ใหม่
        user = CustomUser.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)  # Hash รหัสผ่าน
        user.save()

        messages.success(request, "Registration successful! Please login.")
        return redirect('login')  # เปลี่ยนเส้นทางไปหน้า Login หลังสมัครเสร็จ

    return render(request, 'register.html')


def password_reset_confirm_view(request, uidb64, token):
    if request.method == 'POST':
        password1 = request.POST.get('new_password1')
        password2 = request.POST.get('new_password2')

        if password1 != password2:
            return render(request, 'password_reset_confirm.html', {'error': "Passwords do not match."})

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            if default_token_generator.check_token(user, token):
                user.set_password(password1)
                user.save()
                update_session_auth_hash(request, user)  # ให้ผู้ใช้ยังล็อกอินอยู่
                return redirect('login')
            else:
                return render(request, 'password_reset_confirm.html', {'error': "The reset link is invalid or expired."})

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return render(request, 'password_reset_confirm.html', {'error': "Invalid link."})

    return render(request, 'password_reset_confirm.html', {'uidb64': uidb64, 'token': token})

def password_reset_confirm_view(request, uidb64, token):
    print(f"UID: {uidb64}, Token: {token}")
    context = {'uidb64': uidb64, 'token': token}
    return render(request, 'password_reset_confirm.html', context)


@login_required(login_url='login')
def my_bookings_view(request):
    user_bookings = Booking.objects.filter(user=request.user)
    return render(request, 'my_bookings.html', {'bookings': user_bookings})