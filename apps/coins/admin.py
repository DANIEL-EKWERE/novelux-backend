from django.contrib import admin
from django.utils import timezone
from .models import (
    CoinPackage, SubscriptionPlan, Purchase, Subscription, AuthorPayout,
    DailyRewardClaim, ReadingSession, ReadingSchedule, ReadingHistory,
    CheckinStreak, Task, UserTask, AdRewardTask,
)


admin.site.register(DailyRewardClaim)
admin.site.register(ReadingSession)
admin.site.register(ReadingSchedule)


@admin.register(CheckinStreak)
class CheckinStreakAdmin(admin.ModelAdmin):
    list_display  = ('user', 'current_streak', 'longest_streak', 'total_checkins', 'last_checkin')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('updated_at',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display  = ('title', 'task_type', 'reward_coins', 'icon', 'is_active', 'is_repeatable', 'repeat_cooldown_hours', 'expires_at', 'order')
    actions       = ['activate_tasks', 'deactivate_tasks']

    @admin.action(description='Activate selected tasks')
    def activate_tasks(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=True)} task(s) updated.')

    @admin.action(description='Deactivate selected tasks')
    def deactivate_tasks(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} task(s) updated.')
    list_editable = ('is_active', 'order', 'reward_coins')
    list_filter   = ('task_type', 'is_active', 'is_repeatable')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'created_by')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserTask)
class UserTaskAdmin(admin.ModelAdmin):
    list_display  = ('user', 'task', 'status', 'completed_at', 'claimed_at')
    list_filter   = ('status', 'task__task_type')
    search_fields = ('user__username', 'task__title')
    readonly_fields = ('completed_at', 'claimed_at')


@admin.register(CoinPackage)
class CoinPackageAdmin(admin.ModelAdmin):
    list_display = ['label', 'coins', 'bonus_coins', 'price_usd', 'is_active']
    list_editable= ['is_active']




@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display  = ['label', 'original_price_usd', 'price_usd', 'coins_per_month', 'bonus_coins', 'discount_pct', 'duration_days', 'is_active']
    list_editable = ['price_usd', 'original_price_usd', 'coins_per_month', 'bonus_coins', 'discount_pct', 'is_active']


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
    actions       = ['mark_processed', 'mark_failed']

    @admin.action(description='Mark selected payouts as failed')
    def mark_failed(self, request, queryset):
        n = queryset.update(status=AuthorPayout.STATUS_FAILED)
        self.message_user(request, f'{n} payout(s) marked failed.')

    def mark_processed(self, request, queryset):
        queryset.update(status='processed', processed_at=timezone.now())
    mark_processed.short_description = 'Mark payouts as processed'


@admin.register(ReadingHistory)    
class ReadingHistoryAddmin(admin.ModelAdmin):
    list_display = ['user', 'story', 'chapter_number', 'chapter_title', 'read_at']


@admin.register(AdRewardTask)
class AdRewardTaskAdmin(admin.ModelAdmin):
    list_display  = ('title', 'ads_required', 'reward_coins', 'order', 'is_active')
    actions       = ['activate_ad_tasks', 'deactivate_ad_tasks']

    @admin.action(description='Activate selected ad tasks')
    def activate_ad_tasks(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=True)} ad task(s) updated.')

    @admin.action(description='Deactivate selected ad tasks')
    def deactivate_ad_tasks(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} ad task(s) updated.')
    list_editable = ('ads_required', 'reward_coins', 'order', 'is_active')
