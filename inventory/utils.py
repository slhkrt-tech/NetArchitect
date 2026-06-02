import psutil
import time
from jinja2 import Template
import os
from django.conf import settings
from django.db.models import Q
import ipaddress

# MAC (Layer 2) seviyesinde ağ taraması için gerekli kütüphaneler
import scapy.all as scapy
import socket

# İşletim sistemi seviyesi ping işlemleri ve metin ayrıştırma için
import re
import random
import datetime
from django.utils import timezone

# --- PASSWORD VAULT (ŞİFRE KASASI) AES-256 ---
from cryptography.fernet import Fernet

# DİKKAT: Gerçek sistemlerde bu anahtar .env dosyasında saklanır!
vault_key = getattr(settings, 'VAULT_KEY', None) or os.environ.get('VAULT_KEY')
if not vault_key:
    vault_key = 'q2aL_h5d1WqL1eX_X7pX_P4Q8aZ9sV2xO3cT6nY0jM8='
VAULT_KEY = vault_key.encode('utf-8') if isinstance(vault_key, str) else vault_key
cipher_suite = Fernet(VAULT_KEY)

def encrypt_vault_password(plain_text):
    """Metni AES ile şifreler."""
    if not plain_text:
        return plain_text
    if plain_text.startswith('aes_crypt:'):
        return plain_text
    return 'aes_crypt:' + cipher_suite.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_vault_password(cipher_text):
    """Şifreli metni AES ile çözer."""
    if not cipher_text or not cipher_text.startswith('aes_crypt:'):
        return cipher_text
    try:
        clean_cipher = cipher_text.replace('aes_crypt:', '').encode('utf-8')
        return cipher_suite.decrypt(clean_cipher).decode('utf-8')
    except Exception:
        return ""


def get_netmiko_device_type(vendor):
    vendor_name = (vendor or '').strip().lower()
    if 'cisco' in vendor_name:
        return 'cisco_ios'
    if 'huawei' in vendor_name:
        return 'huawei'
    return 'autodetect'


# Layer 7 (SSH) Ağ Otomasyonu Kütüphanesi
try:
    from netmiko import ConnectHandler, SSHDetect
except ImportError:
    pass 


# ========================================================
# --- HOCAYA ÖZEL: ÜRETİCİ TESPİTİ VE İKİNCİ ŞİFRE ---
# ========================================================

def detect_device_vendor(ip_address, username, password):
    """Cihaza SSH isteği yollayıp dönen parmak izinden (Fingerprint) üreticiyi tespit eder."""
    device_info = {
        "device_type": "autodetect",
        "host": ip_address,
        "username": username,
        "password": password,
    }
    try:
        guesser = SSHDetect(**device_info)
        best_match = guesser.autodetect()
        return best_match if best_match else "Bilinmiyor"
    except Exception as e:
        return f"Tespit Edilemedi: {str(e)}"


# ========================================================
# --- ÇOKLU ÜRETİCİ KONFİGÜRASYON ÜRETİCİ ---
# ========================================================
def generate_device_config(vendor, device_type, hostname, vlan_id, vlan_name, interface_name, enable_ospf=False, ospf_network="", ospf_area="0", enable_port_security=False, mac_limit="1"):
    """Profesyonel ağ konfigürasyonu üretir."""
    template_filename = f"{vendor}_{device_type}.txt"
    template_path = os.path.join(settings.BASE_DIR, 'inventory', 'templates', template_filename)
    
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
    except FileNotFoundError:
        return f"! HATA: {template_filename} şablon dosyası bulunamadı."
        
    jinja_template = Template(template_content)
    rendered_config = jinja_template.render(
        hostname=hostname, vlan_id=vlan_id, vlan_name=vlan_name,
        interface_name=interface_name, enable_ospf=enable_ospf,             
        ospf_network=ospf_network, ospf_area=ospf_area,                 
        enable_port_security=enable_port_security, mac_limit=mac_limit                  
    )
    return rendered_config


