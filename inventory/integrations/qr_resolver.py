from inventory.models import AssetQRTag


def resolve_qr_code(raw_code):
    """QR/barkod kodunu varlık etiketine çözümler."""
    code = (raw_code or '').strip()
    if not code:
        return None

    tag = AssetQRTag.objects.filter(code__iexact=code, is_active=True).select_related(
        'device', 'endpoint', 'it_asset', 'camera', 'printer', 'factory_zone', 'consumable',
    ).first()
    if tag:
        return {
            'found': True,
            'code': tag.code,
            'tag_type': tag.get_tag_type_display(),
            'title': tag.display_name,
            'location': tag.location,
            'url': tag.resolved_url,
        }

    # Etiket bulunamazsa seri numarası veya hostname ile doğrudan arama yap
    from inventory.models import Device, EndpointDevice, ITAsset, CameraDevice

    for model, field, url, label in (
        (Device, 'name', '/topoloji/', 'Cihaz'),
        (EndpointDevice, 'hostname', '/kimlik-operasyonlari/', 'Endpoint'),
        (EndpointDevice, 'serial_number', '/kimlik-operasyonlari/', 'Endpoint'),
        (ITAsset, 'serial_number', '/it-envanter/', 'IT Varlık'),
        (ITAsset, 'name', '/it-envanter/', 'IT Varlık'),
        (CameraDevice, 'name', '/komuta-merkezi/', 'Kamera'),
    ):
        obj = model.objects.filter(**{f'{field}__iexact': code}).first()
        if obj:
            return {
                'found': True,
                'code': code,
                'tag_type': label,
                'title': str(obj),
                'location': getattr(obj, 'location', '') or getattr(obj, 'factory_area', '') or '',
                'url': url,
            }

    return {'found': False, 'code': code, 'title': 'Kayıt bulunamadı', 'url': '/varlik-qr-tara/'}
