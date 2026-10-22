from django.contrib import admin
from .models import AudioChapter, AudioListenHistory


@admin.register(AudioChapter)
class AudioChapterAdmin(admin.ModelAdmin):
    list_display = ['chapter', 'source', 'is_ready', 'duration_secs', 'narrator_name', 'created_at']
    list_filter  = ['source', 'is_ready']
    actions      = ['regenerate_tts']

    def regenerate_tts(self, request, queryset):
        from .tasks import generate_tts_audio
        for audio in queryset.filter(source='tts'):
            audio.is_ready = False
            audio.save(update_fields=['is_ready'])
            generate_tts_audio.delay(audio.id)
    regenerate_tts.short_description = 'Regenerate TTS audio'


# ── Ambient sounds (reader background audio) ──────────────────────────────────
from django.utils.html import format_html
from .models import AmbientSound, AmbientSoundCategory


class AmbientSoundInline(admin.TabularInline):
    model  = AmbientSound
    extra  = 1
    fields = ['title', 'icon', 'audio', 'duration_secs', 'order', 'is_active']


@admin.register(AmbientSoundCategory)
class AmbientSoundCategoryAdmin(admin.ModelAdmin):
    """Upload sounds straight into a category with the table below."""
    list_display  = ['name', 'icon', 'sound_count', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    inlines       = [AmbientSoundInline]
    actions       = ['activate', 'deactivate']

    @admin.display(description='Sounds')
    def sound_count(self, obj):
        return obj.sounds.count()

    @admin.action(description='Show in the app')
    def activate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=True)} category(ies) shown.')

    @admin.action(description='Hide from the app')
    def deactivate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} category(ies) hidden.')


@admin.register(AmbientSound)
class AmbientSoundAdmin(admin.ModelAdmin):
    list_display  = ['title', 'category', 'icon', 'preview', 'plays', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter   = ['category', 'is_active']
    search_fields = ['title', 'category__name']
    actions       = ['activate', 'deactivate']

    @admin.display(description='Listen')
    def preview(self, obj):
        if not obj.audio:
            return '—'
        return format_html('<audio controls preload="none" src="{}" style="height:28px;"></audio>', obj.audio.url)

    @admin.action(description='Show in the app')
    def activate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=True)} sound(s) shown.')

    @admin.action(description='Hide from the app')
    def deactivate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} sound(s) hidden.')
