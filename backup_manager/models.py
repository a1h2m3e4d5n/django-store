from django.db import models

class DatabaseBackup(models.Model):
    file_name = models.CharField(max_length=255, verbose_name="اسم الملف")
    file_path = models.CharField(max_length=512, verbose_name="مسار الملف")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    size = models.PositiveIntegerField(help_text="الحجم بالبايت", verbose_name="الحجم")

    class Meta:
        verbose_name = "نسخة احتياطية"
        verbose_name_plural = "النسخ الاحتياطية"
        ordering = ['-created_at']

    def __str__(self):
        return self.file_name