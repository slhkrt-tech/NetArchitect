from django import forms
from .models import (
    Device, Ticket, IpAddress, ITAsset, License,
    FactoryArea, ConsumableItem, MaintenanceTask, EmployeeITProcess,
    ProcurementRequest, OnCallShift, BackupJobMonitor, VendorSupportCase, AssetHandover,
    MajorIncident, AccessRequest, PrinterFleetItem, Runbook,
    RemoteAccessGrant, DepartmentChannel, DepartmentMessage, CameraDevice,
    BusinessApplication, ReportTemplate,
    ChangeCalendarEvent, ServiceDependency, IntegrationHealthCheck,
    ComplianceControl, DocumentOutputJob,
)

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

class CustomerTicketForm(forms.ModelForm):
    """Müşteri portalı için sınırlı talep formu."""
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'category', 'ticket_category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Başlık Girin'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detaylar...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'ticket_category': forms.Select(attrs={'class': 'form-select'}),
        }


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'device', 'priority', 'category', 'ticket_category', 'status', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Başlık Girin'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detaylar...'}),
            'device': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'ticket_category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
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
        qs = IpAddress.objects.filter(address=address)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Bu IP adresi zaten kullanımda.")
        return address


# ==========================================
# SERVİS MASASI FORMLARI
# ==========================================

class TicketCommentForm(forms.ModelForm):
    class Meta:
        from .models import TicketComment
        model = TicketComment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Yorumunuzu yazın...'}),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'content': 'Yorum',
            'is_internal': 'Dahili not (sadece personel görür)',
        }


class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        from .models import TicketAttachment
        model = TicketAttachment
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {'file': 'Dosya Ekle'}


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, label='Ad',
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, label='Soyad',
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label='E-posta',
                             widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        from .models import UserProfile
        model = UserProfile
        fields = ['phone', 'bio', 'avatar', 'department']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+90 5XX XXX XX XX'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ==========================================
# FABRİKA IT OPERASYON FORMLARI
# ==========================================

class FactoryAreaForm(forms.ModelForm):
    class Meta:
        model = FactoryArea
        fields = ['name', 'code', 'criticality', 'manager_name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Paketleme Hattı 1'}),
            'code': forms.TextInput(attrs={'class': 'form-control font-monospace', 'placeholder': 'PKT-01'}),
            'criticality': forms.Select(attrs={'class': 'form-select'}),
            'manager_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ConsumableItemForm(forms.ModelForm):
    class Meta:
        model = ConsumableItem
        fields = [
            'name', 'category', 'sku', 'compatible_with', 'location',
            'quantity', 'minimum_quantity', 'unit', 'vendor',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'compatible_with': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zebra ZT411, HP M404'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'minimum_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor': forms.TextInput(attrs={'class': 'form-control'}),
        }


