"""Kamera ve NVR cihazları için TCP/HTTP tabanlı sağlık kontrolü."""
import socket
import urllib.error
import urllib.request
from datetime import timedelta

from django.utils import timezone


def _tcp_reachable(host, port, timeout=2.0):
    """Belirtilen host:port çiftine TCP bağlantısı kurulabiliyor mu kontrol eder."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _http_reachable(url, timeout=3.0):
    """Stream veya web arayüzü URL'sine HTTP HEAD isteği ile erişilebilirlik testi."""
    try:
        request = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500
    except Exception:
        return False


def evaluate_camera_health(camera):
    """Kamera/NVR için basit sağlık kontrolü yapar ve durum önerir."""
    checks = []
    if camera.ip_address:
        checks.append(_tcp_reachable(str(camera.ip_address), 554) or _tcp_reachable(str(camera.ip_address), 80))
    if camera.stream_url:
        checks.append(_http_reachable(camera.stream_url))

    if not checks:
        return 'warning', 'IP veya stream URL tanımlı değil'

    if all(checks):
        return 'online', 'Ping/HTTP kontrolü başarılı'
    if any(checks):
        return 'warning', 'Kısmi erişim sorunu'
    return 'offline', 'Kamera/NVR erişilemiyor'


def poll_camera_devices(queryset=None):
    """Tüm kameraları tarar, durumlarını günceller ve özet istatistik döndürür."""
    from inventory.models import CameraDevice

    cameras = queryset or CameraDevice.objects.all()
    summary = {'online': 0, 'warning': 0, 'offline': 0, 'maintenance': 0}
    now = timezone.now()

    for camera in cameras:
        if camera.status == 'maintenance':
            summary['maintenance'] += 1
            continue
        status, _message = evaluate_camera_health(camera)
        camera.status = status
        camera.last_checked_at = now
        camera.save(update_fields=['status', 'last_checked_at', 'updated_at'])
        summary[status] = summary.get(status, 0) + 1

    # 6 saatten uzun süredir kontrol edilmeyen kayıtları say
    stale_cutoff = now - timedelta(hours=6)
    stale_count = CameraDevice.objects.filter(last_checked_at__lt=stale_cutoff).exclude(status='maintenance').count()
    return summary, stale_count
