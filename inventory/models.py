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


class NetworkScan(models.Model):
    """Ping, ARP ve raw socket sonuçlarını saklayan tarama geçmişi."""
    METHOD_CHOICES = (
        ('arp', 'ARP'),
        ('ping', 'Ping'),
        ('raw_socket', 'Raw Socket'),
        ('hybrid', 'Hybrid'),
    )

    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Taramayı Başlatan")
    network = models.CharField(max_length=50, verbose_name="Ağ Bloğu")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='hybrid', verbose_name="Yöntem")
    total_hosts = models.PositiveIntegerField(default=0, verbose_name="Toplam Host")
    active_hosts = models.PositiveIntegerField(default=0, verbose_name="Aktif Host")
    duration_ms = models.PositiveIntegerField(default=0, verbose_name="Süre (ms)")
    error = models.TextField(blank=True, verbose_name="Hata")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Ağ Taraması"
        verbose_name_plural = "Ağ Taramaları"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.network} - {self.created_at:%Y-%m-%d %H:%M}"


class NetworkScanHost(models.Model):
    scan = models.ForeignKey(NetworkScan, on_delete=models.CASCADE, related_name='hosts', verbose_name="Tarama")
    ip_address = models.GenericIPAddressField(verbose_name="IP")
    mac_address = models.CharField(max_length=17, blank=True, verbose_name="MAC")
    hostname = models.CharField(max_length=255, blank=True, verbose_name="Host Adı")
    vendor = models.CharField(max_length=120, blank=True, verbose_name="Üretici")
    detected_by = models.CharField(max_length=80, blank=True, verbose_name="Tespit Yöntemi")
    latency_ms = models.FloatField(null=True, blank=True, verbose_name="Gecikme (ms)")
    raw_socket_open = models.BooleanField(default=False, verbose_name="Raw Socket Yanıtı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Tarama Hostu"
        verbose_name_plural = "Tarama Hostları"
        ordering = ['ip_address']

    def __str__(self):
        return self.ip_address


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

class TicketCategory(models.Model):
    """Yönetilebilir talep kategorileri ve otomatik atama kuralları."""
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    icon = models.CharField(max_length=50, default="mdi:tag-outline", verbose_name="İkon")
    sla_hours = models.PositiveIntegerField(default=24, verbose_name="SLA (Saat)")
    auto_assign_group = models.ForeignKey(
        'auth.Group', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_categories', verbose_name="Otomatik Atama Grubu"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif", db_index=True)

    class Meta:
        verbose_name = "Talep Kategorisi"
        verbose_name_plural = "Talep Kategorileri"
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Kullanıcı profil bilgileri: avatar, biyografi, telefon."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Kullanıcı")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    bio = models.TextField(blank=True, verbose_name="Biyografi")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Avatar")
    department = models.CharField(max_length=100, blank=True, verbose_name="Departman")

    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"

    def __str__(self):
        return self.user.username

    @property
    def initials(self):
        if self.user.first_name:
            return self.user.first_name[0].upper()
        return self.user.username[0].upper()


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
    ticket_category = models.ForeignKey(
        TicketCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets', verbose_name="Kategori (Yönetilebilir)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Acik', verbose_name="Durum", db_index=True)
    
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İlgili Cihaz", db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tickets', null=True, blank=True, verbose_name="Oluşturan")
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='assigned_tickets', null=True, blank=True, verbose_name="Atanan Personel")
    is_escalated = models.BooleanField(default=False, verbose_name="Eskale Edildi Mi?", db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Kapanış Tarihi", db_index=True)
    sla_deadline = models.DateTimeField(null=True, blank=True, verbose_name="SLA Süresi", db_index=True)

    class Meta:
        verbose_name = "Destek Talebi"
        verbose_name_plural = "Destek Talepleri"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.pk and not self.sla_deadline:
            if self.ticket_category and self.ticket_category.sla_hours:
                self.sla_deadline = timezone.now() + timedelta(hours=self.ticket_category.sla_hours)
            elif self.priority == 'Kritik':
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
    is_internal = models.BooleanField(default=False, verbose_name="Dahili Not (Sadece Personel)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Talep Yorumu"
        verbose_name_plural = "Talep Yorumları"
        ordering = ['created_at']

    def __str__(self):
        return self.ticket.title


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments', verbose_name="Talep")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yükleyen")
    file = models.FileField(upload_to='ticket_attachments/%Y/%m/', verbose_name="Dosya")
    filename = models.CharField(max_length=255, verbose_name="Dosya Adı")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Yüklenme Tarihi")

    class Meta:
        verbose_name = "Talep Eki"
        verbose_name_plural = "Talep Ekleri"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)


class Notification(models.Model):
    TYPE_CHOICES = (
        ('info', 'Bilgi'),
        ('assignment', 'Atama'),
        ('comment', 'Yorum'),
        ('status', 'Durum'),
        ('closed', 'Kapanış'),
        ('sla_breach', 'SLA İhlali'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Kullanıcı")
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name="Talep")
    title = models.CharField(max_length=200, verbose_name="Başlık")
    message = models.TextField(verbose_name="Mesaj")
    link = models.CharField(max_length=500, blank=True, verbose_name="Bağlantı")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info', verbose_name="Tür")
    is_read = models.BooleanField(default=False, verbose_name="Okundu", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih", db_index=True)

    class Meta:
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class FieldVisit(models.Model):
    """Saha ekipleri için rota ve yakıt planlama kaydı."""
    STATUS_CHOICES = (
        ('planned', 'Planlandı'),
        ('in_progress', 'Yolda'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal'),
    )

    title = models.CharField(max_length=150, verbose_name="Başlık")
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='field_visits', verbose_name="Teknisyen")
    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='field_visits', verbose_name="Talep")
    customer_name = models.CharField(max_length=150, verbose_name="Müşteri/Lokasyon")
    address = models.CharField(max_length=255, blank=True, verbose_name="Adres")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Enlem")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Boylam")
    order_index = models.PositiveIntegerField(default=0, verbose_name="Rota Sırası")
    distance_km = models.FloatField(default=0.0, verbose_name="Mesafe (km)")
    vehicle_model = models.CharField(max_length=80, default="Standart Servis Aracı", verbose_name="Araç Modeli")
    fuel_l_per_100km = models.FloatField(default=7.5, verbose_name="Yakıt (L/100km)")
    ac_multiplier = models.FloatField(default=1.08, verbose_name="Klima Çarpanı")
    estimated_fuel_l = models.FloatField(default=0.0, verbose_name="Tahmini Yakıt (L)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', db_index=True, verbose_name="Durum")
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="Planlanan Zaman")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Saha Ziyareti"
        verbose_name_plural = "Saha Ziyaretleri"
        ordering = ['order_index', 'scheduled_at', 'id']

    def save(self, *args, **kwargs):
        self.estimated_fuel_l = round((self.distance_km * self.fuel_l_per_100km / 100.0) * self.ac_multiplier, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class SalesOpportunity(models.Model):
    """Drag & drop Kanban satış hunisi için fırsat modeli."""
    STAGE_CHOICES = (
        ('lead', 'Yeni Fırsat'),
        ('qualified', 'Nitelikli'),
        ('proposal', 'Teklif'),
        ('negotiation', 'Pazarlık'),
        ('won', 'Kazanıldı'),
        ('lost', 'Kaybedildi'),
    )

    title = models.CharField(max_length=150, verbose_name="Fırsat")
    customer_name = models.CharField(max_length=150, verbose_name="Müşteri")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_opportunities', verbose_name="Sorumlu")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='lead', db_index=True, verbose_name="Aşama")
    potential_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Potansiyel Gelir")
    probability = models.PositiveIntegerField(default=20, verbose_name="Olasılık (%)")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    position = models.PositiveIntegerField(default=0, verbose_name="Sıra")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Satış Fırsatı"
        verbose_name_plural = "Satış Fırsatları"
        ordering = ['stage', 'position', '-updated_at']

    @property
    def weighted_revenue(self):
        return round(float(self.potential_revenue) * self.probability / 100.0, 2)

    def __str__(self):
        return self.title


class DLPEvent(models.Model):
    """Basit DLP kayıtları: hassas veri sızıntısı risklerini denetim loguna taşır."""
    SEVERITY_CHOICES = (
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kullanıcı")
    source = models.CharField(max_length=80, verbose_name="Kaynak")
    rule = models.CharField(max_length=120, verbose_name="Kural")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium', db_index=True, verbose_name="Seviye")
    excerpt = models.TextField(blank=True, verbose_name="Örnek")
    blocked = models.BooleanField(default=False, verbose_name="Engellendi")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "DLP Olayı"
        verbose_name_plural = "DLP Olayları"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rule} ({self.severity})"

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
    kendi bulunduğu ağı tarayıp merkez OmniOps sunucusuna rapor 
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


class FactoryArea(models.Model):
    """Fabrika içindeki üretim hattı, depo, ofis veya kritik IT bölgesi."""
    CRITICALITY_CHOICES = (
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik'),
    )

    name = models.CharField(max_length=120, verbose_name="Alan/Hat Adı")
    code = models.CharField(max_length=40, unique=True, verbose_name="Kod")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    criticality = models.CharField(max_length=20, choices=CRITICALITY_CHOICES, default='medium', db_index=True, verbose_name="Kritiklik")
    manager_name = models.CharField(max_length=120, blank=True, verbose_name="Sorumlu")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")

    class Meta:
        verbose_name = "Fabrika Alanı"
        verbose_name_plural = "Fabrika Alanları"
        ordering = ['name']

    def __str__(self):
        return self.name


class ConsumableItem(models.Model):
    """Toner, etiket, barkod ribonu, disk, kablo ve kritik IT yedek parçaları."""
    CATEGORY_CHOICES = (
        ('toner', 'Toner/Kartuş'),
        ('label', 'Etiket/Ribon'),
        ('spare', 'Yedek Parça'),
        ('cable', 'Kablo/Adaptör'),
        ('backup_media', 'Yedekleme Medyası'),
        ('other', 'Diğer'),
    )

    name = models.CharField(max_length=150, verbose_name="Kalem Adı")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other', db_index=True, verbose_name="Kategori")
    sku = models.CharField(max_length=80, blank=True, verbose_name="Stok Kodu")
    compatible_with = models.CharField(max_length=200, blank=True, verbose_name="Uyumlu Cihaz/Model")
    location = models.CharField(max_length=120, blank=True, verbose_name="Depo/Lokasyon")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Mevcut Stok")
    minimum_quantity = models.PositiveIntegerField(default=1, verbose_name="Minimum Stok")
    unit = models.CharField(max_length=30, default='adet', verbose_name="Birim")
    vendor = models.CharField(max_length=120, blank=True, verbose_name="Tedarikçi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Sarf/Yedek Stok"
        verbose_name_plural = "Sarf/Yedek Stokları"
        ordering = ['category', 'name']

    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_quantity

    def __str__(self):
        return self.name


class MaintenanceTask(models.Model):
    """Periyodik bakım, yedek kontrolü, patch, printer ve üretim hattı IT checklist işleri."""
    TASK_TYPE_CHOICES = (
        ('backup', 'Yedek Kontrolü'),
        ('patch', 'Patch/Güncelleme'),
        ('printer', 'Yazıcı/Barkod'),
        ('network', 'Ağ Kontrolü'),
        ('server', 'Sunucu/Storage'),
        ('security', 'Güvenlik'),
        ('production_line', 'Üretim Hattı IT'),
        ('other', 'Diğer'),
    )
    STATUS_CHOICES = (
        ('planned', 'Planlandı'),
        ('in_progress', 'Devam Ediyor'),
        ('done', 'Tamamlandı'),
        ('blocked', 'Blokeli'),
    )

    title = models.CharField(max_length=180, verbose_name="İş Başlığı")
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, default='other', db_index=True, verbose_name="İş Tipi")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_tasks', verbose_name="Fabrika Alanı")
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_tasks', verbose_name="Cihaz")
    asset = models.ForeignKey(ITAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_tasks', verbose_name="Varlık")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_tasks', verbose_name="Sorumlu")
    frequency_days = models.PositiveIntegerField(default=30, verbose_name="Periyot (Gün)")
    last_completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Tamamlanma")
    next_due_at = models.DateTimeField(verbose_name="Sonraki Tarih", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', db_index=True, verbose_name="Durum")
    checklist = models.TextField(blank=True, verbose_name="Checklist")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Bakım/Checklist İşi"
        verbose_name_plural = "Bakım/Checklist İşleri"
        ordering = ['next_due_at', 'status']

    @property
    def is_overdue(self):
        return self.status != 'done' and self.next_due_at < timezone.now()

    def mark_done(self, completed_at=None):
        completed_at = completed_at or timezone.now()
        self.status = 'done'
        self.last_completed_at = completed_at
        self.next_due_at = completed_at + timedelta(days=self.frequency_days)
        self.save(update_fields=['status', 'last_completed_at', 'next_due_at', 'updated_at'])

    def __str__(self):
        return self.title


class EmployeeITProcess(models.Model):
    """Personel giriş, çıkış ve departman değişikliği için IT kontrol listesi."""
    PROCESS_CHOICES = (
        ('onboarding', 'İşe Giriş'),
        ('offboarding', 'İşten Çıkış'),
        ('transfer', 'Departman Değişikliği'),
    )
    STATUS_CHOICES = (
        ('open', 'Açık'),
        ('waiting', 'Beklemede'),
        ('done', 'Tamamlandı'),
        ('cancelled', 'İptal'),
    )

    employee_name = models.CharField(max_length=150, verbose_name="Personel")
    department = models.CharField(max_length=120, verbose_name="Departman")
    process_type = models.CharField(max_length=30, choices=PROCESS_CHOICES, db_index=True, verbose_name="Süreç")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_processes', verbose_name="Fabrika Alanı")
    requester = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_employee_processes', verbose_name="Talep Eden")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_employee_processes', verbose_name="Sorumlu IT")
    due_date = models.DateField(null=True, blank=True, verbose_name="Hedef Tarih")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True, verbose_name="Durum")
    ad_account_done = models.BooleanField(default=False, verbose_name="AD/Hesap")
    email_done = models.BooleanField(default=False, verbose_name="E-posta")
    erp_done = models.BooleanField(default=False, verbose_name="ERP/MES")
    vpn_done = models.BooleanField(default=False, verbose_name="VPN/Uzak Erişim")
    device_done = models.BooleanField(default=False, verbose_name="Cihaz/Zimmet")
    badge_done = models.BooleanField(default=False, verbose_name="Kart/Yetki")
    data_backup_done = models.BooleanField(default=False, verbose_name="Veri Yedek/Devir")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Personel IT Süreci"
        verbose_name_plural = "Personel IT Süreçleri"
        ordering = ['status', 'due_date', '-created_at']

    @property
    def completion_percent(self):
        checks = [
            self.ad_account_done, self.email_done, self.erp_done, self.vpn_done,
            self.device_done, self.badge_done, self.data_backup_done,
        ]
        return int((sum(1 for item in checks if item) / len(checks)) * 100)

    @property
    def is_overdue(self):
        return self.status not in ('done', 'cancelled') and self.due_date and self.due_date < timezone.now().date()

    def __str__(self):
        return f"{self.employee_name} - {self.get_process_type_display()}"


class ProcurementRequest(models.Model):
    """Donanım, yazılım ve hizmet satın alma talepleri."""
    CATEGORY_CHOICES = (
        ('hardware', 'Donanım'),
        ('software', 'Yazılım'),
        ('service', 'Hizmet'),
        ('consumable', 'Sarf Malzeme'),
    )
    STATUS_CHOICES = (
        ('pending', 'Onay Bekliyor'),
        ('approved', 'Onaylandı'),
        ('ordered', 'Sipariş Verildi'),
        ('received', 'Teslim Alındı'),
        ('rejected', 'Reddedildi'),
    )

    title = models.CharField(max_length=180, verbose_name="Talep Başlığı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='hardware', db_index=True, verbose_name="Kategori")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Adet")
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Tahmini Maliyet")
    vendor_name = models.CharField(max_length=120, blank=True, verbose_name="Tedarikçi")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='procurement_requests', verbose_name="Fabrika Alanı")
    requester = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='procurement_requests', verbose_name="Talep Eden")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_procurements', verbose_name="Onaylayan")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name="Durum")
    needed_by = models.DateField(null=True, blank=True, verbose_name="İhtiyaç Tarihi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Satın Alma Talebi"
        verbose_name_plural = "Satın Alma Talepleri"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class OnCallShift(models.Model):
    """IT nöbet / vardiya planı."""
    engineer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='oncall_shifts', verbose_name="Nöbetçi")
    start_at = models.DateTimeField(verbose_name="Başlangıç", db_index=True)
    end_at = models.DateTimeField(verbose_name="Bitiş", db_index=True)
    phone = models.CharField(max_length=30, blank=True, verbose_name="İletişim")
    is_primary = models.BooleanField(default=True, verbose_name="Birincil Nöbetçi")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")

    class Meta:
        verbose_name = "Nöbet Kaydı"
        verbose_name_plural = "Nöbet Kayıtları"
        ordering = ['-start_at']

    @property
    def is_active_now(self):
        now = timezone.now()
        return self.start_at <= now <= self.end_at

    def __str__(self):
        return f"{self.engineer.username} ({self.start_at:%d.%m.%Y})"


