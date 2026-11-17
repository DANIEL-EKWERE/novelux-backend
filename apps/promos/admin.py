from django.contrib import admin

from .models import InAppPromo, PromoView


@admin.register(InAppPromo)
class InAppPromoAdmin(admin.ModelAdmin):
    list_display  = ('story', 'kind', 'is_active', 'starts_at', 'ends_at', 'priority', 'impressions', 'clicks', 'created_by')
    list_filter   = ('kind', 'is_active')
    search_fields = ('story__title', 'name', 'tagline')
    raw_id_fields = ('story', 'created_by')
    readonly_fields = ('impressions', 'clicks', 'created_at')


@admin.register(PromoView)
class PromoViewAdmin(admin.ModelAdmin):
    list_display  = ('promo', 'user', 'seen_at', 'clicked_at')
    raw_id_fields = ('promo', 'user')
