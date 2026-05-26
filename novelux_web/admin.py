from django.contrib import admin
from django.utils.html import format_html
from .models import APKRelease
 
 
@admin.register(APKRelease)
class APKReleaseAdmin(admin.ModelAdmin):
    list_display  = ('version_name', 'version_code', 'size_mb', 'is_active',
                     'download_count', 'uploaded_at', 'apk_link')
    list_filter   = ('is_active',)
    readonly_fields = ('download_count', 'size_mb', 'uploaded_at', 'updated_at')
    fieldsets = (
        ('Release Info', {
            'fields': ('version_name', 'version_code', 'min_android', 'is_active')
        }),
        ('File', {
            'fields': ('apk_file', 'size_mb')
        }),
        ('Release Notes', {
            'fields': ('release_notes',)
        }),
        ('Stats', {
            'fields': ('download_count', 'uploaded_at', 'updated_at'),
        }),
    )
 
    def apk_link(self, obj):
        if obj.apk_file:
            return format_html('<a href="{}" target="_blank">Download</a>',
                               obj.apk_file.url)
        return '—'
    apk_link.short_description = 'APK'
 
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Confirm to admin which release is now active
        if obj.is_active:
            self.message_user(request,
                f'v{obj.version_name} is now the active release. '
                f'All other releases deactivated.')