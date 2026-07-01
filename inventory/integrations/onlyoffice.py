"""OnlyOffice Document Server ile tarayıcı tabanlı DOCX/XLSX/PPTX düzenleme."""
import hashlib
import json
import time
from urllib.parse import urljoin

from django.conf import settings


def onlyoffice_enabled():
    return bool(getattr(settings, 'ONLYOFFICE_DOCUMENT_SERVER_URL', ''))


def build_document_key(document):
    """OnlyOffice'in belge sürümünü tanıması için benzersiz anahtar üretir."""
    raw = f'{document.pk}-{document.updated_at.timestamp()}-{document.version}'
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def build_onlyoffice_editor_config(document, request, mode='edit'):
    """OnlyOffice Document Server için editör konfigürasyonu üretir."""
    if not onlyoffice_enabled():
        return None

    file_type = document.file_type if document.file_type in ('docx', 'xlsx', 'pptx', 'pdf') else 'docx'
    document_type_map = {
        'docx': 'word',
        'xlsx': 'cell',
        'pptx': 'slide',
        'pdf': 'word',
    }
    download_url = request.build_absolute_uri(f'/dokuman/{document.pk}/indir/')
    callback_url = request.build_absolute_uri(f'/dokuman/{document.pk}/editor-callback/')

    config = {
        'document': {
            'fileType': file_type,
            'key': build_document_key(document),
            'title': document.title,
            'url': download_url,
        },
        'documentType': document_type_map.get(file_type, 'word'),
        'editorConfig': {
            'callbackUrl': callback_url,
            'lang': 'tr',
            'mode': mode,
            'user': {
                'id': str(request.user.id),
                'name': request.user.get_full_name() or request.user.username,
            },
        },
    }

    jwt_secret = getattr(settings, 'ONLYOFFICE_JWT_SECRET', '')
    if jwt_secret:
        try:
            import jwt
            # JWT etkin sunucularda imzalı token zorunludur
            token = jwt.encode(config, jwt_secret, algorithm='HS256')
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            return {'token': token, 'config': config}
        except ImportError:
            # PyJWT yüklü değilse imzasız konfigürasyon döndürülür
            pass
    return {'config': config}


def get_onlyoffice_script_url():
    """Editör arayüzünü yükleyen OnlyOffice JS dosyasının tam URL'sini döndürür."""
    base = getattr(settings, 'ONLYOFFICE_DOCUMENT_SERVER_URL', '').rstrip('/')
    if not base:
        return ''
    return urljoin(base + '/', 'web-apps/apps/api/documents/api.js')
