from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Device(models.Model):
    DEVICE_TYPES = (
        ('Router', 'Router'),
        ('Switch', 'Switch'),
        ('Server', 'Sunucu'),
        ('PC', 'Bilgisayar'),
    )

    VENDOR_CHOICES = (
        ('cisco', 'Cisco IOS'),
        ('huawei', 'Huawei VRP'),
        ('other', 'Diğer'),
    )

    name = models.CharField(max_length=100, verbose_name="Cihaz Adı")
    # INDEX EKLENDİ: Türüne göre cihaz aramayı hızlandırır
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES, verbose_name="Cihaz Türü", db_index=True)
    
    # INDEX EKLENDİ: MAC adresine göre arama çok sık yapıldığı için indekslendi
    mac_address = models.CharField(max_length=17, blank=True, null=True, verbose_name="MAC Adresi", db_index=True)
    
    # INDEX EKLENDİ: Aktif/Pasif cihaz filtrelemesi hızlandırıldı
    is_active = models.BooleanField(default=True, verbose_name="Durum", db_index=True)
    monitoring_mode = models.CharField(
        max_length=20,
        choices=(
            ('monitoring', 'İzleme'),
            ('error', 'Hata'),
            ('offline', 'Çevrimdışı'),
        ),
        default='monitoring',
        verbose_name="İzleme Modu",
        db_index=True,
    )
    parent_device = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_devices', verbose_name="Üst Cihaz")

    rack_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Kabin Adı")
    position_u = models.IntegerField(blank=True, null=True, verbose_name="Başlangıç U")
    height_u = models.IntegerField(default=1, verbose_name="Yükseklik")

    vendor = models.CharField(max_length=20, choices=VENDOR_CHOICES, default='cisco', verbose_name="Üretici")
    ssh_user = models.CharField(max_length=50, blank=True, null=True, verbose_name="Kullanıcı Adı")
    ssh_password = models.CharField(max_length=100, blank=True, null=True, verbose_name="Parola")
    enable_password = models.CharField(max_length=100, blank=True, null=True, verbose_name="Enable Parolası") 

    os_version = models.CharField(max_length=100, blank=True, null=True, verbose_name="İşletim Sistemi")
    cpu_usage = models.IntegerField(default=0, verbose_name="CPU Kullanımı")
    ram_usage = models.IntegerField(default=0, verbose_name="RAM Kullanımı")
    last_polled = models.DateTimeField(null=True, blank=True, verbose_name="Son Denetim")

    cpu_alarm_threshold = models.IntegerField(default=90, verbose_name="Kritik CPU Eşiği (%)")
    ram_alarm_threshold = models.IntegerField(default=90, verbose_name="Kritik RAM Eşiği (%)")

    def get_children(self):
        return Device.objects.filter(parent_device=self)

    def save(self, *args, **kwargs):
        from .utils import encrypt_vault_password
        if self.ssh_password and not self.ssh_password.startswith('aes_crypt:'):
            self.ssh_password = encrypt_vault_password(self.ssh_password)
        if self.enable_password and not self.enable_password.startswith('aes_crypt:'):
            self.enable_password = encrypt_vault_password(self.enable_password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class IpAddress(models.Model):
    # UNIQUE zaten DB Index oluşturur.
    address = models.GenericIPAddressField(protocol='IPv4', verbose_name="IP Adresi", unique=True)
    is_allocated = models.BooleanField(default=False, verbose_name="Tahsis Durumu", db_index=True)
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bağlı Cihaz", db_index=True)

    def __str__(self):
        return self.address

class ServiceCatalogItem(models.Model):
    CATEGORY_CHOICES = [
        ('Yazılım', 'Yazılım ve Lisans'),
        ('Donanım', 'Donanım Tahsisi'),
        ('Erişim', 'Ağ ve VPN Erişimi'),
        ('Diger', 'Diğer Hizmetler'),
    ]
    
    title = models.CharField(max_length=100, verbose_name="Hizmet Adı")
    description = models.TextField(verbose_name="Açıklama ve Şartlar")
    icon = models.CharField(max_length=50, default="mdi:laptop", verbose_name="Iconify İkon Kodu")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Yazılım', verbose_name="Kategori")
    requires_approval = models.BooleanField(default=False, verbose_name="Yönetici Onayı Gerekli Mi?")
    
    def __str__(self):
        return self.title

class Ticket(models.Model):
    STATUS_CHOICES = (
        ('Acik', 'Açık'),
        ('Inceleniyor', 'İnceleniyor'),
        ('Cozuldu', 'Çözüldü'),
        ('Kapatildi', 'Kapatıldı'),
    )
    
    PRIORITY_CHOICES = (
        ('Kritik', 'Kritik'),
        ('Yuksek', 'Yüksek'),
        ('Orta', 'Orta'),
        ('Dusuk', 'Düşük'),
    )
    
    CATEGORY_CHOICES = (
        ('Donanim', 'Donanım'),
        ('Yazilim', 'Yazılım'),
        ('Ag', 'Ağ'),
        ('Diger', 'Diğer'),
    )
    
    title = models.CharField(max_length=100, verbose_name="Başlık")
    description = models.TextField(verbose_name="Detay")
    
    # INDEX EKLENDİ: Gösterge panelleri için Bilet Statüsü ve Önceliği çok aranır
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Orta', verbose_name="Öncelik", db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Diger', verbose_name="Kategori", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Acik', verbose_name="Durum", db_index=True)
    
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İlgili Cihaz", db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tickets', null=True, blank=True, verbose_name="Oluşturan")
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='assigned_tickets', null=True, blank=True, verbose_name="Atanan Personel")
    is_escalated = models.BooleanField(default=False, verbose_name="Eskale Edildi Mi?", db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    sla_deadline = models.DateTimeField(null=True, blank=True, verbose_name="SLA Süresi", db_index=True)

    class Meta:
        verbose_name = "Destek Talebi"
        verbose_name_plural = "Destek Talepleri"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.pk and not self.sla_deadline:
            if self.priority == 'Kritik':
                self.sla_deadline = timezone.now() + timedelta(hours=4)
            elif self.priority == 'Yuksek':
                self.sla_deadline = timezone.now() + timedelta(hours=8)
            elif self.priority == 'Orta':
                self.sla_deadline = timezone.now() + timedelta(hours=24)
            else:
                self.sla_deadline = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)

    @property
    def is_sla_breached(self):
        if self.status not in ['Cozuldu', 'Kapatildi'] and self.sla_deadline:
            return timezone.now() > self.sla_deadline
        return False

    def __str__(self):
        return self.title

