import os
from django.conf import settings
from django.core.management import call_command
from datetime import datetime
from .models import DatabaseBackup

def create_backup():
    backup_dir = settings.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_{timestamp}.json'
    filepath = os.path.join(backup_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        call_command(
            'dumpdata',
            '--natural-foreign',
            '--natural-primary',
            '-e', 'contenttypes',
            '-e', 'auth.Permission',
            '-e', 'sessions',
            '-e', 'admin.LogEntry',
            stdout=f
        )

    size = os.path.getsize(filepath)
    backup = DatabaseBackup.objects.create(
        file_name=filename,
        file_path=filepath,
        size=size
    )
    return backup

def restore_backup(backup_id):
    backup = DatabaseBackup.objects.get(id=backup_id)
    filepath = backup.file_path

    if not os.path.exists(filepath):
        raise FileNotFoundError("ملف النسخة غير موجود")

    # مسح كل بيانات قاعدة البيانات
    call_command('flush', '--noinput')
    # استعادة النسخة
    call_command('loaddata', filepath)