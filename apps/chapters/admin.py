"""
fromm django.contrib import admin
from .models import Chapter, ChapterUnlock


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display  = ['story', 'chapter_number', 'title', 'is_locked',
                     'coin_cost', 'is_published', 'views', 'unlocks', 'word_count']
    list_filter   = ['is_locked', 'is_published']
    search_fields = ['title', 'story__title']
    readonly_fields = ['views', 'unlocks', 'word_count']


@admin.register(ChapterUnlock)
class ChapterUnlockAdmin(admin.ModelAdmin):
    list_display  = ['user', 'chapter', 'coins_spent', 'created_at']
    search_fields = ['user__username', 'chapter__title']
    readonly_fields = ['user', 'chapter', 'coins_spent', 'created_at']

"""

from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget
from .models import Chapter, ChapterUnlock


class ChapterAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Chapter
        fields = '__all__'


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    form = ChapterAdminForm  # ← add this
    list_display   = ['story', 'chapter_number', 'title', 'is_locked',
                      'coin_cost', 'is_published', 'status', 'views', 'unlocks', 'word_count']
    list_filter    = ['is_locked', 'is_published', 'status']
    search_fields  = ['title', 'story__title']
    readonly_fields = ['views', 'unlocks', 'word_count']
    actions = ['lock_chapters', 'unlock_chapters', 'publish_chapters', 'unpublish_chapters',
               'make_free', 'set_default_price', 'reapply_story_lock']

    # Bulk actions use .update() (fast, no per-chapter side effects).
    @admin.action(description='Lock selected chapters')
    def lock_chapters(self, request, queryset):
        n = queryset.update(is_locked=True)
        self.message_user(request, f'Locked {n} chapter(s). Stories with "lock from chapter N" set '
                                   f'keep following that rule when a chapter is next saved.')

    @admin.action(description='Unlock selected chapters')
    def unlock_chapters(self, request, queryset):
        n = queryset.update(is_locked=False)
        self.message_user(request, f'Unlocked {n} chapter(s). Stories with "lock from chapter N" set '
                                   f'keep following that rule when a chapter is next saved.')

    @admin.action(description='Publish selected chapters')
    def publish_chapters(self, request, queryset):
        n = queryset.update(is_published=True, status=Chapter.STATUS_PUBLISHED)
        self.message_user(request, f'Published {n} chapter(s). (No follower notifications are sent '
                                   f'for admin bulk publishing.)')

    @admin.action(description='Unpublish selected chapters (back to draft)')
    def unpublish_chapters(self, request, queryset):
        n = queryset.update(is_published=False, status=Chapter.STATUS_DRAFT)
        self.message_user(request, f'Unpublished {n} chapter(s).')

    @admin.action(description='Make free (0 coins)')
    def make_free(self, request, queryset):
        n = queryset.update(coin_cost=0)
        self.message_user(request, f'{n} chapter(s) now cost 0 coins.')

    @admin.action(description='Set default price (20 coins)')
    def set_default_price(self, request, queryset):
        n = queryset.update(coin_cost=20)
        self.message_user(request, f'{n} chapter(s) now cost 20 coins.')

    @admin.action(description="Re-apply each story's lock rule")
    def reapply_story_lock(self, request, queryset):
        from apps.stories.models import Story
        from .models import apply_lock_from_chapter
        stories = Story.objects.filter(pk__in=queryset.values('story_id'), lock_from_chapter__isnull=False)
        for story in stories:
            apply_lock_from_chapter(story)
        self.message_user(request, f'Re-applied "lock from chapter N" for {stories.count()} story(ies). '
                                   f'Stories without a lock setting were left as they are.')


@admin.register(ChapterUnlock)
class ChapterUnlockAdmin(admin.ModelAdmin):
    list_display   = ['user', 'chapter', 'coins_spent', 'created_at']
    search_fields  = ['user__username', 'chapter__title']
    readonly_fields = ['user', 'chapter', 'coins_spent', 'created_at']


from .models import ChapterEditRequest

@admin.register(ChapterEditRequest)
class ChapterEditRequestAdmin(admin.ModelAdmin):
    list_display    = ['chapter', 'author', 'status', 'reviewed_by', 'submitted_at', 'reviewed_at']
    list_filter     = ['status']
    search_fields   = ['author__username', 'chapter__title', 'chapter__story__title']
    readonly_fields = ['submitted_at', 'reviewed_at', 'author', 'chapter', 'pending_content']
    raw_id_fields   = ['reviewed_by']


from .models import ChapterUnlockEarning, ChapterAdAccess


