import os
import pandas as pd
from django.conf import settings
from django.shortcuts import redirect, render
import pytz
from django.utils import timezone



def table_status_view(request):
    # ระบุ path ของไฟล์ Excel
    file_path = os.path.join(settings.BASE_DIR, 'data', 'D:\seniorproject\seniorproject\data\data_ex.xlsx')
    
    # อ่านไฟล์ Excel
    excel_data = pd.read_excel(file_path)

    # แปลงข้อมูลเป็น list ของ dicts เพื่อส่งไปยัง template
    table_data = excel_data.to_dict(orient='records')

    # ส่งข้อมูลไปยัง template
    context = {
        'table_data': table_data,
    }

    return render(request, 'table_status.html', context)

# อ่านข้อมูลจากไฟล์ Excel
def load_table_data():
    file_path = os.path.join(settings.BASE_DIR, 'data', 'D:\seniorproject\seniorproject\data\data_ex.xlsx')
    excel_data = pd.read_excel(file_path)
    return excel_data

# บันทึกข้อมูลกลับไปยังไฟล์ Excel
def save_table_data(excel_data):
    file_path = os.path.join(settings.BASE_DIR, 'data', 'D:\seniorproject\seniorproject\data\data_ex.xlsx')
    excel_data.to_excel(file_path, index=False)

# แสดงสถานะโต๊ะ
def table_status_view(request):
    excel_data = load_table_data()
    table_data = excel_data.to_dict(orient='records')
    context = {'table_data': table_data}
    return render(request, 'table_status.html', context)

def booking_view(request, table_name):
    if request.method == 'POST':
        booking_date = request.POST.get('date')
        booking_time = request.POST.get('time')

        # อัปเดตสถานะโต๊ะและบันทึกวันเวลาที่ได้รับจากฟอร์มโดยตรง
        excel_data = load_table_data()
        for index, row in excel_data.iterrows():
            if row['table_name'] == table_name:
                excel_data.at[index, 'status'] = 'จอง'
                excel_data.at[index, 'booking_date'] = booking_date  # บันทึกวันที่ตรงๆ จากฟอร์ม
                excel_data.at[index, 'booking_time'] = booking_time  # บันทึกเวลาตรงๆ จากฟอร์ม

        # บันทึกการอัปเดตกลับไปที่ Excel
        save_table_data(excel_data)

        # หลังจากจองแล้วให้กลับไปที่หน้า table
        return redirect('table_status')

    return render(request, 'booking.html', {'table_name': table_name})