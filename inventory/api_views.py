from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

# Filtreleme, Arama ve Sıralama araçları
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Device, IpAddress, Ticket, DevicePerformanceLog, ChangeRequest, RemoteProbe, SystemLog
from .serializers import (
    DeviceSerializer, IpAddressSerializer, TicketSerializer, UserSerializer,
    DevicePerformanceLogSerializer, ChangeRequestSerializer, RemoteProbeSerializer
)

# Konfigürasyon motorunu içe aktarıyoruz
from .utils import generate_device_config

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Kullanıcı listesini JSON olarak döner."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Güvenlik: Sadece IT Personeli (Admin) kullanıcı listesini API'den çekebilir
    permission_classes = [IsAdminUser] 
    
    # Arama ve Sıralama
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'email']
    ordering_fields = ['date_joined', 'username']

class DeviceViewSet(viewsets.ModelViewSet):
    """Cihaz envanterine API üzerinden CRUD işlemi yapar."""
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    # Cihazlarda filtreleme, arama ve sıralama
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['device_type', 'is_active', 'parent_device'] 
    search_fields = ['name', 'mac_address'] 
    ordering_fields = ['name', 'id']

    # ==================================================
    # API UÇ NOKTASI (CUSTOM ACTION)
    # ==================================================
    @action(detail=False, methods=['post'], url_path='generate-config')
    def generate_config(self, request):
        """
        Dışarıdan JSON olarak gelen cihaz parametrelerini alır
        ve üretilmiş CLI konfigürasyonunu JSON olarak geri döndürür.
        """
        # Gelen JSON verilerini request.data'dan alıyoruz
        vendor = request.data.get('vendor', 'cisco')
        device_type = request.data.get('device_type', 'switch')
        hostname = request.data.get('hostname', 'API-Device')
        vlan_id = request.data.get('vlan_id', '10')
        vlan_name = request.data.get('vlan_name', 'API_VLAN')
        interface_name = request.data.get('interface_name', 'GigabitEthernet0/1')
        
        # Checkbox/Boolean değerler string, boolean veya integer gelebileceği için güvenli dönüşüm
        enable_ospf_raw = request.data.get('enable_ospf', False)
        enable_ospf = str(enable_ospf_raw).lower() in ['yes', 'true', '1']
        
        ospf_network = request.data.get('ospf_network', '')
        ospf_area = request.data.get('ospf_area', '0')
        
        enable_port_security_raw = request.data.get('enable_port_security', False)
        enable_port_security = str(enable_port_security_raw).lower() in ['yes', 'true', '1']
        
        mac_limit = request.data.get('mac_limit', '1')

        # utils.py içindeki asıl motoru çalıştırıyoruz
        generated_code = generate_device_config(
            vendor=vendor, 
            device_type=device_type, 
            hostname=hostname, 
            vlan_id=vlan_id, 
            vlan_name=vlan_name, 
            interface_name=interface_name, 
            enable_ospf=enable_ospf, 
            ospf_network=ospf_network, 
            ospf_area=ospf_area, 
            enable_port_security=enable_port_security, 
            mac_limit=mac_limit
        )

        return Response({
            "status": "success",
            "message": f"{vendor.capitalize()} {device_type.capitalize()} için konfigürasyon başarıyla üretildi.",
            "configuration": generated_code
        })

class IpAddressViewSet(viewsets.ModelViewSet):
    """IP adresi haritasını ve atamalarını JSON döner."""
    queryset = IpAddress.objects.all()
    serializer_class = IpAddressSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['device']
    search_fields = ['address']

