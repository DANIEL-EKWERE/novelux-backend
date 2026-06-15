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
