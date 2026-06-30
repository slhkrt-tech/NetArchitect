import json
import io
import os
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.http import HttpResponse, JsonResponse
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.decorators.http import require_POST
from django.db import connection, models
from django.utils import timezone

from .helpdesk import is_support_staff
from .forms import (
    FactoryAreaForm, ConsumableItemForm,
    MaintenanceTaskForm, EmployeeITProcessForm,
    ProcurementRequestForm, OnCallShiftForm, BackupJobMonitorForm,
    VendorSupportCaseForm, AssetHandoverForm, MajorIncidentForm,
    AccessRequestForm, PrinterFleetItemForm, RunbookForm,
    RemoteAccessGrantForm, DepartmentChannelForm, DepartmentMessageForm,
    CameraDeviceForm, BusinessApplicationForm, ReportTemplateForm,
    ChangeCalendarEventForm, ServiceDependencyForm, IntegrationHealthCheckForm,
    ComplianceControlForm, DocumentOutputJobForm,
)
from .models import (
    FieldVisit, SalesOpportunity, Ticket, DLPEvent, Device, ITAsset, License,
    TicketCategory,
    FactoryArea, ConsumableItem, MaintenanceTask, EmployeeITProcess,
    ProcurementRequest, OnCallShift, BackupJobMonitor, VendorSupportCase, AssetHandover,
    MajorIncident, AccessRequest, PrinterFleetItem, Runbook,
    RemoteAccessGrant, DepartmentChannel, DepartmentMessage, CameraDevice,
    BusinessApplication, ReportTemplate,
    ChangeCalendarEvent, ServiceDependency, IntegrationHealthCheck,
    ComplianceControl, DocumentOutputJob,
)


def _parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_optional_float(value):
    if value in (None, ''):
        return None
    return _parse_float(value, None)


