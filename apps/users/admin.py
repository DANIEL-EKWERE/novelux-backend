# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AuthorProfile, Follow, CoinTransaction, FCMDevice, UserPreferences, AuthorKYC


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['username', 'email', 'role', 'coin_balance', 'is_vip', 'reading_level', 'date_joined']
    list_filter   = ['role', 'is_vip', 'is_active']
    search_fields = ['username', 'email']
    fieldsets     = BaseUserAdmin.fieldsets + (
        ('Platform Info', {'fields': ('role', 'avatar', 'bio', 'coin_balance', 'is_vip',
                                      'vip_expires','editor_code', 'reading_xp', 'reading_level',
                                      'preferred_genres', 'preferred_language')}),
    )

# admin.site.register(Follow)    
@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display  = ['follower', 'following']
    list_filter   = ['follower', 'following']
    search_fields = ['follower__username', 'following__username']

# # @admin.register(FCMDevice)
# class UserAdmin(BaseUserAdmin):
    # list_display  = ['user']
    # list_filter   = ['user']
    # search_fields = ['user']
    # fieldsets     = BaseUserAdmin.fieldsets + (
    #     ('Platform Info', {'fields': ('role', 'avatar', 'bio', 'coin_balance', 'is_vip',
    #                                   'vip_expires', 'reading_xp', 'reading_level',
    #                                   'preferred_genres', 'preferred_language')}),
    # )    

# admin.site.register(FCMDevice)
@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display  = ['user', 'platform', 'device_model',
                     'is_active', 'updated_at']
    list_filter   = ['platform', 'is_active']
    search_fields = ['user__username', 'token', 'device_model']
    readonly_fields = ['token', 'created_at', 'updated_at']


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'pen_name', 'contract_type', 'is_verified',
                     'total_earnings', 'pending_payout']
    list_filter   = ['contract_type', 'is_verified']
    search_fields = ['user__username', 'pen_name']
    actions       = ['verify_authors']

@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display  = ['user', 'preferred_genres']
    list_filter   = ['preferred_genres']
    search_fields = ['user__username']
    # actions       = ['verify_authors']    

    # def verify_authors(self, request, queryset):
    #     queryset.update(is_verified=True)
    # verify_authors.short_description = 'Mark selected authors as verified'


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'amount', 'transaction_type', 'reason', 'created_at']
    list_filter   = ['transaction_type']
    search_fields = ['user__username', 'reason']
    readonly_fields = ['user', 'amount', 'transaction_type', 'reason', 'balance_after', 'created_at']


@admin.register(AuthorKYC)
class AuthorKYCAdmin(admin.ModelAdmin):
    list_display   = ['user', 'full_name', 'id_type', 'payment_method', 'status', 'submitted_at']
    list_filter    = ['status', 'id_type', 'payment_method']
    search_fields  = ['user__username', 'user__email', 'full_name', 'id_number']
    readonly_fields = ['submitted_at', 'id_document']
    fieldsets = (
        ('Personal', {'fields': ('user', 'full_name', 'phone', 'contact_address', 'country', 'id_type', 'id_number', 'id_document')}),
        ('Payment',  {'fields': ('payment_method', 'account_holder', 'bank_name', 'account_number', 'swift_code', 'bank_country', 'paypal_email')}),
        ('Review',   {'fields': ('status', 'admin_notes', 'submitted_at', 'reviewed_at')}),
    )

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if change and 'status' in form.changed_data:
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
