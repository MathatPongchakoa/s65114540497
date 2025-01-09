from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static


urlpatterns = [
    path('booking/<str:table_name>/', booking_view, name='booking'),
    path('', table_status_view, name='table_status'),
    path('success/', success_view, name='success'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('cancel-booking/', cancel_booking, name='cancel_booking'),
    path('my-bookings/', my_bookings_view, name='my_bookings'),
    path('menu/', menu_view, name='menu'),
    path('confirm_booking/<int:booking_id>/', confirm_booking, name='confirm_booking'),
    path('cart/add/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_view, name='cart'),
    path('cart/update/<int:item_id>/', update_cart_item, name='update_cart_item'),
    path('cart/confirm/', confirm_order, name='confirm_order'),
    path('order/success/<int:order_id>/', order_success_view, name='order_success'),

    path('reset-password/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='reset_password'),
    path('reset-password-done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset-password-confirm/<uidb64>/<token>/', password_reset_confirm_view, name='password_reset_confirm'),
    path('reset-password-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    
    path('owner/add-table/', add_table_view, name='add_table'),
    path('owner/manage-table/<int:table_id>/', manage_table_view, name='manage_table'),
    path('table-management/', table_management_view, name='table_management'),
    path('owner/booked-tables/', booked_tables_view, name='booked_tables'),
    path('change-booking-status/<int:booking_id>/', change_booking_status, name='change_booking_status'),

    path('add-zone/', add_zone_view, name='add_zone'),  # เพิ่มโซน
    path('zone-management/', zone_management_view, name='zone_management'),  # จัดการโซน
    path('edit-zone/<int:zone_id>/', edit_zone_view, name='edit_zone'),  # แก้ไขโซน
    path('delete-zone/<int:zone_id>/', delete_zone_view, name='delete_zone'), 
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