class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name="Talep")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    content = models.TextField(verbose_name="Mesaj")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Talep Yorumu"
        verbose_name_plural = "Talep Yorumları"

    def __str__(self):
        return self.ticket.title

class SystemLog(models.Model):
    ACTION_CHOICES = [
        ('CONFIG', 'Konfigürasyon'),
        ('SCAN', 'Ağ Taraması'),
        ('IPAM', 'IP İşlemi'),
        ('TICKET', 'Talep İşlemi'),
        ('SYSTEM', 'Sistem Olayı'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kullanıcı")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="İşlem Türü", db_index=True)
    details = models.TextField(verbose_name="Detay")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih", db_index=True)

    class Meta:
        verbose_name = "Sistem Logu"
        verbose_name_plural = "Sistem Logları"
        ordering = ['-created_at'] 

    def __str__(self):
        return self.action

class DeviceBackup(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='backups', verbose_name="Cihaz")
    config_text = models.TextField(verbose_name="Konfigürasyon")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih", db_index=True)
    backed_up_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İşlemi Yapan")

    class Meta:
        verbose_name = "Yedek"
        verbose_name_plural = "Yedekler"
        ordering = ['-created_at'] 

    def __str__(self):
        return self.device.name

class RemoteProbe(models.Model):
    """
    Dağıtık mimaride uzak şubelere (Örn: Ankara Veri Merkezi) kurulan,
    kendi bulunduğu ağı tarayıp merkez NetArchitect sunucusuna rapor 
    ileten ajan (Agent) yazılımlarının veritabanı modeli.
    """
    STATUS_CHOICES = [
        ('online', 'Çevrimiçi'),
        ('offline', 'Bağlantı Koptu'),
        ('unknown', 'Bilinmiyor')
    ]

    name = models.CharField(max_length=150, unique=True, verbose_name="Probe/Agent Adı")
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name="Lokasyon/Şube")
    ip_address = models.GenericIPAddressField(verbose_name="Probe IP Adresi")
    target_subnet = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tarama Hedef Subnet", help_text="Örn: 192.168.1.0/24")
    agent_version = models.CharField(max_length=50, default="1.0.0", verbose_name="Ajan Sürümü")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown', verbose_name="Durum")
    last_heartbeat = models.DateTimeField(auto_now_add=True, verbose_name="Son İletişim (Heartbeat)")

    class Meta:
        verbose_name = "Uzak Probe (Ajan)"
        verbose_name_plural = "Uzak Probelar (Ajanlar)"
        ordering = ['-last_heartbeat']

    def __str__(self):
        return f"{self.name} ({self.ip_address})"

    @property
    def is_offline(self):
        """Eğer 30 dakikadan uzun süredir Heartbeat (Yaşıyorum) mesajı atmadıysa Offline sayılır."""
        if not self.last_heartbeat:
            return True
        heartbeat_timeout = timezone.now() - timedelta(minutes=30)
        return self.last_heartbeat < heartbeat_timeout

    def save(self, *args, **kwargs):
        # Eğer offline olduysa durumunu otomatik güncelle
        if self.pk and self.is_offline and self.status == 'online':
            self.status = 'offline'
            SystemLog.objects.create(
                action='SYSTEM',
                details=f"🚨 Probe Bağlantısı Koptu: {self.name} ({self.ip_address}) 30 dakikadır yanıt vermiyor."
            )
        super().save(*args, **kwargs)

class ITAsset(models.Model):
    ASSET_TYPES = [
        ('laptop', 'Dizüstü Bilgisayar'),
        ('desktop', 'Masaüstü Bilgisayar'),
        ('monitor', 'Monitör'),
        ('printer', 'Yazıcı'),
        ('mobile', 'Mobil Cihaz'),
        ('peripherals', 'Çevre Birimi'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Donanım Adı")
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES, default='laptop', verbose_name="Tür", db_index=True)
    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Seri No", db_index=True)
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name="Model")
    assigned_to = models.CharField(max_length=100, blank=True, null=True, verbose_name="Zimmet")
    purchase_date = models.DateField(blank=True, null=True, verbose_name="Satın Alma")
    warranty_expiry = models.DateField(blank=True, null=True, verbose_name="Garanti Bitiş")
    
    STATUS_CHOICES = [
        ('active', 'Aktif'), 
        ('repair', 'Tamirde'), 
        ('retired', 'Hurda')
    ]
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES, verbose_name="Durum", db_index=True)

    class Meta:
        verbose_name = "Donanım"
        verbose_name_plural = "Donanımlar"
        ordering = ['-id']

    def __str__(self):
        return self.name