def health_check(request):
    """Load balancer ve Docker healthcheck için hafif sağlık endpoint'i."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return JsonResponse({'status': 'error', 'database': str(exc)}, status=503)
    return JsonResponse({'status': 'ok'})


def _readiness_item(key, title, ok, detail='', action='', severity='success'):
    return {
        'key': key,
        'title': title,
        'ok': bool(ok),
        'detail': detail,
        'action': action,
        'severity': severity if ok else 'danger',
    }


def build_readiness_report():
    """İlk kurulum ve canlı kullanım için ürün hazır olma raporu."""
    checks = []
    db_ok = True
    db_detail = 'Veritabanı bağlantısı çalışıyor.'
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        db_ok = False
        db_detail = str(exc)

    required_groups = ['Admin', 'Yönetim', 'Ağ Ekibi', 'Sistem Ekibi', 'Help Desk Ekibi']
    existing_groups = set(Group.objects.filter(name__in=required_groups).values_list('name', flat=True))
    missing_groups = [name for name in required_groups if name not in existing_groups]

    media_root = getattr(settings, 'MEDIA_ROOT', '')
    log_dir = getattr(settings, 'LOG_DIR', os.path.join(settings.BASE_DIR, 'logs'))

    checks.extend([
        _readiness_item('database', 'Veritabanı', db_ok, db_detail, 'DATABASE_URL ve migration durumunu kontrol edin.'),
        _readiness_item('admin', 'Admin Kullanıcı', User.objects.filter(is_superuser=True).exists(), 'En az bir superuser bulunmalı.', 'python manage.py createsuperuser'),
        _readiness_item('groups', 'Rol Grupları', not missing_groups, 'Eksik grup: ' + ', '.join(missing_groups) if missing_groups else 'Temel RBAC grupları hazır.', 'python manage.py setup_helpdesk'),
        _readiness_item('ticket_categories', 'Ticket Kategorileri', TicketCategory.objects.exists(), 'Varsayılan destek kategorileri hazır olmalı.', 'python manage.py setup_helpdesk'),
        _readiness_item('secret_key', 'Gizli Anahtar', bool(getattr(settings, 'SECRET_KEY', '')) and 'change-me' not in settings.SECRET_KEY.lower(), 'DJANGO_SECRET_KEY canlı ortamda benzersiz olmalı.', '.env içinden DJANGO_SECRET_KEY değerini değiştirin.'),
        _readiness_item('allowed_hosts', 'Allowed Hosts', bool(getattr(settings, 'ALLOWED_HOSTS', [])), ', '.join(getattr(settings, 'ALLOWED_HOSTS', [])) or 'Boş', 'ALLOWED_HOSTS canlı domainleri içermeli.'),
        _readiness_item('remote_secret', 'Remote Probe Secret', bool(getattr(settings, 'REMOTE_PROBE_SHARED_SECRET', '')), 'Uzak ajan senkronizasyon şifresi.', 'REMOTE_PROBE_SHARED_SECRET ayarlayın.'),
        _readiness_item('media_root', 'Media Dizini', bool(media_root) and os.path.isdir(media_root), str(media_root), 'media klasörünü oluşturup yazılabilir yapın.'),
        _readiness_item('logs', 'Log Dizini', bool(log_dir) and os.path.isdir(log_dir), str(log_dir), 'logs klasörünü oluşturup kalıcı volume bağlayın.'),
        _readiness_item('email', 'E-posta Ayarı', bool(getattr(settings, 'EMAIL_HOST', '')), getattr(settings, 'EMAIL_HOST', '') or 'Tanımlı değil', 'SMTP bilgilerini .env içine ekleyin.', 'warning'),
        _readiness_item('sso', 'SSO Hazırlığı', any([
            bool(getattr(settings, 'SOCIAL_AUTH_AZUREAD_OAUTH2_KEY', '')),
            bool(getattr(settings, 'SOCIAL_AUTH_OIDC_KEY', '')),
            bool(getattr(settings, 'SAML_ENABLED', False)),
        ]), 'Azure AD/OIDC/SAML opsiyonel.', 'Kurumsal giriş isteniyorsa SSO bilgilerini girin.', 'warning'),
        _readiness_item('celery', 'Celery/Redis Ayarı', bool(getattr(settings, 'CELERY_BROKER_URL', '')), getattr(settings, 'CELERY_BROKER_URL', ''), 'Redis ve Celery worker/beat servislerini çalıştırın.'),
    ])

    module_status = [
        {'title': 'Cihaz', 'count': Device.objects.count(), 'url': '/topoloji/'},
        {'title': 'Ticket', 'count': Ticket.objects.count(), 'url': '/panel/'},
        {'title': 'BT Varlık', 'count': ITAsset.objects.count(), 'url': '/it-envanter/'},
        {'title': 'Lisans', 'count': License.objects.count(), 'url': '/it-envanter/'},
        {'title': 'Fabrika Alanı', 'count': FactoryArea.objects.count(), 'url': '/fabrika-operasyonlari/'},
        {'title': 'Kamera', 'count': CameraDevice.objects.count(), 'url': '/komuta-merkezi/'},
        {'title': 'İş Uygulaması', 'count': BusinessApplication.objects.count(), 'url': '/komuta-merkezi/'},
        {'title': 'Runbook', 'count': Runbook.objects.count(), 'url': '/servis-surecleri/'},
        {'title': 'Rapor Şablonu', 'count': ReportTemplate.objects.count(), 'url': '/komuta-merkezi/'},
    ]

    critical_total = len([item for item in checks if item['severity'] == 'danger'])
    warning_total = len([item for item in checks if item['severity'] == 'warning' and not item['ok']])
    ok_total = len([item for item in checks if item['ok']])
    score = int((ok_total / len(checks)) * 100) if checks else 0

    return {
        'score': score,
        'critical_total': critical_total,
        'warning_total': warning_total,
        'ok_total': ok_total,
        'checks': checks,
        'module_status': module_status,
        'quick_start': [
            {'title': '1. Rolleri ve kategorileri hazırla', 'command': 'python manage.py setup_helpdesk'},
            {'title': '2. Admin oluştur', 'command': 'python manage.py createsuperuser'},
            {'title': '3. Veritabanını güncelle', 'command': 'python manage.py migrate'},
            {'title': '4. Üretim servislerini başlat', 'command': 'docker compose up --build -d'},
            {'title': '5. Sağlık kontrolü', 'command': 'curl http://127.0.0.1:8000/health/'},
        ],
    }


@login_required
def setup_center_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')
    return render(request, 'setup_center.html', build_readiness_report())


@login_required
def readiness_api(request):
    if not is_support_staff(request.user):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    return JsonResponse(build_readiness_report())


@login_required
def field_routes_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    if request.method == 'POST':
        visit = FieldVisit.objects.create(
            title=request.POST.get('title') or 'Saha Ziyareti',
            customer_name=request.POST.get('customer_name') or 'Müşteri',
            address=request.POST.get('address', ''),
            latitude=_parse_optional_float(request.POST.get('latitude')),
            longitude=_parse_optional_float(request.POST.get('longitude')),
            distance_km=_parse_float(request.POST.get('distance_km'), 0),
            vehicle_model=request.POST.get('vehicle_model') or 'Standart Servis Aracı',
            fuel_l_per_100km=_parse_float(request.POST.get('fuel_l_per_100km'), 7.5),
            ac_multiplier=_parse_float(request.POST.get('ac_multiplier'), 1.08),
            technician_id=request.POST.get('technician') or request.user.id,
            ticket_id=request.POST.get('ticket') or None,
        )
        messages.success(request, f"Rota durağı eklendi: {visit.title}")
        return redirect('field_routes')

    visits = FieldVisit.objects.select_related('technician', 'ticket').order_by('order_index', 'id')
    route_points = [
        {
            'id': visit.id,
            'title': visit.title,
            'customer': visit.customer_name,
            'lat': visit.latitude,
            'lng': visit.longitude,
            'fuel': visit.estimated_fuel_l,
            'distance': visit.distance_km,
        }
        for visit in visits if visit.latitude is not None and visit.longitude is not None
    ]
    return render(request, 'field_routes.html', {
        'visits': visits,
        'route_points_json': json.dumps(route_points),
        'technicians': User.objects.filter(is_active=True).order_by('username'),
        'tickets': Ticket.objects.filter(status__in=['Acik', 'Inceleniyor']).order_by('-created_at')[:100],
    })


@login_required
def sales_kanban_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    if request.method == 'POST':
        SalesOpportunity.objects.create(
            title=request.POST.get('title') or 'Yeni Fırsat',
            customer_name=request.POST.get('customer_name') or 'Müşteri',
            potential_revenue=_parse_float(request.POST.get('potential_revenue'), 0),
            probability=_parse_int(request.POST.get('probability'), 20),
            owner=request.user,
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, "Satış fırsatı eklendi.")
        return redirect('sales_kanban')

    stages = []
    for value, label in SalesOpportunity.STAGE_CHOICES:
        opportunities = SalesOpportunity.objects.filter(stage=value).select_related('owner').order_by('position', '-updated_at')
        total = sum(item.weighted_revenue for item in opportunities)
        stages.append({
            'value': value,
            'label': label,
            'items': opportunities,
            'weighted_total': total,
        })
    return render(request, 'sales_kanban.html', {'stages': stages})


@login_required
def offline_field_app(request):
    if not is_support_staff(request.user):
        return redirect('user_panel')
    return render(request, 'offline_field_app.html')


def service_worker_js(request):
    source_path = finders.find('js/service-worker.js')
    if source_path:
        with open(source_path, 'r', encoding='utf-8') as handle:
            return HttpResponse(handle.read(), content_type='application/javascript')
    with staticfiles_storage.open('js/service-worker.js', 'r') as handle:
        return HttpResponse(handle.read(), content_type='application/javascript')


@login_required
def factory_operations_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    forms = {
        'area': FactoryAreaForm(),
        'consumable': ConsumableItemForm(),
        'maintenance': MaintenanceTaskForm(),
        'employee_process': EmployeeITProcessForm(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        form_map = {
            'area': FactoryAreaForm,
            'consumable': ConsumableItemForm,
            'maintenance': MaintenanceTaskForm,
            'employee_process': EmployeeITProcessForm,
        }
        form_class = form_map.get(action)
        if form_class:
            form = form_class(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                if action == 'employee_process':
                    obj.requester = request.user
                obj.save()
                messages.success(request, "Fabrika IT operasyon kaydı oluşturuldu.")
                return redirect('factory_operations')
            forms[action] = form
        elif action == 'mark_maintenance_done':
            task = MaintenanceTask.objects.filter(pk=request.POST.get('task_id')).first()
            if task:
                task.mark_done()
                messages.success(request, f"Bakım tamamlandı: {task.title}")
                return redirect('factory_operations')
        elif action == 'close_employee_process':
            process = EmployeeITProcess.objects.filter(pk=request.POST.get('process_id')).first()
            if process:
                process.status = 'done'
                process.save(update_fields=['status', 'updated_at'])
                messages.success(request, f"Personel IT süreci tamamlandı: {process.employee_name}")
                return redirect('factory_operations')

    now = timezone.now()
    today = now.date()
    low_stock = ConsumableItem.objects.filter(quantity__lte=models.F('minimum_quantity')).order_by('quantity', 'name')
    due_tasks = MaintenanceTask.objects.select_related('factory_area', 'owner').exclude(status='done').filter(next_due_at__lte=now + timedelta(days=7))
    open_processes = EmployeeITProcess.objects.select_related('factory_area', 'assigned_to').exclude(status__in=['done', 'cancelled'])

    context = {
        'forms': forms,
        'areas': FactoryArea.objects.all()[:50],
        'consumables': ConsumableItem.objects.all()[:100],
        'low_stock': low_stock[:20],
        'maintenance_tasks': MaintenanceTask.objects.select_related('factory_area', 'owner').order_by('next_due_at')[:100],
        'due_tasks': due_tasks[:20],
        'employee_processes': open_processes[:100],
        'overdue_processes_count': open_processes.filter(due_date__lt=today).count(),
        'metrics': {
            'areas': FactoryArea.objects.count(),
            'low_stock': low_stock.count(),
            'due_tasks': due_tasks.count(),
            'open_processes': open_processes.count(),
        },
    }
    return render(request, 'factory_operations.html', context)


@login_required
def it_operations_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    forms = {
        'procurement': ProcurementRequestForm(),
        'oncall': OnCallShiftForm(),
        'backup': BackupJobMonitorForm(),
        'vendor_case': VendorSupportCaseForm(),
        'handover': AssetHandoverForm(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        form_map = {
            'procurement': ProcurementRequestForm,
            'oncall': OnCallShiftForm,
            'backup': BackupJobMonitorForm,
            'vendor_case': VendorSupportCaseForm,
            'handover': AssetHandoverForm,
        }
        form_class = form_map.get(action)
        if form_class:
            form = form_class(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                if action == 'procurement':
                    obj.requester = request.user
                elif action == 'handover':
                    obj.performed_by = request.user
                obj.save()
                messages.success(request, "IT operasyon kaydı oluşturuldu.")
                return redirect('it_operations')
            forms[action] = form
        elif action == 'approve_procurement':
            procurement = ProcurementRequest.objects.filter(pk=request.POST.get('procurement_id')).first()
            if procurement:
                procurement.status = 'approved'
                procurement.approved_by = request.user
                procurement.save(update_fields=['status', 'approved_by', 'updated_at'])
                messages.success(request, f"Satın alma talebi onaylandı: {procurement.title}")
                return redirect('it_operations')
        elif action == 'resolve_vendor_case':
            case = VendorSupportCase.objects.filter(pk=request.POST.get('case_id')).first()
            if case:
                case.status = 'resolved'
                case.resolved_at = timezone.now()
                case.save(update_fields=['status', 'resolved_at', 'updated_at'])
                messages.success(request, f"Tedarikçi vakası çözüldü: {case.title}")
                return redirect('it_operations')
        elif action == 'mark_backup_success':
            job = BackupJobMonitor.objects.filter(pk=request.POST.get('job_id')).first()
            if job:
                job.last_status = 'success'
                job.last_run_at = timezone.now()
                job.save(update_fields=['last_status', 'last_run_at', 'updated_at'])
                messages.success(request, f"Yedekleme başarılı işaretlendi: {job.name}")
                return redirect('it_operations')

    now = timezone.now()
    active_oncall = OnCallShift.objects.filter(start_at__lte=now, end_at__gte=now).select_related('engineer')
    unhealthy_backups = BackupJobMonitor.objects.filter(is_active=True, last_status__in=['failed', 'missed', 'warning'])
    pending_procurements = ProcurementRequest.objects.filter(status='pending').select_related('requester')
    open_vendor_cases = VendorSupportCase.objects.exclude(status__in=['resolved', 'closed']).select_related('assigned_to')

    context = {
        'forms': forms,
        'active_oncall': active_oncall,
        'pending_procurements': pending_procurements[:20],
        'unhealthy_backups': unhealthy_backups[:20],
        'open_vendor_cases': open_vendor_cases[:20],
        'recent_handovers': AssetHandover.objects.select_related('asset', 'performed_by').order_by('-handover_date')[:20],
        'metrics': {
            'pending_procurements': pending_procurements.count(),
            'active_oncall': active_oncall.count(),
            'unhealthy_backups': unhealthy_backups.count(),
            'open_vendor_cases': open_vendor_cases.count(),
        },
    }
    return render(request, 'it_operations.html', context)


@login_required
def service_operations_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    forms = {
        'incident': MajorIncidentForm(),
        'access': AccessRequestForm(),
        'printer': PrinterFleetItemForm(),
        'runbook': RunbookForm(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        form_map = {
            'incident': MajorIncidentForm,
            'access': AccessRequestForm,
            'printer': PrinterFleetItemForm,
            'runbook': RunbookForm,
        }
        form_class = form_map.get(action)
        if form_class:
            form = form_class(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                if action == 'access':
                    obj.requester = request.user
                obj.save()
                messages.success(request, "Servis süreç kaydı oluşturuldu.")
                return redirect('service_operations')
            forms[action] = form
        elif action == 'resolve_incident':
            incident = MajorIncident.objects.filter(pk=request.POST.get('incident_id')).first()
            if incident:
                incident.status = 'resolved'
                incident.resolved_at = timezone.now()
                incident.save(update_fields=['status', 'resolved_at', 'updated_at'])
                messages.success(request, f"Major incident çözüldü: {incident.title}")
                return redirect('service_operations')
        elif action == 'approve_access':
            access_request = AccessRequest.objects.filter(pk=request.POST.get('access_id')).first()
            if access_request:
                access_request.status = 'approved'
                access_request.approved_by = request.user
                access_request.save(update_fields=['status', 'approved_by', 'updated_at'])
                messages.success(request, f"Erişim talebi onaylandı: {access_request.target_system}")
                return redirect('service_operations')
        elif action == 'printer_maintenance_done':
            printer = PrinterFleetItem.objects.filter(pk=request.POST.get('printer_id')).first()
            if printer:
                printer.status = 'online'
                printer.last_maintenance_at = timezone.now()
                printer.save(update_fields=['status', 'last_maintenance_at', 'updated_at'])
                messages.success(request, f"Yazıcı bakım tamamlandı: {printer.name}")
                return redirect('service_operations')

    open_incidents = MajorIncident.objects.exclude(status__in=['resolved', 'closed']).select_related('factory_area', 'incident_commander')
    pending_access = AccessRequest.objects.filter(status='pending').select_related('requester')
    printer_alerts = PrinterFleetItem.objects.filter(models.Q(toner_level_percent__lte=15) | models.Q(status__in=['warning', 'maintenance', 'offline'])).select_related('factory_area')
    active_runbooks = Runbook.objects.filter(is_active=True).select_related('owner')

    context = {
        'forms': forms,
        'open_incidents': open_incidents[:20],
        'pending_access': pending_access[:20],
        'printer_alerts': printer_alerts[:20],
        'runbooks': active_runbooks[:30],
        'metrics': {
            'open_incidents': open_incidents.count(),
            'pending_access': pending_access.count(),
            'printer_alerts': printer_alerts.count(),
            'runbooks': active_runbooks.count(),
        },
    }
    return render(request, 'service_operations.html', context)


@login_required
def command_center_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    forms = {
        'remote_access': RemoteAccessGrantForm(),
        'channel': DepartmentChannelForm(),
        'message': DepartmentMessageForm(),
        'camera': CameraDeviceForm(),
        'application': BusinessApplicationForm(),
        'report': ReportTemplateForm(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        form_map = {
            'remote_access': RemoteAccessGrantForm,
            'channel': DepartmentChannelForm,
            'message': DepartmentMessageForm,
            'camera': CameraDeviceForm,
            'application': BusinessApplicationForm,
            'report': ReportTemplateForm,
        }
        form_class = form_map.get(action)
        if form_class:
            form = form_class(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                if action == 'message':
                    obj.author = request.user
                obj.save()
                messages.success(request, "Komuta merkezi kaydı oluşturuldu.")
                return redirect('command_center')
            forms[action] = form
        elif action == 'activate_remote_access':
            grant = RemoteAccessGrant.objects.filter(pk=request.POST.get('grant_id')).first()
            if grant:
                grant.status = 'active'
                grant.approved_by = request.user
                grant.save(update_fields=['status', 'approved_by', 'updated_at'])
                messages.success(request, f"Uzaktan erişim aktif edildi: {grant.employee_name}")
                return redirect('command_center')
        elif action == 'camera_checked':
            camera = CameraDevice.objects.filter(pk=request.POST.get('camera_id')).first()
            if camera:
                camera.status = 'online'
                camera.last_checked_at = timezone.now()
                camera.save(update_fields=['status', 'last_checked_at', 'updated_at'])
                messages.success(request, f"Kamera kontrol edildi: {camera.name}")
                return redirect('command_center')

    remote_access = RemoteAccessGrant.objects.exclude(status__in=['revoked', 'expired']).select_related('approved_by')
    camera_alerts = CameraDevice.objects.filter(status__in=['warning', 'offline', 'maintenance']).select_related('factory_area')
    applications = BusinessApplication.objects.select_related('technical_owner').order_by('status', 'name')
    channels = DepartmentChannel.objects.filter(is_active=True).order_by('department', 'name')

    context = {
        'forms': forms,
        'remote_access': remote_access[:20],
        'camera_alerts': camera_alerts[:20],
        'applications': applications[:24],
        'channels': channels[:20],
        'recent_messages': DepartmentMessage.objects.select_related('channel', 'author').order_by('-created_at')[:30],
        'reports': ReportTemplate.objects.filter(is_active=True).select_related('owner')[:20],
        'metrics': {
            'remote_access': remote_access.count(),
            'camera_alerts': camera_alerts.count(),
            'applications': applications.count(),
            'channels': channels.count(),
        },
    }
    return render(request, 'command_center.html', context)


@login_required
def governance_center_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    forms = {
        'calendar': ChangeCalendarEventForm(),
        'dependency': ServiceDependencyForm(),
        'integration': IntegrationHealthCheckForm(),
        'compliance': ComplianceControlForm(),
        'document': DocumentOutputJobForm(),
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        form_map = {
            'calendar': ChangeCalendarEventForm,
            'dependency': ServiceDependencyForm,
            'integration': IntegrationHealthCheckForm,
            'compliance': ComplianceControlForm,
            'document': DocumentOutputJobForm,
        }
        form_class = form_map.get(action)
        if form_class:
            form = form_class(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                if action == 'document':
                    obj.requested_by = request.user
                obj.save()
                messages.success(request, "Yönetişim kaydı oluşturuldu.")
                return redirect('governance_center')
            forms[action] = form
        elif action == 'complete_calendar':
            event = ChangeCalendarEvent.objects.filter(pk=request.POST.get('event_id')).first()
            if event:
                event.status = 'completed'
                event.save(update_fields=['status', 'updated_at'])
                messages.success(request, f"Takvim işi tamamlandı: {event.title}")
                return redirect('governance_center')
        elif action == 'mark_integration_healthy':
            check = IntegrationHealthCheck.objects.filter(pk=request.POST.get('check_id')).first()
            if check:
                check.last_status = 'healthy'
                check.last_checked_at = timezone.now()
                check.save(update_fields=['last_status', 'last_checked_at', 'updated_at'])
                messages.success(request, f"Entegrasyon sağlıklı işaretlendi: {check.name}")
                return redirect('governance_center')
        elif action == 'mark_compliant':
            control = ComplianceControl.objects.filter(pk=request.POST.get('control_id')).first()
            if control:
                control.status = 'compliant'
                control.last_checked_at = timezone.now().date()
                control.save(update_fields=['status', 'last_checked_at', 'updated_at'])
                messages.success(request, f"Uyum kontrolü tamamlandı: {control.title}")
                return redirect('governance_center')
        elif action == 'mark_document_ready':
            job = DocumentOutputJob.objects.filter(pk=request.POST.get('job_id')).first()
            if job:
                job.status = 'ready'
                job.save(update_fields=['status', 'updated_at'])
                messages.success(request, f"Çıktı işi hazır: {job.title}")
                return redirect('governance_center')

    now = timezone.now()
    upcoming_events = ChangeCalendarEvent.objects.exclude(status__in=['completed', 'cancelled']).filter(start_at__lte=now + timedelta(days=14)).select_related('factory_area', 'owner')
    unhealthy_integrations = IntegrationHealthCheck.objects.filter(last_status__in=['degraded', 'down']).select_related('owner')
    open_controls = ComplianceControl.objects.exclude(status='compliant').select_related('owner')
    document_jobs = DocumentOutputJob.objects.exclude(status__in=['delivered']).select_related('requested_by', 'template')

    context = {
        'forms': forms,
        'upcoming_events': upcoming_events[:20],
        'dependencies': ServiceDependency.objects.select_related('business_application', 'device').order_by('criticality')[:30],
        'unhealthy_integrations': unhealthy_integrations[:20],
        'open_controls': open_controls[:20],
        'document_jobs': document_jobs[:20],
        'metrics': {
            'upcoming_events': upcoming_events.count(),
            'dependencies': ServiceDependency.objects.count(),
            'unhealthy_integrations': unhealthy_integrations.count(),
            'open_controls': open_controls.count(),
            'document_jobs': document_jobs.count(),
        },
    }
    return render(request, 'governance_center.html', context)


@login_required
def dlp_events_view(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')
    events = DLPEvent.objects.select_related('user').order_by('-created_at')[:200]
    return render(request, 'dlp_events.html', {'events': events})


@login_required
def topology_png_export(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import networkx as nx

    graph = nx.Graph()
    devices = Device.objects.select_related('parent_device').all()
    for device in devices:
        graph.add_node(device.name, device_type=device.device_type)
        if device.parent_device:
            graph.add_edge(device.parent_device.name, device.name)

    fig, ax = plt.subplots(figsize=(12, 8))
    pos = nx.spring_layout(graph, seed=42)
    colors = [
        '#ef4444' if graph.nodes[node].get('device_type') == 'Router'
        else '#22c55e' if graph.nodes[node].get('device_type') == 'Switch'
        else '#0ea5e9'
        for node in graph.nodes
    ]
    nx.draw_networkx(graph, pos, node_color=colors, edge_color='#94a3b8', with_labels=True, ax=ax, font_size=9)
    ax.set_axis_off()
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format='png', dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required
@require_POST
def optimize_field_route(request):
    if not is_support_staff(request.user):
        return redirect('dashboard')
    visits = list(FieldVisit.objects.all().order_by('order_index', 'id'))
    current = None
    ordered = []
    remaining = visits[:]
    while remaining:
        if not current:
            next_visit = remaining.pop(0)
        else:
            next_visit = min(
                remaining,
                key=lambda v: ((v.latitude or 0) - (current.latitude or 0)) ** 2 + ((v.longitude or 0) - (current.longitude or 0)) ** 2,
            )
            remaining.remove(next_visit)
        ordered.append(next_visit)
        current = next_visit

    for index, visit in enumerate(ordered):
        visit.order_index = index + 1
        visit.save(update_fields=['order_index', 'updated_at'])
    messages.success(request, "Rota en yakın komşu algoritmasıyla optimize edildi.")
    return redirect('field_routes')