def calculate_subnets(network_address, new_prefix):
    """Bir network'ü alt ağlara (subnet) böler."""
    try:
        net = ipaddress.ip_network(network_address)
        subnets = list(net.subnets(new_prefix=int(new_prefix)))
        results = []
        for s in subnets:
            results.append({
                'network': str(s.network_address),
                'netmask': str(s.netmask),
                'broadcast': str(s.broadcast_address),
                'first_ip': str(s[1]),
                'last_ip': str(s[-2]),
            })
        return results
    except Exception as e:
        return str(e)


# ========================================================
# --- YENİ NESİL AĞ TARAMA (ARP LAYER 2 SCANNER) ---
# ========================================================
def scan_network(ip_range):
    """Layer 2 (ARP) tabanlı ağ tarayıcı."""
    devices = []
    try:
        arp_request = scapy.ARP(pdst=ip_range)
        broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast / arp_request
        answered_list = scapy.srp(arp_request_broadcast, timeout=2, verbose=False)[0]
        
        for element in answered_list:
            ip_addr = element[1].psrc
            mac_addr = element[1].hwsrc
            try:
                hostname = socket.gethostbyaddr(ip_addr)[0]
            except socket.herror:
                hostname = "Bilinmeyen Cihaz"
            devices.append({'ip': ip_addr, 'mac': mac_addr, 'hostname': hostname, 'status': 'Aktif 🟢'})
        return {"active_ips": devices, "total_scanned": len(devices)}
    except Exception as e:
        return {"error": str(e)}

# ========================================================
# --- MANAGEENGINE TARZI DERİN KEŞİF (DEEP DISCOVERY) ---
# ========================================================
def deep_discover_device(ip_address):
    """SNMP/WMI/SSH portları üzerinden donanım detaylarını simüle ederek çeker."""
    last_octet = int(ip_address.split('.')[-1])
    if last_octet < 20:
        os_type, vendor, model, device_type = "Cisco IOS XE 17.03", "Cisco", "Catalyst 9300", "Switch"
    elif last_octet < 100:
        os_type, vendor, model, device_type = "Windows Server 2022", "Microsoft", "VMware Platform", "Server"
    else:
        os_type, vendor, model, device_type = "Ubuntu 22.04 LTS", "Canonical", "Dell OptiPlex", "PC"

    return {
        "status": "success", "ip": ip_address, "os_version": os_type,
        "vendor": vendor, "model": model, "device_type": device_type,
        "serial_number": f"SN-{random.randint(100000, 999999)}",
        "disk_total_gb": random.choice([256, 512, 1024]),
        "discovery_method": "SNMPv3/WMI"
    }

# ========================================================
# --- AĞ OTOMASYONU (SSH PUSH & ENABLE MODU) ---
# ========================================================
def push_config_to_device(ip_address, username, password, enable_secret, vendor, config_payload, device_obj=None, change_request_id=None):
    """Cihaza SSH üzerinden bağlanıp konfigürasyon basar."""
    from .models import ChangeRequest, IpAddress, SystemLog, Ticket

    try:
        device = {
            'device_type': get_netmiko_device_type(vendor),
            'host': ip_address, 'username': username, 'password': password,
            'secret': enable_secret, 'port': 22, 'timeout': 10,
        }
        net_connect = ConnectHandler(**device)
        if enable_secret:
            net_connect.enable()

        config_lines = config_payload.split('\n')
        clean_cmds = [cmd.strip() for cmd in config_lines if cmd.strip() and not cmd.startswith('!')]
        net_connect.send_config_set(clean_cmds)

        if vendor == 'cisco':
            net_connect.save_config()
        net_connect.disconnect()

        if device_obj:
            device_obj.monitoring_mode = 'monitoring'
            device_obj.save(update_fields=['monitoring_mode'])

        if change_request_id:
            ChangeRequest.objects.filter(id=change_request_id).update(status='approved', execution_log='Konfigürasyon başarıyla uygulandı.')

        return True, "Başarıyla uygulandı."

    except Exception as e:
        error_text = str(e)
        if not device_obj:
            ip_record = IpAddress.objects.filter(address=ip_address).select_related('device').first()
            device_obj = ip_record.device if ip_record else None

        if change_request_id:
            ChangeRequest.objects.filter(id=change_request_id).update(status='failed', execution_log=f"SSH Hatası: {error_text}")
        else:
            q = Q(status__in=['pending', 'approved'])
            q &= Q(target_ip=ip_address)
            if device_obj:
                q |= Q(target_devices=device_obj)
            ChangeRequest.objects.filter(q).distinct().update(status='failed', execution_log=f"SSH Hatası: {error_text}")

        if device_obj:
            device_obj.monitoring_mode = 'error'
            device_obj.is_active = False
            device_obj.save(update_fields=['monitoring_mode', 'is_active'])
            Ticket.objects.create(
                title=f"Konfigürasyon Başarısızlığı: {device_obj.name}",
                description=f"{device_obj.name} ({ip_address}) cihazına konfigürasyon yazılırken hata oluştu. Hata: {error_text}",
                priority='Kritik', category='Ag', status='Acik', device=device_obj, created_by=None
            )

        SystemLog.objects.create(
            user=None,
            action='SYSTEM',
            details=f"SSH Hatası: {ip_address} | Talep durumu failed olarak güncellendi. Hata: {error_text}"
        )
        return False, error_text


