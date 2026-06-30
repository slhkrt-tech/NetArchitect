from django.core.management.base import BaseCommand
from inventory.helpdesk import ensure_default_groups, ensure_default_categories, ensure_default_permissions


class Command(BaseCommand):
    help = 'Servis masası varsayılan rollerini ve kategorilerini oluşturur'

    def handle(self, *args, **options):
        ensure_default_groups()
        ensure_default_categories()
        ensure_default_permissions()
        self.stdout.write(self.style.SUCCESS('Servis masası rolleri ve kategorileri hazır.'))