class TicketViewSet(viewsets.ModelViewSet):
    """Destek biletlerini API üzerinden yönetir."""
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'category', 'device']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'priority']

    def get_queryset(self):
        """Güvenlik Filtresi: Admin tümünü, kullanıcı sadece kendi biletlerini görür."""
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class DevicePerformanceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Cihaz performans geçmişini API olarak sunar."""
    queryset = DevicePerformanceLog.objects.select_related('device').all()
    serializer_class = DevicePerformanceLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['device']
    search_fields = ['device__name']
    ordering_fields = ['recorded_at']

# ==================================================
# --- DAĞITIK PROBE (AJAN) UÇ NOKTALARI ---
# ==================================================
class RemoteProbeViewSet(viewsets.ModelViewSet):
    """Uzak Ajanların (Probe) merkez sunucuyla iletişim kurduğu API noktası."""
    queryset = RemoteProbe.objects.all()
    serializer_class = RemoteProbeSerializer
    
    # Probelar standart kullanıcı olmadığından Auth'u pas geçip Header Secret ile doğrulayacağız
    permission_classes = [AllowAny]
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'location']
    search_fields = ['name', 'location', 'ip_address']
    ordering_fields = ['last_heartbeat']

    def _verify_probe_secret(self, request):
        """Güvenlik: Gelen isteğin gerçekten bizim ajanımızdan gelip gelmediğini doğrula."""
        client_secret = request.headers.get('X-Remote-Probe-Secret') or request.data.get('secret')
        server_secret = getattr(settings, 'REMOTE_PROBE_SHARED_SECRET', None)
        if not server_secret or client_secret != server_secret:
            return False
        return True

    @action(detail=False, methods=['post'], url_path='heartbeat')
    def heartbeat(self, request):
        """Ajanın her 15 dakikada bir 'Ben Hayattayım' dediği ve yeni görevleri aldığı uç nokta."""
        if not self._verify_probe_secret(request):
            return Response({'error': 'Unauthorized Probe'}, status=status.HTTP_401_UNAUTHORIZED)

        probe_name = request.data.get('name')
        ip_addr = request.data.get('ip_address')
        if not probe_name or not ip_addr:
            return Response({'error': 'Name and IP required'}, status=status.HTTP_400_BAD_REQUEST)

        probe, created = RemoteProbe.objects.update_or_create(
            name=probe_name,
            defaults={
                'ip_address': ip_addr,
                'location': request.data.get('location', ''),
                'target_subnet': request.data.get('target_subnet', ''),
                'agent_version': request.data.get('agent_version', '1.0.0'),
                'status': 'online',
                'last_heartbeat': timezone.now(),
            }
        )

        if created:
            SystemLog.objects.create(action='SYSTEM', details=f"Yeni Ajan (Probe) Sisteme Eklendi: {probe.name}")

        tasks = self._get_pending_tasks_for_probe(probe)

        return Response({
            'status': 'success',
            'probe_id': probe.id,
            'created': created,
            'last_heartbeat': probe.last_heartbeat.isoformat(),
            'tasks': tasks,
        })

    @action(detail=False, methods=['post'], url_path='sync-data')
    def sync_data(self, request):
        """Ajanın bulduğu IP'leri, performans verilerini ve konfigürasyonları merkeze kaydeder."""
        if not self._verify_probe_secret(request):
            return Response({'error': 'Unauthorized Probe'}, status=status.HTTP_401_UNAUTHORIZED)

        probe_id = request.data.get('probe_id')
        discovered_ips = request.data.get('discovered_ips', [])
        performance_metrics = request.data.get('performance_metrics', {})
        device_configs = request.data.get('device_configs', [])

        try:
            probe = RemoteProbe.objects.get(id=probe_id)
        except RemoteProbe.DoesNotExist:
            return Response({'error': 'Probe not found'}, status=status.HTTP_404_NOT_FOUND)

        processed_ips = 0
        processed_configs = 0

        # 1. IP Adreslerini Kaydet
        for ip in discovered_ips:
            obj, created = IpAddress.objects.get_or_create(
                address=ip,
                defaults={'is_allocated': True}
            )
            if created:
                processed_ips += 1

        # 2. Cihaz Konfigürasyonlarını Yedekle
        from .models import DeviceBackup, DevicePerformanceLog
        for config_data in device_configs:
            ip_addr = config_data.get('ip')
            config_text = config_data.get('config')
            
            if ip_addr and config_text:
                # Gelen IP sistemde kayıtlı bir 'Cihaz' (Device) ile eşleşiyorsa yedeği al
                ip_record = IpAddress.objects.filter(address=ip_addr).select_related('device').first()
                if ip_record and ip_record.device:
                    DeviceBackup.objects.create(
                        device=ip_record.device,
                        config_text=config_text,
                        backed_up_by=None # Otomatik ajan yedeği
                    )
                    processed_configs += 1

        # 3. Probe Performans Verisi (AIOps Tahminlemesi İçin)
        if performance_metrics:
            # Ajanın kurulu olduğu sunucu da bizim envanterimizde kayıtlı bir Device ise logla
            probe_ip_record = IpAddress.objects.filter(address=probe.ip_address).select_related('device').first()
            if probe_ip_record and probe_ip_record.device:
                DevicePerformanceLog.objects.create(
                    device=probe_ip_record.device,
                    cpu_usage=performance_metrics.get('cpu_usage', 0),
                    ram_usage=performance_metrics.get('ram_usage', 0),
                    disk_usage=performance_metrics.get('disk_usage', 0)
                )

        if processed_ips > 0 or processed_configs > 0:
            SystemLog.objects.create(
                action='SCAN',
                details=f"Dağıtık Mimari: '{probe.name}' ajanı {processed_ips} yeni IP keşfetti ve {processed_configs} cihazın konfigürasyon yedeğini aldı."
            )

        return Response({
            'status': 'success',
            'message': 'Probe verisi başarıyla alındı ve işlendi.',
            'processed_ips': processed_ips,
            'processed_configs': processed_configs
        })

    def _get_pending_tasks_for_probe(self, probe):
        tasks = []
        if probe.target_subnet:
            tasks.append({
                'id': f"scan_{probe.id}_{int(timezone.now().timestamp())}",
                'type': 'network_scan',
                'target': probe.target_subnet,
                'priority': 'high'
            })
        return tasks

