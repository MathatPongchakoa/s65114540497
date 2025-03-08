from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required,user_passes_test
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
from django.http import HttpResponseBadRequest
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import math
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import make_aware, localtime
from django.utils.timezone import localtime
from datetime import datetime
from django.utils.timezone import make_aware, localtime
from django.contrib.auth.models import AnonymousUser
from urllib.parse import urlencode
from collections import defaultdict 

from django.http import JsonResponse
from django.utils.timezone import localdate
from collections import defaultdict
from datetime import datetime
from django.shortcuts import render
from django.utils.timezone import make_aware
from .models import Order, OrderItem


def is_staff(user):
    """ตรวจสอบว่า user เป็น staff หรือไม่"""
    return user.is_staff


from django.shortcuts import render, get_object_or_404
from .models import Table, Zone, Booking
from datetime import datetime
from django.utils.timezone import make_aware

def table_status_view(request):
    selected_zone_id = request.GET.get('zone', None)
    selected_date = request.GET.get('date', None)
    selected_time = request.GET.get('time', None)

    # ✅ ถ้า selected_date เป็น None ให้ใช้วันที่ปัจจุบัน
    if not selected_date:
        selected_date = localdate().strftime("%Y-%m-%d")  # กำหนดเป็น YYYY-MM-DD

    zones = Zone.objects.all()
    tables = Table.objects.all()
    selected_zone = None
    has_active_booking = False

    if request.user.is_authenticated:
        active_booking = Booking.objects.filter(user=request.user, status="pending").first()
        has_active_booking = bool(active_booking)

    if selected_zone_id:
        selected_zone = get_object_or_404(Zone, id=selected_zone_id)
        tables = tables.filter(zone=selected_zone)

    booked_table_ids = set()

    if selected_date and selected_time:
        selected_datetime = make_aware(datetime.strptime(f"{selected_date} {selected_time}", "%Y-%m-%d %H:%M"))

        booked_tables = Booking.objects.filter(
            booking_date=selected_date,
            booking_time__lte=selected_datetime.time(),
            booking_end_time__gte=selected_datetime.time(),
            status__in=["pending", "confirmed"]
        ).values_list('table_id', flat=True)

        booked_table_ids.update(booked_tables)

    table_data = []
    for table in tables:
        if table.id in booked_table_ids:
            current_status = "booked"
        elif table.table_status == "occupied":
            current_status = "occupied"
        else:
            current_status = "available"

        x_position = table.x_position
        y_position = table.y_position

        table_data.append({
            'table_id': table.id,
            'table_name': table.table_name,
            'seating_capacity': table.seating_capacity,
            'table_status': current_status,
            'zone': table.zone.name if table.zone else None,
            'x_position': x_position,
            'y_position': y_position,
        })

    context = {
        'zones': zones,
        'selected_zone': selected_zone,
        'table_data': table_data,
        'has_active_booking': has_active_booking,
        'selected_date': selected_date,  
        'selected_time': selected_time,
    }

    return render(request, 'table_status.html', context)

from django.shortcuts import redirect

