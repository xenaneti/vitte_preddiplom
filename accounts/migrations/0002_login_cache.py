from django.core.management import call_command
from django.db import migrations


def create_cache(apps, schema_editor):
    call_command('createcachetable', 'attendance_cache', database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [migrations.RunPython(create_cache, migrations.RunPython.noop)]
