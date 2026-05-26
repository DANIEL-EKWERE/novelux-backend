from django.contrib import admin
from .models import Tip


@admin.register(Tip)
class TipAdmin(admin.ModelAdmin):
    list_display  = ['sender', 'recipient', 'story', 'coins_amount', 'message', 'created_at']
    search_fields = ['sender__username', 'recipient__username', 'story__title']
    readonly_fields = ['sender', 'recipient', 'story', 'chapter', 'coins_amount', 'created_at']
