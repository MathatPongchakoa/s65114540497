from django import forms
from tableapp.models import CustomUser,Table
from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['table_name', 'table_status', 'seating_capacity']
        widgets = {
            'table_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อโต๊ะ'}),
            'table_status': forms.Select(attrs={'class': 'form-control'}),
            'seating_capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'จำนวนที่นั่ง'}),
        }
        labels = {
            'table_name': 'ชื่อโต๊ะ',
            'table_status': 'สถานะโต๊ะ',
            'seating_capacity': 'จำนวนที่นั่ง',
        }