python -m venv venv  
.\venv\Scripts\Activate  
pip install -r requirements.txt  

### สร้างดาต้าเบส ###

mysql -u root -p  
CREATE DATABASE sn_project CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;  

python manage.py makemigrations  
python manage.py migrate  



