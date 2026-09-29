from pathlib import Path

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from .backup_db import pg_program, run_pg


class Command(BaseCommand):
    help = 'Восстанавливает копию в отдельную пустую базу PostgreSQL.'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Копия, созданная командой backup_db')
        parser.add_argument('--database', required=True, help='Имя заранее созданной пустой базы')

    def handle(self, *args, **options):
        source = settings.DATABASES['default']
        name = options['database']
        if name in [source['NAME'], 'postgres', 'template0', 'template1']:
            raise CommandError('Укажите отдельную базу. Рабочую и системные базы перезаписывать нельзя.')
        path = Path(options['file']).resolve()
        if not path.is_file():
            raise CommandError('Файл резервной копии не найден.')
        with path.open('rb') as file:
            signature = file.read(5)
        if signature != b'PGDMP':
            raise CommandError('Нужна копия PostgreSQL в формате custom (.dump).')
        try:
            connection = psycopg.connect(dbname=name, user=source['USER'], password=source['PASSWORD'],
                                         host=source['HOST'], port=source['PORT'], connect_timeout=10,
                                         sslmode=source.get('OPTIONS', {}).get('sslmode', 'prefer'))
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
                    if cursor.fetchone()[0]:
                        raise CommandError('Выбранная база не пуста. Создайте другую базу для восстановления.')
        except psycopg.OperationalError:
            raise CommandError('Не удалось подключиться к базе восстановления. Проверьте имя и права доступа.')
        run_pg([pg_program('pg_restore'), '--no-owner', '--no-acl', '--exit-on-error', '--single-transaction',
                '--dbname', name, str(path)], database=name)
        self.stdout.write(f'База {name} восстановлена. Проверьте данные перед переключением приложения.')