class ChangeRequestViewSet(viewsets.ModelViewSet):
    """ChangeRequest nesnesini API ile yöneten viewset."""
    queryset = ChangeRequest.objects.all()
    serializer_class = ChangeRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'requester', 'target_ip', 'vendor']
    search_fields = ['title', 'config_payload']
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        if self.request.user.is_staff:
            return ChangeRequest.objects.all()
        return ChangeRequest.objects.filter(requester=self.request.user)

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk konfigürasyon talebini API üzerinden yaratır ve Celery kuyruğuna alır."""
        target_device_ids = request.data.get('target_devices', [])
        config_payload = request.data.get('config_payload', '')
        vendor = request.data.get('vendor', '')
        title = request.data.get('title', f"Toplu Konfigürasyon Talebi - {timezone.now().strftime('%d.%m.%Y %H:%M')}")

        if not target_device_ids or not config_payload:
            return Response(
                {'status': 'error', 'message': 'target_devices ve config_payload alanları zorunludur.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        change_request = ChangeRequest.objects.create(
            title=title,
            requester=request.user,
            status='pending',
            vendor=vendor,
            config_payload=config_payload
        )
        change_request.target_devices.set(Device.objects.filter(id__in=target_device_ids))

        from .tasks import bulk_push_config_to_devices
        bulk_push_config_to_devices.delay(change_request.id)

        serializer = self.get_serializer(change_request)
        return Response(
            {'status': 'success', 'message': 'Bulk operation queued.', 'change_request': serializer.data},
            status=status.HTTP_201_CREATED
        )

# ==================================================
# --- KABİN ÇİZİMİ İÇİN API ---
# ==================================================
@api_view(['GET'])
@permission_classes([AllowAny]) 
def get_rack_devices(request):
    """
    Sadece 'rack_name' (kabin adı) olan cihazları JSON olarak döndürür.
    Rack çizim sayfasındaki (JavaScript) fetch API bu endpoint'i kullanır.
    """
    # Kabin adı boş olmayan cihazları getir
    devices = Device.objects.exclude(rack_name__isnull=True).exclude(rack_name__exact='')
    data = []
    for d in devices:
        data.append({
            'id': d.id,
            'name': d.name,
            'type': d.device_type,
            'rack_name': d.rack_name,
            'rack_u_position': d.position_u,  
            'rack_u_height': d.height_u,      
        })
    return Response(data)