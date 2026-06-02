"""
Django settings for core project.
"""

from pathlib import Path
from datetime import timedelta # Token süresi hesaplamak için
from celery.schedules import crontab # Zamanlanmış görevler için
import os
import dj_database_url
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# SECURITY: load sensitive settings from environment in production
# NOTE: Keep the fallback values only for local development/testing.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-for-dev-only-please-set-env')

# DEBUG should be False in production; enable via DJANGO_DEBUG env var if needed
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'social_django',
    'inventory',
    'rest_framework', 
    'django_filters', # API Filtreleme Motoru
    'drf_spectacular', # Swagger API Dokümantasyonu
    'guardian', # YENİ: Nesne Bazlı Yetkilendirme (OLP)
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', # YENİ: Dil değiştirme altyapısı
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'postgres://netarchitect:netarchitect@db:5432/netarchitect'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==========================================
# --- YENİ: I18N (ÇOKLU DİL) AYARLARI ---
# ==========================================
LANGUAGE_CODE = 'tr'

TIME_ZONE = 'Europe/Istanbul'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Desteklenen diller
LANGUAGES = [
    ('tr', _('Türkçe')),
    ('en', _('English')),
]

# Çeviri dosyalarının duracağı klasör
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# --- SSO / OAuth2 / OpenID Connect / Azure AD Ayarları ---
SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/login/'
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'email']

# Azure AD / Okta / Keycloak için placeholder ayarlar
SOCIAL_AUTH_AZUREAD_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_AZUREAD_OAUTH2_KEY', '')
SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET', '')
SOCIAL_AUTH_AZUREAD_OAUTH2_TENANT_ID = os.environ.get('SOCIAL_AUTH_AZUREAD_OAUTH2_TENANT_ID', '')

SOCIAL_AUTH_OIDC_ENABLED = True
SOCIAL_AUTH_OIDC_KEY = os.environ.get('SOCIAL_AUTH_OIDC_KEY', '')
SOCIAL_AUTH_OIDC_SECRET = os.environ.get('SOCIAL_AUTH_OIDC_SECRET', '')
SOCIAL_AUTH_OIDC_ENDPOINT = os.environ.get('SOCIAL_AUTH_OIDC_ENDPOINT', '')

POSTGRES_BACKUP_DIR = os.environ.get('POSTGRES_BACKUP_DIR', os.path.join(BASE_DIR, 'db_backups'))
POSTGRES_BACKUP_FORMAT = os.environ.get('POSTGRES_BACKUP_FORMAT', 'custom')
PG_DUMP_PATH = os.environ.get('PG_DUMP_PATH', 'pg_dump')
POSTGRES_BACKUP_FILE_PREFIX = os.environ.get('POSTGRES_BACKUP_FILE_PREFIX', 'netarchitect_backup')

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_S3_BACKUP_BUCKET = os.environ.get('AWS_S3_BACKUP_BUCKET', '')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', '')

REMOTE_PROBE_SHARED_SECRET = os.environ.get('REMOTE_PROBE_SHARED_SECRET', 'netarchitect_probe_secret')

# ==========================================

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- GİRİŞ / ÇIKIŞ YÖNLENDİRMELERİ ---
LOGIN_REDIRECT_URL = '/'  # Giriş başarılıysa ana sayfaya git
LOGIN_URL = 'login'       # Giriş yapmamış biri zorlanırsa buraya at

# --- DJANGO REST FRAMEWORK AYARLARI ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',      
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10, 
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --- JWT (JSON Web Token) AYARLARI ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60), 
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),    
}

# --- SWAGGER / OPENAPI AYARLARI ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'NetArchitect API',
    'DESCRIPTION': 'Ağ Cihazları, IPAM, Otomatik Konfigürasyon ve Bilet Yönetim Sistemi',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# ==========================================
# --- CELERY & REDİS AYARLARI ---
# ==========================================
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Istanbul'

# ==========================================
# --- CELERY BEAT (ZAMANLANMIŞ GÖREVLER) ---
# ==========================================
CELERY_BEAT_SCHEDULE = {
    'otomatik-ag-taramasi-gece': {
        'task': 'inventory.tasks.otomatik_ag_taramasi',
        'schedule': crontab(hour=3, minute=0),
    },
    'sla-ve-lisans-uyarilari': {
        'task': 'inventory.tasks.otomatik_sla_ve_lisans_kontrolu',
        'schedule': crontab(hour=8, minute=0),
    },
    'zabbix-threshold-monitor-5dk': {
        'task': 'inventory.tasks.zabbix_threshold_monitor',
        'schedule': crontab(minute='*/5'),
    },
    'otomatik-gece-yedekleme': {
        'task': 'inventory.tasks.otomatik_gece_yedekleme',
        'schedule': crontab(hour=4, minute=0),
    },
    'ai-tahminleyici-bakim': {
        'task': 'inventory.tasks.run_predictive_maintenance',
        'schedule': crontab(hour=5, minute=0),
    },
    # VERİ ARŞİVLEME VE TEMİZLEME (DATA RETENTION POLICY)
    'veri-arsivleme-ve-temizleme': {
        'task': 'inventory.tasks.data_retention_policy_task',
        'schedule': crontab(day_of_month=1, hour=1, minute=0), # Her ayın 1'inde gece 1'de çalışır
    },
    'postgres-backup-db': {
        'task': 'inventory.tasks.postgres_dump_backup_task',
        'schedule': crontab(hour=4, minute=0),
    },
    'distributed-probe-polling': {
        'task': 'inventory.tasks.distributed_probe_polling',
        'schedule': crontab(minute='*/15'),
    },
    # YENİ EKLENDİ: DENETİM RAPORU (Her Pazartesi Sabah 08:00)
    'haftalik-denetim-raporu': {
        'task': 'inventory.tasks.generate_and_send_audit_report',
        'schedule': crontab(day_of_week='1', hour=8, minute=0), 
    },
}

# ==========================================
# --- NETARCHITECT GÜVENLİK VE WEBHOOK AYARLARI ---
# ==========================================
WAZUH_API_KEY = os.environ.get('WAZUH_API_KEY', '')
WEBHOOK_ALLOWED_IPS = [ip.strip() for ip in os.environ.get('WEBHOOK_ALLOWED_IPS', '127.0.0.1,::1').split(',') if ip.strip()]


# ==========================================
# --- GUARDIAN VE SSO YETKİLENDİRME MOTORLARI ---
# ==========================================
# Temel motorlar (Normal şifreli giriş ve Guardian) her zaman aktif olmalı
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend', # Django'nun varsayılan motoru (Şifreli giriş)
    'guardian.backends.ObjectPermissionBackend', # Guardian OLP motoru
]

# SADECE .env DOSYASINDA ANAHTARLAR VARSA SSO MOTORLARINI AKTİF ET!
# Bu sayede anahtarlar boşken uygulamanın (HTTP 500) çökmesini kalıcı olarak önleriz.
if os.environ.get('SOCIAL_AUTH_AZUREAD_OAUTH2_KEY'):
    AUTHENTICATION_BACKENDS.insert(0, 'social_core.backends.azuread.AzureADOAuth2')

if os.environ.get('SOCIAL_AUTH_OIDC_KEY'):
    AUTHENTICATION_BACKENDS.insert(0, 'social_core.backends.open_id_connect.OpenIdConnectAuth')

if os.environ.get('SAML_METADATA_URL'):
    AUTHENTICATION_BACKENDS.insert(0, 'social_core.backends.saml.SAMLAuth')

# ==========================================
# --- SSO / OAUTH2 / OIDC / SAML2 AYARLARI ---
# ==========================================

# OIDC (OpenID Connect) Genel Ayarları
SOCIAL_AUTH_OIDC_ENDPOINT = os.environ.get('SOCIAL_AUTH_OIDC_ENDPOINT', 'https://accounts.google.com/.well-known/openid-configuration')
SOCIAL_AUTH_OIDC_KEY = os.environ.get('SOCIAL_AUTH_OIDC_KEY', 'oidc-client-id')
SOCIAL_AUTH_OIDC_SECRET = os.environ.get('SOCIAL_AUTH_OIDC_SECRET', 'oidc-client-secret')

# Azure AD / Azure B2C Ayarları
SOCIAL_AUTH_AZUREAD_OAUTH2_TENANT_ID = os.environ.get('SOCIAL_AUTH_AZUREAD_OAUTH2_TENANT_ID', '')
SOCIAL_AUTH_AZUREAD_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_AZUREAD_OAUTH2_KEY', '')
SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET', '')

# Okta Ayarları (OIDC üzerinden)
SOCIAL_AUTH_OKTA_OPENID_ENDPOINT = os.environ.get('SOCIAL_AUTH_OKTA_OPENID_ENDPOINT', '')
SOCIAL_AUTH_OKTA_OPENID_KEY = os.environ.get('SOCIAL_AUTH_OKTA_OPENID_KEY', '')
SOCIAL_AUTH_OKTA_OPENID_SECRET = os.environ.get('SOCIAL_AUTH_OKTA_OPENID_SECRET', '')

# SAML 2.0 Ayarları
SOCIAL_AUTH_SAML_ORG_INFO = {
    'en-US': {
        'name': 'NetArchitect',
        'displayname': 'NetArchitect - Network Management System',
        'url': os.environ.get('SAML_ORG_URL', 'https://netarchitect.example.com/'),
    },
}

SOCIAL_AUTH_SAML_TECHNICAL_CONTACT = {
    'givenName': 'IT Support',
    'emailAddress': os.environ.get('SAML_TECH_CONTACT_EMAIL', 'support@netarchitect.example.com'),
}

SOCIAL_AUTH_SAML_SUPPORT_CONTACT = {
    'givenName': 'IT Support',
    'emailAddress': os.environ.get('SAML_SUPPORT_CONTACT_EMAIL', 'support@netarchitect.example.com'),
}

# SAML Attribute Mapping: SAML'deki attributes'ları Django user fields'ine eşle
SOCIAL_AUTH_SAML_ATTRIBUTE_MAPPING = {
    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress': ('email',),
    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname': ('first_name',),
    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname': ('last_name',),
    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn': ('username',),
    'groups': ('groups',),  # Grup bilgisi - Just-in-Time Provisioning için
}

# SAML Metadata dosyasının URL'si (IdP'den alınır)
SAML_METADATA_URL = os.environ.get('SAML_METADATA_URL', '')
SAML_ENTITY_ID = os.environ.get('SAML_ENTITY_ID', 'https://netarchitect.example.com/saml2/metadata/')
SAML_ASSERTION_CONSUMER_SERVICE_URL = os.environ.get('SAML_ACS_URL', 'https://netarchitect.example.com/accounts/complete/saml/')

# Social Auth Just-in-Time Provisioning Pipeline
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.auth.auth_allowed',
    'social_core.pipeline.auth.social_uid_from_whomami',
    'social_core.pipeline.auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'inventory.sso_pipeline.update_user_role_from_sso',  # YENİ: Rol/Grup Eşleştirmesi
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# SSO Yönlendirmeleri
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/kullanici-paneli/'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/login/'
SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/login/'

# SSO ile giriş yapan kullanıcıları admin olarak işle (opsiyonel)
SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True

# Kullanıcı ayrıntılarını otomatik olarak güncelle
SOCIAL_AUTH_POSTGRES_JSONFIELD = True

# ==========================================
# --- SAML2 GÜVENLİK AYARLARI ---
# ==========================================
# SAML2 sertifika ve anahtar dosyaları (üretim ortamında gerekli)
# Format: /path/to/sp.crt, /path/to/sp.key
SOCIAL_AUTH_SAML_SP_CERTIFICATE_FILE = os.environ.get('SAML_SP_CERTIFICATE_FILE', None)
SOCIAL_AUTH_SAML_SP_PRIVATE_KEY_FILE = os.environ.get('SAML_SP_PRIVATE_KEY_FILE', None)

# SAML2 imzalama ve şifreleme ayarları
SOCIAL_AUTH_SAML_SECURITY_CONFIG = {
    'nameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
    'signMetadata': True,  # Metadata'yı imzala
    'wantAssertionsSigned': True,  # Assertion imzalaması iste
    'wantAssertionsEncrypted': False,  # Assertion şifrelemesi iste (mı?)
    'wantNameIDEncrypted': False,  # NameID şifrelemesi iste
}

# ==========================================
# --- OKTA / OKTA WORKFORCE İDENTİTY MANAGEMENT
# ==========================================
# Okta SAML ayarları (alternatif: OIDC)
SOCIAL_AUTH_OKTA_SAML_METADATA_URL = os.environ.get('SOCIAL_AUTH_OKTA_SAML_METADATA_URL', '')

# ==========================================
# --- OPENID CONNECT (OIDC) GENIŞLETME AYARLARI
# ==========================================
# OIDC kapsamı (scope) - hangi bilgileri talep edelim
SOCIAL_AUTH_OIDC_SCOPE = ['openid', 'profile', 'email', 'groups']

# OIDC claim mapping - IdP'den gelen claim'leri user field'lerine eşle
SOCIAL_AUTH_OIDC_ID_TOKEN_DECRYPTION_ALGORITHM = 'RS256'

# Google OAuth2 (Opsiyonel)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', '')

# GitHub OAuth2 (Opsiyonel)
SOCIAL_AUTH_GITHUB_KEY = os.environ.get('SOCIAL_AUTH_GITHUB_KEY', '')
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get('SOCIAL_AUTH_GITHUB_SECRET', '')

# ==========================================
# --- SSO EXTENDED SECURITY
# ==========================================
# Sosyal auth ile birden fazla bağlantıya izin ver
SOCIAL_AUTH_ALLOW_REDIRECT_AFTER_DISCONNECT = True

# SAML sertifikası doğrulaması zorunlu
SOCIAL_AUTH_SAML_STRICT_METADATA_VALIDATION = os.environ.get('SOCIAL_AUTH_SAML_STRICT_VALIDATION', 'True').lower() == 'true'

# Kullanıcı kaydında email doğrulaması gerekliliği
SOCIAL_AUTH_EMAIL_VALIDATION_FUNCTION = 'social_core.utils.silent_email_validator'
SOCIAL_AUTH_EMAIL_REQUIRED = True

# SSO ile kayıtlı olsa da yerel şifre değişikliğine izin ver
SOCIAL_AUTH_DEFAULT_USERNAME_FUNCTION = 'social_core.utils.slugify'