from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import *
from datetime import datetime
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.http import Http404
import json
from django.views.decorators.csrf import csrf_exempt



def table_status_view(request):
    if request.user.is_authenticated:
        user_bookings = Booking.objects.filter(user=request.user, status="pending")
    else:
        user_bookings = None  # ผู้ใช้ที่ยังไม่ได้ล็อกอิน ไม่มีข้อมูลการจอง

    table_data = Table.objects.all()
    return render(request, "table_status.html", {
        "table_data": table_data,
        "has_active_booking": user_bookings.exists() if user_bookings else False,
    })


def booking_view(request, table_name):
    table = get_object_or_404(Table, table_name=table_name)

    if request.method == "POST":
        data = json.loads(request.body)
        booking_start = datetime.strptime(data["booking_start"], "%Y-%m-%d %H:%M")
        booking_end = datetime.strptime(data["booking_end"], "%Y-%m-%d %H:%M")

        # ตรวจสอบว่าผู้ใช้คนนี้มีการจองในช่วงเวลาเดียวกันอยู่หรือไม่
        overlapping_user_bookings = Booking.objects.filter(
            user=request.user,
            booking_date=booking_start.date(),
        ).filter(
            booking_time__lt=booking_end.time(),
            booking_end_time__gt=booking_start.time()
        )
        if overlapping_user_bookings.exists():
            return JsonResponse({"success": False, "message": "คุณมีการจองโต๊ะอยู่แล้วในช่วงเวลานี้"})

        # ตรวจสอบการจองทับซ้อนของโต๊ะ
        conflicting_bookings = Booking.objects.filter(
            table=table,
            booking_date=booking_start.date()
        ).filter(
            booking_time__lt=booking_end.time(),
            booking_end_time__gt=booking_start.time()
        )
        if conflicting_bookings.exists():
            return JsonResponse({"success": False, "message": "เวลานี้โต๊ะถูกจองแล้ว"})

        # สร้างการจองใหม่
        Booking.objects.create(
            table=table,
            booking_date=booking_start.date(),
            booking_time=booking_start.time(),
            booking_end_time=booking_end.time(),
            user=request.user,
            status='pending'  # ใช้ภาษาอังกฤษแทน
        )
        return JsonResponse({"success": True, "message": "จองโต๊ะสำเร็จ!"})

    elif request.method == "GET" and "date" in request.GET:
        # ดึงข้อมูลการจองในวันนั้น
        selected_date = request.GET.get("date")
        existing_bookings = Booking.objects.filter(table=table, booking_date=selected_date).values("booking_time", "booking_end_time")
        bookings_list = [
            {"start_time": str(booking["booking_time"]), "end_time": str(booking["booking_end_time"])}
            for booking in existing_bookings
        ]
        return JsonResponse({"bookings": bookings_list})

    return render(request, "booking.html", {"table_name": table.table_name, "seating_capacity": table.seating_capacity})


def cancel_booking(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        # ลบการจอง
        booking.delete()

        # เปลี่ยนสถานะโต๊ะกลับเป็น "ว่าง"
        booking.table.table_status = "available"
        booking.table.save()

        return redirect('my_bookings')  # กลับไปหน้าสถานะการจองของฉัน

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)



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

@never_cache
def logout_view(request):
    logout(request)
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
    print(f"UID: {uidb64}, Token: {token}")

    User = get_user_model()  # ใช้ CustomUser แทน User เริ่มต้น

    if request.user.is_authenticated:
        print("User is logged in, logging out...")
        logout(request)

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)  # ใช้ CustomUser
        print(f"User: {user.username}")

        if not default_token_generator.check_token(user, token):
            print("Token is invalid or expired")
            return render(request, 'password_reset_confirm.html', {
                'error': "The reset link is invalid or expired.",
                'uidb64': uidb64,
                'token': token
            })

        if request.method == 'POST':
            password1 = request.POST.get('new_password1')
            password2 = request.POST.get('new_password2')

            if password1 != password2:
                print("Passwords do not match")
                return render(request, 'password_reset_confirm.html', {
                    'error': "Passwords do not match.",
                    'uidb64': uidb64,
                    'token': token
                })

            try:
                validate_password(password1, user)
                user.set_password(password1)
                user.save()
                print("Password reset successful")
                update_session_auth_hash(request, user)
                return redirect('login')
            except ValidationError as e:
                print(f"Password validation failed: {e.messages}")
                return render(request, 'password_reset_confirm.html', {
                    'error': e.messages,
                    'uidb64': uidb64,
                    'token': token
                })
    except Exception as e:
        print(f"Error during password reset: {e}")
        return render(request, 'password_reset_confirm.html', {
            'error': "Invalid link.",
            'uidb64': uidb64,
            'token': token
        })

    return render(request, 'password_reset_confirm.html', {
        'uidb64': uidb64,
        'token': token
    })



@login_required(login_url='login')
def my_bookings_view(request):
    user_bookings = Booking.objects.filter(user=request.user)
    return render(request, 'my_bookings.html', {'bookings': user_bookings})

def menu_view(request):
    # รับค่าพารามิเตอร์หมวดหมู่จาก URL
    category_name = request.GET.get('category', None)

    # ค้นหาหมวดหมู่ทั้งหมด
    categories = Category.objects.all()

    if category_name:
        try:
            # ค้นหา Category instance จากชื่อ
            category = Category.objects.get(name=category_name)
            menus = Menu.objects.filter(category=category)
        except Category.DoesNotExist:
            raise Http404("หมวดหมู่ที่ระบุไม่มีอยู่ในระบบ")
    else:
        menus = Menu.objects.all()  # แสดงเมนูทั้งหมด

    context = {
        'categories': categories,
        'menus': menus,
    }
    return render(request, 'menu.html', context)

def confirm_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        booking.status = 'มีคนนั่ง'
        booking.save()
        return JsonResponse({'success': True, 'message': 'เปลี่ยนสถานะเป็นมีคนนั่งแล้ว'})
    else:
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
@login_required  # ถ้าผู้ใช้ต้องล็อกอินก่อน
def add_to_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        food_id = data.get('food_id')
        
        # ดึงเมนูจาก ID
        menu_item = get_object_or_404(Menu, id=food_id)
        
        # ถ้าไม่มีตะกร้าของผู้ใช้ ให้สร้างใหม่
        cart, created = Cart.objects.get_or_create(user=request.user, is_active=True)

        # เพิ่มสินค้าลงในตะกร้า
        cart_item, created = CartItem.objects.get_or_create(cart=cart, menu=menu_item)

        if created:
            cart_item.quantity = 1  # ตั้งค่าจำนวนสินค้าเริ่มต้นเป็น 1
            cart_item.save()

        # ส่งผลลัพธ์กลับไป
        return JsonResponse({
            'success': True,
            'food_name': menu_item.food_name
        })
    return JsonResponse({'success': False}, status=400)

