import os
from celery import Celery
from celery.schedules import crontab

# Celery'ye varsayılan Django ayarlarını gösteriyoruz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat zamanlanmış görevleri (Periyodik Görevler)
app.conf.beat_schedule = {
    # 1. Mevcut Ağ Taraması (Her gece 03:00)
    'otomatik-ag-taramasi': {
        'task': 'inventory.tasks.otomatik_ag_taramasi',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # 2. AIOps Tahminleyici Bakım (Her sabah 05:00)
    'ai-tahminleyici-bakim': {
        'task': 'inventory.tasks.run_predictive_maintenance',
        'schedule': crontab(hour=5, minute=0),
    },
    
    # 3. Veri Arşivleme ve Temizleme (Data Retention - Her Ayın 1'i Gece 01:00)
    'veri-arsivleme-ve-temizleme': {
        'task': 'inventory.tasks.data_retention_policy_task',
        'schedule': crontab(day_of_month='1', hour=1, minute=0),
    },
    
    # 4. Denetim Raporu (Her Pazartesi Sabah 08:00'de Müdürlere PDF At)
    'haftalik-denetim-raporu': {
        'task': 'inventory.tasks.generate_and_send_audit_report',
        'schedule': crontab(day_of_week='1', hour=8, minute=0),
    },
    
    # 5. Kendi Veritabanı Yedeğini S3'e Atma (Her gece 04:00)
    'postgres-backup-db': {
        'task': 'inventory.tasks.postgres_dump_backup_task',
        'schedule': crontab(hour=4, minute=0),
    },
}