class MaintenanceTaskForm(forms.ModelForm):
    class Meta:
        model = MaintenanceTask
        fields = [
            'title', 'task_type', 'factory_area', 'device', 'asset', 'owner',
            'frequency_days', 'next_due_at', 'status', 'checklist', 'notes',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'task_type': forms.Select(attrs={'class': 'form-select'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'device': forms.Select(attrs={'class': 'form-select'}),
            'asset': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'frequency_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'next_due_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'checklist': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Her satıra bir kontrol maddesi'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class EmployeeITProcessForm(forms.ModelForm):
    class Meta:
        model = EmployeeITProcess
        fields = [
            'employee_name', 'department', 'process_type', 'factory_area',
            'assigned_to', 'due_date', 'status', 'ad_account_done', 'email_done',
            'erp_done', 'vpn_done', 'device_done', 'badge_done', 'data_backup_done',
            'notes',
        ]
        widgets = {
            'employee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'process_type': forms.Select(attrs={'class': 'form-select'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ProcurementRequestForm(forms.ModelForm):
    class Meta:
        model = ProcurementRequest
        fields = [
            'title', 'description', 'category', 'quantity', 'estimated_cost',
            'vendor_name', 'factory_area', 'needed_by', 'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'vendor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'needed_by': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class OnCallShiftForm(forms.ModelForm):
    class Meta:
        model = OnCallShift
        fields = ['engineer', 'start_at', 'end_at', 'phone', 'is_primary', 'notes']
        widgets = {
            'engineer': forms.Select(attrs={'class': 'form-select'}),
            'start_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BackupJobMonitorForm(forms.ModelForm):
    class Meta:
        model = BackupJobMonitor
        fields = [
            'name', 'system_type', 'target_host', 'schedule_description',
            'last_run_at', 'last_status', 'next_run_at', 'retention_days',
            'owner', 'is_active', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'system_type': forms.Select(attrs={'class': 'form-select'}),
            'target_host': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'schedule_description': forms.TextInput(attrs={'class': 'form-control'}),
            'last_run_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'last_status': forms.Select(attrs={'class': 'form-select'}),
            'next_run_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class VendorSupportCaseForm(forms.ModelForm):
    class Meta:
        model = VendorSupportCase
        fields = [
            'title', 'vendor_name', 'vendor_contract', 'case_number',
            'priority', 'status', 'assigned_to', 'opened_at', 'description',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor_contract': forms.Select(attrs={'class': 'form-select'}),
            'case_number': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'opened_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class AssetHandoverForm(forms.ModelForm):
    class Meta:
        model = AssetHandover
        fields = [
            'asset', 'employee_name', 'department', 'factory_area',
            'action', 'handover_date', 'condition_notes',
        ]
        widgets = {
            'asset': forms.Select(attrs={'class': 'form-select'}),
            'employee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'action': forms.Select(attrs={'class': 'form-select'}),
            'handover_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'condition_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class MajorIncidentForm(forms.ModelForm):
    class Meta:
        model = MajorIncident
        fields = [
            'title', 'severity', 'status', 'factory_area', 'ticket',
            'incident_commander', 'started_at', 'impact_summary',
            'root_cause', 'corrective_actions',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'ticket': forms.Select(attrs={'class': 'form-select'}),
            'incident_commander': forms.Select(attrs={'class': 'form-select'}),
            'started_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'impact_summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'root_cause': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'corrective_actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class AccessRequestForm(forms.ModelForm):
    class Meta:
        model = AccessRequest
        fields = [
            'employee_name', 'department', 'access_type', 'target_system',
            'justification', 'status', 'expires_at',
        ]
        widgets = {
            'employee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'access_type': forms.Select(attrs={'class': 'form-select'}),
            'target_system': forms.TextInput(attrs={'class': 'form-control'}),
            'justification': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class PrinterFleetItemForm(forms.ModelForm):
    class Meta:
        model = PrinterFleetItem
        fields = [
            'name', 'device_kind', 'ip_address', 'serial_number', 'model',
            'factory_area', 'consumable', 'page_counter', 'toner_level_percent',
            'status', 'last_maintenance_at', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'device_kind': forms.Select(attrs={'class': 'form-select'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'consumable': forms.Select(attrs={'class': 'form-select'}),
            'page_counter': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'toner_level_percent': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'last_maintenance_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class RunbookForm(forms.ModelForm):
    class Meta:
        model = Runbook
        fields = [
            'title', 'category', 'owner', 'related_device_type', 'steps',
            'rollback_steps', 'is_active', 'version', 'last_reviewed_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'related_device_type': forms.TextInput(attrs={'class': 'form-control'}),
            'steps': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Her satıra bir adım yazın'}),
            'rollback_steps': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'last_reviewed_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class RemoteAccessGrantForm(forms.ModelForm):
    class Meta:
        model = RemoteAccessGrant
        fields = [
            'employee_name', 'department', 'access_method', 'target_resource',
            'gateway', 'allowed_source', 'mfa_required', 'status', 'expires_at', 'notes',
        ]
        widgets = {
            'employee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'access_method': forms.Select(attrs={'class': 'form-select'}),
            'target_resource': forms.TextInput(attrs={'class': 'form-control'}),
            'gateway': forms.TextInput(attrs={'class': 'form-control'}),
            'allowed_source': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'mfa_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class DepartmentChannelForm(forms.ModelForm):
    class Meta:
        model = DepartmentChannel
        fields = ['name', 'department', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DepartmentMessageForm(forms.ModelForm):
    class Meta:
        model = DepartmentMessage
        fields = ['channel', 'message', 'is_announcement']
        widgets = {
            'channel': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_announcement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CameraDeviceForm(forms.ModelForm):
    class Meta:
        model = CameraDevice
        fields = [
            'name', 'device_type', 'ip_address', 'stream_url', 'location',
            'factory_area', 'recording_days', 'status', 'last_checked_at', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'device_type': forms.Select(attrs={'class': 'form-select'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'stream_url': forms.URLInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'recording_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'last_checked_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BusinessApplicationForm(forms.ModelForm):
    class Meta:
        model = BusinessApplication
        fields = ['name', 'app_type', 'url', 'owner_department', 'technical_owner', 'sso_enabled', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'app_type': forms.Select(attrs={'class': 'form-select'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'owner_department': forms.TextInput(attrs={'class': 'form-control'}),
            'technical_owner': forms.Select(attrs={'class': 'form-select'}),
            'sso_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = ReportTemplate
        fields = ['title', 'report_type', 'description', 'query_notes', 'output_format', 'is_active', 'owner']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'query_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'output_format': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'pdf,csv,xlsx'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
        }


class ChangeCalendarEventForm(forms.ModelForm):
    class Meta:
        model = ChangeCalendarEvent
        fields = [
            'title', 'event_type', 'risk_level', 'factory_area', 'change_request',
            'owner', 'start_at', 'end_at', 'expected_impact', 'rollback_plan', 'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'factory_area': forms.Select(attrs={'class': 'form-select'}),
            'change_request': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'start_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'expected_impact': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'rollback_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class ServiceDependencyForm(forms.ModelForm):
    class Meta:
        model = ServiceDependency
        fields = ['name', 'business_application', 'device', 'dependency_type', 'criticality', 'impact_description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_application': forms.Select(attrs={'class': 'form-select'}),
            'device': forms.Select(attrs={'class': 'form-select'}),
            'dependency_type': forms.Select(attrs={'class': 'form-select'}),
            'criticality': forms.Select(attrs={'class': 'form-select'}),
            'impact_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class IntegrationHealthCheckForm(forms.ModelForm):
    class Meta:
        model = IntegrationHealthCheck
        fields = [
            'name', 'integration_type', 'endpoint_url', 'owner',
            'last_status', 'last_checked_at', 'response_time_ms', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'integration_type': forms.Select(attrs={'class': 'form-select'}),
            'endpoint_url': forms.TextInput(attrs={'class': 'form-control'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'last_status': forms.Select(attrs={'class': 'form-select'}),
            'last_checked_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'response_time_ms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ComplianceControlForm(forms.ModelForm):
    class Meta:
        model = ComplianceControl
        fields = [
            'title', 'framework', 'owner', 'status', 'evidence',
            'remediation_plan', 'due_date', 'last_checked_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'framework': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'evidence': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'remediation_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'last_checked_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class DocumentOutputJobForm(forms.ModelForm):
    class Meta:
        model = DocumentOutputJob
        fields = ['title', 'job_type', 'template', 'output_format', 'status', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'job_type': forms.Select(attrs={'class': 'form-select'}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'output_format': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'pdf'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }