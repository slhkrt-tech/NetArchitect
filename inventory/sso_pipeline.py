"""
SSO / OAuth2 / SAML Pipeline - Just-in-Time Provisioning (Anında Yetkilendirme)

Bu modül, SSO ile giriş yapan kullanıcıları otomatik olarak Django grup ve rollerine atar.
Kullanıcı SSO'dan geldikten sonra, ID token/assertion'daki grup bilgisine bakarak
ilgili Django grup/permissionlara otomatik olarak eklenir.

Kullanım:
- settings.SOCIAL_AUTH_PIPELINE içinde 'inventory.sso_pipeline.update_user_role_from_sso' çağrılır
- Her SSO giriş işleminde bu fonksiyon otomatik olarak tetiklenir
"""

from django.contrib.auth.models import User, Group
from django.conf import settings
import logging
from inventory.models import SystemLog

logger = logging.getLogger(__name__)


def update_user_role_from_sso(backend, user, response, *args, **kwargs):
    """
    SSO token/assertion'daki grup bilgisine göre kullanıcıyı Django grup/rollerine otomatik atama.
    
    Just-in-Time Provisioning (Anında Yetkilendirme):
    - Kullanıcı ilk kez SSO ile giriş yaptığında otomatik oluşturulur
    - SSO'daki grup bilgisine bakarak Django grup/permission'ları otomatik atanır
    - Her giriş yapıldığında, SSO'daki grup bilgisine göre Django grupları güncellenir
    
    Örnek SAML/OIDC Token:
    {
        "email": "user@example.com",
        "name": "John Doe",
        "groups": ["IT_Network_Admins", "IT_Security_Team"]
    }
    
    Eşleştirme Mantığı:
    - IT_Network_Admins -> Django "Ağ Ekibi" grubu
    - IT_Security_Team -> Django "Güvenlik Ekibi" grubu
    - IT_Infrastructure_Admins -> Django "Altyapı Ekibi" grubu
    """
    
    if not user:
        return
    
    # Backend'den gelen response'u ve user bilgisini kontrol et
    sso_groups = _extract_groups_from_sso_response(backend, response)
    
    if not sso_groups:
        logger.info(f'SSO Pipeline: Kullanıcı {user.username} için grup bilgisi bulunamadı.')
        return
    
    # SSO gruplarını Django gruplarına eşle
    django_groups = _map_sso_groups_to_django_groups(sso_groups)
    
    # Kullanıcıyı Django gruplarına atama veya güncelleme yap
    _assign_user_to_django_groups(user, django_groups)
    
    logger.info(f'SSO Pipeline: Kullanıcı {user.username} şu gruplara atandı: {django_groups}')


def _extract_groups_from_sso_response(backend, response):
    """
    Backend'e göre SSO response'undan grup bilgisini çıkart.
    
    Farklı SSO sağlayıcıları grup bilgisini farklı yerlerde saklar:
    - Azure AD: token_response['access_token'] (JWT içinde)
    - Okta: response['groups'] veya token içinde
    - Generic SAML: response['attributes']['groups']
    - Generic OIDC: token claims içinde
    """
    
    sso_groups = []
    
    # Azure AD / Okta / OIDC durumu
    if hasattr(backend, 'name'):
        backend_name = backend.name
    else:
        backend_name = backend.__class__.__name__
    
    logger.debug(f'SSO Provider: {backend_name}')
    
    # SAML durumu
    if backend_name in ['saml', 'SAMLAuth']:
        if 'attributes' in response:
            sso_groups = response['attributes'].get('groups', [])
            if isinstance(sso_groups, list) and len(sso_groups) > 0:
                # SAML'de groups genellikle liste içinde liste olarak gelir
                if isinstance(sso_groups[0], list):
                    sso_groups = sso_groups[0]
    
    # Azure AD durumu (OIDC)
    elif backend_name in ['azuread-oauth2', 'AzureADOAuth2']:
        # Azure AD, groups claim'ini access token'ında veya ID token'ında saklar
        if 'groups' in response:
            sso_groups = response.get('groups', [])
        elif '_raw_user_data' in response:
            sso_groups = response['_raw_user_data'].get('groups', [])
    
    # Generic OIDC durumu
    elif backend_name in ['openidconnect', 'OpenIdConnectAuth', 'oidc']:
        if 'groups' in response:
            sso_groups = response.get('groups', [])
    
    # Okta durumu (OIDC)
    elif 'okta' in backend_name.lower():
        if 'groups' in response:
            sso_groups = response.get('groups', [])
    
    # Fallback: Direkt response'ta groups alanı ara
    else:
        sso_groups = response.get('groups', [])
    
    # Eğer sso_groups bir string ise, liste'ye çevir
    if isinstance(sso_groups, str):
        sso_groups = [sso_groups]
    
    # Boş değerleri filtrele
    sso_groups = [g for g in sso_groups if g and isinstance(g, str)]
    
    return sso_groups


