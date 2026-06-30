from rest_framework import serializers
from django.contrib.auth.models import User, Group
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from .models import (
    Device, IpAddress, Ticket, DevicePerformanceLog,
    ChangeRequest, RemoteProbe, TicketComment, TicketAttachment,
    TicketCategory, UserProfile, Notification, NetworkScan, NetworkScanHost,
    FieldVisit, SalesOpportunity, DLPEvent, FactoryArea, ConsumableItem,
    MaintenanceTask, EmployeeITProcess, ProcurementRequest, OnCallShift,
    BackupJobMonitor, VendorSupportCase, AssetHandover, MajorIncident,
    AccessRequest, PrinterFleetItem, Runbook, RemoteAccessGrant,
    DepartmentChannel, DepartmentMessage, CameraDevice, BusinessApplication,
    ReportTemplate,
    ChangeCalendarEvent, ServiceDependency, IntegrationHealthCheck,
    ComplianceControl, DocumentOutputJob,
)
from .helpdesk import is_support_staff


class UserProfileSerializer(serializers.ModelSerializer):
    initials = serializers.CharField(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['phone', 'bio', 'avatar', 'department', 'initials']


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'date_joined', 'profile', 'groups', 'role',
        ]
        read_only_fields = ['date_joined']

    @extend_schema_field(OpenApiTypes.STR)
    def get_role(self, obj):
        if obj.is_superuser:
            return 'Admin'
        group_names = list(obj.groups.values_list('name', flat=True))
        if 'Admin' in group_names:
            return 'Admin'
        if any(g in group_names for g in ['Destek Personeli', 'Help Desk Ekibi', 'Ağ Ekibi', 'Sistem Ekibi']):
            return 'Destek Personeli'
        return 'Müşteri'

    @extend_schema_field(UserProfileSerializer)
    def get_profile(self, obj):
        try:
            return UserProfileSerializer(obj.profile).data
        except UserProfile.DoesNotExist:
            return None


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10)
    role = serializers.ChoiceField(
        choices=['Admin', 'Destek Personeli', 'Müşteri'], write_only=True, default='Müşteri'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'is_staff']

    def create(self, validated_data):
        role = validated_data.pop('role', 'Müşteri')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        group = Group.objects.filter(name=role).first()
        if group:
            user.groups.add(group)
        UserProfile.objects.get_or_create(user=user)
        return user


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'device_type', 'vendor', 'mac_address',
            'is_active', 'monitoring_mode', 'parent_device',
        ]


class IpAddressSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)

    class Meta:
        model = IpAddress
        fields = ['id', 'address', 'is_allocated', 'device']


class NetworkScanHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkScanHost
        fields = [
            'id', 'ip_address', 'mac_address', 'hostname', 'vendor',
            'detected_by', 'latency_ms', 'raw_socket_open', 'created_at',
        ]


class NetworkScanSerializer(serializers.ModelSerializer):
    hosts = NetworkScanHostSerializer(many=True, read_only=True)
    requested_by = UserSerializer(read_only=True)

    class Meta:
        model = NetworkScan
        fields = [
            'id', 'requested_by', 'network', 'method', 'total_hosts',
            'active_hosts', 'duration_ms', 'error', 'created_at', 'hosts',
        ]
        read_only_fields = ['requested_by', 'total_hosts', 'active_hosts', 'duration_ms', 'error', 'created_at', 'hosts']


class TicketCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'sla_hours', 'is_active']


class TicketCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'author', 'content', 'is_internal', 'created_at']
        read_only_fields = ['author', 'created_at']

    def validate_is_internal(self, value):
        request = self.context.get('request')
        if value and request and not is_support_staff(request.user):
            raise serializers.ValidationError('Dahili not oluşturma yetkiniz yok.')
        return value

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        comment = super().create(validated_data)
        from .helpdesk import notify_ticket_event
        notify_ticket_event(comment.ticket, 'comment', actor=validated_data['author'])
        return comment


class TicketAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = TicketAttachment
        fields = ['id', 'ticket', 'uploaded_by', 'file', 'filename', 'uploaded_at']
        read_only_fields = ['uploaded_by', 'filename', 'uploaded_at']

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class TicketSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    device = DeviceSerializer(read_only=True)
    ticket_category = TicketCategorySerializer(read_only=True)
    ticket_category_id = serializers.PrimaryKeyRelatedField(
        queryset=TicketCategory.objects.filter(is_active=True),
        source='ticket_category', write_only=True, required=False, allow_null=True,
    )
    is_sla_breached = serializers.BooleanField(read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'priority', 'category', 'ticket_category',
            'ticket_category_id', 'status', 'device', 'created_by', 'assigned_to',
            'is_escalated', 'is_sla_breached', 'created_at', 'updated_at',
            'closed_at', 'sla_deadline', 'comments_count',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'closed_at']

    @extend_schema_field(OpenApiTypes.INT)
    def get_comments_count(self, obj):
        return obj.comments.count()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'link', 'notification_type',
            'is_read', 'created_at', 'ticket',
        ]
        read_only_fields = ['created_at']


