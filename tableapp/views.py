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
from .tasks import check_booking_status, delete_cancelled_bookings
from django.http import HttpResponseBadRequest
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import math
from .forms import TableForm
from django.contrib.admin.views.decorators import staff_member_required

def is_staff(user):
    """ตรวจสอบว่า user เป็น staff หรือไม่"""
    return user.is_staff


def table_status_view(request):
    # รับค่าโซนจาก URL
    selected_zone_id = request.GET.get('zone', None)
    
    # กรองโซน
    zones = Zone.objects.all()
    tables = Table.objects.all()
    selected_zone = None

    if selected_zone_id:
        selected_zone = get_object_or_404(Zone, id=selected_zone_id)
        tables = tables.filter(zone=selected_zone)

    # เตรียมข้อมูลโต๊ะ
    table_data = []
    for table in tables:
        # ตรวจสอบสถานะโต๊ะ
        if table.table_status == "occupied":
            current_status = "occupied"
        elif table.table_status == "booked":
            current_status = "booked"
        else:
            current_status = "available"

        # วาดตำแหน่งเก้าอี้รอบโต๊ะ
        chairs = []
        radius = 70
        for i in range(table.seating_capacity):
            angle = (360 / table.seating_capacity) * i
            angle_rad = math.radians(angle)
            x = 100 + radius * math.cos(angle_rad)
            y = 100 + radius * math.sin(angle_rad)
            chairs.append({'x': x, 'y': y})

        table_data.append({
            'table_name': table.table_name,
            'seating_capacity': table.seating_capacity,
            'table_status': current_status,
            'zone': table.zone.name if table.zone else "ไม่ระบุโซน",
            'chairs': chairs,
        })

    context = {
        'zones': zones,  # แสดงรายการโซนทั้งหมด
        'selected_zone': selected_zone,  # โซนที่ถูกเลือก
        'table_data': table_data,  # ข้อมูลโต๊ะ
    }

    return render(request, 'table_status.html', context)




@login_required(login_url='login')
def booking_view(request, table_name):
    table = get_object_or_404(Table, table_name=table_name)
    active_booking = Booking.objects.filter(user=request.user, table=table, status="pending").first()

    if request.method == "POST":
        data = json.loads(request.body)

        if "booking_start" in data and "booking_end" in data:
            # การจองโต๊ะ
            booking_start = datetime.strptime(data["booking_start"], "%Y-%m-%d %H:%M")
            booking_end = datetime.strptime(data["booking_end"], "%Y-%m-%d %H:%M")

            # ตรวจสอบการจองซ้ำ
            overlapping_user_bookings = Booking.objects.filter(
                user=request.user,
                booking_date=booking_start.date(),
            ).filter(
                booking_time__lt=booking_end.time(),
                booking_end_time__gt=booking_start.time()
            )
            if overlapping_user_bookings.exists():
                return JsonResponse({"success": False, "message": "คุณมีการจองโต๊ะอยู่แล้วในช่วงเวลานี้"})

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
            new_booking = Booking.objects.create(
                table=table,
                booking_date=booking_start.date(),
                booking_time=booking_start.time(),
                booking_end_time=booking_end.time(),
                user=request.user,
                status='pending'
            )

            # อัปเดตสถานะโต๊ะ
            if table.table_status != "occupied":
                table.table_status = "booked"
                table.save()

            # อัปเดต Cart ของผู้ใช้
            cart, created = Cart.objects.get_or_create(user=request.user, is_active=True)
            cart.table = table
            cart.save()

            return JsonResponse({"success": True, "message": "จองโต๊ะสำเร็จ!"})

        return HttpResponseBadRequest("Invalid data")

    elif request.method == "GET" and "date" in request.GET:
        selected_date = request.GET.get("date")
        existing_bookings = Booking.objects.filter(table=table, booking_date=selected_date).values("booking_time", "booking_end_time")
        bookings_list = [
            {"start_time": str(booking["booking_time"]), "end_time": str(booking["booking_end_time"])}
            for booking in existing_bookings
        ]
        return JsonResponse({"bookings": bookings_list})

    context = {
        "table_name": table.table_name,
        "seating_capacity": table.seating_capacity,
        "active_booking": active_booking,
    }

    if active_booking:
        context["menus"] = Menu.objects.all()

    return render(request, "booking.html", context)