class BackupJobMonitor(models.Model):
    """Sunucu, veritabanı ve uygulama yedekleme işlerinin durumu."""
    SYSTEM_TYPE_CHOICES = (
        ('server', 'Sunucu'),
        ('database', 'Veritabanı'),
        ('application', 'Uygulama'),
        ('vm', 'Sanal Makine'),
        ('file', 'Dosya Paylaşımı'),
    )
    STATUS_CHOICES = (
        ('success', 'Başarılı'),
        ('failed', 'Başarısız'),
        ('warning', 'Uyarı'),
        ('missed', 'Kaçırıldı'),
        ('unknown', 'Bilinmiyor'),
    )

    name = models.CharField(max_length=150, verbose_name="Yedekleme Adı")
    system_type = models.CharField(max_length=20, choices=SYSTEM_TYPE_CHOICES, default='server', db_index=True, verbose_name="Sistem Tipi")
    target_host = models.CharField(max_length=120, blank=True, verbose_name="Hedef Sunucu")
    schedule_description = models.CharField(max_length=120, default='Günlük 02:00', verbose_name="Plan")
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Çalışma")
    last_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown', db_index=True, verbose_name="Son Durum")
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Sonraki Çalışma")
    retention_days = models.PositiveIntegerField(default=30, verbose_name="Saklama (Gün)")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='backup_jobs', verbose_name="Sorumlu")
    is_active = models.BooleanField(default=True, verbose_name="Aktif", db_index=True)
    notes = models.TextField(blank=True, verbose_name="Notlar")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Yedekleme İşi"
        verbose_name_plural = "Yedekleme İşleri"
        ordering = ['last_status', 'next_run_at', 'name']

    @property
    def is_unhealthy(self):
        return self.is_active and self.last_status in ('failed', 'missed', 'warning')

    def __str__(self):
        return self.name


