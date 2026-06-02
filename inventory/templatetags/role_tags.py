from django import template

register = template.Library()

@register.filter(name='has_role')
def has_role(user, role_name):
    """
    Kullanıcının belirtilen role (Group) sahip olup olmadığını kontrol eder.
    Kullanımı: {% if request.user|has_role:"Ağ Ekibi" %}
    """
    if not user.is_authenticated:
        return False
    # Superuser (Sistem Kurucusu) her role otomatik sahiptir
    if user.is_superuser:
        return True 
    
    # Virgülle ayrılmış çoklu rol kontrolü (Örn: "Ağ Ekibi,Sistem Ekibi")
    roles = [role.strip() for role in role_name.split(',')]
    return user.groups.filter(name__in=roles).exists()