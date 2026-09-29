import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def pg_program(name):
    directory = os.getenv('PG_BIN')
    filename = name + '.exe' if os.name == 'nt' else name
    return str(Path(directory) / filename) if directory else filename


def pg_environment(database=None):
    source = settings.DATABASES['default']
    environment = os.environ.copy()
    environment.update(PGHOST=source['HOST'], PGPORT=str(source['PORT']), PGUSER=source['USER'],
                       PGPASSWORD=source['PASSWORD'], PGDATABASE=database or source['NAME'],
                       PGSSLMODE=source.get('OPTIONS', {}).get('sslmode', 'prefer'))
    return environment


def run_pg(arguments, database=None):
    try:
        result = subprocess.run(arguments, env=pg_environment(database), capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=300,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except FileNotFoundError:
        raise CommandError('Утилиты PostgreSQL не найдены. Укажите каталог bin в PG_BIN.')
    except subprocess.TimeoutExpired:
        raise CommandError('Операция с базой заняла больше пяти минут.')
    if result.returncode:
        error = result.stderr.strip()
        password = settings.DATABASES['default']['PASSWORD']
        if password:
            error = error.replace(password, '***')
        raise CommandError(error)


class Command(BaseCommand):
    help = 'Сохраняет резервную копию PostgreSQL в указанный каталог.'

    def add_arguments(self, parser):
        parser.add_argument('--directory', required=True, help='Каталог вне публичных файлов сайта')

    def handle(self, *args, **options):
        directory = Path(options['directory']).resolve()
        static_root = Path(settings.STATIC_ROOT).resolve()
        if directory == static_root or static_root in directory.parents:
            raise CommandError('Резервную копию нельзя сохранять в каталоге статики.')
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        target = directory / f'attendance-{stamp}.dump'
        temporary = target.with_suffix('.part')
        try:
            run_pg([pg_program('pg_dump'), '--format=custom', '--no-owner', '--no-acl', '--file', str(temporary)])
            temporary.replace(target)
            if os.name != 'nt':
                target.chmod(0o600)
        finally:
            temporary.unlink(missing_ok=True)
        self.stdout.write(f'Резервная копия сохранена: {target}')