@login_required
def booking_view(request, table_name):
    table = get_object_or_404(Table, table_name=table_name)

    active_booking = Booking.objects.filter(
        user=request.user,
        table=table
    ).exclude(status="completed").first()

    selected_date = None
    booked_times = []
    time_error = None

    if request.method == "POST":
        selected_date = request.POST.get('date')

        if not selected_date:
            time_error = "กรุณาเลือกวันที่"
            return render(request, "booking.html", {
                "success": False,
                "message": time_error,
                "table_name": table.table_name,
                "seating_capacity": table.seating_capacity,
                "active_booking": active_booking,
                "selected_date": selected_date,
                "booked_times": booked_times,
            })

        try:
            selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()

            # กรองการจองจากฐานข้อมูลในวันที่เลือก
            booked_times = Booking.objects.filter(
                table=table,
                booking_date=selected_date_obj
            ).values("booking_time", "booking_end_time")

            # ใช้ Paginator เพื่อแบ่งหน้าของรายการ
            paginator = Paginator(booked_times, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            # สร้าง list ของการจอง
            booked_times_list = list(page_obj)

            # เพิ่มข้อมูลการจองใหม่ถ้าผู้ใช้ยังไม่เคยจอง
            booking_time = request.POST.get('booking_time')
            booking_end_time = request.POST.get('booking_end_time')

            # ตรวจสอบการจอง
            if not active_booking:
                if booking_time and booking_end_time:
                    new_booking = Booking(
                        user=request.user,
                        table=table,  # เพิ่มการส่ง table_id
                        booking_date=selected_date_obj,
                        booking_time=booking_time,
                        booking_end_time=booking_end_time,
                        status="pending"
                    )
                    new_booking.save()
                    active_booking = new_booking

                    # ตั้งค่า table_id ใน Cart หากยังไม่มี
                    cart = Cart.objects.filter(user=request.user, is_active=True).first()
                    if cart:
                        cart.table = table  # เพิ่ม table_id ใน Cart
                        cart.save()

                    # หลังจากการจองสำเร็จ, ควรทำการเปลี่ยนเส้นทางไปยังหน้า my_bookings
                    return redirect('my_bookings')  # ใช้ URL ที่ถูกต้องสำหรับ my_bookings

        except ValueError:
            booked_times = []

    return render(request, "booking.html", {
        "table_name": table.table_name,
        "seating_capacity": table.seating_capacity,
        "active_booking": active_booking,
        "selected_date": selected_date,
        "booked_times": booked_times,
        "page_obj": page_obj,
    })







@login_required
def cancel_booking(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        booking_start = make_aware(datetime.combine(booking.booking_date, booking.booking_time))
        booking_end = make_aware(datetime.combine(booking.booking_date, booking.booking_end_time))

        related_orders = Order.objects.filter(
            user=request.user,
            table_name=booking.table.table_name,
            booking_start__gte=booking_start - timedelta(seconds=1),
            booking_start__lt=booking_start + timedelta(seconds=1)
        )

        if related_orders.exists():
            related_orders.update(status="cancelled")

        Cart.objects.filter(user=request.user).delete()

        table = booking.table
        other_active_bookings = Booking.objects.filter(
            table=table,
            status__in=["occupied", "pending"]
        ).exclude(id=booking.id)

        if not other_active_bookings.exists():
            table.table_status = "available"
        elif other_active_bookings.filter(status="occupied").exists():
            table.table_status = "occupied"
        elif other_active_bookings.filter(status="pending").exists():
            table.table_status = "booked"

        table.save()
        booking.delete()

        return redirect('my_bookings')

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)




def login_view(request):
    errors = {}  # ✅ กำหนดค่าให้ errors ตั้งแต่ต้น
    username = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        # ✅ ตรวจสอบว่าช่องกรอกข้อมูลว่างหรือไม่
        if not username:
            errors["username"] = "กรุณากรอกชื่อผู้ใช้"

        if not password:
            errors["password"] = "กรุณากรอกรหัสผ่าน"

        # ✅ ถ้าช่องไหนว่าง ให้ส่ง errors กลับไปที่ login.html
        if errors:
            return render(request, "login.html", {"errors": errors, "username": username})

        # ✅ ตรวจสอบว่า Username มีอยู่จริงหรือไม่
        if not User.objects.filter(username=username).exists():
            errors["username"] = "ไม่มีชื่อผู้ใช้ในระบบ"
            return render(request, "login.html", {"errors": errors, "username": username})

        # ✅ ตรวจสอบข้อมูลผู้ใช้
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect("sales_report")  # Redirect ไปยังหน้า รายงานยอดขาย สำหรับเจ้าของร้าน
            elif user.is_staff:
                return redirect("table_management")  # Redirect ไปยัง table_management สำหรับ staff
            else:
                return redirect("table_status")  # Redirect ไปยัง table_status สำหรับผู้ใช้ทั่วไป
        else:
            errors["password"] = "รหัสผ่านไม่ถูกต้อง"

    return render(request, "login.html", {"errors": errors, "username": username})

@never_cache
def logout_view(request):
    logout(request)
    return redirect('/')

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        errors = {}

        # ✅ ตรวจสอบว่ามีฟิลด์ไหนว่างหรือไม่
        if not all([username, email, first_name, last_name, password, confirm_password]):
            errors["form"] = "กรุณากรอกข้อมูลให้ครบทุกช่อง"

        # ✅ ตรวจสอบว่ารหัสผ่านและยืนยันรหัสผ่านตรงกันหรือไม่
        if password != confirm_password:
            errors["confirm_password"] = "รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน"

        # ✅ ตรวจสอบว่ามี username หรือ email ซ้ำหรือไม่
        if CustomUser.objects.filter(username=username).exists():
            errors["username"] = "ชื่อผู้ใช้นี้ถูกใช้แล้ว กรุณาใช้ชื่ออื่น"

        if CustomUser.objects.filter(email=email).exists():
            errors["email"] = "อีเมลนี้ถูกใช้แล้ว กรุณาใช้อีเมลอื่น"

        # ❌ ถ้ามีข้อผิดพลาด → ส่ง error กลับไปแสดงที่หน้า `register.html`
        if errors:
            return render(request, "register.html", {
                "errors": errors,
                "username": username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            })

        # ✅ ถ้าข้อมูลถูกต้อง → สร้างบัญชีผู้ใช้ใหม่
        user = CustomUser.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)  # เข้ารหัสรหัสผ่าน
        user.save()

        return render(request, "register.html", {"success": "ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ"})

    return render(request, "register.html")


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
    user_bookings = Booking.objects.filter(user=request.user).exclude(status="completed")
    return render(request, 'my_bookings.html', {'bookings': user_bookings})

def menu_view(request):
    # รับค่าพารามิเตอร์หมวดหมู่จาก URL
    category_name = request.GET.get('category', None)
    categories = Category.objects.all()

    # ตรวจสอบสถานะการจองของผู้ใช้งาน (เฉพาะเมื่อ Login)
    active_booking = None
    if request.user.is_authenticated:
        active_booking = Booking.objects.filter(user=request.user, status="pending").first()

    # ดึงเมนูตามหมวดหมู่ที่เลือก
    if category_name:
        try:
            category = Category.objects.get(name=category_name)
            menus = Menu.objects.filter(category=category)
        except Category.DoesNotExist:
            raise Http404("หมวดหมู่ที่ระบุไม่มีอยู่ในระบบ")
    else:
        menus = Menu.objects.all()

    # ดึงโปรโมชันที่กำลังใช้งาน
    active_promotions = Promotion.objects.filter(is_active=True, start_time__lte=now(), end_time__gte=now())

    # คำนวณราคาส่วนลดให้ถูกต้อง
    menu_data = []
    for menu in menus:
        promo = active_promotions.filter(promotion_menus__menu=menu).first()
        if promo:
            if promo.discount_type == "percentage":
                discounted_price = round(menu.price * (1 - (promo.discount_value / 100)), 2)
            else:
                discounted_price = round(max(0, menu.price - promo.discount_value), 2)
        else:
            discounted_price = menu.price

        menu_data.append({
            "menu": menu,
            "discounted_price": discounted_price,
            "promotion": promo,
        })

    # แบ่งหน้า (Pagination)
    paginator = Paginator(menu_data, 8)  # 8 เมนูต่อหน้า
    page = request.GET.get('page')

    try:
        menu_data = paginator.page(page)
    except PageNotAnInteger:
        menu_data = paginator.page(1)  # ถ้าไม่มีหน้าที่เลือกให้ไปที่หน้าหมายเลข 1
    except EmptyPage:
        menu_data = paginator.page(paginator.num_pages)  # ถ้าเกินหน้าที่มีให้ไปที่หน้าสุดท้าย

    # ส่งค่าไปยัง template
    context = {
        'categories': categories,
        'menus': menu_data,
        'active_booking': active_booking,  # ตอนนี้จะไม่พังถ้ายังไม่ Login
        'category_name': category_name,
    }
    return render(request, 'menu.html', context)


