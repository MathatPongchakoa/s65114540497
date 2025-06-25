# สร้าง virtual environment ชื่อว่า venv
python -m venv venv  

# เปิดใช้งาน virtual environment (เฉพาะ Windows)
.\venv\Scripts\Activate  

# ติดตั้งไลบรารีทั้งหมดจากไฟล์ requirements.txt
pip install -r requirements.txt  


### สร้างดาต้าเบส ###

# เข้าสู่ MySQL ด้วย user root (จะถามรหัสผ่าน)
mysql -u root -p  

# สร้างฐานข้อมูลชื่อ sn_project พร้อมตั้งค่า charset และ collation ให้รองรับภาษาไทย
CREATE DATABASE sn_project CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;  


# สร้างไฟล์ migration สำหรับการเปลี่ยนแปลง models
python manage.py makemigrations  

# นำ migration ไปสร้างตารางในฐานข้อมูล
python manage.py migrate  

# รันเซิร์ฟเวอร์ Django เพื่อเริ่มต้นโปรเจกต์
python manage.py runserver  