class VendorSupportCase(models.Model):
    """Dış tedarikçi / üretici destek kayıtları."""
    PRIORITY_CHOICES = Ticket.PRIORITY_CHOICES
    STATUS_CHOICES = (
        ('open', 'Açık'),
        ('waiting_vendor', 'Tedarikçi Bekleniyor'),
        ('resolved', 'Çözüldü'),
        ('closed', 'Kapatıldı'),
    )

    title = models.CharField(max_length=180, verbose_name="Konu")
    vendor_name = models.CharField(max_length=120, verbose_name="Tedarikçi")
    vendor_contract = models.ForeignKey(VendorContract, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_cases', verbose_name="Sözleşme")
    case_number = models.CharField(max_length=80, blank=True, verbose_name="Tedarikçi Vaka No")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Orta', db_index=True, verbose_name="Öncelik")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True, verbose_name="Durum")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendor_support_cases', verbose_name="Sorumlu IT")
    opened_at = models.DateTimeField(default=timezone.now, verbose_name="Açılış")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Çözüm Tarihi")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Tedarikçi Destek Kaydı"
        verbose_name_plural = "Tedarikçi Destek Kayıtları"
        ordering = ['status', '-opened_at']

    def __str__(self):
        return self.title


class AssetHandover(models.Model):
    """Donanım zimmet teslim, iade ve transfer geçmişi."""
    ACTION_CHOICES = (
        ('assign', 'Zimmet Verme'),
        ('return', 'Zimmet İade'),
        ('transfer', 'Transfer'),
    )

    asset = models.ForeignKey(ITAsset, on_delete=models.CASCADE, related_name='handovers', verbose_name="Varlık")
    employee_name = models.CharField(max_length=150, verbose_name="Personel")
    department = models.CharField(max_length=120, blank=True, verbose_name="Departman")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_handovers', verbose_name="Fabrika Alanı")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='assign', db_index=True, verbose_name="İşlem")
    handover_date = models.DateField(default=timezone.now, verbose_name="Tarih")
    condition_notes = models.TextField(blank=True, verbose_name="Durum Notu")
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_handovers', verbose_name="İşlemi Yapan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Kayıt Tarihi")

    class Meta:
        verbose_name = "Zimmet Kaydı"
        verbose_name_plural = "Zimmet Kayıtları"
        ordering = ['-handover_date', '-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.action == 'assign':
            self.asset.assigned_to = self.employee_name
            self.asset.status = 'active'
        elif self.action == 'return':
            self.asset.assigned_to = ''
        elif self.action == 'transfer':
            self.asset.assigned_to = self.employee_name
        self.asset.save(update_fields=['assigned_to', 'status'])

    def __str__(self):
        return f"{self.asset.name} - {self.get_action_display()}"


class MajorIncident(models.Model):
    """Üretimi veya kritik IT servislerini etkileyen büyük olay yönetimi."""
    SEVERITY_CHOICES = (
        ('sev1', 'SEV1 - Üretim Durdu'),
        ('sev2', 'SEV2 - Kritik Etki'),
        ('sev3', 'SEV3 - Sınırlı Etki'),
        ('sev4', 'SEV4 - Düşük Etki'),
    )
    STATUS_CHOICES = (
        ('open', 'Açık'),
        ('war_room', 'Savaş Odası'),
        ('monitoring', 'İzlemede'),
        ('resolved', 'Çözüldü'),
        ('postmortem', 'Post-mortem'),
        ('closed', 'Kapatıldı'),
    )

    title = models.CharField(max_length=180, verbose_name="Olay Başlığı")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='sev3', db_index=True, verbose_name="Seviye")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True, verbose_name="Durum")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='major_incidents', verbose_name="Etkilenen Alan")
    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='major_incidents', verbose_name="İlgili Talep")
    incident_commander = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='commanded_incidents', verbose_name="Olay Lideri")
    started_at = models.DateTimeField(default=timezone.now, verbose_name="Başlangıç")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Çözüm")
    impact_summary = models.TextField(blank=True, verbose_name="Etki Özeti")
    root_cause = models.TextField(blank=True, verbose_name="Kök Neden")
    corrective_actions = models.TextField(blank=True, verbose_name="Kalıcı Aksiyonlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Major Incident"
        verbose_name_plural = "Major Incident Kayıtları"
        ordering = ['status', '-started_at']

    @property
    def duration_minutes(self):
        end = self.resolved_at or timezone.now()
        return int((end - self.started_at).total_seconds() // 60)

    def __str__(self):
        return self.title


class AccessRequest(models.Model):
    """VPN, dosya paylaşımı, ERP/MES ve uygulama erişim talepleri."""
    ACCESS_TYPE_CHOICES = (
        ('vpn', 'VPN'),
        ('file_share', 'Dosya Paylaşımı'),
        ('erp', 'ERP/MES'),
        ('email_group', 'E-posta Grubu'),
        ('application', 'Uygulama'),
        ('admin', 'Geçici Admin Yetkisi'),
        ('other', 'Diğer'),
    )
    STATUS_CHOICES = (
        ('pending', 'Onay Bekliyor'),
        ('approved', 'Onaylandı'),
        ('provisioned', 'Yetki Verildi'),
        ('rejected', 'Reddedildi'),
        ('revoked', 'Geri Alındı'),
    )

    requester = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='access_requests', verbose_name="Talep Eden")
    employee_name = models.CharField(max_length=150, verbose_name="Kullanıcı/Personel")
    department = models.CharField(max_length=120, blank=True, verbose_name="Departman")
    access_type = models.CharField(max_length=30, choices=ACCESS_TYPE_CHOICES, default='application', db_index=True, verbose_name="Erişim Tipi")
    target_system = models.CharField(max_length=150, verbose_name="Hedef Sistem/Paylaşım")
    justification = models.TextField(verbose_name="Gerekçe")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_access_requests', verbose_name="Onaylayan")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name="Durum")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Süre Sonu")
    provisioned_at = models.DateTimeField(null=True, blank=True, verbose_name="Yetki Verilme")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Erişim Talebi"
        verbose_name_plural = "Erişim Talepleri"
        ordering = ['status', '-created_at']

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.now())

    def __str__(self):
        return f"{self.employee_name} - {self.target_system}"


