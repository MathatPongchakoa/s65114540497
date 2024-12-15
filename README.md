65114540497

นายเมธัส พงษ์ชะเกาะ

mathat.po.65@ubu.ac.th

docker run --name redis-server -p 6379:6379 -d redis จากนั้นไปก็ไปกดรันที่ img

รัน celery -A seniorproject worker --loglevel=info --pool=solo
celery -A seniorproject beat --loglevel=info
ก่อน runserver