@admin.register(ChapterUnlockEarning)
class ChapterUnlockEarningAdmin(admin.ModelAdmin):
    """Editorial queue for unlock revenue.

    Coins reach the author only through the Release action below — nothing is
    credited when the reader unlocks the chapter.
    """
    list_display    = ['author', 'chapter', 'coins', 'coins_spent', 'status',
                       'released_by', 'released_at', 'created_at']
    list_filter     = ['status', 'created_at']
    search_fields   = ['author__username', 'chapter__title', 'chapter__story__title']
    readonly_fields = ['author', 'chapter', 'unlock', 'coins', 'coins_spent',
                       'status', 'released_by', 'released_at', 'created_at']
    raw_id_fields   = ['author', 'chapter', 'unlock']
    actions         = ['release_earnings', 'reject_earnings']

    @admin.action(description='Release to author (credits coins)')
    def release_earnings(self, request, queryset):
        released = sum(
            1 for e in queryset.filter(status=ChapterUnlockEarning.STATUS_HELD)
            if e.release(by=request.user)
        )
        skipped = queryset.count() - released
        self.message_user(
            request,
            f'{released} earning(s) released.'
            + (f' {skipped} skipped (already resolved).' if skipped else '')
        )

    @admin.action(description='Reject (resolve without paying)')
    def reject_earnings(self, request, queryset):
        rejected = sum(
            1 for e in queryset.filter(status=ChapterUnlockEarning.STATUS_HELD)
            if e.reject(by=request.user)
        )
        self.message_user(request, f'{rejected} earning(s) rejected.')


@admin.register(ChapterAdAccess)
class ChapterAdAccessAdmin(admin.ModelAdmin):
    list_display    = ['user', 'chapter', 'created_at']
    list_filter     = ['created_at']
    search_fields   = ['user__username', 'chapter__title', 'chapter__story__title']
    readonly_fields = ['user', 'chapter', 'created_at']
    raw_id_fields   = ['user', 'chapter']


from .models import VipPayoutRun, VipEarning, VipChapterRead


class VipEarningInline(admin.TabularInline):
    model           = VipEarning
    extra           = 0
    can_delete      = False
    fields          = ['author', 'reads', 'usd', 'coins', 'status', 'released_by', 'released_at']
    readonly_fields = fields


@admin.register(VipPayoutRun)
class VipPayoutRunAdmin(admin.ModelAdmin):
    """Monthly VIP statement. "Excess not paid" is VIP money a reader's reads
    didn't use up — recorded, never paid out."""
    list_display    = ['month', 'vip_readers', 'vip_revenue_usd', 'author_pool_usd', 'reads_value_usd',
                       'paid_to_authors_usd', 'excess_ignored_usd', 'readers_with_excess',
                       'readers_scaled_down', 'created_at']
    readonly_fields = list_display
    inlines         = [VipEarningInline]

    def has_add_permission(self, request):
        return False    # created by the monthly job / run_vip_payouts command


@admin.register(VipEarning)
class VipEarningAdmin(admin.ModelAdmin):
    list_display    = ['author', 'run', 'reads', 'usd', 'coins', 'status', 'released_by', 'released_at']
    list_filter     = ['status', 'run']
    search_fields   = ['author__username']
    readonly_fields = ['run', 'author', 'reads', 'usd', 'coins', 'status', 'released_by', 'released_at']
    actions         = ['release_earnings', 'reject_earnings']

    def has_add_permission(self, request):
        return False

    @admin.action(description='Release to author (credits coins)')
    def release_earnings(self, request, queryset):
        n = sum(1 for e in queryset.filter(status=VipEarning.STATUS_HELD) if e.release(by=request.user))
        self.message_user(request, f'{n} VIP earning(s) released.')

    @admin.action(description='Reject (resolve without paying)')
    def reject_earnings(self, request, queryset):
        n = sum(1 for e in queryset.filter(status=VipEarning.STATUS_HELD) if e.reject(by=request.user))
        self.message_user(request, f'{n} VIP earning(s) rejected.')


@admin.register(VipChapterRead)
class VipChapterReadAdmin(admin.ModelAdmin):
    list_display    = ['user', 'chapter', 'author', 'coin_cost', 'month', 'created_at']
    list_filter     = ['month']
    search_fields   = ['user__username', 'author__username', 'chapter__story__title']
    raw_id_fields   = ['user', 'chapter', 'author']
    readonly_fields = ['user', 'chapter', 'author', 'coin_cost', 'month', 'created_at']