class PrinterFleetItem(models.Model):
    """Yazıcı, barkod yazıcı ve etiket cihazlarının sayaç/toner takibi."""
    DEVICE_KIND_CHOICES = (
        ('printer', 'Yazıcı'),
        ('barcode', 'Barkod Yazıcı'),
        ('label', 'Etiket Yazıcı'),
        ('scanner', 'Tarayıcı'),
        ('mfp', 'Çok Fonksiyonlu'),
    )
    STATUS_CHOICES = (
        ('online', 'Aktif'),
        ('warning', 'Uyarı'),
        ('maintenance', 'Bakımda'),
        ('offline', 'Çevrimdışı'),
        ('retired', 'Emekli'),
    )

    name = models.CharField(max_length=150, verbose_name="Cihaz Adı")
    device_kind = models.CharField(max_length=20, choices=DEVICE_KIND_CHOICES, default='printer', db_index=True, verbose_name="Tip")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    serial_number = models.CharField(max_length=100, blank=True, db_index=True, verbose_name="Seri No")
    model = models.CharField(max_length=120, blank=True, verbose_name="Model")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='printers', verbose_name="Alan")
    consumable = models.ForeignKey(ConsumableItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='printers', verbose_name="Toner/Ribon")
    page_counter = models.PositiveIntegerField(default=0, verbose_name="Sayaç")
    toner_level_percent = models.PositiveIntegerField(default=100, verbose_name="Toner/Ribon (%)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online', db_index=True, verbose_name="Durum")
    last_maintenance_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Bakım")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Yazıcı Filosu"
        verbose_name_plural = "Yazıcı Filosu"
        ordering = ['status', 'name']

    @property
    def needs_consumable(self):
        return self.toner_level_percent <= 15

    def __str__(self):
        return self.name


class Runbook(models.Model):
    """SOP/runbook şablonları: arıza, bakım, güvenlik ve üretim hattı prosedürleri."""
    CATEGORY_CHOICES = (
        ('incident', 'Olay Müdahalesi'),
        ('maintenance', 'Bakım'),
        ('security', 'Güvenlik'),
        ('backup', 'Yedekleme'),
        ('onboarding', 'Personel Süreci'),
        ('network', 'Ağ'),
        ('other', 'Diğer'),
    )

    title = models.CharField(max_length=180, verbose_name="Başlık")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other', db_index=True, verbose_name="Kategori")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='runbooks', verbose_name="Sahip")
    related_device_type = models.CharField(max_length=80, blank=True, verbose_name="İlgili Cihaz Tipi")
    steps = models.TextField(verbose_name="Adımlar")
    rollback_steps = models.TextField(blank=True, verbose_name="Geri Dönüş Adımları")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Aktif")
    version = models.CharField(max_length=20, default='1.0', verbose_name="Versiyon")
    last_reviewed_at = models.DateField(null=True, blank=True, verbose_name="Son Gözden Geçirme")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Runbook / SOP"
        verbose_name_plural = "Runbook / SOP Kayıtları"
        ordering = ['category', 'title']

    def __str__(self):
        return self.title


class RemoteAccessGrant(models.Model):
    """VPN, RDP, SSH ve zero-trust uzaktan erişim yetkilerinin merkezi takibi."""
    ACCESS_METHOD_CHOICES = (
        ('vpn', 'VPN'),
        ('rdp', 'RDP'),
        ('ssh', 'SSH'),
        ('ztna', 'Zero Trust'),
        ('web_portal', 'Web Portal'),
    )
    STATUS_CHOICES = (
        ('requested', 'Talep Edildi'),
        ('approved', 'Onaylandı'),
        ('active', 'Aktif'),
        ('suspended', 'Askıya Alındı'),
        ('expired', 'Süresi Doldu'),
        ('revoked', 'İptal Edildi'),
    )

    employee_name = models.CharField(max_length=150, verbose_name="Kullanıcı/Personel")
    department = models.CharField(max_length=120, blank=True, verbose_name="Departman")
    access_method = models.CharField(max_length=20, choices=ACCESS_METHOD_CHOICES, default='vpn', db_index=True, verbose_name="Erişim Yöntemi")
    target_resource = models.CharField(max_length=180, verbose_name="Hedef Kaynak")
    gateway = models.CharField(max_length=180, blank=True, verbose_name="VPN Gateway / Portal")
    allowed_source = models.CharField(max_length=180, blank=True, verbose_name="İzinli Kaynak IP")
    mfa_required = models.BooleanField(default=True, verbose_name="MFA Zorunlu")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested', db_index=True, verbose_name="Durum")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_remote_access', verbose_name="Onaylayan")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Süre Sonu")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Uzaktan Erişim Yetkisi"
        verbose_name_plural = "Uzaktan Erişim Yetkileri"
        ordering = ['status', 'expires_at', '-created_at']

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.now())

    def __str__(self):
        return f"{self.employee_name} - {self.get_access_method_display()}"