def confirm_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        # เปลี่ยนสถานะการจองเป็น "มีคนนั่ง"
        booking.status = 'occupied'
        booking.save()

        # ตรวจสอบสถานะโต๊ะ
        table = booking.table
        if table.table_status != "occupied":
            table.table_status = "occupied"  # เปลี่ยนสถานะโต๊ะเป็น "occupied"
            table.save()

        # อัปเดตสถานะออเดอร์ที่เกี่ยวข้อง
        related_order = Order.objects.filter(
            user=booking.user,
            table_name=table.table_name,
            booking_start__date=booking.booking_date
        ).first()
        if related_order and related_order.status == 'pending':
            related_order.status = 'in_progress'
            related_order.save()

        return JsonResponse({'success': True, 'message': 'เปลี่ยนสถานะเป็นมีคนนั่งและเริ่มเตรียมออเดอร์แล้ว'})
    else:
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


    
@login_required
def add_to_cart(request):
    if request.method == "POST":
        active_booking = Booking.objects.filter(user=request.user, status="pending").first()
        if not active_booking:
            return JsonResponse({"success": False, "message": "คุณต้องจองโต๊ะก่อนสั่งอาหาร"}, status=403)

        menu_id = request.POST.get("food_id")
        if not menu_id:
            return JsonResponse({"success": False, "message": "ไม่พบเมนูที่เลือก"}, status=400)

        try:
            menu_item = Menu.objects.get(id=menu_id)

            # ตรวจสอบโปรโมชันที่ใช้งาน
            active_promotion = Promotion.objects.filter(
                is_active=True,
                start_time__lte=now(),
                end_time__gte=now(),
                promotion_menus__menu=menu_item
            ).first()

            # คำนวณราคาหลังหักส่วนลด
            if active_promotion:
                if active_promotion.discount_type == "percentage":
                    discounted_price = round(menu_item.price * (1 - (active_promotion.discount_value / 100)), 2)
                else:
                    discounted_price = round(max(0, menu_item.price - active_promotion.discount_value), 2)
            else:
                discounted_price = menu_item.price

            # เพิ่มสินค้าเข้าตะกร้า
            cart, created = Cart.objects.get_or_create(user=request.user, is_active=True)

            # ตรวจสอบว่ามีการตั้งค่า table_id ใน Cart หรือไม่
            if not cart.table:  # ถ้า table_id ยังไม่ได้ถูกตั้งค่าใน Cart
                cart.table = active_booking.table  # ใช้ table ที่ผู้ใช้จอง
                cart.save()

            cart_item, created = CartItem.objects.get_or_create(cart=cart, menu=menu_item)

            if not created:
                cart_item.quantity += 1  # เพิ่มจำนวนสินค้า
            cart_item.price = discounted_price  # ใช้ราคาหลังหักส่วนลด
            cart_item.save()

            return JsonResponse({
                "success": True,
                "food_name": menu_item.food_name,
                "discounted_price": discounted_price
            })

        except Menu.DoesNotExist:
            return JsonResponse({"success": False, "message": "เมนูไม่พบ"}, status=404)

    return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

def cart_view(request):
    if not request.user.is_authenticated:
        return redirect(f'/login/?next={request.path}')

    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    cart_items = cart.items.all() if cart else []

    total_price = 0
    updated_cart_items = []

    for item in cart_items:
        promo = Promotion.objects.filter(
            is_active=True, 
            start_time__lte=now(), 
            end_time__gte=now(),
            promotion_menus__menu=item.menu
        ).first()

        original_price = item.menu.price

        if promo:
            if promo.discount_type == "percentage":
                discounted_price = item.menu.price * (1 - (promo.discount_value / 100))
            else:
                discounted_price = max(0, item.menu.price - promo.discount_value)
        else:
            discounted_price = item.menu.price

        item.original_price = original_price
        item.discounted_price = discounted_price
        item.total_price = discounted_price * item.quantity

        total_price += item.total_price
        updated_cart_items.append(item)

    context = {
        "cart_items": updated_cart_items,
        "total_price": total_price,
    }

    return render(request, "cart.html", context)


@csrf_exempt
def update_cart_item(request, item_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")

            # ค้นหา CartItem
            cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)

            if action == "increase":
                cart_item.quantity += 1
                cart_item.save()
            elif action == "decrease":
                if cart_item.quantity > 1:
                    cart_item.quantity -= 1
                    cart_item.save()
                else:
                    cart_item.delete()  # ลบสินค้าออกหากจำนวนลดเป็น 0
            elif action == "remove":
                cart_item.delete()

            return JsonResponse({"success": True})
        except CartItem.DoesNotExist:
            return JsonResponse({"success": False, "error": "ไม่พบสินค้าในตะกร้า"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})




