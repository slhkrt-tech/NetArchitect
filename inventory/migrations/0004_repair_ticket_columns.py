from django.db import migrations


def add_missing_ticket_columns(apps, schema_editor):
    Ticket = apps.get_model('inventory', 'Ticket')
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            Ticket._meta.db_table,
        )
    }

    for field_name in ('closed_at',):
        if Ticket._meta.get_field(field_name).column not in existing_columns:
            schema_editor.add_field(Ticket, Ticket._meta.get_field(field_name))


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_repair_helpdesk_tables'),
    ]

    operations = [
        migrations.RunPython(add_missing_ticket_columns, migrations.RunPython.noop),
    ]