# ========================================================
# --- EKSİK FONKSİYON EKLENDİ: YEDEKLEME (BACKUP) ---
# ========================================================
def backup_device_config(device_obj, device_ip, username, password, vendor, user):
    """
    Cihaza SSH ile bağlanıp konfigürasyonunu çeker ve DeviceBackup tablosuna kaydeder.
    """
    from .models import DeviceBackup, SystemLog
    
    try:
        device_details = {
            'device_type': get_netmiko_device_type(vendor),
            'host': device_ip,
            'username': username,
            'password': password,
            'port': 22,
            'timeout': 10,
        }
        
        # Sadece konfigürasyonu çekmek (show run) için Netmiko bağlantısı
        net_connect = ConnectHandler(**device_details)
        
        if vendor == 'cisco':
            output = net_connect.send_command("show running-config")
        else:
            output = net_connect.send_command("display current-configuration")
            
        net_connect.disconnect()
        
        # Veritabanına Yedek Kaydı
        DeviceBackup.objects.create(
            device=device_obj,
            config_text=output,
            backed_up_by=user
        )
        SystemLog.objects.create(
            user=user, 
            action='CONFIG', 
            details=f"Yedekleme: {device_obj.name} cihazının yedeği başarıyla alındı."
        )
        return True, "Yedek başarıyla alındı."
        
    except Exception as e:
        from .models import SystemLog
        SystemLog.objects.create(
            user=user, 
            action='CONFIG', 
            details=f"Yedekleme Hatası: {device_obj.name} cihazının yedeği alınamadı. Hata: {str(e)}"
        )
        return False, f"Cihaza bağlanılamadı: {str(e)}"


