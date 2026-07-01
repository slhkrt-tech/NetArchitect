"""Fabrika BT Komuta Merkezi için varsayılan kartela ve alt alan bootstrap verisi."""

from inventory.models import AssetQRTag, FactoryArea, FactoryDepartment, FactoryZone, Device, ITAsset


DEFAULT_DEPARTMENTS = [
    {
        'name': 'Üretim',
        'code': 'URETIM',
        'department_type': 'production',
        'criticality': 'high',
        'manager_name': 'Üretim Müdürü',
        'floor_label': 'Zemin / 1. Kat',
        'zones': [
            {'name': 'Paketleme Hattı 1', 'code': 'PKT-01', 'zone_type': 'production_line', 'criticality': 'high'},
            {'name': 'Montaj Hattı 2', 'code': 'MNT-02', 'zone_type': 'production_line', 'criticality': 'medium'},
        ],
    },
    {
        'name': 'Kalite Kontrol',
        'code': 'KALITE',
        'department_type': 'quality',
        'criticality': 'medium',
        'manager_name': 'Kalite Sorumlusu',
        'floor_label': '1. Kat',
        'zones': [
            {'name': 'Laboratuvar', 'code': 'LAB-01', 'zone_type': 'room', 'criticality': 'medium'},
        ],
    },
    {
        'name': 'Bilgi İşlem',
        'code': 'BIT',
        'department_type': 'it',
        'criticality': 'critical',
        'manager_name': 'BT Sorumlusu',
        'floor_label': '2. Kat',
        'zones': [
            {'name': 'Sistem Odası A', 'code': 'SYS-A', 'zone_type': 'server_room', 'criticality': 'critical'},
            {'name': 'Network Closet B', 'code': 'NET-B', 'zone_type': 'room', 'criticality': 'high'},
        ],
    },
    {
        'name': 'Depo & Lojistik',
        'code': 'DEPO',
        'department_type': 'warehouse',
        'criticality': 'medium',
        'manager_name': 'Depo Sorumlusu',
        'floor_label': 'Zemin',
        'zones': [
            {'name': 'Ana Depo', 'code': 'DEP-01', 'zone_type': 'warehouse', 'criticality': 'medium'},
        ],
    },
    {
        'name': 'Güvenlik',
        'code': 'GUVENLIK',
        'department_type': 'security',
        'criticality': 'high',
        'manager_name': 'Güvenlik Amiri',
        'floor_label': 'Giriş / Perimeter',
        'zones': [
            {'name': 'Kamera Merkezi', 'code': 'CAM-01', 'zone_type': 'camera_zone', 'criticality': 'high'},
            {'name': 'Güvenlik Kulübesi', 'code': 'SEC-01', 'zone_type': 'security_post', 'criticality': 'medium'},
        ],
    },
]


def ensure_default_factory_structure():
    """Varsayılan fabrika departman kartelası ve alt alanları oluşturur (idempotent)."""
    created_departments = 0
    created_zones = 0
    factory_area = FactoryArea.objects.order_by('id').first()

    for item in DEFAULT_DEPARTMENTS:
        department, dept_created = FactoryDepartment.objects.get_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'department_type': item['department_type'],
                'criticality': item['criticality'],
                'manager_name': item['manager_name'],
                'floor_label': item['floor_label'],
                'description': f"OmniOps varsayılan kartela kaydı: {item['name']}",
                'is_active': True,
            },
        )
        if dept_created:
            created_departments += 1

        for zone_item in item.get('zones', []):
            _, zone_created = FactoryZone.objects.get_or_create(
                department=department,
                code=zone_item['code'],
                defaults={
                    'name': zone_item['name'],
                    'zone_type': zone_item['zone_type'],
                    'criticality': zone_item['criticality'],
                    'factory_area': factory_area if zone_item['zone_type'] in ('server_room', 'production_line', 'camera_zone') else None,
                    'is_active': True,
                },
            )
            if zone_created:
                created_zones += 1

    return created_departments, created_zones


def ensure_default_qr_tags():
    """Örnek QR etiketleri oluşturur (idempotent)."""
    created = 0
    for zone in FactoryZone.objects.filter(is_active=True).order_by('id')[:8]:
        code = f'OMNI-ZONE-{zone.code}'
        _, was_created = AssetQRTag.objects.get_or_create(
            code=code,
            defaults={
                'tag_type': 'factory_zone',
                'label': zone.name,
                'location': zone.department.name,
                'factory_zone': zone,
                'is_active': True,
            },
        )
        if was_created:
            created += 1

    for device in Device.objects.order_by('id')[:5]:
        code = f'OMNI-DEV-{device.id:04d}'
        _, was_created = AssetQRTag.objects.get_or_create(
            code=code,
            defaults={
                'tag_type': 'device',
                'label': device.name,
                'device': device,
                'is_active': True,
            },
        )
        if was_created:
            created += 1

    for asset in ITAsset.objects.order_by('id')[:5]:
        if not asset.serial_number:
            continue
        code = f'OMNI-AST-{asset.serial_number[:20]}'
        _, was_created = AssetQRTag.objects.get_or_create(
            code=code,
            defaults={
                'tag_type': 'it_asset',
                'label': asset.name,
                'it_asset': asset,
                'is_active': True,
            },
        )
        if was_created:
            created += 1

    return created
