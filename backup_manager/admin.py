import os
import io
from datetime import datetime

from django.contrib import admin, messages
from django.urls import path
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django import forms
from django.core.mail import EmailMessage
from django.core.management import call_command
from django.conf import settings

from .models import DatabaseBackup
from .utils import create_backup, restore_backup


class UploadBackupForm(forms.Form):
    backup_file = forms.FileField(
        label="ملف النسخة الاحتياطية (JSON)",
        help_text="اختر ملف JSON صالح تم تصديره من dumpdata"
    )


class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'created_at', 'size_format')
    actions = ['restore_selected_backup', 'send_backup_email']
    change_list_template = 'admin/backup_manager/change_list.html'

    def size_format(self, obj):
        from django.template.defaultfilters import filesizeformat
        return filesizeformat(obj.size)
    size_format.short_description = 'الحجم'

    # ---------- مزامنة الملفات من المجلد ----------
    def _sync_backup_files(self):
        backup_dir = settings.BACKUP_DIR
        if not os.path.exists(backup_dir):
            return
        existing_paths = set(
            DatabaseBackup.objects.values_list('file_path', flat=True)
        )
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                if filepath not in existing_paths:
                    size = os.path.getsize(filepath)
                    DatabaseBackup.objects.create(
                        file_name=filename,
                        file_path=filepath,
                        size=size,
                        created_at=datetime.fromtimestamp(os.path.getctime(filepath))
                    )
                    existing_paths.add(filepath)

    def changelist_view(self, request, extra_context=None):
        self._sync_backup_files()
        return super().changelist_view(request, extra_context)

    # ---------- حذف الملف مع السجل ----------
    def delete_queryset(self, request, queryset):
        for backup in queryset:
            if backup.file_path and os.path.exists(backup.file_path):
                os.remove(backup.file_path)
        queryset.delete()

    def delete_model(self, request, obj):
        if obj.file_path and os.path.exists(obj.file_path):
            os.remove(obj.file_path)
        obj.delete()

    # ---------- المسارات المخصصة ----------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('create_backup/',
                 self.admin_site.admin_view(self.create_backup_view),
                 name='backup-create'),
            path('upload_backup/',
                 self.admin_site.admin_view(self.upload_backup_view),
                 name='backup-upload'),
            path('download_backup/',
                 self.admin_site.admin_view(self.download_backup_view),
                 name='backup-download-to-device'),
        ]
        return custom_urls + urls

    # ---------- إنشاء نسخة وتنزيلها مباشرة إلى الجهاز ----------
    def download_backup_view(self, request):
        """
        ينشئ نسخة احتياطية ويعيدها كملف JSON للتحميل المباشر (لا تخزن على السيرفر).
        """
        try:
            output = io.StringIO()
            call_command(
                'dumpdata',
                '--natural-foreign',
                '--natural-primary',
                '-e', 'contenttypes',
                '-e', 'auth.Permission',
                '-e', 'sessions',
                '-e', 'admin.LogEntry',
                stdout=output
            )
            response = HttpResponse(output.getvalue(), content_type='application/json')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_{timestamp}.json"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            self.message_user(request, "تم تحضير النسخة للتنزيل.", level=messages.SUCCESS)
            return response
        except Exception as e:
            self.message_user(request, f"فشل إنشاء النسخة للتنزيل: {e}", level=messages.ERROR)
            return HttpResponseRedirect("../")

    # ---------- إنشاء نسخة على الخادم (كما هي) ----------
    def create_backup_view(self, request):
        try:
            backup = create_backup()
            self.message_user(request, f"تم إنشاء النسخة بنجاح: {backup.file_name}", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"فشل إنشاء النسخة: {e}", level=messages.ERROR)
        return HttpResponseRedirect("../")

    # ---------- رفع نسخة خارجية ----------
    def upload_backup_view(self, request):
        if request.method == 'POST':
            form = UploadBackupForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded_file = request.FILES['backup_file']
                if not uploaded_file.name.endswith('.json'):
                    self.message_user(request, "يرجى رفع ملف JSON فقط.", level=messages.ERROR)
                    return HttpResponseRedirect(".")
                backup_dir = settings.BACKUP_DIR
                os.makedirs(backup_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"uploaded_backup_{timestamp}.json"
                filepath = os.path.join(backup_dir, filename)
                with open(filepath, 'wb+') as dest:
                    for chunk in uploaded_file.chunks():
                        dest.write(chunk)
                size = os.path.getsize(filepath)
                DatabaseBackup.objects.create(
                    file_name=filename,
                    file_path=filepath,
                    size=size
                )
                self.message_user(request, f"تم رفع النسخة بنجاح: {filename}", level=messages.SUCCESS)
                return HttpResponseRedirect("../")
        else:
            form = UploadBackupForm()
        context = {
            'title': 'رفع نسخة احتياطية خارجية',
            'form': form,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/backup_manager/upload_backup.html', context)

    # ---------- استعادة نسخة ----------
    def restore_selected_backup(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "الرجاء تحديد نسخة واحدة فقط للاستعادة.", level=messages.ERROR)
            return
        backup = queryset.first()
        if 'confirm' in request.POST:
            try:
                restore_backup(backup.id)
                self.message_user(request, "تمت استعادة قاعدة البيانات بنجاح! قد تحتاج إلى إعادة تسجيل الدخول.", level=messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"فشلت عملية الاستعادة: {e}", level=messages.ERROR)
            return HttpResponseRedirect(request.get_full_path())
        context = {
            'title': 'تأكيد استعادة النسخة الاحتياطية',
            'backup': backup,
            'opts': self.model._meta,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'queryset': queryset,
        }
        return TemplateResponse(request, 'admin/backup_manager/restore_confirm.html', context)

    restore_selected_backup.short_description = "استعادة النسخة المحددة"

    # ---------- إرسال النسخة عبر البريد ----------
    def send_backup_email(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "الرجاء تحديد نسخة واحدة فقط لإرسالها.", level=messages.ERROR)
            return

        backup = queryset.first()

        if request.method == 'POST' and 'confirm_email' in request.POST:
            recipient = request.POST.get('email', '').strip()
            if not recipient:
                self.message_user(request, "يرجى إدخال بريد إلكتروني صالح.", level=messages.ERROR)
                context = {
                    'title': 'حفظ النسخة في البريد',
                    'backup': backup,
                    'opts': self.model._meta,
                    'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
                    'queryset': queryset,
                    'error': 'يرجى إدخال البريد الإلكتروني.'
                }
                return TemplateResponse(request, 'admin/backup_manager/send_email.html', context)

            try:
                subject = f"نسخة احتياطية لقاعدة البيانات - {backup.file_name}"
                body = f"مرفق ملف النسخة الاحتياطية الذي تم إنشاؤه بتاريخ {backup.created_at}."
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient],
                )
                email.attach_file(backup.file_path, mimetype='application/json')
                email.send(fail_silently=False)
                self.message_user(request, f"تم حفظ النسخة في بريد {recipient} بنجاح.", level=messages.SUCCESS)
                return HttpResponseRedirect(request.get_full_path())
            except Exception as e:
                self.message_user(request, f"فشل إرسال البريد: {e}", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())

        context = {
            'title': 'حفظ النسخة في البريد',
            'backup': backup,
            'opts': self.model._meta,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'queryset': queryset,
        }
        return TemplateResponse(request, 'admin/backup_manager/send_email.html', context)

    send_backup_email.short_description = "حفظ النسخة في البريد"


admin.site.register(DatabaseBackup, DatabaseBackupAdmin)