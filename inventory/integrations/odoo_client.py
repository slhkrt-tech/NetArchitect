import xmlrpc.client


class OdooClientError(Exception):
    pass


class OdooClient:
    """Odoo XML-RPC istemcisi (common ve object uç noktaları)."""

    def __init__(self, base_url, database, username, api_key):
        self.base_url = base_url.rstrip('/')
        self.database = database
        self.username = username
        self.api_key = api_key
        self.uid = None
        self._common = xmlrpc.client.ServerProxy(f'{self.base_url}/xmlrpc/2/common', allow_none=True)
        self._models = xmlrpc.client.ServerProxy(f'{self.base_url}/xmlrpc/2/object', allow_none=True)

    def authenticate(self):
        uid = self._common.authenticate(self.database, self.username, self.api_key, {})
        if not uid:
            raise OdooClientError('Odoo kimlik doğrulama başarısız.')
        self.uid = uid
        return uid

    def execute(self, model, method, *args, **kwargs):
        if not self.uid:
            self.authenticate()
        return self._models.execute_kw(
            self.database, self.uid, self.api_key,
            model, method, list(args), kwargs or {},
        )

    def test_connection(self):
        version = self._common.version()
        uid = self.authenticate()
        partner_count = self.execute('res.partner', 'search_count', [[('active', '=', True)]])
        return {
            'server_version': version.get('server_version', 'unknown'),
            'uid': uid,
            'partner_count': partner_count,
        }

    def sync_partners_preview(self, limit=25):
        partners = self.execute(
            'res.partner', 'search_read',
            [[('active', '=', True)]],
            {'fields': ['name', 'email', 'phone', 'company_type'], 'limit': limit},
        )
        return partners


def test_erp_connection(connection):
    """ERP bağlantı kaydını test eder; desteklenen tipe göre kimlik doğrulama yapar."""
    if connection.erp_type == 'odoo':
        client = OdooClient(connection.base_url, connection.database_name, connection.username, connection.api_key)
        return client.test_connection()
    raise OdooClientError(f'{connection.get_erp_type_display()} için test henüz desteklenmiyor.')


def sync_erp_connection(connection, limit=50):
    """Seçili ERP bağlantısından partner, ürün ve helpdesk verilerini önizleme amaçlı okur."""
    if connection.erp_type == 'odoo':
        client = OdooClient(connection.base_url, connection.database_name, connection.username, connection.api_key)
        client.authenticate()
        synced = 0
        messages = []

        if connection.sync_partners:
            partners = client.sync_partners_preview(limit=limit)
            synced += len(partners)
            messages.append(f'{len(partners)} partner okundu')

        if connection.sync_products:
            product_count = client.execute('product.product', 'search_count', [[('active', '=', True)]])
            synced += min(product_count, limit)
            messages.append(f'{product_count} ürün envanteri görüldü')

        if connection.sync_helpdesk:
            ticket_models = ['helpdesk.ticket', 'project.task']
            for model_name in ticket_models:
                try:
                    count = client.execute(model_name, 'search_count', [[]])
                    synced += min(count, limit)
                    messages.append(f'{model_name}: {count} kayıt')
                    break
                except Exception:
                    continue

        return synced, '; '.join(messages) or 'Senkronizasyon tamamlandı'

    raise OdooClientError(f'{connection.get_erp_type_display()} sync henüz desteklenmiyor.')
