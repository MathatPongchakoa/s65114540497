# ใช้ image Nginx อย่างเป็นทางการเป็น base
FROM nginx:latest

# กำหนด working directory ภายในคอนเทนเนอร์

COPY nginx.conf /etc/nginx/nginx.conf
# คัดลอกไฟล์เว็บไซต์ (HTML, CSS, JS) ทั้งหมดจากโฟลเดอร์ 'html'
# ในเครื่องของคุณไปยังโฟลเดอร์ที่ Nginx ใช้ serve ไฟล์


# Expose พอร์ต 80 เพื่อให้ Nginx สามารถรับคำขอจากภายนอกได้
EXPOSE 80

# คำสั่งเริ่มต้นของคอนเทนเนอร์ ซึ่ง Nginx จะรันเป็น foreground
CMD ["nginx", "-g", "daemon off;"]