@login_required
def cancel_booking(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        # ลบคำสั่งซื้อที่เกี่ยวข้องกับการจองนี้
        related_order = Order.objects.filter(
            user=request.user,
            table_name=booking.table.table_name,
            booking_start__date=booking.booking_date
        ).first()
        if related_order:
            related_order.delete()

        # ลบ Cart ทั้งหมดที่เกี่ยวข้องกับผู้ใช้
        carts = Cart.objects.filter(user=request.user)  # ไม่กรอง is_active
        if carts.exists():
            carts.delete()

        # ตรวจสอบการจองอื่นที่ยัง active
        table = booking.table
        other_active_bookings = Booking.objects.filter(
            table=table,
            status__in=["occupied", "pending"]
        ).exclude(id=booking.id)

        # เปลี่ยนสถานะโต๊ะก็ต่อเมื่อไม่มีการจองที่ active เหลืออยู่
        if not other_active_bookings.exists():
            table.table_status = "available"
        elif other_active_bookings.filter(status="occupied").exists():
            table.table_status = "occupied"
        elif other_active_bookings.filter(status="pending").exists():
            table.table_status = "booked"
        
        table.save()

        # ลบการจอง
        booking.delete()

        return redirect('my_bookings')  # กลับไปหน้าแสดงรายการจอง

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
                # ตรวจสอบว่าผู้ใช้เป็น staff หรือไม่
                if user.is_staff:
                    return redirect('table_management')  # Redirect ไปยัง table_management สำหรับ staff
                else:
                    return redirect('table_status')  # Redirect ไปยัง table_status สำหรับผู้ใช้ทั่วไป
            else:
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
    categories = Category.objects.all()

    # ตรวจสอบสถานะการจองของผู้ใช้งาน
    active_booking = Booking.objects.filter(user=request.user, status="pending").first()

    if category_name:
        try:
            category = Category.objects.get(name=category_name)
            menus = Menu.objects.filter(category=category)
        except Category.DoesNotExist:
            raise Http404("หมวดหมู่ที่ระบุไม่มีอยู่ในระบบ")
    else:
        menus = Menu.objects.all()

    # แบ่งหน้า
    paginator = Paginator(menus, 8)  # แสดง 8 เมนูต่อหน้า
    page = request.GET.get('page')

    try:
        menus = paginator.page(page)
    except PageNotAnInteger:
        menus = paginator.page(1)
    except EmptyPage:
        menus = paginator.page(paginator.num_pages)

    context = {
        'categories': categories,
        'menus': menus,
        'active_booking': active_booking,
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
@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        # ตรวจสอบว่าผู้ใช้มีการจองโต๊ะหรือไม่
        active_booking = Booking.objects.filter(user=request.user, status="pending").first()
        if not active_booking:
            return JsonResponse({"success": False, "message": "คุณต้องจองโต๊ะก่อนสั่งอาหาร"}, status=403)

        # ดำเนินการเพิ่มอาหารลงในตะกร้า
        try:
            data = json.loads(request.body)
            menu_id = data.get("food_id")
            if not menu_id:
                return JsonResponse({"success": False, "message": "ไม่พบเมนูที่เลือก"}, status=400)

            menu_item = Menu.objects.get(id=menu_id)
            cart, created = Cart.objects.get_or_create(user=request.user, is_active=True)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, menu=menu_item)

            if not created:
                cart_item.quantity += 1  # เพิ่มจำนวนสินค้า
                cart_item.save()

            return JsonResponse({"success": True, "food_name": menu_item.food_name})
        except Menu.DoesNotExist:
            return JsonResponse({"success": False, "message": "เมนูไม่พบ"}, status=404)
    return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

@login_required
def cart_view(request):
    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    cart_items = cart.items.all() if cart else []

    # คำนวณ total_price สำหรับแต่ละ item และรวมทั้งหมด
    for item in cart_items:
        item.total_price = item.menu.price * item.quantity  # คำนวณราคาสินค้าแต่ละชิ้น

    total_price = sum(item.total_price for item in cart_items)

    context = {
        "cart_items": cart_items,
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

def order_success_view(request, order_id):
    return render(request, 'order_success.html', {'order_id': order_id})


@staff_member_required
def table_management_view(request):
    tables = Table.objects.all()
    table_data = []

    for table in tables:
        seating_capacity = table.seating_capacity
        chairs = []
        radius = 70  # ระยะห่างระหว่างโต๊ะกับเก้าอี้
        for i in range(seating_capacity):
            angle = (360 / seating_capacity) * i
            angle_rad = math.radians(angle)
            x = 100 + radius * math.cos(angle_rad)
            y = 100 + radius * math.sin(angle_rad)
            chairs.append({'x': x, 'y': y})
        table_data.append({
            'table_id': table.id,
            'table_name': table.table_name,
            'seating_capacity': table.seating_capacity,
            'table_status': table.table_status,
            'chairs': chairs
        })

    return render(request, 'owner/table_management.html', {'table_data': table_data})



@login_required
@user_passes_test(is_staff, login_url='login')
def add_table_view(request):
    if request.method == 'POST':
        table_name = request.POST.get('table_name')
        seating_capacity = request.POST.get('seating_capacity')
        zone_id = request.POST.get('zone')  # รับค่าโซนจากฟอร์ม

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
        # กรองการจองที่สถานะไม่ใช่ completed
        bookings = table.booking_set.exclude(status='completed').order_by('booking_date', 'booking_time')  # กรองสถานะ completed และเรียงลำดับตามวันและเวลา
        current_status = table.table_status

        # ตรวจสอบว่ามีสถานะ occupied อยู่หรือไม่
        if current_status == "occupied":
            display_status = "occupied"
        elif bookings.exists():
            display_status = "booked"
        else:
            display_status = "available"

        table_data.append({
            'table_name': table.table_name,
            'seating_capacity': table.seating_capacity,
            'bookings': bookings,
            'table_status': display_status,
        })

    return render(request, 'owner/booked_tables.html', {'table_data': table_data})


@login_required
def change_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status == "pending":
        # เปลี่ยนสถานะการจอง
        booking.status = "occupied"
        booking.save()
        print(f"Debug: Booking ID {booking_id} status updated to 'occupied'.")

        # ตรวจสอบสถานะโต๊ะ
        table = booking.table
        if table.table_status != "occupied":
            table.table_status = "occupied"
            table.save()
            print(f"Debug: Table {table.table_name} status updated to 'occupied'.")

        # แสดง Debug ข้อมูลที่เกี่ยวข้องกับ Booking และ Order
        print(f"Debug: Booking User: {booking.user.username}")
        print(f"Debug: Booking Table Name: {table.table_name}")
        print(f"Debug: Booking Date: {booking.booking_date}")

        # ใช้ booking.booking_date โดยตรงหากเป็น datetime.date
        related_orders = Order.objects.filter(
            user=booking.user,
            table_name=table.table_name,
            booking_start__date=booking.booking_date  # ไม่ใช้ localtime เนื่องจากเป็น date
        )

        # เพิ่ม Debug Log เพื่อแสดง Query SQL
        print(f"Debug: Related Orders Query: {related_orders.query}")

        # ตรวจสอบและอัปเดตออเดอร์
        if related_orders.exists():
            for order in related_orders:
                print(f"Debug: Found Order ID {order.id} with Status {order.status}")
                if order.status == "pending":
                    order.status = "in_progress"
                    order.save()
                    print(f"Debug: Order ID {order.id} status updated to 'in_progress'.")
        else:
            # Debug ว่าข้อมูลที่ส่งไปเปรียบเทียบมีอะไรบ้าง
            print(f"Debug: No related order found. Debugging fields:")
            print(f" - User ID: {booking.user.id}")
            print(f" - Table Name: {table.table_name}")
            print(f" - Booking Date: {booking.booking_date}")
            all_orders = Order.objects.all()
            for order in all_orders:
                print(f" - Order ID: {order.id}, User: {order.user.username}, Table: {order.table_name}, Start: {order.booking_start}")

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
        food_name = request.POST.get('food_name')
        price = request.POST.get('price')
        category_id = request.POST.get('category_id')
        image = request.FILES.get('image')

        # ตรวจสอบ category
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            messages.error(request, 'หมวดหมู่ที่เลือกไม่ถูกต้อง')
            return render(request, 'owner/add_menu.html')

        # สร้างเมนูใหม่
        Menu.objects.create(
            food_name=food_name,
            price=price,
            category=category,
            image=image
        )
        messages.success(request, 'เพิ่มเมนูใหม่สำเร็จ!')
        return redirect('/menu-management/')  # เปลี่ยนเส้นทางกลับไปยังหน้าเมนูการจัดการ

    # GET method: แสดงแบบฟอร์ม
    categories = Category.objects.all()
    return render(request, 'owner/add_menu.html', {'categories': categories})

def menu_management_view(request):
    menus = Menu.objects.all()
    for menu in menus:
        print(menu.image)  # ตรวจสอบ URL รูปภาพ
    return render(request, 'owner/menu_management.html', {'menus': menus})

def edit_menu_view(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)

    if request.method == 'POST':
        food_name = request.POST.get('food_name')
        price = request.POST.get('price')
        category_name = request.POST.get('category_name')
        image = request.FILES.get('image')

        # ตรวจสอบหรือสร้าง Category ใหม่
        category, created = Category.objects.get_or_create(name=category_name)

        # อัปเดตเมนู
        menu.food_name = food_name
        menu.price = price
        menu.category = category

        if image:
            menu.image = image

        menu.save()
        messages.success(request, 'แก้ไขเมนูสำเร็จแล้ว')
        return redirect('/menu-management/')

    categories = Category.objects.all()
    return render(request, 'owner/edit_menu.html', {'menu': menu, 'categories': categories})



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
        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "error": "กรุณาเข้าสู่ระบบก่อนทำการสั่งซื้อ"}, status=401)

        try:
            cart = Cart.objects.get(user=request.user, is_active=True)
        except Cart.DoesNotExist:
            return JsonResponse({"success": False, "error": "ไม่มีตะกร้าที่ใช้งานอยู่"}, status=404)

        if not cart.table:
            return JsonResponse({"success": False, "error": "กรุณาจองโต๊ะก่อนทำการสั่งซื้อ"}, status=400)

        # ดึง Booking ที่เกี่ยวข้อง
        try:
            booking = Booking.objects.get(user=request.user, table=cart.table, status="pending")
        except Booking.DoesNotExist:
            return JsonResponse({"success": False, "error": "ไม่พบการจองที่เกี่ยวข้อง"}, status=404)

        # ใช้เวลา booking_start และ booking_end จาก Booking
        booking_start = timezone.make_aware(datetime.combine(booking.booking_date, booking.booking_time))
        booking_end = timezone.make_aware(datetime.combine(booking.booking_date, booking.booking_end_time))

        total_price = sum(item.menu.price * item.quantity for item in cart.items.all())
        order = Order.objects.create(
            user=request.user,
            table_name=cart.table.table_name,
            booking_start=booking_start,
            booking_end=booking_end,
            total_price=total_price
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                menu=item.menu.food_name,
                price=item.menu.price,
                quantity=item.quantity
            )

        cart.is_active = False
        cart.items.all().delete()
        cart.save()

        return JsonResponse({"success": True, "order_id": order.id, "message": "การสั่งซื้อสำเร็จ"})
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)


