from django.urls import path, include
from rest_framework.routers import DefaultRouter

# --- GÖRÜNÜMLERİ (VIEWS) İÇE AKTAR ---
from . import views

# api_views.py dosyasındaki tüm ViewSet'leri içe aktarıyoruz
from .api_views import (
    UserViewSet,
    DeviceViewSet,
    IpAddressViewSet,
    TicketViewSet,
    DevicePerformanceLogViewSet,
    ChangeRequestViewSet,
    RemoteProbeViewSet  # Yeni eklenen Dağıtık Ajan API'si
)

# API Router tanımlaması
router = DefaultRouter()

# Mevcut API Uç Noktaları
router.register(r'users', UserViewSet, basename='user')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'ip-addresses', IpAddressViewSet, basename='ipaddress')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'performance-logs', DevicePerformanceLogViewSet, basename='performancelog')
router.register(r'change-requests', ChangeRequestViewSet, basename='changerequest')

# =========================================================
# --- YENİ EKLENEN: DAĞITIK PROBE (AJAN) API UÇ NOKTASI ---
# =========================================================
router.register(r'probes', RemoteProbeViewSet, basename='probe')

# URL Patterns
urlpatterns = [
    # ---------------------------------------------------------
    # --- API YÖNLENDİRMELERİ (DRF ROUTER) ---
    # ---------------------------------------------------------
    path('api/', include(router.urls)), # API yollarını /api/ altına aldık ki sayfalarla karışmasın

    # ---------------------------------------------------------
    # --- WEB SAYFASI (CRUD) YÖNLENDİRMELERİ ---
    # ---------------------------------------------------------
    
    # Cihazlar (Donanım Envanteri)
    path('device/<int:pk>/edit/', views.DeviceUpdateView.as_view(), name='device_edit'),
    path('device/<int:pk>/delete/', views.DeviceDeleteView.as_view(), name='device_delete'),
    
    # Yazılım Lisansları
    path('license/<int:pk>/edit/', views.LicenseUpdateView.as_view(), name='license_edit'),
    path('license/<int:pk>/delete/', views.LicenseDeleteView.as_view(), name='license_delete'),
    
    # Tedarikçi Sözleşmeleri (Vendor)
    path('vendor-contract/<int:pk>/edit/', views.VendorContractUpdateView.as_view(), name='vendor_edit'),
    path('vendor-contract/<int:pk>/delete/', views.VendorContractDeleteView.as_view(), name='vendor_delete'),
    
    # IT Varlıkları (Zimmet Yönetimi)
    path('asset/<int:pk>/edit/', views.ITAssetUpdateView.as_view(), name='asset_edit'),
    path('asset/<int:pk>/delete/', views.ITAssetDeleteView.as_view(), name='asset_delete'),
    
    # IP Adresleri (IPAM)
    path('ip-address/<int:pk>/edit/', views.IpAddressUpdateView.as_view(), name='ip_edit'),
    path('ip-address/<int:pk>/delete/', views.IpAddressDeleteView.as_view(), name='ip_delete'),
    
    # Destek Biletleri (Tickets)
    path('ticket/<int:pk>/edit/', views.TicketUpdateView.as_view(), name='ticket_edit'),
    path('ticket/<int:pk>/delete/', views.TicketDeleteView.as_view(), name='ticket_delete'),
]