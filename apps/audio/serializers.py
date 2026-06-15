# serializers.py
from rest_framework import serializers
from .models import AudioChapter, AudioListenHistory


class AudioChapterSerializer(serializers.ModelSerializer):
    duration_display = serializers.ReadOnlyField()

    class Meta:
        model  = AudioChapter
        fields = ['id', 'chapter', 'audio_url', 'audio_file', 'duration_secs',
                  'duration_display', 'source', 'is_ready', 'narrator_name', 'created_at']
        read_only_fields = ['is_ready', 'created_at']


class AudioListenProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AudioListenHistory
        fields = ['audio_chapter', 'progress_secs', 'completed', 'updated_at']
        read_only_fields = ['updated_at']