def _map_sso_groups_to_django_groups(sso_groups):
    """
    SSO'daki grup adlarını Django grup adlarına eşle.
    
    Eşleştirme Tablosu:
    SSO Grup Adı                    -> Django Grup Adı
    ============================================================
    IT_Network_Admins               -> Ağ Ekibi
    IT_Security_Team                -> Güvenlik Ekibi
    IT_Infrastructure_Admins        -> Altyapı Ekibi
    IT_Database_Admins              -> Veritabanı Ekibi
    IT_Help_Desk                    -> Help Desk Ekibi
    Network_Administrators          -> Ağ Ekibi (alternatif)
    Domain_Admins                   -> Domain Admins
    Everyone                        -> (otomatik atanır, skip)
    
    Örnek:
        SSO: ["IT_Network_Admins", "IT_Security_Team"]
        -> Django: ["Ağ Ekibi", "Güvenlik Ekibi"]
    """
    
    # SSO grup adı -> Django grup adı eşlemesi
    sso_to_django_mapping = {
        'IT_Network_Admins': 'Ağ Ekibi',
        'IT_Security_Team': 'Güvenlik Ekibi',
        'IT_Infrastructure_Admins': 'Altyapı Ekibi',
        'IT_Database_Admins': 'Veritabanı Ekibi',
        'IT_Help_Desk': 'Help Desk Ekibi',
        'Network_Administrators': 'Ağ Ekibi',
        'Domain_Admins': 'Domain Admins',
        'Administrators': 'Administrators',
        'IT_Operations': 'IT Operasyonlar',
        'IT_Support': 'Help Desk Ekibi',
    }
    
    django_groups = []
    
    for sso_group in sso_groups:
        # Büyük/küçük harf duyarlılığını ortadan kaldır
        sso_group_lower = str(sso_group).strip()
        
        # Doğru eşleştirmeyi bul
        django_group = None
        for sso_key, django_val in sso_to_django_mapping.items():
            if sso_key.lower() == sso_group_lower.lower():
                django_group = django_val
                break
        
        # Eğer eşleştirme bulunamazsa, SSO grup adını kullan
        if not django_group:
            django_group = sso_group.replace('_', ' ').title()
        
        # Eğer 'Everyone' ise atla (tüm kullanıcılar otomatik bu gruba girer)
        if django_group.lower() != 'everyone':
            django_groups.append(django_group)
    
    # Tekrarları kaldır
    django_groups = list(set(django_groups))
    
    return django_groups


def _assign_user_to_django_groups(user, django_groups):
    """
    Kullanıcıyı Django gruplarına atama veya güncelleme yap.
    
    Mantık:
    1. Eğer grup yoksa, oluştur
    2. Kullanıcıyı gruba ekle
    3. Eski/gereksiz gruplardan çıkart (sync)
    """
    
    try:
        # Hedef Django gruplarını al veya oluştur
        django_group_objects = []
        for group_name in django_groups:
            group, created = Group.objects.get_or_create(name=group_name)
            django_group_objects.append(group)
            
            if created:
                logger.info(f'SSO Pipeline: Yeni Django grubu oluşturuldu: {group_name}')
        
        # Mevcut grupları al
        current_groups = set(user.groups.all())
        target_groups = set(django_group_objects)
        
        # Yeni atanacak gruplar
        groups_to_add = target_groups - current_groups
        for group in groups_to_add:
            user.groups.add(group)
            logger.info(f'SSO Pipeline: Kullanıcı {user.username} şu gruba eklendi: {group.name}')
            
            # SystemLog kaydı oluştur
            SystemLog.objects.create(
                action='SYSTEM', 
                details=f"SSO JIT Provisioning: {user.username} kullanıcısı '{group.name}' grubuna otomatik atandı."
            )
        
        # Kaldırılacak gruplar (SSO'da artık bulunmayan ama Django'da olan gruplar)
        # Opsiyonel: Eğer tam senkronizasyon istiyorsan
        groups_to_remove = current_groups - target_groups
        for group in groups_to_remove:
            # Sadece SSO ile yönetilen grupları kaldır (güvenlik: manuel atanan grupları kaldırma)
            if group.name in ['Ağ Ekibi', 'Güvenlik Ekibi', 'Altyapı Ekibi', 'Veritabanı Ekibi', 'Help Desk Ekibi']:
                user.groups.remove(group)
                logger.info(f'SSO Pipeline: Kullanıcı {user.username} şu gruptan çıkartıldı: {group.name}')
                
                SystemLog.objects.create(
                    action='SYSTEM', 
                    details=f"SSO Senkronizasyonu: {user.username} kullanıcısı '{group.name}' grubundan çıkarıldı."
                )
        
        # Eğer hiç gruba atanmadıysa, "Read-Only User" grubu atama
        if not user.groups.exists():
            read_only_group, created = Group.objects.get_or_create(name='Okuma-Yazma Yok')
            user.groups.add(read_only_group)
            logger.info(f'SSO Pipeline: Kullanıcı {user.username} varsayılan Read-Only grubuna atandı.')
        
    except Exception as e:
        logger.error(f'SSO Pipeline: Grup atama başarısız - Kullanıcı: {user.username}, Hata: {str(e)}')
        SystemLog.objects.create(
            action='SYSTEM', 
            details=f"SSO Role Mapping Hatası: {user.username} için işlem başarısız oldu. Detay: {str(e)}"
        )


# ==========================================
# OPSIYONEL: SSO Disconnect Sinyali
# ==========================================
def disconnect_user_on_sso_logout(backend, user, *args, **kwargs):
    """
    Kullanıcı SSO'dan logout olduğunda, local session'ını da sonlandır.
    (Opsiyonel - güvenlik yükseltmek için kullanılabilir)
    """
    logger.info(f"SSO Pipeline: Kullanıcı {user.username} SSO'dan logout oldu.")
    # Burada ek cleanup işlemleri yapılabilir