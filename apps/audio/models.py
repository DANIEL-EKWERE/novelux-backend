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


# ══════════════════════════════════════════════════════════════════════════════
#  Ambient sounds — background audio readers can play while reading
#  (rain, café, fireplace…). Uploaded by admins, streamed by the app.
# ══════════════════════════════════════════════════════════════════════════════

from django.core.validators import FileExtensionValidator

AMBIENT_EXTENSIONS = ['mp3', 'm4a', 'aac', 'ogg', 'wav']
AMBIENT_MAX_MB     = 20


def _validate_ambient_size(f):
    from django.core.exceptions import ValidationError
    if f.size > AMBIENT_MAX_MB * 1024 * 1024:
        raise ValidationError(f'Sound files must be {AMBIENT_MAX_MB} MB or smaller.')


class AmbientSoundCategory(models.Model):
    name       = models.CharField(max_length=60, unique=True)
    icon       = models.CharField(max_length=8, blank=True, help_text='An emoji shown on the tab, e.g. 🌧️')
    order      = models.PositiveSmallIntegerField(default=0, help_text='Lower shows first.')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ambient_sound_categories'
        ordering = ['order', 'name']
        verbose_name = 'Ambient sound category'
        verbose_name_plural = 'Ambient sound categories'

    def __str__(self):
        return self.name


class AmbientSound(models.Model):
    category   = models.ForeignKey(AmbientSoundCategory, on_delete=models.CASCADE, related_name='sounds')
    title      = models.CharField(max_length=80)
    audio      = models.FileField(
        upload_to='ambient_sounds/',
        validators=[FileExtensionValidator(AMBIENT_EXTENSIONS), _validate_ambient_size],
        help_text=f'MP3, M4A, AAC, OGG or WAV, up to {AMBIENT_MAX_MB} MB. Loops while the reader reads, '
                  'so a seamless loop works best.')
    icon       = models.CharField(max_length=8, blank=True, help_text='Optional emoji, e.g. 🔥')
    duration_secs = models.PositiveIntegerField(default=0, blank=True,
        help_text='Optional — shown in the app.')
    order      = models.PositiveSmallIntegerField(default=0, help_text='Lower shows first.')
    is_active  = models.BooleanField(default=True)
    plays      = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ambient_sounds'
        ordering = ['order', 'title']

    def __str__(self):
        return f'{self.category} — {self.title}'
