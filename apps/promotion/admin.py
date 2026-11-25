from django.contrib import admin

from .models import Placement, Shelf


@admin.register(Shelf)
class ShelfAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'key', 'capacity', 'is_active')
    list_editable = ('capacity', 'is_active')


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ('story', 'shelf', 'position', 'starts_at', 'ends_at', 'paused', 'cancelled', 'source')
    list_filter = ('shelf', 'source', 'paused', 'cancelled')
    raw_id_fields = ('story', 'request', 'created_by')
