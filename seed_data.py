import os
import sys
import socket
import psutil
import platform
import uuid
import django
from django.utils import timezone
from datetime import timedelta
import random

# Django ortamını başlat
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User, Group
from inventory.models import (
    Device, IpAddress, Ticket, RemoteProbe, ITAsset, 
    License, VendorContract, ChangeRequest, DevicePerformanceLog, SystemLog
)

def get_real_system_info():
    """Çalışan bilgisayarın gerçek donanım ve ağ bilgilerini alır."""
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # MAC adresini güvenli bir şekilde al
        mac_num = hex(uuid.getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i: i + 2] for i in range(0, 11, 2))
        
        os_version = f"{platform.system()} {platform.release()}"
        
        # Gerçek zamanlı performans metrikleri
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        return {
            'hostname': hostname,
            'ip': ip_address,
            'mac': mac,
            'os_version': os_version,
            'cpu': cpu_usage,
            'ram': ram_usage,
            'disk': disk_usage
        }
    except Exception as e:
        print(f"Gerçek sistem bilgileri alınamadı: {e}")
        return None

def run_seed():
    print("🌱 NetArchitect Tohum Veri (Seed Data) Yükleniyor...")

    # 1. GRUPLAR VE KULLANICILAR
    print("Kullanıcılar oluşturuluyor...")
    ag_ekibi, _ = Group.objects.get_or_create(name='Ağ Ekibi')
    sistem_ekibi, _ = Group.objects.get_or_create(name='Sistem Ekibi')

    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser('admin', 'admin@netarchitect.local', 'Admin123!')
    else:
        admin = User.objects.get(username='admin')

    user_ag, _ = User.objects.get_or_create(username='ahmet.network', defaults={'email': 'ahmet@firma.com', 'first_name': 'Ahmet', 'last_name': 'Yılmaz'})
    user_ag.set_password('Pass123!')
    user_ag.groups.add(ag_ekibi)
    user_ag.save()

    # 2. CİHAZLAR VE IP ADRESLERİ
    print("Ağ Envanteri oluşturuluyor...")
    
    # GERÇEK SİSTEM BİLGİSİNİ AL (Burası işin şov kısmı)
    real_sys = get_real_system_info()
    devices = []
    
    if real_sys:
        print(f"💻 Gerçek Donanım Tespit Edildi: {real_sys['hostname']} ({real_sys['ip']})")
        real_dev, _ = Device.objects.get_or_create(
            name=real_sys['hostname'], 
            defaults={
                'device_type': 'Server', 
                'vendor': 'other', 
                'mac_address': real_sys['mac'], 
                'os_version': real_sys['os_version'],
                'monitoring_mode': 'monitoring', 
                'is_active': True,
                'cpu_usage': real_sys['cpu'],
                'ram_usage': real_sys['ram']
            }
        )
        IpAddress.objects.get_or_create(address=real_sys['ip'], defaults={'is_allocated': True, 'device': real_dev})
        devices.append(real_dev)
        
        # Gerçek cihaz için anlık performans logu oluştur
        DevicePerformanceLog.objects.create(
            device=real_dev, 
            cpu_usage=real_sys['cpu'], 
            ram_usage=real_sys['ram'], 
            disk_usage=real_sys['disk']
        )
        
        # Gerçek cihazı ITAsset (Zimmet) tablosuna ekle
        ITAsset.objects.get_or_create(
            serial_number=f"SN-{real_sys['mac'].replace('-', '')}",
            defaults={
                'name': f"NetArchitect Ana Sunucu ({real_sys['hostname']})",
                'asset_type': 'server',
                'model': 'Local Host Machine',
                'status': 'active',
                'assigned_to': 'BT Departmanı'
            }
        )

    # SAHTE (SIMÜLASYON) CİHAZLAR
    devices_data = [
        {'name': 'HQ-Core-Switch', 'type': 'Switch', 'vendor': 'cisco', 'ip': '10.0.0.1', 'mac': '00:1A:2B:3C:4D:5E', 'status': 'monitoring'},
        {'name': 'Ankara-Edge-Router', 'type': 'Router', 'vendor': 'cisco', 'ip': '192.168.10.1', 'mac': '00:1A:2B:AA:BB:CC', 'status': 'monitoring'},
        {'name': 'FW-Main-Datacenter', 'type': 'Router', 'vendor': 'other', 'ip': '10.0.0.254', 'mac': '00:1A:2B:FF:FF:FF', 'status': 'error'}, # Çökmüş cihaz simülasyonu
    ]

    for d in devices_data:
        dev, _ = Device.objects.get_or_create(
            name=d['name'], 
            defaults={
                'device_type': d['type'], 'vendor': d['vendor'], 'mac_address': d['mac'], 
                'monitoring_mode': d['status'], 'is_active': (d['status'] == 'monitoring')
            }
        )
        IpAddress.objects.get_or_create(address=d['ip'], defaults={'is_allocated': True, 'device': dev})
        devices.append(dev)

    # 3. AI TAHMİNLEYİCİ İÇİN PERFORMANS LOGLARI (Son 24 Saat)
    print("Yapay Zeka (AIOps) için geçmiş performans verileri üretiliyor...")
    now = timezone.now()
    
    # Cihaz listesindeki ilk simülasyon cihazını (HQ-Core-Switch) ve çökmüş olanı bul
    core_switch = next((d for d in devices if d.name == 'HQ-Core-Switch'), devices[0])
    
    # Gerçek cihazı bul (eğer eklendiyse) ve ona yük bindir, yoksa başka bir cihaza
    ai_target_device = devices[0] if real_sys else devices[1]
    
    for i in range(24):
        past_time = now - timedelta(hours=i)
        
        # Core Switch normal yükte
        if core_switch:
            DevicePerformanceLog.objects.create(device=core_switch, cpu_usage=random.uniform(20, 45), ram_usage=random.uniform(30, 50), disk_usage=random.uniform(40, 60), recorded_at=past_time)
        
        # AI Hedef Cihazı (Gerçek makinen veya Router) gitgide şişiyor (Tahminleyiciyi tetiklemek için)
        trend_cpu = min(98, 40 + (24-i)*2.5) 
        DevicePerformanceLog.objects.create(device=ai_target_device, cpu_usage=trend_cpu, ram_usage=random.uniform(70, 95), disk_usage=random.uniform(80, 95), recorded_at=past_time)

    # 4. UZAK AJANLAR (PROBES)
    print("Dağıtık Mimari Ajanları oluşturuluyor...")
    RemoteProbe.objects.get_or_create(name='Istanbul-HQ-Probe', defaults={'location': 'İstanbul Merkez', 'ip_address': '10.0.0.100', 'target_subnet': '10.0.0.0/16', 'status': 'online', 'last_heartbeat': now})
    RemoteProbe.objects.get_or_create(name='Ankara-DRC-Probe', defaults={'location': 'Ankara Felaket Kurtarma', 'ip_address': '192.168.10.100', 'target_subnet': '192.168.10.0/24', 'status': 'offline', 'last_heartbeat': now - timedelta(hours=2)})

    # 5. DESTEK BİLETLERİ (ITSM) VE SLA İHLALLERİ
    print("Destek Biletleri (Tickets) oluşturuluyor...")
    Ticket.objects.get_or_create(title='Cihaz Kapasite Alarmı', defaults={'description': 'Zabbix eşik değeri aşıldı. Kritik CPU kullanımı tespit edildi.', 'priority': 'Kritik', 'category': 'Donanim', 'status': 'Acik', 'device': ai_target_device, 'created_by': admin, 'sla_deadline': now - timedelta(hours=1), 'is_escalated': True}) # SLA Patlamış
    Ticket.objects.get_or_create(title='Yeni VLAN Talebi', defaults={'description': 'Misafir ağı için VLAN 50 oluşturulmalı.', 'priority': 'Orta', 'category': 'Ag', 'status': 'Inceleniyor', 'assigned_to': user_ag, 'created_by': admin})
    Ticket.objects.get_or_create(title='Kullanıcı Şifre Sıfırlama', defaults={'description': 'Muhasebe departmanı şifre sıfırlaması yapıldı.', 'priority': 'Dusuk', 'category': 'Diger', 'status': 'Cozuldu', 'created_by': admin})

    # 6. SÖZLEŞME VE LİSANSLAR (Yakında bitecekler simülasyonu)
    print("Sözleşmeler ve Lisanslar ekleniyor...")
    VendorContract.objects.get_or_create(title='TurkTelekom Metro Ethernet', defaults={'vendor_name': 'TurkTelekom', 'contract_type': 'internet', 'start_date': now.date() - timedelta(days=300), 'end_date': now.date() + timedelta(days=15), 'cost': 5000})
    License.objects.get_or_create(name='Cisco IOS XE Advanced', defaults={'vendor': 'Cisco', 'total_slots': 10, 'used_slots': 10, 'expiry_date': now.date() + timedelta(days=5)})

    # 7. SİSTEM LOGLARI
    SystemLog.objects.create(action='SYSTEM', details="NetArchitect kurulumu tamamlandı ve Tohum Veriler (Seed Data) yüklendi.", user=admin)
    SystemLog.objects.create(action='CONFIG', details="Ankara-Edge-Router OSPF konfigürasyonu başarıyla basıldı.", user=user_ag)
    
    if real_sys:
        SystemLog.objects.create(action='SYSTEM', details=f"Gerçek donanım tespiti yapıldı: {real_sys['hostname']} ağa dahil edildi.", user=admin)

    print("✅ BİTTİ! NetArchitect Sunum (Showcase) veritabanı başarıyla hazırlandı.")
    print("🔑 Kullanıcı Girişi -> admin / Admin123!")

if __name__ == '__main__':
    run_seed()