@login_required(login_url='login')
def order_summary(request):
    # ดึงข้อมูลคำสั่งซื้อของผู้ใช้
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        "orders": orders,
    }
    return render(request, "order_summary.html", context)

@login_required(login_url='login')
def order_management(request):
    orders = Order.objects.prefetch_related('items').all().order_by('-created_at')
    
    # Mapping Order กับ Booking
    for order in orders:
        related_booking = Booking.objects.filter(
            table__table_name=order.table_name,
            user=order.user,
            booking_date=order.booking_start.date()  # Match วันที่
        ).first()
        if related_booking:
            order.booking_time = related_booking.booking_time
            order.booking_date = related_booking.booking_date

    context = {
        "orders": orders,
    }
    return render(request, "owner/order_management.html", context)

@login_required
def update_order_status(request, order_id, new_status):
    # ดึงข้อมูล Order ที่ต้องการแก้ไข
    order = get_object_or_404(Order, id=order_id)

    # ตรวจสอบว่าสถานะที่ส่งมาเป็นสถานะที่อนุญาต
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()
        messages.success(request, f"สถานะออเดอร์ ID {order_id} เปลี่ยนเป็น '{dict(Order.STATUS_CHOICES).get(new_status)}'")
    else:
        messages.error(request, "สถานะที่ระบุไม่ถูกต้อง")

    return redirect('order_management')  # เปลี่ยนเป็น URL ที่เหมาะสม