@staff_member_required
def table_management_view(request):
    tables = Table.objects.select_related('zone').all()
    zones = Zone.objects.all()
    table_data = []

    for table in tables:
        seating_capacity = table.seating_capacity
        chairs = []
        radius = 70

        for i in range(seating_capacity):
            angle = (360 / seating_capacity) * i
            angle_rad = math.radians(angle)
            x = 100 + radius * math.cos(angle_rad)
            y = 100 + radius * math.sin(angle_rad)
            chairs.append({'x': x, 'y': y})

        # 🔹 ไม่ต้องเพิ่ม 20 ที่ y_position
        x_position = table.x_position if table.x_position is not None else 0
        y_position = table.y_position if table.y_position is not None else 0

        table_data.append({
            'table_id': table.id,
            'table_name': table.table_name,
            'seating_capacity': table.seating_capacity,
            'table_status': table.table_status,
            'zone': table.zone.name if table.zone else "ไม่ระบุโซน",
            'chairs': chairs,
            'x_position': x_position,  # ✅ ค่าที่ได้จาก DB ตรง ๆ
            'y_position': y_position,  # ✅ ค่าที่ได้จาก DB ตรง ๆ
        })

    return render(request, 'owner/table_management.html', {
        'table_data': table_data,
        'zones': zones
    })

@csrf_exempt
@staff_member_required
def update_table_position_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            tables = data.get("tables", [])

            if tables:
                for table_data in tables:
                    table_id = table_data.get("tableId")
                    new_x = table_data.get("x_position")
                    new_y = table_data.get("y_position")

                    if table_id is None or new_x is None or new_y is None:
                        continue

                    new_x = float(new_x)
                    new_y = float(new_y)

                    try:
                        table = Table.objects.get(id=table_id)
                        table.x_position = new_x
                        table.y_position = new_y
                        table.save()
                    except Table.DoesNotExist:
                        continue

                return JsonResponse({"success": True, "message": "ตำแหน่งโต๊ะอัปเดตเรียบร้อยแล้ว"})
            else:
                return JsonResponse({"success": True, "message": "ไม่มีข้อมูลการเปลี่ยนแปลงตำแหน่งโต๊ะ"})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "JSON ไม่ถูกต้อง"}, status=400)

    return JsonResponse({"success": False, "message": "Method Not Allowed"}, status=405)


@login_required
@user_passes_test(is_staff, login_url='login')
def add_table_view(request):
    if request.method == 'POST':
        table_name = request.POST.get('table_name')
        seating_capacity = request.POST.get('seating_capacity')
        zone_id = request.POST.get('zone')  # รับค่าโซนจากฟอร์ม

        errors = {}

        # ตรวจสอบข้อมูล
        if not table_name:
            errors['table_name'] = "กรุณากรอกชื่อโต๊ะ"
        if not seating_capacity:
            errors['seating_capacity'] = "กรุณากรอกจำนวนที่นั่ง"
        if not zone_id:
            errors['zone'] = "กรุณาเลือกโซน"

        # หากมีข้อผิดพลาดให้แสดงในฟอร์ม
        if errors:
            zones = Zone.objects.all()  # ดึงข้อมูลโซนทั้งหมดสำหรับ dropdown
            return render(request, 'owner/add_table.html', {'zones': zones, 'errors': errors, 'table_name': table_name, 'seating_capacity': seating_capacity, 'zone_id': zone_id})

        # ตรวจสอบว่าโซนที่เลือกมีอยู่หรือไม่
        zone = Zone.objects.filter(id=zone_id).first()

        # สร้างโต๊ะใหม่
        Table.objects.create(
            table_name=table_name,
            seating_capacity=seating_capacity,
            zone=zone  # กำหนดโซน
        )
        return redirect('table_management')  # Redirect กลับไปยังหน้าการจัดการโต๊ะ

    zones = Zone.objects.all()  # ดึงข้อมูลโซนทั้งหมดสำหรับ dropdown
    return render(request, 'owner/add_table.html', {'zones': zones})


def manage_table_view(request, table_id):
    # ดึงข้อมูลโต๊ะตาม ID
    table = get_object_or_404(Table, id=table_id)

    if request.method == 'POST':
        new_status = request.POST.get('table_status')
        if new_status in ['available', 'occupied', 'booked']:
            if new_status == 'available':
                # ตรวจสอบการจองในอนาคต
                future_bookings = Booking.objects.filter(
                    table=table,
                    booking_date__gte=datetime.now().date(),
                    booking_time__gte=datetime.now().time(),
                    status='pending'
                )
                if future_bookings.exists():
                    # แจ้งเตือนผู้ใช้หากมีการจองในอนาคต
                    return render(request, 'owner/manage_table.html', {
                        'table': table,
                        'error_message': "ไม่สามารถเปลี่ยนสถานะเป็น 'ว่าง' ได้ เนื่องจากมีการจองในอนาคต"
                    })

            # อัปเดตสถานะโต๊ะ
            table.table_status = new_status
            table.save()
            return redirect('table_management')  # กลับไปหน้าการจัดการโต๊ะ

    return render(request, 'owner/manage_table.html', {'table': table})


