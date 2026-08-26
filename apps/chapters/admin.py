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
                      'coin_cost', 'is_published', 'views', 'unlocks', 'word_count']
    list_filter    = ['is_locked', 'is_published']
    search_fields  = ['title', 'story__title']
    readonly_fields = ['views', 'unlocks', 'word_count']


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