# ========================================================
# --- SOC / SIEM: GÜVENLİK LOG ANALİZİ VE DONANIM ---
# ========================================================
def poll_device_hardware(device_obj, ip):
    """
    WAZUH MANTIĞI: Cihazdan sadece performans değil, GÜVENLİK loglarını da analiz eder.
    """
    from .models import DevicePerformanceLog, SystemLog
    
    # Netmiko SSH Bilgileri
    device = {
        'device_type': 'cisco_ios' if device_obj.vendor == 'cisco' else 'huawei',
        'host': ip, 'username': device_obj.ssh_user or 'admin',
        'password': decrypt_vault_password(device_obj.ssh_password) or 'admin',
        'secret': decrypt_vault_password(device_obj.enable_password) or '',
        'timeout': 5,
    }
    
    security_alert = False
    security_details = ""

    try:
        device['device_type'] = get_netmiko_device_type(device_obj.vendor)
        net_connect = ConnectHandler(**device)
        if device['secret']:
            net_connect.enable()
            
        # 1. Donanım Verisi Çek
        version_out = net_connect.send_command("show version")
        cpu_out = net_connect.send_command("show processes cpu")
        
        # 2. GÜVENLİK DENETİMİ (SIEM ANALİZİ)
        # Cihazdaki son logları kontrol et (Brute-Force tespiti simülasyonu)
        log_out = net_connect.send_command("show logging | include Failed")
        
        if "Failed" in log_out or "denied" in log_out:
            security_alert = True
            security_details = f"Kritik: {ip} üzerinde başarısız oturum açma denemeleri saptandı!"

        # Verileri Ayıkla
        os_match = re.search(r'Version (.*?),', version_out)
        if os_match:
            device_obj.os_version = f"IOS v{os_match.group(1)}"
        
        cpu_match = re.search(r'CPU utilization for five seconds: (\d+)%', cpu_out)
        device_obj.cpu_usage = int(cpu_match.group(1)) if cpu_match else random.randint(10, 30)
        device_obj.ram_usage = random.randint(30, 75) 
        net_connect.disconnect()
        
    except Exception:
        # DEMO / SİMÜLASYON MODU
        device_obj.os_version = f"{device_obj.get_vendor_display()} v15.2"
        device_obj.cpu_usage = random.randint(10, 85)
        device_obj.ram_usage = random.randint(20, 90)
        
        # Simülasyon: %5 ihtimalle siber saldırı uyarısı üret
        if random.random() < 0.05:
            security_alert = True
            security_details = "Simüle Edilmiş Brute-Force Saldırısı Saptandı!"

    # Saldırı Varsa Sisteme Log At
    if security_alert:
        device_obj.os_version = "⚠️ GÜVENLİK İHLALİ!"
        SystemLog.objects.create(
            action='SYSTEM',
            details=f"SOC ALARMI: {device_obj.name} ({ip}) loglarında siber saldırı izi bulundu: {security_details}"
        )

    device_obj.last_polled = timezone.now()
    device_obj.save()
    
    # AIOps Modeli İçin Log Kaydı! 
    # Dikkat: Disk usage 0-100 arası rasgele arttırılarak simüle edildi (Test edebilmen için)
    DevicePerformanceLog.objects.create(
        device=device_obj, 
        cpu_usage=device_obj.cpu_usage, 
        ram_usage=device_obj.ram_usage,
        disk_usage=min(100.0, random.uniform(60, 98)) # Test için yüksek disk kullanımları
    )
    return device_obj

# ========================================================
# --- CANLI İZLEME MOTORU ---
# ========================================================
last_net_io = psutil.net_io_counters()
last_time = time.time()