def booked_tables_view(request):
    # ดึงข้อมูลโต๊ะทั้งหมด
    tables = Table.objects.prefetch_related('booking_set')

    # เตรียมข้อมูลสำหรับแสดงผล
    table_data = []
    for table in tables:
        # ✅ กรอง `status='complete'` ออก
        bookings = table.booking_set.exclude(status='completed').order_by('booking_date', 'booking_time')

        # ✅ กำหนดสถานะโต๊ะตามการจอง
        if table.table_status == "occupied":
            display_status = "occupied"
        elif bookings.exists():
            display_status = "booked"
        else:
            display_status = "available"

        table_data.append({
            'table_id': table.id,  # ✅ ส่ง ID ไปด้วย
            'table_name': table.table_name,
            'seating_capacity': table.seating_capacity,
            'bookings': bookings,
            'table_status': display_status,
        })

    return render(request, 'owner/booked_tables.html', {'table_data': table_data})



@csrf_exempt
@login_required
def change_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == "POST":
        new_status = request.POST.get("status")

        if new_status in ["occupied", "completed"]:
            booking.status = new_status
            booking.save()

            table = booking.table

            if new_status == "occupied" and table.table_status != "occupied":
                table.table_status = "occupied"
                table.save()

            elif new_status == "completed" and table.table_status != "available":
                table.table_status = "available"
                table.save()

            booking_start = make_aware(datetime.combine(booking.booking_date, booking.booking_time))

            related_orders = Order.objects.filter(
                user=booking.user,
                table_name=table.table_name,
                booking_start__range=[booking_start - timedelta(seconds=2), booking_start + timedelta(seconds=2)]
            )

            if related_orders.exists():
                for order in related_orders:
                    if new_status == "occupied" and order.status == "pending":
                        order.status = "in_progress"
                        order.save()
                    elif new_status == "completed" and order.status != "completed":
                        order.status = "completed"
                        order.save()

    return redirect('booked_tables')

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def add_zone_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        image = request.FILES.get('image')  # รองรับรูปภาพ (ถ้ามี)

        Zone.objects.create(name=name, description=description, image=image)
        return redirect('zone_management')  # Redirect ไปยังหน้าจัดการโซน

    return render(request, 'owner/add_zone.html')


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def zone_management_view(request):
    zones = Zone.objects.all()
    return render(request, 'owner/zone_management.html', {'zones': zones})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def edit_zone_view(request, zone_id):
    zone = get_object_or_404(Zone, id=zone_id)

    if request.method == 'POST':
        zone.name = request.POST.get('name')
        zone.description = request.POST.get('description')
        if 'image' in request.FILES:  # หากมีการอัปโหลดรูปใหม่
            zone.image = request.FILES['image']
        zone.save()
        return redirect('zone_management')

    return render(request, 'owner/edit_zone.html', {'zone': zone})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def delete_zone_view(request, zone_id):
    zone = get_object_or_404(Zone, id=zone_id)
    zone.delete()
    return redirect('zone_management')

def add_menu_view(request):
    if request.method == 'POST':
        food_name = request.POST.get('food_name').strip()
        price = request.POST.get('price')
        category_name = request.POST.get('category').strip()
        image = request.FILES.get('image')

        # ✅ ตรวจสอบค่าที่รับมา
        if not food_name or not price:
            query_params = urlencode({'error': 'กรุณากรอกชื่ออาหารและราคา'})
            return redirect(f"/add-menu/?{query_params}")

        # ✅ ตรวจสอบว่ามีเมนูนี้อยู่แล้วหรือไม่
        if Menu.objects.filter(food_name=food_name).exists():
            query_params = urlencode({'error': 'เมนูนี้มีอยู่ในระบบแล้ว!'})
            return redirect(f"/add-menu/?{query_params}")

        # ✅ ตรวจสอบหรือสร้างหมวดหมู่
        category, created = Category.objects.get_or_create(name=category_name)

        # ✅ สร้างเมนูใหม่
        Menu.objects.create(
            food_name=food_name,
            price=price,
            category=category,
            image=image
        )

        # ✅ ใช้ Query Parameter เพื่อส่งค่า success แทน messages
        query_params = urlencode({'success': 'true'})
        return redirect(f"/add-menu/?{query_params}")

    return render(request, 'owner/add_menu.html')

def menu_management_view(request):
    # ดึงข้อมูลทั้งหมดจาก Menu
    menus = Menu.objects.all()

    # สร้าง Paginator เพื่อแบ่งหน้าละ 10 เมนู
    paginator = Paginator(menus, 8)  # 10 เมนูต่อหน้า

    # รับหมายเลขหน้าจาก request
    page_number = request.GET.get('page')  # ใช้ GET parameter ที่ชื่อว่า 'page'

    # ดึงเมนูในหน้าปัจจุบัน
    page_obj = paginator.get_page(page_number)

    # ส่งข้อมูลไปยัง template
    return render(request, 'owner/menu_management.html', {'page_obj': page_obj})

def edit_menu_view(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)

    if request.method == 'POST':
        food_name = request.POST.get('food_name')
        price = request.POST.get('price')
        category_name = request.POST.get('category_name')
        image = request.FILES.get('image')

        category, created = Category.objects.get_or_create(name=category_name)

        menu.food_name = food_name
        menu.price = price
        menu.category = category

        if image:
            menu.image = image

        menu.save()

        # ✅ ส่งตัวแปร success ให้ template แทน redirect ทันที
        return render(request, 'owner/edit_menu.html', {
            'menu': menu,
            'categories': Category.objects.all(),
            'success': True  # ✅ ส่งตัวแปร success ไปใช้ใน template
        })

    return render(request, 'owner/edit_menu.html', {'menu': menu, 'categories': Category.objects.all()})


def delete_menu(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)
    menu.delete()
    return redirect('menu_management')

def check_reservation(request):
    if request.user.is_authenticated:
        # ใช้ related_name เพื่อเข้าถึงการจอง
        booking = request.user.bookings.filter(status='pending').first()
        if booking:
            return JsonResponse({
                "has_reservation": True,
                "table_name": booking.table.table_name
            })
    return JsonResponse({"has_reservation": False})

