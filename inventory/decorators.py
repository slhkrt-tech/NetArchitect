from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(allowed_roles):
    """
    Sadece belirtilen rollere (Gruplara) sahip kullanıcıların View'a erişmesine izin verir.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('login')
                
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            # Kullanıcının gruplarından en az biri allowed_roles içinde mi?
            user_groups = request.user.groups.values_list('name', flat=True)
            if any(role in user_groups for role in allowed_roles):
                return view_func(request, *args, **kwargs)
                
            raise PermissionDenied("🚨 GÜVENLİK İHLALİ: Bu sayfaya/işleme erişim yetkiniz (Rolünüz) bulunmamaktadır.")
        return _wrapped_view
    return decorator