def get_snmp_data(target_ip, community='public'):
    global last_net_io, last_time
    if target_ip in ['127.0.0.1', 'localhost']:
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            ram_usage = psutil.virtual_memory().percent
            return {
                "status": "success",
                "device": "Local Server",
                "cpu": round(cpu_usage, 1),
                "ram": round(ram_usage, 1),
                "traffic_in": random.randint(1, 5),
                "traffic_out": random.randint(1, 5),
                "latency": "<1",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return {
        "status": "success",
        "device": target_ip,
        "cpu": random.randint(5, 20),
        "ram": random.randint(30, 50),
        "traffic_in": 2.5,
        "traffic_out": 1.8,
        "latency": "15",
    }

# ========================================================
# --- YENİ: AIOps (Yapay Zeka Destekli) Tahminleyici Bakım ---
# ========================================================
def predict_resource_exhaustion(device_id, resource_type='cpu_usage', lookback_days=30, threshold=95.0):
    """
    Linear Regression (Doğrusal Regresyon) kullanarak cihazın CPU/RAM/Disk kaynağının 
    ne zaman 'threshold' (örn: %95) sınırına ulaşacağını tahmin eder.
    """
    from .models import DevicePerformanceLog

    cutoff_date = timezone.now() - datetime.timedelta(days=lookback_days)
    logs = DevicePerformanceLog.objects.filter(device_id=device_id, recorded_at__gte=cutoff_date).order_by('recorded_at')

    # Eğer en az 10 veri noktası yoksa tahmin yapmak sağlıksız olur
    if logs.count() < 10:
        return None, "Tahminleme için yeterli tarihsel veri (log) bulunmuyor."

    # X = Zaman (Unix Timestamp formatında saniye)
    # Y = Kullanım Yüzdesi (CPU, RAM vb.)
    x_values = [log.recorded_at.timestamp() for log in logs]
    y_values = [getattr(log, resource_type) for log in logs]

    # --- PURE PYTHON LİNEER REGRESYON ALGORİTMASI ---
    n = len(x_values)
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_x_sq = sum(x**2 for x in x_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))

    # Eğim (Slope - m) ve Kesişim (Intercept - b)
    denominator = (n * sum_x_sq - sum_x**2)
    if denominator == 0:
        return None, "Verilerde hiçbir değişiklik yok (Düz çizgi)."

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    # Eğer eğim 0 veya negatifse (Kullanım stabil veya düşüyorsa)
    if slope <= 0:
        return None, "Tehlike yok. Kaynak kullanımı stabil veya düşüş trendinde."

    # Hedef değere (Örn: %95) ulaşacağı X (Zaman) değerini bul: Y = mX + b => X = (Y - b) / m
    predicted_timestamp = (threshold - intercept) / slope
    
    # Hesaplanan zamanı okunabilir tarihe çevir
    predicted_date = datetime.datetime.fromtimestamp(predicted_timestamp)
    predicted_date = timezone.make_aware(predicted_date) if timezone.is_naive(predicted_date) else predicted_date
    
    # Şu andan itibaren kaç gün kaldığını hesapla
    days_left = (predicted_date - timezone.now()).days

    # Eğer geçmişte dolmuş gibi görünüyorsa (anomali)
    if days_left < 0:
        return 0, "Kaynak halihazırda kritik seviyenin üzerinde seyrediyor!"

    return days_left, predicted_date


def check_all_devices_predictive_maintenance():
    """ 
    Tüm cihazları AI modelinden geçirir. Eğer 14 gün içinde disk veya CPU 
    dolacaksa IT ekibine önceden haber vermek için Ticket açar. 
    """
    from .models import Device, Ticket, SystemLog
    
    devices = Device.objects.filter(is_active=True)
    alert_triggered = 0

    for device in devices:
        # Örnek: Disk kullanımı için tahmin yap
        days_left, result = predict_resource_exhaustion(device.id, resource_type='disk_usage', threshold=95.0)

        # Eğer günler sayısal döndüyse ve 14 günden az zaman kaldıysa
        if isinstance(days_left, int) and days_left <= 14:
            
            # Aynı cihaz için zaten açık bir "Tahmin" bileti var mı diye kontrol et (Spam yapmamak için)
            existing_ticket = Ticket.objects.filter(
                device=device, 
                status__in=['Acik', 'Inceleniyor'], 
                title__contains="Yapay Zeka Uyarısı"
            ).exists()

            if not existing_ticket:
                # Ticket oluştur!
                Ticket.objects.create(
                    title=f"🤖 Yapay Zeka Uyarısı: {device.name} Diski {days_left} Gün Sonra Dolacak!",
                    description=(
                        f"AIOps Tahmin Modülü, {device.name} cihazının disk kullanım trendini analiz etti.\n\n"
                        f"📊 Algoritma Sonucu: Cihazın diskinin yaklaşık {days_left} gün sonra (%95) kapasitesine ulaşması beklenmektedir.\n"
                        f"Tahmini Kapanma Tarihi: {result.strftime('%d %B %Y') if isinstance(result, datetime.datetime) else result}\n\n"
                        f"Lütfen sistem çökmeden önce logları temizleyin veya disk kapasitesini artırın."
                    ),
                    priority='Yuksek',
                    category='Donanim',
                    status='Acik',
                    device=device
                )
                SystemLog.objects.create(
                    action='SYSTEM', 
                    details=f"AIOps: {device.name} için {days_left} gün sonrasına tahminleyici bakım alarmı oluşturuldu."
                )
                alert_triggered += 1

    return f"Tarama tamamlandı. {alert_triggered} adet proaktif alarm üretildi."