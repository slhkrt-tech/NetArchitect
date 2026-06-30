#!/usr/bin/env python3
"""
OmniOps Dağıtık Probe Agent (probe_agent.py)

Bu script, uzak şubeler (Ankara Veri Merkezi, İstanbul Ofis vb.) sunucularına kurulup
burada bulunan ağ cihazlarını tarayarak merkezi OmniOps sunucusuna bilgi gönderir.

Özellikler:
- Periyodik ağ taraması (ARP, SNMP, SSH probe)
- Merkezi sunucuya heartbeat gönderme
- CPU/RAM performans metriklerinin toplanması
- Cihaz konfigürasyonlarının merkeze aktarılması
- Şifreli JSON paketleri ile iletişim
- Arka planda Celery-like görev depo sistemi (opsiyonel)

Bağımlılıklar (pip install):
- requests
- netmiko
- scapy
- psutil

Kurulum:
    1. requirements.txt'deki paketleri yükle
    2. config.ini dosyasını düzenle (sunucu IP'si, shared secret)
    3. python probe_agent.py

Çalıştırma:
    # Ön planda:
    python probe_agent.py
    
    # Arka planda (Linux):
    nohup python probe_agent.py > probe_agent.log 2>&1 &
    
    # Cron ile (Her 15 dakika):
    */15 * * * * /usr/bin/python3 /opt/probe_agent/probe_agent.py

Yapılandırma:
    config.ini dosyasında şu alanları belirle:
    [server]
    url = https://omniops.example.com
    shared_secret = your_shared_secret_key
    
    [probe]
    name = Ankara-Veri-Merkezi
    location = Ankara
    target_subnet = 192.168.1.0/24
    
    [network]
    timeout = 5
    retries = 2
    
    [ssh]
    username = admin
    password = password123
"""

import os
import sys
import json
import time
import logging
import configparser
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import ipaddress
import hashlib
import hmac
import base64

try:
    import requests
except ImportError:
    print("ERROR: requests kütüphanesi yüklü değil. Kurmak için: pip install requests")
    sys.exit(1)

try:
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
except ImportError:
    print("WARNING: netmiko kütüphanesi yüklü değil. SSH üzerinden config alınamayacak.")
    netmiko_available = False
else:
    netmiko_available = True

try:
    from scapy.all import ARP, Ether, srp
    from scapy.layers.inet import IP, ICMP
except ImportError:
    print("WARNING: scapy kütüphanesi yüklü değil. Ağ taraması sınırlı olacak.")
    scapy_available = False
else:
    scapy_available = True

try:
    from cryptography.fernet import Fernet, InvalidToken
    cryptography_available = True
except Exception:
    cryptography_available = False

