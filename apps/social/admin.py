from django.contrib import admin

from .models import SocialAccount, SocialPost, SocialPostTarget, SocialSettings


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform', 'handle', 'is_active', 'last_checked', 'last_error')
    list_filter = ('platform', 'is_active')
    exclude = ('_secrets',)          # tokens are managed from the Social dashboard only
    readonly_fields = ('connected_by', 'connected_at', 'last_checked', 'last_error')


class TargetInline(admin.TabularInline):
    model = SocialPostTarget
    extra = 0
    readonly_fields = ('account', 'status', 'url', 'error', 'published_at')


@admin.register(SocialPost)
class SocialPostAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'author', 'status', 'scheduled_at', 'published_at')
    list_filter = ('status',)
    search_fields = ('text',)
    inlines = [TargetInline]


admin.site.register(SocialSettings)