class DepartmentChannel(models.Model):
    """Departmanlar arası hızlı iletişim kanalı."""
    name = models.CharField(max_length=120, verbose_name="Kanal Adı")
    department = models.CharField(max_length=120, blank=True, verbose_name="Departman")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")

    class Meta:
        verbose_name = "Departman Chat Kanalı"
        verbose_name_plural = "Departman Chat Kanalları"
        ordering = ['department', 'name']

    def __str__(self):
        return self.name


class DepartmentMessage(models.Model):
    channel = models.ForeignKey(DepartmentChannel, on_delete=models.CASCADE, related_name='messages', verbose_name="Kanal")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='department_messages', verbose_name="Yazan")
    message = models.TextField(verbose_name="Mesaj")
    is_announcement = models.BooleanField(default=False, verbose_name="Duyuru")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Departman Mesajı"
        verbose_name_plural = "Departman Mesajları"
        ordering = ['-created_at']

    def __str__(self):
        return self.message[:80]


class CameraDevice(models.Model):
    """Kamera/NVR/DVR varlıkları ve erişim bilgileri."""
    DEVICE_TYPE_CHOICES = (
        ('ip_camera', 'IP Kamera'),
        ('nvr', 'NVR'),
        ('dvr', 'DVR'),
        ('vms', 'VMS Sunucusu'),
    )
    STATUS_CHOICES = (
        ('online', 'Aktif'),
        ('warning', 'Uyarı'),
        ('offline', 'Çevrimdışı'),
        ('maintenance', 'Bakımda'),
    )

    name = models.CharField(max_length=150, verbose_name="Kamera/NVR Adı")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES, default='ip_camera', db_index=True, verbose_name="Tip")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    stream_url = models.CharField(max_length=500, blank=True, verbose_name="Canlı İzleme URL")
    location = models.CharField(max_length=150, blank=True, verbose_name="Lokasyon")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='cameras', verbose_name="Fabrika Alanı")
    recording_days = models.PositiveIntegerField(default=15, verbose_name="Kayıt Saklama (Gün)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online', db_index=True, verbose_name="Durum")
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Kontrol")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Kamera Sistemi"
        verbose_name_plural = "Kamera Sistemleri"
        ordering = ['status', 'location', 'name']

    def __str__(self):
        return self.name


class BusinessApplication(models.Model):
    """Odoo, ERP, MES, muhasebe, HR ve diğer iş uygulamaları portal kaydı."""
    APP_TYPE_CHOICES = (
        ('erp', 'ERP'),
        ('mes', 'MES'),
        ('crm', 'CRM'),
        ('hr', 'İK'),
        ('accounting', 'Muhasebe'),
        ('document', 'Doküman'),
        ('reporting', 'Raporlama'),
        ('other', 'Diğer'),
    )
    STATUS_CHOICES = (
        ('online', 'Aktif'),
        ('degraded', 'Kısmi Sorun'),
        ('offline', 'Çevrimdışı'),
        ('maintenance', 'Bakımda'),
    )

    name = models.CharField(max_length=150, verbose_name="Uygulama Adı")
    app_type = models.CharField(max_length=20, choices=APP_TYPE_CHOICES, default='other', db_index=True, verbose_name="Tip")
    url = models.URLField(max_length=500, blank=True, verbose_name="URL")
    owner_department = models.CharField(max_length=120, blank=True, verbose_name="Sahip Departman")
    technical_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='business_apps', verbose_name="Teknik Sorumlu")
    sso_enabled = models.BooleanField(default=False, verbose_name="SSO Aktif")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online', db_index=True, verbose_name="Durum")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "İş Uygulaması"
        verbose_name_plural = "İş Uygulamaları"
        ordering = ['app_type', 'name']

    def __str__(self):
        return self.name