@login_required
def confirm_orders(request):
    if request.method == "POST":
        try:
            cart = Cart.objects.get(user=request.user, is_active=True)
        except Cart.DoesNotExist:
            return JsonResponse({"success": False, "error": "ไม่มีตะกร้าที่ใช้งานอยู่"}, status=404)

        if not cart.table:
            return JsonResponse({"success": False, "error": "กรุณาจองโต๊ะก่อนทำการสั่งซื้อ"}, status=400)

        try:
            booking = Booking.objects.get(user=request.user, table=cart.table, status="pending")
        except Booking.DoesNotExist:
            return JsonResponse({"success": False, "error": "ไม่พบการจองที่เกี่ยวข้อง"}, status=404)

        booking_start = make_aware(datetime.combine(booking.booking_date, booking.booking_time))
        booking_end = make_aware(datetime.combine(booking.booking_date, booking.booking_end_time))

        order = Order.objects.filter(user=request.user, status="pending").first()

        if order:
            total_price = order.total_price
        else:
            order = Order.objects.create(
                user=request.user,
                table_name=cart.table.table_name,
                booking_start=booking_start,
                booking_end=booking_end,
                total_price=0
            )
            total_price = 0

        for item in cart.items.all():
            promo = Promotion.objects.filter(
                is_active=True,
                start_time__lte=now(),
                end_time__gte=now(),
                promotion_menus__menu=item.menu
            ).first()

            if promo:
                if promo.discount_type == "percentage":
                    discounted_price = item.menu.price * (1 - (promo.discount_value / 100))
                else:
                    discounted_price = max(0, item.menu.price - promo.discount_value)
            else:
                discounted_price = item.menu.price

            total_item_price = discounted_price * item.quantity
            total_price += total_item_price

            order_item = OrderItem.objects.filter(order=order, menu=item.menu).first()

            if order_item:
                order_item.quantity += item.quantity
                order_item.price = discounted_price
                order_item.save()
            else:
                OrderItem.objects.create(
                    order=order,
                    menu=item.menu,
                    price=discounted_price,
                    quantity=item.quantity
                )

            try:
                item.delete()
            except Exception as e:
                return JsonResponse({"success": False, "error": str(e)}, status=400)

        order.total_price = total_price
        order.save()

        return JsonResponse({"success": True, "message": "การสั่งซื้อสำเร็จ!", "redirect_url": '/order-summary/'})







@login_required(login_url='login')
def order_summary(request):
    # ✅ ดึงเฉพาะคำสั่งซื้อที่ยังไม่ถูกยกเลิก
    orders_list = Order.objects.filter(user=request.user).exclude(status="cancelled").order_by('-created_at')

    # ✅ ตั้งค่า Paginator ให้แสดง 10 ออเดอร์ต่อหน้า
    paginator = Paginator(orders_list, 10)  # แสดง 10 รายการต่อหน้า
    page_number = request.GET.get('page')  # ดึงหมายเลขหน้าจาก URL
    orders = paginator.get_page(page_number)  # ดึงออเดอร์ของหน้านั้นๆ

    context = {
        "orders": orders,
    }
    return render(request, "order_summary.html", context)

@never_cache
@login_required(login_url='login')
def order_management(request):
    orders_list = Order.objects.prefetch_related('items').exclude(status="cancelled").order_by('-created_at')

    for order in orders_list:
        
        if order.booking_start:
            order.booking_start_local = localtime(order.booking_start)
            order.booking_date = order.booking_start_local.date()
            order.booking_time = order.booking_start_local.time()
        else:
            order.booking_date = None
            order.booking_time = None

    paginator = Paginator(orders_list, 10)
    page = request.GET.get('page')

    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    return render(request, "owner/order_management.html", {"orders": orders})

@login_required
def update_order_status(request, order_id, new_status):
    # ดึงข้อมูล Order ที่ต้องการแก้ไข
    order = get_object_or_404(Order, id=order_id)

    # ตรวจสอบว่าสถานะที่ส่งมาเป็นสถานะที่อนุญาต
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()
        messages.success(request, f"สถานะออเดอร์ ID {order_id} เปลี่ยนเป็น '{dict(Order.STATUS_CHOICES).get(new_status)}'")

        # ✅ ถ้าออเดอร์สำเร็จ ("completed") ให้ลบ Cart ของผู้ใช้งาน
        if new_status == "completed":
            Cart.objects.filter(user=order.user).delete()
    else:
        messages.error(request, "สถานะที่ระบุไม่ถูกต้อง")

    return redirect('order_management')  # เปลี่ยนเป็น URL ที่เหมาะสม

def promotion_list(request):
    promotions = Promotion.objects.all()
    for promo in promotions:
       print(f"Promotion: {promo.name}, Type: {promo.discount_type}, Value: {promo.discount_value}")

    promotion_menus = PromotionMenu.objects.select_related("promotion", "menu").all()
    
    return render(request, "owner/promotion_list.html", {
        "promotions": promotions,
        "promotion_menus": promotion_menus
    })

