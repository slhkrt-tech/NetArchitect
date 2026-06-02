from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Device, IpAddress, Ticket, DevicePerformanceLog, 
    ChangeRequest, RemoteProbe
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'device_type', 'vendor', 'mac_address', 
            'is_active', 'monitoring_mode', 'parent_device'
        ]

class IpAddressSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)

    class Meta:
        model = IpAddress
        fields = ['id', 'address', 'is_allocated', 'device']

class TicketSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    device = DeviceSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'priority', 'category', 
            'status', 'device', 'created_by', 'created_at', 'sla_deadline'
        ]

class DevicePerformanceLogSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = DevicePerformanceLog
        fields = ['id', 'device', 'device_name', 'cpu_usage', 'ram_usage', 'disk_usage', 'recorded_at']

class ChangeRequestSerializer(serializers.ModelSerializer):
    target_devices = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all(), many=True, required=False)
    requester = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = ChangeRequest
        fields = [
            'id', 'title', 'target_devices', 'target_ip', 'vendor',
            'config_payload', 'requester', 'status', 'reviewed_by',
            'created_at', 'updated_at', 'execution_log'
        ]

# ==========================================
# --- YENİ: DAĞITIK PROBE (AJAN) API DÖNÜŞTÜRÜCÜSÜ ---
# ==========================================
class RemoteProbeSerializer(serializers.ModelSerializer):
    # is_offline, models.py içerisindeki @property metodundan otomatik beslenir.
    # ReadOnlyField olduğu için dışarıdan POST isteğiyle değiştirilemez.
    is_offline = serializers.ReadOnlyField()

    class Meta:
        model = RemoteProbe
        fields = [
            'id', 'name', 'location', 'ip_address', 'target_subnet',
            'agent_version', 'status', 'last_heartbeat', 'is_offline'
        ]