class FieldVisitSerializer(serializers.ModelSerializer):
    technician = UserSerializer(read_only=True)
    ticket_title = serializers.CharField(source='ticket.title', read_only=True)

    class Meta:
        model = FieldVisit
        fields = [
            'id', 'title', 'technician', 'ticket', 'ticket_title',
            'customer_name', 'address', 'latitude', 'longitude', 'order_index',
            'distance_km', 'vehicle_model', 'fuel_l_per_100km', 'ac_multiplier',
            'estimated_fuel_l', 'status', 'scheduled_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['estimated_fuel_l', 'created_at', 'updated_at']


class SalesOpportunitySerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    weighted_revenue = serializers.FloatField(read_only=True)

    class Meta:
        model = SalesOpportunity
        fields = [
            'id', 'title', 'customer_name', 'owner', 'stage',
            'potential_revenue', 'probability', 'weighted_revenue',
            'notes', 'position', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'weighted_revenue']


class DLPEventSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = DLPEvent
        fields = ['id', 'user', 'source', 'rule', 'severity', 'excerpt', 'blocked', 'created_at']
        read_only_fields = ['created_at']


class FactoryAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactoryArea
        fields = ['id', 'name', 'code', 'description', 'criticality', 'manager_name', 'created_at']
        read_only_fields = ['created_at']


class ConsumableItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ConsumableItem
        fields = [
            'id', 'name', 'category', 'sku', 'compatible_with', 'location',
            'quantity', 'minimum_quantity', 'unit', 'vendor', 'is_low_stock', 'updated_at',
        ]
        read_only_fields = ['is_low_stock', 'updated_at']


class MaintenanceTaskSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    factory_area_name = serializers.CharField(source='factory_area.name', read_only=True)

    class Meta:
        model = MaintenanceTask
        fields = [
            'id', 'title', 'task_type', 'factory_area', 'factory_area_name',
            'device', 'asset', 'owner', 'owner_name', 'frequency_days',
            'last_completed_at', 'next_due_at', 'status', 'checklist', 'notes',
            'is_overdue', 'created_at', 'updated_at',
        ]
        read_only_fields = ['last_completed_at', 'is_overdue', 'created_at', 'updated_at']


class EmployeeITProcessSerializer(serializers.ModelSerializer):
    completion_percent = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    requester_name = serializers.CharField(source='requester.username', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)

    class Meta:
        model = EmployeeITProcess
        fields = [
            'id', 'employee_name', 'department', 'process_type', 'factory_area',
            'requester', 'requester_name', 'assigned_to', 'assigned_to_name',
            'due_date', 'status', 'ad_account_done', 'email_done', 'erp_done',
            'vpn_done', 'device_done', 'badge_done', 'data_backup_done',
            'completion_percent', 'is_overdue', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['requester', 'completion_percent', 'is_overdue', 'created_at', 'updated_at']


class ProcurementRequestSerializer(serializers.ModelSerializer):
    requester = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = ProcurementRequest
        fields = [
            'id', 'title', 'description', 'category', 'quantity', 'estimated_cost',
            'vendor_name', 'factory_area', 'requester', 'approved_by', 'status',
            'needed_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['requester', 'approved_by', 'created_at', 'updated_at']


class OnCallShiftSerializer(serializers.ModelSerializer):
    engineer_name = serializers.CharField(source='engineer.username', read_only=True)
    is_active_now = serializers.BooleanField(read_only=True)

    class Meta:
        model = OnCallShift
        fields = [
            'id', 'engineer', 'engineer_name', 'start_at', 'end_at', 'phone',
            'is_primary', 'is_active_now', 'notes', 'created_at',
        ]
        read_only_fields = ['is_active_now', 'created_at']


class BackupJobMonitorSerializer(serializers.ModelSerializer):
    is_unhealthy = serializers.BooleanField(read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = BackupJobMonitor
        fields = [
            'id', 'name', 'system_type', 'target_host', 'schedule_description',
            'last_run_at', 'last_status', 'next_run_at', 'retention_days',
            'owner', 'owner_name', 'is_active', 'is_unhealthy', 'notes', 'updated_at',
        ]
        read_only_fields = ['is_unhealthy', 'updated_at']


class VendorSupportCaseSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)

    class Meta:
        model = VendorSupportCase
        fields = [
            'id', 'title', 'vendor_name', 'vendor_contract', 'case_number',
            'priority', 'status', 'assigned_to', 'assigned_to_name',
            'opened_at', 'resolved_at', 'description', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class AssetHandoverSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.username', read_only=True)

    class Meta:
        model = AssetHandover
        fields = [
            'id', 'asset', 'asset_name', 'employee_name', 'department', 'factory_area',
            'action', 'handover_date', 'condition_notes', 'performed_by',
            'performed_by_name', 'created_at',
        ]
        read_only_fields = ['performed_by', 'created_at']


class MajorIncidentSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.IntegerField(read_only=True)
    commander_name = serializers.CharField(source='incident_commander.username', read_only=True)

    class Meta:
        model = MajorIncident
        fields = [
            'id', 'title', 'severity', 'status', 'factory_area', 'ticket',
            'incident_commander', 'commander_name', 'started_at', 'resolved_at',
            'impact_summary', 'root_cause', 'corrective_actions',
            'duration_minutes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['duration_minutes', 'created_at', 'updated_at']


class AccessRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = AccessRequest
        fields = [
            'id', 'requester', 'requester_name', 'employee_name', 'department',
            'access_type', 'target_system', 'justification', 'approved_by',
            'approved_by_name', 'status', 'expires_at', 'provisioned_at',
            'is_expired', 'created_at', 'updated_at',
        ]
        read_only_fields = ['requester', 'approved_by', 'provisioned_at', 'is_expired', 'created_at', 'updated_at']


class PrinterFleetItemSerializer(serializers.ModelSerializer):
    needs_consumable = serializers.BooleanField(read_only=True)

    class Meta:
        model = PrinterFleetItem
        fields = [
            'id', 'name', 'device_kind', 'ip_address', 'serial_number', 'model',
            'factory_area', 'consumable', 'page_counter', 'toner_level_percent',
            'status', 'last_maintenance_at', 'needs_consumable', 'notes', 'updated_at',
        ]
        read_only_fields = ['needs_consumable', 'updated_at']


class RunbookSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Runbook
        fields = [
            'id', 'title', 'category', 'owner', 'owner_name', 'related_device_type',
            'steps', 'rollback_steps', 'is_active', 'version',
            'last_reviewed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class RemoteAccessGrantSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = RemoteAccessGrant
        fields = [
            'id', 'employee_name', 'department', 'access_method', 'target_resource',
            'gateway', 'allowed_source', 'mfa_required', 'status', 'approved_by',
            'approved_by_name', 'expires_at', 'is_expired', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['approved_by', 'is_expired', 'created_at', 'updated_at']


class DepartmentChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentChannel
        fields = ['id', 'name', 'department', 'description', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class DepartmentMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = DepartmentMessage
        fields = ['id', 'channel', 'author', 'author_name', 'message', 'is_announcement', 'created_at']
        read_only_fields = ['author', 'created_at']


class CameraDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraDevice
        fields = [
            'id', 'name', 'device_type', 'ip_address', 'stream_url', 'location',
            'factory_area', 'recording_days', 'status', 'last_checked_at',
            'notes', 'updated_at',
        ]
        read_only_fields = ['updated_at']


class BusinessApplicationSerializer(serializers.ModelSerializer):
    technical_owner_name = serializers.CharField(source='technical_owner.username', read_only=True)

    class Meta:
        model = BusinessApplication
        fields = [
            'id', 'name', 'app_type', 'url', 'owner_department',
            'technical_owner', 'technical_owner_name', 'sso_enabled',
            'status', 'notes', 'updated_at',
        ]
        read_only_fields = ['updated_at']


class ReportTemplateSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'title', 'report_type', 'description', 'query_notes',
            'output_format', 'is_active', 'owner', 'owner_name', 'updated_at',
        ]
        read_only_fields = ['updated_at']


class ChangeCalendarEventSerializer(serializers.ModelSerializer):
    is_active_now = serializers.BooleanField(read_only=True)

    class Meta:
        model = ChangeCalendarEvent
        fields = [
            'id', 'title', 'event_type', 'risk_level', 'factory_area',
            'change_request', 'owner', 'start_at', 'end_at',
            'expected_impact', 'rollback_plan', 'status', 'is_active_now',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['is_active_now', 'created_at', 'updated_at']


class ServiceDependencySerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(source='business_application.name', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = ServiceDependency
        fields = [
            'id', 'name', 'business_application', 'application_name', 'device',
            'device_name', 'dependency_type', 'criticality',
            'impact_description', 'created_at',
        ]
        read_only_fields = ['created_at']


class IntegrationHealthCheckSerializer(serializers.ModelSerializer):
    is_unhealthy = serializers.BooleanField(read_only=True)

    class Meta:
        model = IntegrationHealthCheck
        fields = [
            'id', 'name', 'integration_type', 'endpoint_url', 'owner',
            'last_status', 'last_checked_at', 'response_time_ms',
            'is_unhealthy', 'notes', 'updated_at',
        ]
        read_only_fields = ['is_unhealthy', 'updated_at']


class ComplianceControlSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = ComplianceControl
        fields = [
            'id', 'title', 'framework', 'owner', 'status', 'evidence',
            'remediation_plan', 'due_date', 'last_checked_at',
            'is_overdue', 'updated_at',
        ]
        read_only_fields = ['is_overdue', 'updated_at']


class DocumentOutputJobSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)

    class Meta:
        model = DocumentOutputJob
        fields = [
            'id', 'title', 'job_type', 'requested_by', 'requested_by_name',
            'template', 'output_format', 'status', 'file', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['requested_by', 'created_at', 'updated_at']


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
            'created_at', 'updated_at', 'execution_log',
        ]


class RemoteProbeSerializer(serializers.ModelSerializer):
    is_offline = serializers.BooleanField(read_only=True)

    class Meta:
        model = RemoteProbe
        fields = [
            'id', 'name', 'location', 'ip_address', 'target_subnet',
            'agent_version', 'status', 'last_heartbeat', 'is_offline',
        ]