@login_required
@user_passes_test(is_staff, login_url='login')
def add_promotion(request):
    if request.method == "POST":
        data = request.POST
        promo_name = data.get("promo_name")
        discount_type = data.get("discount_type")
        discount_value = data.get("discount_value")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        selected_menus = request.POST.getlist("selected_menus")

        # ตรวจสอบว่าโปรโมชันที่มีชื่อเดียวกันมีอยู่แล้วหรือไม่
        if Promotion.objects.filter(name=promo_name).exists():
            messages.error(request, f"❌ โปรโมชันชื่อ '{promo_name}' นี้มีอยู่แล้วในระบบ!")
            return redirect("add_promotion")  # Redirect กลับไปหน้าฟอร์ม

        # ตรวจสอบว่าเมนูมีโปรโมชันอยู่แล้วหรือไม่
        existing_promos = PromotionMenu.objects.filter(menu_id__in=selected_menus).select_related("menu")
        existing_menu_names = [promo.menu.food_name for promo in existing_promos]

        if existing_menu_names:
            messages.error(request, f"❌ เมนู {', '.join(existing_menu_names)} มีโปรโมชันอยู่แล้ว!")
            return redirect("add_promotion")  # Redirect กลับไปหน้าฟอร์ม

        # สร้างโปรโมชันใหม่
        promotion = Promotion.objects.create(
            name=promo_name,
            discount_type=discount_type,
            discount_value=discount_value,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )

        # เพิ่มเมนูที่เลือกเข้าไปใน `PromotionMenu`
        for menu_id in selected_menus:
            menu = Menu.objects.get(id=menu_id)
            PromotionMenu.objects.create(promotion=promotion, menu=menu)

        messages.success(request, "✅ เพิ่มโปรโมชันสำเร็จ!")
        return redirect("add_promotion")  # Redirect ไปหน้าโปรโมชัน

    categories = Category.objects.all()
    return render(request, "owner/add_promotion.html", {"categories": categories})


def get_menus_by_category(request):
    category_id = request.GET.get("category_id")
    if category_id:
        menus = Menu.objects.filter(category_id=category_id).values("id", "food_name")
        return JsonResponse({"menus": list(menus)})
    return JsonResponse({"menus": []})


def delete_promotion(request, promo_id):
    if request.method == "POST":
        promo = get_object_or_404(Promotion, id=promo_id)
        promo.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)

def user_promotion_list(request):
    promotions = Promotion.objects.filter(is_active=True, start_time__lte=now(), end_time__gte=now())

    context = {
        "promotions": promotions
    }
    return render(request, "user_promotion_list.html", context)

def edit_promotion(request, promo_id):
    promo = get_object_or_404(Promotion, id=promo_id)

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            promo.name = data.get("name", promo.name)
            promo.discount_value = data.get("discount_value", promo.discount_value)
            promo.start_time = data.get("start_time", promo.start_time)
            promo.end_time = data.get("end_time", promo.end_time)

            new_discount_type = data.get("discount_type", promo.discount_type)
            if new_discount_type in ["percentage", "fixed"]:
                promo.discount_type = new_discount_type

            promo.save()

            return JsonResponse({"success": True, "message": "อัปเดตโปรโมชันเรียบร้อย!"})

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=400)

    return render(request, "owner/edit_promotion.html", {"promo": promo})

@csrf_exempt
def delete_table(request, table_id):
    if request.method == "POST":
        try:
            table = Table.objects.get(id=table_id)
            table_name = table.table_name  # ✅ ดึงชื่อโต๊ะก่อนลบ
            table.delete()
            return JsonResponse({"success": True, "message": f"ลบโต๊ะ {table_name} สำเร็จ!", "redirect_url": "/table-management/"})
        except Table.DoesNotExist:
            return JsonResponse({"success": False, "message": "ไม่พบโต๊ะที่ต้องการลบ"}, status=404)
    return JsonResponse({"success": False, "message": "Method Not Allowed"}, status=405)


def edit_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    zones = Zone.objects.all()  # ✅ ดึงโซนทั้งหมด

    if request.method == 'POST':
        table.table_name = request.POST.get('table_name')

        # ✅ ดึง Zone จาก ID
        zone_id = request.POST.get('zone')
        table.zone = Zone.objects.get(id=zone_id) if zone_id else None  # ตรวจสอบว่ามีค่าหรือไม่

        table.table_status = request.POST.get('table_status')
        table.seating_capacity = request.POST.get('seating_capacity')
        table.save()

        return redirect('table_management')

    return render(request, 'owner/edit_table.html', {'table': table, 'zones': zones})  # ✅ ส่ง zones ไป template



def sales_report_view(request):
    selected_date = request.GET.get('date', None)
    menu_sales = defaultdict(lambda: {'quantity': 0, 'total_price': 0})
    total_sales = 0

    if selected_date:
        try:
            # แปลงวันที่ให้เป็น Timezone-aware datetime
            date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
            date_aware_start = make_aware(date_obj)
            date_aware_end = date_aware_start + timedelta(days=1)

            # ดึง `completed orders` ที่สร้างในวันนั้น
            completed_orders = Order.objects.filter(
                status="completed",
                created_at__range=(date_aware_start, date_aware_end)
            ).order_by('-created_at')

            if completed_orders.exists():
                order_items = OrderItem.objects.filter(order__in=completed_orders).select_related('menu')

                for item in order_items:
                    menu_name = item.menu.food_name
                    menu_sales[menu_name]['quantity'] += item.quantity
                    menu_sales[menu_name]['total_price'] += item.price * item.quantity
                    total_sales += item.price * item.quantity

        except ValueError:
            selected_date = None

    # ส่งข้อมูลกราฟไปยังเทมเพลต
    menu_sales_data = {
    "labels": [menu_name for menu_name in menu_sales.keys()],
    "data": [float(data['total_price']) for data in menu_sales.values()],  # แปลง Decimal เป็น float
}
    print(menu_sales_data)

    context = {
        "report_type": "daily",  # รายงานรายวัน
        "menu_sales": dict(menu_sales),
        "total_sales": total_sales,
        "selected_date": selected_date,
        "menu_sales_data": menu_sales_data,  # ส่งข้อมูลกราฟ
    }

    return render(request, "owner/sales_report.html", context)

