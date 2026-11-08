from django.contrib import admin
from .models import PageVisit, ScheduledJobRun


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display  = ('created_at', 'path', 'country', 'city', 'device_type', 'browser', 'ip_address', 'user')
    list_filter   = ('device_type', 'country', 'browser')
    search_fields = ('ip_address', 'path', 'country', 'city', 'referrer')
    readonly_fields = ('created_at',)
    date_hierarchy  = 'created_at'


@admin.register(ScheduledJobRun)
class ScheduledJobRunAdmin(admin.ModelAdmin):
    """When each scheduled job last ran (via /api/cron/run/)."""
    list_display    = ('name', 'last_started', 'last_finished', 'last_ok', 'runs', 'last_result')
    readonly_fields = list_display