class ReportTemplate(models.Model):
    """Yönetici çıktıları için rapor/çıktı şablonları."""
    REPORT_TYPE_CHOICES = (
        ('inventory', 'Envanter'),
        ('ticket', 'Ticket/SLA'),
        ('security', 'Güvenlik'),
        ('factory', 'Fabrika Operasyon'),
        ('asset', 'Zimmet'),
        ('backup', 'Yedekleme'),
        ('custom', 'Özel'),
    )

    title = models.CharField(max_length=180, verbose_name="Rapor Adı")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='custom', db_index=True, verbose_name="Rapor Tipi")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    query_notes = models.TextField(blank=True, verbose_name="Veri Kaynağı / Filtre Notu")
    output_format = models.CharField(max_length=20, default='pdf,csv', verbose_name="Çıktı Formatları")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Aktif")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='report_templates', verbose_name="Sahip")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Rapor Şablonu"
        verbose_name_plural = "Rapor Şablonları"
        ordering = ['report_type', 'title']

    def __str__(self):
        return self.title


class ChangeCalendarEvent(models.Model):
    """Üretim etkisi olan bakım, değişiklik ve planlı kesinti takvimi."""
    EVENT_TYPE_CHOICES = (
        ('maintenance', 'Bakım'),
        ('change', 'Değişiklik'),
        ('outage', 'Planlı Kesinti'),
        ('release', 'Sürüm Geçişi'),
        ('audit', 'Denetim'),
    )
    RISK_CHOICES = (
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik'),
    )
    STATUS_CHOICES = (
        ('planned', 'Planlandı'),
        ('approved', 'Onaylandı'),
        ('in_progress', 'Devam Ediyor'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal'),
    )

    title = models.CharField(max_length=180, verbose_name="Başlık")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='maintenance', db_index=True, verbose_name="Tip")
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default='medium', db_index=True, verbose_name="Risk")
    factory_area = models.ForeignKey(FactoryArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='calendar_events', verbose_name="Etkilenen Alan")
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='calendar_events', verbose_name="CAB Kaydı")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='change_calendar_events', verbose_name="Sorumlu")
    start_at = models.DateTimeField(verbose_name="Başlangıç", db_index=True)
    end_at = models.DateTimeField(verbose_name="Bitiş", db_index=True)
    expected_impact = models.TextField(blank=True, verbose_name="Beklenen Etki")
    rollback_plan = models.TextField(blank=True, verbose_name="Geri Dönüş Planı")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', db_index=True, verbose_name="Durum")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Değişiklik/Bakım Takvimi"
        verbose_name_plural = "Değişiklik/Bakım Takvimi"
        ordering = ['start_at', 'risk_level']

    @property
    def is_active_now(self):
        now = timezone.now()
        return self.start_at <= now <= self.end_at

    def __str__(self):
        return self.title


