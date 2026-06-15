from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AudioChapter(models.Model):
    SOURCE_TTS    = 'tts'
    SOURCE_UPLOAD = 'upload'
    SOURCE_CHOICES= [(SOURCE_TTS, 'Text-to-Speech'), (SOURCE_UPLOAD, 'Author Upload')]

    chapter       = models.OneToOneField('chapters.Chapter', on_delete=models.CASCADE,
                                          related_name='audio')
    audio_file    = models.FileField(upload_to='audio/chapters/', blank=True, null=True)
    audio_url     = models.URLField(blank=True)
    duration_secs = models.PositiveIntegerField(default=0)
    source        = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_TTS)
    is_ready      = models.BooleanField(default=False)
    narrator_name = models.CharField(max_length=100, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'audio_chapters'

    def __str__(self):
        return f'Audio: {self.chapter}'

    @property
    def duration_display(self):
        m, s = divmod(self.duration_secs, 60)
        return f'{m}:{s:02d}'


class AudioListenHistory(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE)
    audio_chapter   = models.ForeignKey(AudioChapter, on_delete=models.CASCADE)
    progress_secs   = models.PositiveIntegerField(default=0)
    completed       = models.BooleanField(default=False)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table      = 'audio_listen_history'
        unique_together = ('user', 'audio_chapter')
