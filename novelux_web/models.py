from django.db import models
 
 
def apk_upload_path(instance, filename):
    # Saves as media/apk/novelux-v1.2.3.apk
    return f'apk/novelux-v{instance.version_name}.apk'
 
 
class APKRelease(models.Model):
    version_name  = models.CharField(max_length=20, unique=True,
                        help_text='e.g. 1.0.0')
    version_code  = models.PositiveIntegerField(unique=True,
                        help_text='Integer build number, must increase each release')
    apk_file      = models.FileField(upload_to=apk_upload_path,
                        help_text='Upload the .apk file here')
    release_notes = models.TextField(blank=True,
                        help_text='What changed in this version (shown on download page)')
    is_active     = models.BooleanField(default=True,
                        help_text='Only the active release is served to users')
    min_android   = models.CharField(max_length=10, default='8.0',
                        help_text='Minimum Android version required')
    size_mb       = models.DecimalField(max_digits=6, decimal_places=1,
                        blank=True, null=True,
                        help_text='Leave blank — auto-calculated on save')
    download_count= models.PositiveIntegerField(default=0, editable=False)
    uploaded_at   = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
 
    class Meta:
        db_table = 'apk_releases'
        ordering = ['-version_code']
 
    def __str__(self):
        return f'Novelux v{self.version_name} (build {self.version_code})'
 
    def save(self, *args, **kwargs):
        # Auto-calculate file size
        if self.apk_file:
            try:
                self.size_mb = round(self.apk_file.size / (1024 * 1024), 1)
            except Exception:
                pass
        # Deactivate all other releases when this one is set active
        if self.is_active:
            APKRelease.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
 
    @classmethod
    def get_latest(cls):
        return cls.objects.filter(is_active=True).first()