class ServiceDependency(models.Model):
    """CMDB bağımlılık ilişkisi: uygulama, cihaz, servis ve departman etkisi."""
    DEPENDENCY_TYPE_CHOICES = (
        ('runs_on', 'Üzerinde Çalışır'),
        ('connects_to', 'Bağlanır'),
        ('depends_on', 'Bağımlı'),
        ('backs_up_to', 'Yedeklenir'),
        ('monitors', 'İzler'),
    )
    CRITICALITY_CHOICES = FactoryArea.CRITICALITY_CHOICES

    name = models.CharField(max_length=180, verbose_name="İlişki Adı")
    business_application = models.ForeignKey(BusinessApplication, on_delete=models.CASCADE, related_name='dependencies', verbose_name="Uygulama")
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_dependencies', verbose_name="Cihaz")
    dependency_type = models.CharField(max_length=20, choices=DEPENDENCY_TYPE_CHOICES, default='depends_on', db_index=True, verbose_name="Bağımlılık Tipi")
    criticality = models.CharField(max_length=20, choices=CRITICALITY_CHOICES, default='medium', db_index=True, verbose_name="Kritiklik")
    impact_description = models.TextField(blank=True, verbose_name="Etki Açıklaması")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")

    class Meta:
        verbose_name = "CMDB Bağımlılığı"
        verbose_name_plural = "CMDB Bağımlılıkları"
        ordering = ['criticality', 'business_application__name']

    def __str__(self):
        return self.name


