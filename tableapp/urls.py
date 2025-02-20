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
    path('menu-management/', menu_management_view, name='menu_management'),
    path('add-menu/', add_menu_view, name='add_menu'),
    path('zone-management/', zone_management_view, name='zone_management'),  # จัดการโซน
    path('edit-zone/<int:zone_id>/', edit_zone_view, name='edit_zone'),  # แก้ไขโซน
    path('delete-zone/<int:zone_id>/', delete_zone_view, name='delete_zone'), 
    path('menu-management/edit/<int:menu_id>/', edit_menu_view, name='edit_menu'),
    path('menu-management/delete/<int:menu_id>/', delete_menu, name='edit_menu'),

    path('menu/<int:menu_id>/delete/', delete_menu, name='delete_menu'),
    path('cart/check-reservation/', check_reservation, name='check_reservation'),
    path('cart/confirm-order/', confirm_orders, name='confirm_order'),
    path('order-summary/', order_summary, name='order_summary'),
    path('order-management/', order_management, name='order_management'),
    path('order/update-status/<int:order_id>/<str:new_status>/', update_order_status, name='update_order_status'),
    path("update-table-position/", update_table_position_view, name="update_table_position"),

    path('add-promotion/', add_promotion, name='add_promotion'),  # ✅ Path สำหรับเพิ่มโปรโมชัน
    path('get-menus-by-category/', get_menus_by_category, name='get_menus_by_category'),  # ✅ ดึงเมนูตามหมวดหมู่
    path('promotions/', promotion_list, name='promotion_list'),  # ✅ แสดงหน้าโปรโมชัน
    path('delete-promotion/<int:promo_id>/', delete_promotion, name='delete_promotion'),  # ✅ ลบโปรโมชัน
    path('user/promotions/', user_promotion_list, name='user_promotion_list'),
    path("edit-promotion/<int:promo_id>/", edit_promotion, name="edit_promotion"),
    path('edit-table/<int:table_id>/', edit_table, name='edit_table'),
    path('table-management/delete/<int:table_id>/', delete_table, name='delete_table'),
     path('sales-report/', sales_report_view, name='sales_report'),
     path("monthly-sales-report/", monthly_sales_report_view, name="monthly_sales_report"),
     path("yearly-sales-report/", yearly_sales_report_view, name="yearly_sales_report"),
    

    
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
