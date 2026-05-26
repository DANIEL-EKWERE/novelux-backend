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
