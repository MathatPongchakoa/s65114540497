from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # สร้าง path หลักที่ครอบ URL ทั้งหมดของโปรเจกต์
    path('s65114540497/', include([
        # URL ของหน้า Admin จะกลายเป็น /s65114540497/admin/
        path('admin/', admin.site.urls),
        
        # นำ URL ทั้งหมดจาก tableapp/urls.py มาต่อท้าย /s65114540497/
        # เช่น /s65114540497/login/, /s65114540497/menu-management/edit/1/
        path("__reload__/", include("django_browser_reload.urls")),
        path('', include('tableapp.urls')),
    ])),
]

# การตั้งค่านี้จำเป็นเพื่อให้ Django สามารถแสดงไฟล์ Media (ที่ผู้ใช้อัปโหลด) ได้ในโหมด DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
