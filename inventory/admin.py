from django.contrib import admin

from .models import (
    Device, IpAddress, Ticket, SystemLog, DeviceBackup,
    ServiceCatalogItem, ITAsset, License, Port,
    KnowledgeBaseArticle, VendorContract, ChangeRequest,
    DevicePerformanceLog, TicketComment, TicketAttachment,
    TicketCategory, UserProfile, Notification, NetworkScan, NetworkScanHost,
    FieldVisit, SalesOpportunity, DLPEvent, FactoryArea, ConsumableItem,
    MaintenanceTask, EmployeeITProcess, ProcurementRequest, OnCallShift,
    BackupJobMonitor, VendorSupportCase, AssetHandover, MajorIncident,
    AccessRequest, PrinterFleetItem, Runbook, RemoteAccessGrant,
    DepartmentChannel, DepartmentMessage, CameraDevice, BusinessApplication,
    ReportTemplate, ChangeCalendarEvent, ServiceDependency,
    IntegrationHealthCheck, ComplianceControl, DocumentOutputJob,
)

# Temel ve basit modellerin doğrudan kaydı
admin.site.register(Device)
admin.site.register(IpAddress)
admin.site.register(Ticket)
admin.site.register(ITAsset)
admin.site.register(License)
admin.site.register(Port)
admin.site.register(KnowledgeBaseArticle)
admin.site.register(VendorContract)
admin.site.register(ChangeRequest)
admin.site.register(DevicePerformanceLog)
admin.site.register(TicketComment)
admin.site.register(TicketAttachment)
admin.site.register(TicketCategory)
admin.site.register(UserProfile)
admin.site.register(Notification)
admin.site.register(NetworkScan)
admin.site.register(NetworkScanHost)
admin.site.register(FieldVisit)
admin.site.register(SalesOpportunity)
admin.site.register(DLPEvent)
admin.site.register(FactoryArea)
admin.site.register(ConsumableItem)
admin.site.register(MaintenanceTask)
admin.site.register(EmployeeITProcess)
admin.site.register(ProcurementRequest)
admin.site.register(OnCallShift)
admin.site.register(BackupJobMonitor)
admin.site.register(VendorSupportCase)
admin.site.register(AssetHandover)
admin.site.register(MajorIncident)
admin.site.register(AccessRequest)
admin.site.register(PrinterFleetItem)
admin.site.register(Runbook)
admin.site.register(RemoteAccessGrant)
admin.site.register(DepartmentChannel)
admin.site.register(DepartmentMessage)
admin.site.register(CameraDevice)
admin.site.register(BusinessApplication)
admin.site.register(ReportTemplate)
admin.site.register(ChangeCalendarEvent)
admin.site.register(ServiceDependency)
admin.site.register(IntegrationHealthCheck)
admin.site.register(ComplianceControl)
admin.site.register(DocumentOutputJob)

# ========================================================
# --- ITSM HİZMET KATALOĞU YÖNETİMİ ---
# ========================================================
@admin.register(ServiceCatalogItem)
class ServiceCatalogItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'requires_approval')
    search_fields = ('title', 'description')
    list_filter = ('category', 'requires_approval')

# ========================================================
# --- SİSTEM LOGLARI YÖNETİMİ ---
# ========================================================
@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'created_at') # Listede görünecek sütunlar
    list_filter = ('action', 'created_at')          # Sağ taraftaki filtreleme menüsü
    search_fields = ('details', 'user__username')   # Arama kutusu yetenekleri
    
    # GÜVENLİK: Loglar değiştirilemez! Sadece okunabilir.
    readonly_fields = ('user', 'action', 'details', 'created_at') 
    
    # Yeni log ekleme butonunu admin panelinden kaldırır (Sadece kod ekleyebilir)
    def has_add_permission(self, request):
        return False

# ========================================================
# --- CİHAZ YEDEKLERİ YÖNETİMİ ---
# ========================================================
@admin.register(DeviceBackup)
class DeviceBackupAdmin(admin.ModelAdmin):
    list_display = ('device', 'created_at', 'backed_up_by')
    list_filter = ('device', 'created_at')
    search_fields = ('device__name', 'config_text')
    
    # GÜVENLİK: Alınan yedekler admin panelinden elle değiştirilemez! Sadece okunabilir.
    readonly_fields = ('device', 'config_text', 'created_at', 'backed_up_by')