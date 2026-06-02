from django import forms
from .models import Device, Ticket, IpAddress, ITAsset, License

# Kullanıcı formu için gerekli importlar
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'name', 'device_type', 'vendor', 'parent_device', 
            'mac_address', 'ssh_user', 'ssh_password', 'is_active',
            'rack_name', 'position_u', 'height_u',
            'cpu_alarm_threshold', 'ram_alarm_threshold' # YENİ ZABBIX EŞİKLERİ
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Core-Router-01'}),
            'device_type': forms.Select(attrs={'class': 'form-select'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'parent_device': forms.Select(attrs={'class': 'form-select'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control font-monospace', 'placeholder': '00:1A:2B:3C:4D:5E'}),
            'ssh_user': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'admin'}),
            'ssh_password': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': '••••••••'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input mt-0'}),
            
            # KABİN ALANLARININ TASARIMI
            'rack_name': forms.TextInput(attrs={'class': 'form-control fw-bold text-primary', 'placeholder': 'RACK-01'}),
            'position_u': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'min': '1', 'max': '42'}),
            'height_u': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'min': '1'}),
            
            # ZABBIX EŞİK TASARIMLARI
            'cpu_alarm_threshold': forms.NumberInput(attrs={'class': 'form-control text-danger fw-bold', 'min': '10', 'max': '100'}),
            'ram_alarm_threshold': forms.NumberInput(attrs={'class': 'form-control text-danger fw-bold', 'min': '10', 'max': '100'}),
        }

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'device', 'priority', 'category', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Başlık Girin'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detaylar...'}),
            'device': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}), 
            'category': forms.Select(attrs={'class': 'form-select'}), 
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

# ==========================================
# ITAM & LİSANS FORMLARI
# ==========================================

class ITAssetForm(forms.ModelForm):
    class Meta:
        model = ITAsset
        fields = ['name', 'asset_type', 'serial_number', 'model', 'assigned_to', 'purchase_date', 'warranty_expiry', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'asset_type': forms.Select(attrs={'class': 'form-select'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'assigned_to': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'warranty_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class LicenseForm(forms.ModelForm):
    class Meta:
        model = License
        fields = ['name', 'vendor', 'license_key', 'total_slots', 'used_slots', 'expiry_date', 'is_subscription']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor': forms.TextInput(attrs={'class': 'form-control'}),
            'license_key': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'total_slots': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'used_slots': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_subscription': forms.CheckboxInput(attrs={'class': 'form-check-input mt-0'}),
        }


# ==========================================
# KULLANICI & SİSTEM FORMLARI
# ==========================================

# YÖNETİCİ PANELİ KULLANICI OLUŞTURMA FORMU (is_staff yetkisi verebilir)
class RegisterUserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('is_staff',)
        labels = {
            'username': 'Kullanıcı Adı',
            'is_staff': 'Yönetici Yetkisi'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'password1' in self.fields:
            self.fields['password1'].label = "Parola"
        if 'password2' in self.fields:
            self.fields['password2'].label = "Parola (Tekrar)"

        for field_name, field in self.fields.items():
            if field_name == 'is_staff':
                field.widget.attrs['class'] = 'form-check-input mt-0'
            else:
                field.widget.attrs['class'] = 'form-control'

# DIŞARIDAN KAYIT OLMA FORMU
class PublicRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',) 
        labels = {
            'username': 'Kullanıcı Adı',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'password1' in self.fields:
            self.fields['password1'].label = "Parola"
        if 'password2' in self.fields:
            self.fields['password2'].label = "Parola (Tekrar)"
            
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

# IP Adres Yönetimi ve Çakışma Önleme Formu
class IpAddressForm(forms.ModelForm):
    class Meta:
        model = IpAddress
        fields = ['address', 'device']
        labels = {
            'address': 'IP Adresi',
            'device': 'Cihaz'
        }
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control font-monospace fw-bold'}),
            'device': forms.Select(attrs={'class': 'form-select'}),
        }

    # ÇAKIŞMA ÖNLEME ALGORİTMASI
    def clean_address(self):
        address = self.cleaned_data.get('address')
        if IpAddress.objects.filter(address=address).exists():
            raise forms.ValidationError("Bu IP adresi zaten kullanımda.")
        return address