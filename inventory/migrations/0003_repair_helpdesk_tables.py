from django.db import migrations


def create_missing_helpdesk_tables(apps, schema_editor):
    existing_tables = set(schema_editor.connection.introspection.table_names())

    Ticket = apps.get_model('inventory', 'Ticket')
    TicketCategory = apps.get_model('inventory', 'TicketCategory')
    TicketAttachment = apps.get_model('inventory', 'TicketAttachment')
    UserProfile = apps.get_model('inventory', 'UserProfile')
    Notification = apps.get_model('inventory', 'Notification')

    for model in (TicketCategory, TicketAttachment, UserProfile, Notification):
        if model._meta.db_table not in existing_tables:
            schema_editor.create_model(model)
            existing_tables.add(model._meta.db_table)

    ticket_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            Ticket._meta.db_table,
        )
    }
    if 'ticket_category_id' not in ticket_columns:
        schema_editor.add_field(Ticket, Ticket._meta.get_field('ticket_category'))


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_dlpevent_fieldvisit_networkscan_networkscanhost_and_more'),
    ]

    operations = [
        migrations.RunPython(create_missing_helpdesk_tables, migrations.RunPython.noop),
    ]
