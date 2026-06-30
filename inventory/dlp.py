import re

SENSITIVE_PATTERNS = (
    ('Kredi Kartı', re.compile(r'\b(?:\d[ -]*?){13,16}\b'), 'high'),
    ('TC Kimlik Benzeri', re.compile(r'\b\d{11}\b'), 'medium'),
    ('API Anahtarı', re.compile(r'(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{12,}'), 'critical'),
    ('Parola İfadesi', re.compile(r'(?i)(password|parola|şifre)\s*[:=]\s*\S+'), 'high'),
)


def inspect_text_for_dlp(text, user=None, source='unknown', block=False):
    """Basit DLP denetimi yapar ve eşleşmeleri DLPEvent olarak kaydeder."""
    from .models import DLPEvent

    text = text or ''
    events = []
    for rule_name, pattern, severity in SENSITIVE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        events.append(DLPEvent.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            source=source,
            rule=rule_name,
            severity=severity,
            excerpt=match.group(0)[:120],
            blocked=block and severity in ('high', 'critical'),
        ))
    return events


def has_blocking_dlp_event(events):
    return any(event.blocked for event in events)
