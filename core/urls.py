from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views 
from inventory.views import (
    config_generator, dashboard, dashboard_refresh, subnet_calculator, export_pdf, 
    export_csv, network_scanner, custom_admin, user_panel, 
    register_page, visual_ipam, live_monitor, get_monitor_data, 
    network_topology, device_backup_view, 
    bulk_config_generator, # Toplu İşlem Fonksiyonu
    it_inventory_view,
    system_logs_view,
    port_mapping_view,
    port_mapping_list_view,
    sync_ad_users,
    knowledge_base_view,
    search_kb_api,
    device_alert_webhook, # Webhook Fonksiyonu
    config_diff_view,     # Config Karşılaştırma (Diff)
    rack_elevation_view,  # Veri Merkezi Kabin Çizimi
    reporting_hub_view    # YENİ: Raporlama Merkezi
)

# API Router ve api_views içe aktarmaları
from rest_framework.routers import DefaultRouter
from inventory import api_views
from inventory.api_views import get_rack_devices # YENİ: Kabin çizim API'sini içe aktardık

# JWT Kimlik Doğrulaması için gerekli view'lar
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Swagger ve ReDoc için gerekli Spectacular view'ları
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularRedocView, 
    SpectacularSwaggerView
)

# --- DRF ROUTER KURULUMU ---
router = DefaultRouter()
router.register(r'devices', api_views.DeviceViewSet, basename='device')
router.register(r'ip-addresses', api_views.IpAddressViewSet, basename='ipaddress')
router.register(r'tickets', api_views.TicketViewSet, basename='ticket')
router.register(r'change-requests', api_views.ChangeRequestViewSet, basename='change-request')
router.register(r'performance-logs', api_views.DevicePerformanceLogViewSet, basename='performance-log')
router.register(r'users', api_views.UserViewSet, basename='user')

urlpatterns = [
    # YENİ: Dil değiştirme rotası
    path('i18n/', include('django.conf.urls.i18n')),

    # Django'nun varsayılan admin paneli
    path('admin/', admin.site.urls), 
    
    # --- GİRİŞ, ÇIKIŞ VE KAYIT SAYFALARI ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('kayit-ol/', register_page, name='register'),
    
    # --- UYGULAMA SAYFALARI ---
    path('uretici/', config_generator, name='generator'),
    path('subnet-hesapla/', subnet_calculator, name='subnet_calc'),
    path('indir-pdf/', export_pdf, name='export_pdf'),
    path('indir-csv/', export_csv, name='export_csv'),
    path('ag-tarayici/', network_scanner, name='network_scanner'),
    path('ipam/', visual_ipam, name='visual_ipam'),
    path('monitor/', live_monitor, name='live_monitor'),
    path('api/monitor-data/', get_monitor_data, name='get_monitor_data'),
    path('api/dashboard-refresh/', dashboard_refresh, name='dashboard_refresh'),
    path('topoloji/', network_topology, name='network_topology'),
    
    path('yedekleme/', device_backup_view, name='device_backup'), 
    path('toplu-generator/', bulk_config_generator, name='bulk_config_generator'), # Toplu İşlem Rotası
    path('konfigurasyon-karsilastir/<int:device_id>/', config_diff_view, name='config_diff'),
    
    # Veri Merkezi Kabin Haritası Rotası
    path('veri-merkezi/', rack_elevation_view, name='rack_elevation'),
    
    # YENİ: Raporlama Merkezi (PDF Çıktıları)
    path('raporlar/', reporting_hub_view, name='reporting_hub'), 
    
    path('panel/', custom_admin, name='custom_admin'), 
    path('kullanici-paneli/', user_panel, name='user_panel'),
    path('it-envanter/', it_inventory_view, name='it_inventory'),
    path('sistem-loglari/', system_logs_view, name='system_logs'),
    path('port-haritasi/', port_mapping_list_view, name='port_mapping_list'),
    path('port-haritasi/<int:device_id>/', port_mapping_view, name='port_mapping'),
    path('ad-sync/', sync_ad_users, name='sync_ad_users'), 
    
    # ==========================================
    # --- BİLGİ BANKASI ROTALARI ---
    # ==========================================
    path('bilgi-bankasi/', knowledge_base_view, name='knowledge_base'),
    path('api/kb-ara/', search_kb_api, name='search_kb_api'),
    
    # ==========================================
    # --- REST API VE WEBHOOK ROTALARI ---
    # ==========================================
    path('api/', include(router.urls)), 
    path('api/', include('inventory.urls')), 
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), 
    path('oauth/', include('social_django.urls', namespace='social')),
    
    # YENİ EKLENEN RACK API ROTASI
    path('api/rack-devices/', get_rack_devices, name='rack_devices_api'),
    
    # Reaktif İzleme (Syslog/Trap) Uç Noktası
    path('api/webhook/alert/', device_alert_webhook, name='device_alert_webhook'),
    
    # JWT Token Rotaları
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ==========================================
    # --- API DOKÜMANTASYONU (SWAGGER/REDOC) ---
    # ==========================================
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Ana Sayfa (Dashboard)
    path('', dashboard, name='dashboard'),
]