from django.contrib import admin
from django.utils import timezone
from .models import CoinPackage, SubscriptionPlan, Purchase, Subscription, AuthorPayout, DailyRewardClaim, ReadingSession, ReadingSchedule, ReadingHistory


admin.site.register(DailyRewardClaim)
admin.site.register(ReadingSession)
admin.site.register(ReadingSchedule)


@admin.register(CoinPackage)
class CoinPackageAdmin(admin.ModelAdmin):
    list_display = ['label', 'coins', 'bonus_coins', 'price_usd', 'is_active']
    list_editable= ['is_active']




@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['label', 'price_usd', 'coins_per_month', 'discount_pct', 'is_active']
    list_editable= ['is_active']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display  = ['user', 'purchase_type', 'coins_granted', 'amount_paid_usd',
                     'status', 'created_at']
    list_filter   = ['purchase_type', 'status']
    search_fields = ['user__username', 'stripe_session_id']
    readonly_fields = ['user', 'purchase_type', 'coins_granted', 'amount_paid_usd',
                       'stripe_payment_id', 'stripe_session_id', 'created_at']


@admin.register(AuthorPayout)
class AuthorPayoutAdmin(admin.ModelAdmin):
    list_display  = ['author', 'amount_usd', 'status', 'payout_method', 'requested_at']
    list_filter   = ['status', 'payout_method']
    search_fields = ['author__username']
    actions       = ['mark_processed']

    def mark_processed(self, request, queryset):
        queryset.update(status='processed', processed_at=timezone.now())
    mark_processed.short_description = 'Mark payouts as processed'


@admin.register(ReadingHistory)    
class ReadingHistoryAddmin(admin.ModelAdmin):
    list_display = ['user', 'story', 'chapter_number', 'chapter_title', 'read_at']
