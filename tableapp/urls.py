from django.urls import path
from . import views

urlpatterns = [
    path('', views.table_status_view, name='table_status'),
    path('booking/<str:table_name>/', views.booking_view, name='booking'),
]