def monthly_sales_report_view(request):
    selected_month = request.GET.get("month", None)
    selected_year = request.GET.get("year", None)
    menu_sales = defaultdict(lambda: {"quantity": 0, "total_price": 0})
    total_sales = 0

    current_year = datetime.now().year
    years = list(range(current_year - 10, current_year + 1))

    months = {
        1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
        5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
        9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
    }

    selected_month_name = None
    monthly_sales_data = [0] * 12  # Initialize list for monthly sales data
    months_in_year = [month_name for month_number, month_name in months.items()]  # Create list of month names

    # เพิ่มการตรวจสอบค่า selected_month และ selected_year
    if selected_month and selected_year:
        try:
            selected_month = int(selected_month)
            selected_year = int(selected_year)

            start_date = make_aware(datetime(selected_year, selected_month, 1))
            if selected_month == 12:
                end_date = make_aware(datetime(selected_year + 1, 1, 1))
            else:
                end_date = make_aware(datetime(selected_year, selected_month + 1, 1))

            completed_orders = Order.objects.filter(
                status="completed",
                created_at__gte=start_date,
                created_at__lt=end_date
            ).order_by("-created_at")

            if completed_orders.exists():
                order_items = OrderItem.objects.filter(order__in=completed_orders).select_related("menu")

                for item in order_items:
                    menu_name = item.menu.food_name
                    menu_sales[menu_name]["quantity"] += item.quantity
                    menu_sales[menu_name]["total_price"] += item.price * item.quantity
                    total_sales += item.price * item.quantity

            selected_month_name = months.get(selected_month, "")

        except ValueError:
            selected_month = None
            selected_year = None

    # Generate sales data for each month of the year
    for month in range(1, 13):
        if selected_year is not None:
            start_date = make_aware(datetime(selected_year, month, 1))
            if month == 12:
                end_date = make_aware(datetime(selected_year + 1, 1, 1))
            else:
                end_date = make_aware(datetime(selected_year, month + 1, 1))

            completed_orders = Order.objects.filter(
                status="completed",
                created_at__gte=start_date,
                created_at__lt=end_date
            )

            total_month_sales = 0
            if completed_orders.exists():
                order_items = OrderItem.objects.filter(order__in=completed_orders).select_related("menu")
                for item in order_items:
                    total_month_sales += item.price * item.quantity

            # ถ้าไม่มีข้อมูลยอดขายในเดือนนั้น กำหนดให้เป็น 0
            monthly_sales_data[month - 1] = int(total_month_sales) if total_month_sales > 0 else 0  # Set to 0 if no sales

    context = {
        "report_type": "monthly",  # ✅ ระบุว่าเป็นหน้ารายเดือน
        "menu_sales": dict(menu_sales),
        "total_sales": total_sales,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_month_name": selected_month_name,
        "years": years,
        "months": months.items(),
        "monthly_sales_data": monthly_sales_data,  # Pass the monthly sales data
        "months_in_year": months_in_year,  # Pass the list of month names
    }
    return render(request, "owner/monthly_sales_report.html", context)

def yearly_sales_report_view(request):
    selected_year = request.GET.get("year", None)
    menu_sales = defaultdict(lambda: {"quantity": 0, "total_price": 0})
    total_sales = 0

    current_year = datetime.now().year
    years = list(range(current_year - 10, current_year + 1))  # 10 ปีย้อนหลัง

    # ตัวแปรเพื่อเก็บข้อมูลยอดขายรายปี
    yearly_sales_data = [0] * len(years)  # สร้าง list สำหรับเก็บยอดขายปีที่เลือกจากทั้งหมด

    if selected_year:
        try:
            selected_year = int(selected_year)

            completed_orders = Order.objects.filter(
                status="completed",
                created_at__year=selected_year
            ).order_by("-created_at")

            if completed_orders.exists():
                order_items = OrderItem.objects.filter(order__in=completed_orders).select_related("menu")

                for item in order_items:
                    menu_name = item.menu.food_name
                    menu_sales[menu_name]["quantity"] += item.quantity
                    menu_sales[menu_name]["total_price"] += item.price * item.quantity
                    total_sales += item.price * item.quantity

        except ValueError:
            selected_year = None

    # ดึงข้อมูลยอดขายรายปีจาก 10 ปีที่ผ่านมา
    for idx, year in enumerate(years):  # ใช้ enumerate เพื่อให้ได้ทั้ง index และ year
        start_date = make_aware(datetime(year, 1, 1))
        end_date = make_aware(datetime(year + 1, 1, 1))

        completed_orders = Order.objects.filter(
            status="completed",
            created_at__gte=start_date,
            created_at__lt=end_date
        )

        total_year_sales = 0
        if completed_orders.exists():
            order_items = OrderItem.objects.filter(order__in=completed_orders).select_related("menu")
            for item in order_items:
                total_year_sales += item.price * item.quantity

        yearly_sales_data[idx] = int(total_year_sales)  # เก็บยอดขายรายปีใน list

    context = {
        "report_type": "yearly",  # ✅ ระบุว่าเป็นหน้ารายปี
        "menu_sales": dict(menu_sales),
        "total_sales": total_sales,
        "selected_year": selected_year,
        "years": years,
        "yearly_sales_data": yearly_sales_data,  # ส่งข้อมูลยอดขายรายปี
    }
    return render(request, "owner/yearly_sales_report.html", context)