class License(models.Model):
    name = models.CharField(max_length=100, verbose_name="Yazılım Adı")
    license_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Lisans Anahtarı")
    total_slots = models.IntegerField(default=1, verbose_name="Toplam Kullanım")
    used_slots = models.IntegerField(default=0, verbose_name="Kullanılan")
    expiry_date = models.DateField(verbose_name="Bitiş Tarihi", db_index=True)
    
    vendor = models.CharField(max_length=100, verbose_name="Üretici")
    is_subscription = models.BooleanField(default=True, verbose_name="Abonelik")

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_left(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return 0

    class Meta:
        verbose_name = "Lisans"
        verbose_name_plural = "Lisanslar"
        ordering = ['expiry_date']

    def __str__(self):
        return self.name

class Port(models.Model):
    PORT_STATUS_CHOICES = (
        ('up', 'Up'),
        ('down', 'Down'),
        ('disabled', 'Disabled'),
    )

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='ports', verbose_name="Cihaz")
    port_number = models.IntegerField(verbose_name="Port No")
    name = models.CharField(max_length=50, verbose_name="Port Adı", default="FastEthernet0/X")
    status = models.CharField(max_length=20, choices=PORT_STATUS_CHOICES, default='down', verbose_name="Durum")
    
    connected_asset = models.ForeignKey(ITAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name='connected_port', verbose_name="Bağlı Cihaz")
    description = models.CharField(max_length=150, blank=True, null=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Port"
        verbose_name_plural = "Portlar"
        ordering = ['device', 'port_number']
        unique_together = ('device', 'port_number') 

    def __str__(self):
        return self.name

class KnowledgeBaseArticle(models.Model):
    CATEGORY_CHOICES = (
        ('network', 'Ağ'),
        ('hardware', 'Donanım'),
        ('software', 'Yazılım'),
        ('account', 'Hesap'),
        ('other', 'Diğer'),
    )

    title = models.CharField(max_length=200, verbose_name="Başlık", db_index=True)
    content = models.TextField(verbose_name="İçerik")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name="Kategori", db_index=True)
    
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yazar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")
    
    views_count = models.IntegerField(default=0, verbose_name="Görüntülenme")
    helpful_count = models.IntegerField(default=0, verbose_name="Faydalı")

    class Meta:
        verbose_name = "Makale"
        verbose_name_plural = "Makaleler"
        ordering = ['-helpful_count', '-views_count'] 

    def __str__(self):
        return self.title