class IntegrationHealthCheck(models.Model):
    """Odoo, ERP, kamera VMS, SMTP, LDAP, yedekleme ve API entegrasyon sağlık durumu."""
    INTEGRATION_TYPE_CHOICES = (
        ('odoo', 'Odoo'),
        ('erp', 'ERP'),
        ('mes', 'MES'),
        ('ldap', 'LDAP/AD'),
        ('smtp', 'SMTP'),
        ('camera_vms', 'Kamera VMS'),
        ('backup', 'Yedekleme'),
        ('api', 'API'),
        ('other', 'Diğer'),
    )
    STATUS_CHOICES = (
        ('healthy', 'Sağlıklı'),
        ('degraded', 'Yavaş/Sorunlu'),
        ('down', 'Çalışmıyor'),
        ('unknown', 'Bilinmiyor'),
    )

    name = models.CharField(max_length=150, verbose_name="Entegrasyon")
    integration_type = models.CharField(max_length=20, choices=INTEGRATION_TYPE_CHOICES, default='api', db_index=True, verbose_name="Tip")
    endpoint_url = models.CharField(max_length=500, blank=True, verbose_name="Endpoint/URL")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='integration_checks', verbose_name="Sorumlu")
    last_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown', db_index=True, verbose_name="Son Durum")
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Kontrol")
    response_time_ms = models.PositiveIntegerField(default=0, verbose_name="Yanıt Süresi (ms)")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Entegrasyon Sağlık Kontrolü"
        verbose_name_plural = "Entegrasyon Sağlık Kontrolleri"
        ordering = ['last_status', 'name']

    @property
    def is_unhealthy(self):
        return self.last_status in ('degraded', 'down')

    def __str__(self):
        return self.name


class ComplianceControl(models.Model):
    """ISO 27001/KVKK/internal audit gibi periyodik uyum kontrolleri."""
    FRAMEWORK_CHOICES = (
        ('iso27001', 'ISO 27001'),
        ('kvkk', 'KVKK'),
        ('internal', 'İç Denetim'),
        ('backup', 'Yedekleme Politikası'),
        ('access', 'Erişim Denetimi'),
        ('other', 'Diğer'),
    )
    STATUS_CHOICES = (
        ('compliant', 'Uygun'),
        ('gap', 'Açık Var'),
        ('in_progress', 'Devam Ediyor'),
        ('not_checked', 'Kontrol Edilmedi'),
    )

    title = models.CharField(max_length=180, verbose_name="Kontrol")
    framework = models.CharField(max_length=20, choices=FRAMEWORK_CHOICES, default='internal', db_index=True, verbose_name="Çerçeve")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='compliance_controls', verbose_name="Sorumlu")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_checked', db_index=True, verbose_name="Durum")
    evidence = models.TextField(blank=True, verbose_name="Kanıt / Bulgu")
    remediation_plan = models.TextField(blank=True, verbose_name="İyileştirme Planı")
    due_date = models.DateField(null=True, blank=True, verbose_name="Hedef Tarih")
    last_checked_at = models.DateField(null=True, blank=True, verbose_name="Son Kontrol")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Uyum Kontrolü"
        verbose_name_plural = "Uyum Kontrolleri"
        ordering = ['status', 'due_date', 'framework']

    @property
    def is_overdue(self):
        return self.status != 'compliant' and self.due_date and self.due_date < timezone.now().date()

    def __str__(self):
        return self.title


class DocumentOutputJob(models.Model):
    """Yönetici raporu, zimmet formu, bakım çıktısı gibi doküman/çıktı işleri."""
    JOB_TYPE_CHOICES = (
        ('report', 'Rapor'),
        ('handover', 'Zimmet Formu'),
        ('maintenance', 'Bakım Formu'),
        ('incident', 'Olay Raporu'),
        ('audit', 'Denetim Kanıtı'),
        ('custom', 'Özel'),
    )
    STATUS_CHOICES = (
        ('queued', 'Kuyrukta'),
        ('processing', 'Hazırlanıyor'),
        ('ready', 'Hazır'),
        ('delivered', 'Teslim Edildi'),
        ('failed', 'Hata'),
    )

    title = models.CharField(max_length=180, verbose_name="İş Başlığı")
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='report', db_index=True, verbose_name="Tip")
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='document_jobs', verbose_name="Talep Eden")
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='document_jobs', verbose_name="Rapor Şablonu")
    output_format = models.CharField(max_length=20, default='pdf', verbose_name="Format")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued', db_index=True, verbose_name="Durum")
    file = models.FileField(upload_to='document_outputs/%Y/%m/', null=True, blank=True, verbose_name="Dosya")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    class Meta:
        verbose_name = "Doküman/Çıktı İşi"
        verbose_name_plural = "Doküman/Çıktı İşleri"
        ordering = ['status', '-created_at']

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