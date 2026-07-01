from django.contrib import admin
from .models import PageVisit


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display  = ('created_at', 'path', 'country', 'city', 'device_type', 'browser', 'ip_address', 'user')
    list_filter   = ('device_type', 'country', 'browser')
    search_fields = ('ip_address', 'path', 'country', 'city', 'referrer')
    readonly_fields = ('created_at',)
    date_hierarchy  = 'created_at'