class VendorContract(models.Model):
    CONTRACT_TYPES = (
        ('internet', 'İnternet'),
        ('cloud', 'Bulut'),
        ('maintenance', 'Bakım'),
        ('software', 'Yazılım'),
        ('other', 'Diğer'),
    )
    SLA_CHOICES = (
        ('24_7', '7/24'),
        ('8_5_nbd', '8x5 NBD'),
        ('standard', 'Standart'),
    )

    title = models.CharField(max_length=150, verbose_name="Başlık")
    vendor_name = models.CharField(max_length=100, verbose_name="Tedarikçi", db_index=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPES, default='internet', verbose_name="Tür")
    sla_level = models.CharField(max_length=20, choices=SLA_CHOICES, default='standard', verbose_name="SLA")
    
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(verbose_name="Bitiş Tarihi", db_index=True)
    
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Maliyet")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")

    @property
    def is_expired(self):
        if self.end_date:
            return self.end_date < timezone.now().date()
        return False

    @property
    def days_left(self):
        if self.end_date:
            return (self.end_date - timezone.now().date()).days
        return 0

    class Meta:
        verbose_name = "Sözleşme"
        verbose_name_plural = "Sözleşmeler"
        ordering = ['end_date'] 

    def __str__(self):
        return self.title

class ChangeRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Bekliyor'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi'),
        ('failed', 'Başarısız'),
    )
    title = models.CharField(max_length=150, verbose_name="Başlık")
    
    # YENİ EKLENEN: Toplu İşlem (Bulk Operation) Desteği
    target_devices = models.ManyToManyField(Device, related_name='change_requests', blank=True, verbose_name="Hedef Cihazlar")
    
    # ESKİ (Geriye Uyumluluk İçin Opsiyonel Bırakıldı)
    target_ip = models.CharField(max_length=50, blank=True, null=True, verbose_name="Hedef IP", db_index=True)
    vendor = models.CharField(max_length=50, blank=True, null=True, verbose_name="Üretici")
    
    config_payload = models.TextField(verbose_name="Konfigürasyon")
    
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='change_requests', verbose_name="Talep Eden")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Durum", db_index=True)
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_changes', verbose_name="Yönetici")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")
    execution_log = models.TextField(blank=True, null=True, verbose_name="İşlem Logu")

    class Meta:
        verbose_name = "Değişiklik"
        verbose_name_plural = "Değişiklikler"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ==========================================
# --- YENİ: AIOps Tahminleyici Bakım Modeli ---
# ==========================================
class DevicePerformanceLog(models.Model):
    """ Cihazların anlık performans verilerini tutan ve AI Tahminlemesi için kullanılan model """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='performance_logs')
    cpu_usage = models.FloatField(default=0.0, help_text="Yüzdelik CPU Kullanımı")
    ram_usage = models.FloatField(default=0.0, help_text="Yüzdelik RAM Kullanımı")
    disk_usage = models.FloatField(default=0.0, help_text="Yüzdelik Disk Kullanımı")
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Performans Logu'
        verbose_name_plural = 'Performans Logları'
        # AI algoritmaları zaman bazlı çalıştığı için zamana göre indeksleme çok önemli
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.device.name} - CPU: {self.cpu_usage}% - Tarih: {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"