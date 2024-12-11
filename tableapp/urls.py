from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('booking/<str:table_name>/', booking_view, name='booking'),
    path('', table_status_view, name='table_status'),
    path('success/', success_view, name='success'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('cancel-booking/', cancel_booking_view, name='cancel_booking'),
    path('my-bookings/', my_bookings_view, name='my_bookings'),

    path('reset-password/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='reset_password'),
    path('reset-password-done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset-password-confirm/<uidb64>/<token>/', password_reset_confirm_view, name='password_reset_confirm'),
    path('reset-password-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    
]
