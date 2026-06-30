from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .helpdesk import auto_assign_ticket, assign_customer_role, notify_ticket_event, CATEGORY_SLUG_MAP
from .models import Ticket, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        if not instance.is_staff and not instance.is_superuser:
            assign_customer_role(instance)


@receiver(pre_save, sender=Ticket)
def sync_ticket_category_and_closure(sender, instance, **kwargs):
    if instance.ticket_category_id:
        slug = instance.ticket_category.slug
        instance.category = CATEGORY_SLUG_MAP.get(slug, slug.capitalize())

    if instance.status in ('Cozuldu', 'Kapatildi') and not instance.closed_at:
        instance.closed_at = timezone.now()


@receiver(post_save, sender=Ticket)
def handle_new_ticket(sender, instance, created, **kwargs):
    if created and not instance.assigned_to_id:
        auto_assign_ticket(instance)
    elif not created:
        old_status = getattr(instance, '_previous_status', None)
        if old_status and old_status != instance.status:
            if instance.status in ('Cozuldu', 'Kapatildi'):
                notify_ticket_event(instance, 'closed')
            else:
                notify_ticket_event(instance, 'status')


@receiver(pre_save, sender=Ticket)
def store_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Ticket.objects.get(pk=instance.pk)
            instance._previous_status = old.status
        except Ticket.DoesNotExist:
            instance._previous_status = None
