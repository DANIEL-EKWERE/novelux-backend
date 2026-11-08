from django.db import models
from django.conf import settings


class PageVisit(models.Model):
    DEVICE_MOBILE  = 'mobile'
    DEVICE_TABLET  = 'tablet'
    DEVICE_DESKTOP = 'desktop'
    DEVICE_BOT     = 'bot'
    DEVICE_CHOICES = [
        (DEVICE_MOBILE,  'Mobile'),
        (DEVICE_TABLET,  'Tablet'),
        (DEVICE_DESKTOP, 'Desktop'),
        (DEVICE_BOT,     'Bot'),
    ]

    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    country     = models.CharField(max_length=100, blank=True, db_index=True)
    country_code= models.CharField(max_length=2,   blank=True)
    city        = models.CharField(max_length=100, blank=True)
    path        = models.CharField(max_length=500, db_index=True)
    referrer    = models.CharField(max_length=500, blank=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_CHOICES, blank=True, db_index=True)
    browser     = models.CharField(max_length=80, blank=True)
    os          = models.CharField(max_length=80, blank=True)
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='page_visits',
    )
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'page_visits'
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['created_at', 'country']),
            models.Index(fields=['created_at', 'device_type']),
        ]

    def __str__(self):
        return f'{self.ip_address} → {self.path} [{self.created_at:%Y-%m-%d}]'


class ScheduledJobRun(models.Model):
    """When each scheduled job last ran via /api/cron/run/ (the stand-in for
    celery beat when no worker is running)."""
    name          = models.CharField(max_length=60, unique=True)
    last_started  = models.DateTimeField(null=True, blank=True)
    last_finished = models.DateTimeField(null=True, blank=True)
    last_ok       = models.BooleanField(default=True)
    last_result   = models.TextField(blank=True)
    runs          = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'scheduled_job_runs'
        ordering = ['name']

    def __str__(self):
        return self.name