# ==========================================
# LOGGING KURULUMU
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('probe_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ==========================================
# YAPILANDIRMA SINIFI
# ==========================================
class ProbeConfig:
    """Probe yapılandırmasını yönetir"""
    
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        
        if os.path.exists(config_file):
            self.config.read(config_file)
        else:
            self._create_default_config(config_file)
            logger.warning(f"Yapılandırma dosyası bulunamadı. Varsayılan '{config_file}' oluşturuldu.")
    
    def _create_default_config(self, config_file):
        """Varsayılan config.ini dosyasını oluştur"""
        self.config.add_section('server')
        self.config.set('server', 'url', 'https://omniops.example.com')
        self.config.set('server', 'shared_secret', 'omniops_probe_secret')
        self.config.set('server', 'heartbeat_interval', '900')  # 15 dakika
        self.config.set('server', 'sync_interval', '900')  # 15 dakika
        
        self.config.add_section('probe')
        self.config.set('probe', 'name', 'Remote-Probe-1')
        self.config.set('probe', 'location', 'Branch-Office')
        self.config.set('probe', 'target_subnet', '192.168.1.0/24')
        self.config.set('probe', 'agent_version', '1.0.0')
        
        self.config.add_section('network')
        self.config.set('network', 'timeout', '5')
        self.config.set('network', 'retries', '2')
        self.config.set('network', 'enable_arp_scan', 'true')
        self.config.set('network', 'enable_icmp_ping', 'true')
        
        self.config.add_section('ssh')
        self.config.set('ssh', 'username', 'admin')
        self.config.set('ssh', 'password', 'password123')
        self.config.set('ssh', 'port', '22')
        self.config.set('ssh', 'collect_configs', 'true')
        
        with open(config_file, 'w') as f:
            self.config.write(f)
    
    def get(self, section, key, default=None):
        """Config değerini güvenli şekilde al"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def getint(self, section, key, default=None):
        """Config integer değerini al"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def getbool(self, section, key, default=False):
        """Config boolean değerini al"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default


# ==========================================
# AĞ TARAMA MOTORLARİ
# ==========================================
class NetworkScanner:
    """Ağ taraması yapan sınıf"""
    
    def __init__(self, config: ProbeConfig):
        self.config = config
        self.timeout = config.getint('network', 'timeout', 5)
        self.retries = config.getint('network', 'retries', 2)
    
    def scan_subnet(self, subnet: str) -> List[str]:
        """
        Subnet içinde IP adreslerini tara.
        
        Tarama yöntemleri (sırasıyla):
        1. ARP taraması (en hızlı ve güvenilir)
        2. ICMP ping (fallback)
        3. Basit IP listesi (teknik tarama olmaksızın)
        """
        discovered_ips = []
        
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            logger.info(f"Tarama başladı: {subnet}")
            
            # 1. ARP Taraması (Scapy varsa)
            if scapy_available and self.config.getbool('network', 'enable_arp_scan', True):
                discovered_ips.extend(self._arp_scan(str(network)))
            
            # 2. ICMP Ping (Fallback)
            elif self.config.getbool('network', 'enable_icmp_ping', True):
                discovered_ips.extend(self._icmp_ping_scan(str(network)))
            
            # 3. Basit liste (timeout durumunda)
            if not discovered_ips:
                logger.warning(f"Tarama yöntemleri başarısız. Subnet IP'leri listesi oluşturuluyor: {subnet}")
                discovered_ips = self._get_subnet_ips(str(network))
            
            logger.info(f"Tarama tamamlandı: {len(discovered_ips)} IP bulundu")
            return list(set(discovered_ips))  # Tekrarları kaldır
            
        except ValueError as e:
            logger.error(f"Geçersiz subnet: {subnet} - {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Tarama hatası ({subnet}): {str(e)}")
            return []
    
    def _arp_scan(self, subnet: str) -> List[str]:
        """ARP taraması ile IP'leri bul (en hızlı yöntem)"""
        if not scapy_available:
            return []
        
        try:
            logger.info(f"ARP taraması yapılıyor: {subnet}")
            arp = ARP(pdst=subnet)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether / arp
            
            result = srp(packet, timeout=self.timeout, verbose=False)[0]
            discovered = [sent.psrc for sent, recv in result]
            
            logger.info(f"ARP taraması sonuç: {len(discovered)} cihaz bulundu")
            return discovered
            
        except Exception as e:
            logger.warning(f"ARP taraması başarısız: {str(e)}")
            return []
    
    def _icmp_ping_scan(self, subnet: str) -> List[str]:
        """ICMP ping ile IP'leri bul"""
        discovered = []
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            
            # Örnek: /24 subnet için tüm host'ları ping'le
            for host in list(network.hosts())[:256]:  # En fazla 256 host
                try:
                    result = subprocess.run(
                        ['ping', '-c' if os.name != 'nt' else '-n', '1', '-W', '1', str(host)],
                        capture_output=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        discovered.append(str(host))
                except Exception:
                    pass
            
            return discovered
        except Exception as e:
            logger.warning(f"ICMP ping taraması başarısız: {str(e)}")
            return []
    
    def _get_subnet_ips(self, subnet: str) -> List[str]:
        """Subnet içindeki tüm IP adreslerini listele (tarama olmaksızın)"""
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            return [str(ip) for ip in list(network.hosts())[:100]]  # İlk 100 IP
        except Exception as e:
            logger.error(f"Subnet IP listesi oluşturulamadı: {str(e)}")
            return []


# ==========================================
# CİHAZ KONFİGÜRASYONU TOPLAMA
# ==========================================
class DeviceConfigCollector:
    """Cihaz yapılandırmasını SSH/SNMP üzerinden toplar"""
    
    def __init__(self, config: ProbeConfig):
        self.config = config
    
    def collect_config(self, device_ip: str, device_type: str = 'cisco') -> Optional[str]:
        """
        SSH üzerinden cihaz konfigürasyonunu topla
        
        Desteklenen cihazlar: cisco, huawei, arista, juniper
        """
        if not netmiko_available:
            logger.warning(f"netmiko yüklü değil, config alınamıyor: {device_ip}")
            return None
        
        try:
            ssh_params = {
                'device_type': f'{device_type}_ssh',
                'host': device_ip,
                'username': self.config.get('ssh', 'username', 'admin'),
                'password': self.config.get('ssh', 'password', ''),
                'port': self.config.getint('ssh', 'port', 22),
                'timeout': self.config.getint('network', 'timeout', 5),
                'auth_timeout': 10,
            }
            
            logger.info(f"SSH bağlantısı kurulmaya çalışılıyor: {device_ip}")
            
            with ConnectHandler(**ssh_params) as net_connect:
                # Cihaz tipi komutlarına göre konfigürasyon al
                if device_type.lower() in ['cisco']:
                    config = net_connect.send_command('show running-config')
                elif device_type.lower() in ['huawei']:
                    config = net_connect.send_command('display current-configuration')
                elif device_type.lower() in ['juniper']:
                    config = net_connect.send_command('show configuration')
                else:
                    config = net_connect.send_command('show configuration')
                
                logger.info(f"Konfigürasyon alındı: {device_ip} ({len(config)} bytes)")
                return config
        
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            logger.warning(f"SSH bağlantı hatası ({device_ip}): {str(e)}")
            return None
        except Exception as e:
            logger.debug(f"Config toplama hatası ({device_ip}): {str(e)}")
            return None


# ==========================================
# PERFORMANS METRİKLERİ TOPLAMA
# ==========================================
class PerformanceCollector:
    """Sistem performans metriklerini toplar"""
    
    @staticmethod
    def get_system_metrics() -> Dict:
        """Sistem CPU ve RAM kullanım verilerini al"""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage': round(cpu_usage, 2),
                'ram_usage': round(ram.percent, 2),
                'disk_usage': round(disk.percent, 2),
                'ram_available_mb': round(ram.available / (1024 * 1024), 2),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        except Exception as e:
            logger.warning(f"Performans metriği alınamadı: {str(e)}")
            return {}


# ==========================================
# API KLİENTİ
# ==========================================
class OmniOpsAPIClient:
    """OmniOps sunucusuyla iletişim kuran API client"""
    
    def __init__(self, config: ProbeConfig):
        self.config = config
        self.base_url = config.get('server', 'url', 'https://omniops.example.com')
        self.shared_secret = config.get('server', 'shared_secret', 'omniops_probe_secret')
        self.probe_id = None
        self.session = requests.Session()
        self.session.verify = False  # Self-signed sertifikalar için (production'da True yapılmalı)
        # Optional payload encryption using Fernet. Provide `server.encryption_key` in config.ini
        self.encryption_enabled = False
        self.fernet = None
        enc_key = config.get('server', 'encryption_key', None)
        if enc_key and cryptography_available:
            try:
                # If user provided a URL-safe base64 32-byte key (44 chars), use it; otherwise derive from passphrase
                if len(enc_key) == 44:
                    key_b64 = enc_key.encode()
                else:
                    key_b64 = base64.urlsafe_b64encode(hashlib.sha256(enc_key.encode()).digest())
                self.fernet = Fernet(key_b64)
                self.encryption_enabled = True
            except Exception as e:
                logger.warning(f"Encryption key invalid, continuing without payload encryption: {e}")
    
    def send_heartbeat(self, probe_name: str, location: str, target_subnet: str, agent_version: str = '1.0.0') -> bool:
        """Sunucuya heartbeat gönder ve probe_id'yi al"""
        try:
            endpoint = f'{self.base_url}/api/probes/heartbeat/'
            
            payload = {
                'name': probe_name,
                'location': location,
                'ip_address': self._get_local_ip(),
                'target_subnet': target_subnet,
                'agent_version': agent_version,
            }
            
            headers = {
                'X-Remote-Probe-Secret': self.shared_secret,
                'Content-Type': 'application/json'
            }
            # Optionally encrypt payload
            if self.encryption_enabled and self.fernet:
                try:
                    token = self.fernet.encrypt(json.dumps(payload).encode()).decode()
                    post_payload = {'encrypted': True, 'data': token}
                except Exception as e:
                    logger.warning(f"Heartbeat payload encryption failed: {e}")
                    post_payload = payload
            else:
                post_payload = payload

            logger.info(f"Heartbeat gönderiliyor: {endpoint}")
            response = self.session.post(endpoint, json=post_payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.probe_id = data.get('probe_id')
                logger.info(f"Heartbeat başarılı. Probe ID: {self.probe_id}")
                
                # Sunucudan gelen görevleri işle (gelecekte)
                tasks = data.get('tasks', [])
                if tasks:
                    logger.info(f"Sunucudan {len(tasks)} görev alındı")
                
                return True
            else:
                logger.error(f"Heartbeat hatası: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Heartbeat gönderme hatası: {str(e)}")
            return False
    
    def sync_discovered_data(self, discovered_ips: List[str], performance_metrics: Dict, device_configs: List[Dict] = None) -> bool:
        """Keşfedilen IP'ler, performans ve config'leri sunucuya gönder"""
        if not self.probe_id:
            logger.warning("Probe ID alınmadı. Heartbeat gönder önce.")
            return False
        
        try:
            endpoint = f'{self.base_url}/api/probes/sync-data/'
            
            payload = {
                'secret': self.shared_secret,
                'probe_id': self.probe_id,
                'discovered_ips': discovered_ips,
                'performance_metrics': performance_metrics,
                'device_configs': device_configs or [],
            }
            
            headers = {
                'X-Remote-Probe-Secret': self.shared_secret,
                'Content-Type': 'application/json'
            }
            # Optionally encrypt payload
            if self.encryption_enabled and self.fernet:
                try:
                    token = self.fernet.encrypt(json.dumps(payload).encode()).decode()
                    post_payload = {'encrypted': True, 'data': token}
                except Exception as e:
                    logger.warning(f"Data payload encryption failed: {e}")
                    post_payload = payload
            else:
                post_payload = payload

            logger.info(f"Veri senkronizasyonu başlatılıyor: {len(discovered_ips)} IP, {len(device_configs or [])} config")
            response = self.session.post(endpoint, json=post_payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Senkronizasyon başarılı: {data.get('message')}")
                logger.info(f"  - İşlenen IP'ler: {data.get('processed_ips')}")
                logger.info(f"  - İşlenen Configler: {data.get('processed_configs')}")
                return True
            else:
                logger.error(f"Senkronizasyon hatası: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Veri senkronizasyonu hatası: {str(e)}")
            return False
    
    @staticmethod
    def _get_local_ip() -> str:
        """Probe'un yerel IP adresini al"""
        try:
            # Dış IP adresine sorgu yaparak yerel IP'yi öğren
            s = requests.Session()
            response = s.get('https://api.ipify.org?format=json', timeout=5)
            if response.status_code == 200:
                return response.json().get('ip', '127.0.0.1')
        except Exception:
            pass
        
        # Fallback: İlk aktif network interface'i al
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'


# ==========================================
# ANA PROBE KONTROL SİSTEMİ
# ==========================================
class RemoteProbe:
    """Ana Probe kontrol sınıfı - tüm işlemleri koordine eder"""
    
    def __init__(self, config_file: str = 'config.ini'):
        self.config = ProbeConfig(config_file)
        self.scanner = NetworkScanner(self.config)
        self.config_collector = DeviceConfigCollector(self.config)
        self.performance_collector = PerformanceCollector()
        self.api_client = OmniOpsAPIClient(self.config)
        
        self.probe_name = self.config.get('probe', 'name', 'Remote-Probe-1')
        self.location = self.config.get('probe', 'location', 'Branch')
        self.target_subnet = self.config.get('probe', 'target_subnet', '192.168.1.0/24')
        self.agent_version = self.config.get('probe', 'agent_version', '1.0.0')
        
        self.heartbeat_interval = self.config.getint('server', 'heartbeat_interval', 900)
        self.sync_interval = self.config.getint('server', 'sync_interval', 900)
        
        self.last_heartbeat = 0
        self.last_sync = 0
    
    def run(self):
        """Probe'u çalıştır (ana döngü)"""
        logger.info(f"=== OmniOps Remote Probe Başlatılıyor ===")
        logger.info(f"Probe Adı: {self.probe_name}")
        logger.info(f"Konum: {self.location}")
        logger.info(f"Hedef Subnet: {self.target_subnet}")
        logger.info(f"Agent Versiyonu: {self.agent_version}")
        logger.info(f"Sunucu: {self.api_client.base_url}")
        logger.info(f"===============================================")
        
        try:
            # İlk heartbeat
            self._send_heartbeat()
            
            # Ana döngü
            while True:
                now = time.time()
                
                # Heartbeat gönder (belirtilen aralıkta)
                if now - self.last_heartbeat >= self.heartbeat_interval:
                    self._send_heartbeat()
                
                # Ağ taraması ve veri senkronizasyonu (belirtilen aralıkta)
                if now - self.last_sync >= self.sync_interval:
                    self._scan_and_sync()
                
                # 60 saniye bekle, sonra kontrol et
                time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Probe kapatılıyor...")
        except Exception as e:
            logger.error(f"Ana döngü hatası: {str(e)}")
    
    def _send_heartbeat(self):
        """Heartbeat gönder"""
        logger.info("Heartbeat gönderiliyor...")
        if self.api_client.send_heartbeat(
            self.probe_name,
            self.location,
            self.target_subnet,
            self.agent_version
        ):
            self.last_heartbeat = time.time()
        else:
            logger.warning("Heartbeat gönderilemedi. Sunucu erişilemiyor mu?")
    
    def _scan_and_sync(self):
        """Ağ taraması ve veri senkronizasyonu"""
        logger.info("Ağ taraması ve veri senkronizasyonu başlatılıyor...")
        
        try:
            # 1. Ağ taraması
            discovered_ips = self.scanner.scan_subnet(self.target_subnet)
            logger.info(f"Tarama tamamlandı: {len(discovered_ips)} IP bulundu")
            
            # 2. Performans metriklerini topla
            performance_metrics = self.performance_collector.get_system_metrics()
            logger.info(f"Performans metriği: CPU={performance_metrics.get('cpu_usage')}%, RAM={performance_metrics.get('ram_usage')}%")
            
            # 3. Cihaz konfigürasyonlarını topla (opsiyonel ve yavaş)
            device_configs = []
            if self.config.getbool('ssh', 'collect_configs', True) and discovered_ips:
                logger.info("Cihaz konfigürasyonları toplanıyor...")
                # Sadece ilk 5 IP'den config al (performans için)
                for ip in discovered_ips[:5]:
                    config = self.config_collector.collect_config(ip, 'cisco')
                    if config:
                        device_configs.append({
                            'ip': ip,
                            'hostname': f'device-{ip.split(".")[-1]}',
                            'config': config,
                            'vendor': 'cisco'
                        })
                        time.sleep(2)  # SSH bağlantıları arasında bekleme
            
            # 4. Sunucuya senkronize et
            if self.api_client.sync_discovered_data(discovered_ips, performance_metrics, device_configs):
                self.last_sync = time.time()
                logger.info("Veri senkronizasyonu başarılı")
            else:
                logger.warning("Veri senkronizasyonu başarısız")
        
        except Exception as e:
            logger.error(f"Tarama ve senkronizasyon hatası: {str(e)}")


# ==========================================
# KOMUT SATIRI ARGÜMANLARİ
# ==========================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='OmniOps Remote Probe Agent'
    )
    parser.add_argument(
        '--config',
        default='config.ini',
        help='Yapılandırma dosyası yolu (varsayılan: config.ini)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test modu - tek seferlik tarama ve senkronizasyon yap'
    )
    parser.add_argument(
        '--subnet',
        help='Tarama yapılacak subnet (CIDR formatı: 192.168.1.0/24)'
    )
    
    args = parser.parse_args()
    
    # Probe'u başlat
    probe = RemoteProbe(args.config)
    
    # Test modu
    if args.test:
        logger.info("TEST MODU: Tek seferlik tarama yapılıyor...")
        subnet = args.subnet or probe.target_subnet
        discovered_ips = probe.scanner.scan_subnet(subnet)
        logger.info(f"Bulundu {len(discovered_ips)} IP:")
        for ip in discovered_ips:
            logger.info(f"  - {ip}")
        
        performance_metrics = probe.performance_collector.get_system_metrics()
        logger.info(f"Performans: {json.dumps(performance_metrics, indent=2)}")
    else:
        # Normal çalışma modu
        probe.run()


if __name__ == '__main__':
    main()
