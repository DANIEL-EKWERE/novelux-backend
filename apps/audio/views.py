# views.py
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import AudioChapter, AudioListenHistory
from .serializers import AudioChapterSerializer, AudioListenProgressSerializer
from apps.chapters.models import Chapter
from apps.stories.models import Story
from .tasks import generate_tts_audio


class ChapterAudioView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, story_slug, chapter_number):
        chapter = get_object_or_404(
            Chapter, story__slug=story_slug, chapter_number=chapter_number
        )
        try:
            audio = chapter.audio
            serializer = AudioChapterSerializer(audio)
            return Response(serializer.data)
        except AudioChapter.DoesNotExist:
            return Response({'detail': 'No audio for this chapter.'}, status=404)

    def post(self, request, story_slug, chapter_number):
        """Author requests TTS generation or uploads audio."""
        story   = get_object_or_404(Story, slug=story_slug)
        chapter = get_object_or_404(Chapter, story=story, chapter_number=chapter_number)

        if story.author != request.user:
            return Response({'detail': 'Only the author can manage audio.'}, status=403)

        source = request.data.get('source', 'tts')
        audio, created = AudioChapter.objects.get_or_create(chapter=chapter, defaults={'source': source})

        if source == 'tts':
            audio.source   = 'tts'
            audio.is_ready = False
            audio.save()
            generate_tts_audio.delay(audio.id)
            return Response({'detail': 'TTS generation queued.'}, status=202)

        elif source == 'upload':
            if 'audio_file' not in request.FILES:
                return Response({'detail': 'audio_file required.'}, status=400)
            audio.source     = 'upload'
            audio.audio_file = request.FILES['audio_file']
            audio.narrator_name = request.data.get('narrator_name', '')
            audio.is_ready   = True
            audio.save()
            return Response(AudioChapterSerializer(audio).data, status=201)

        return Response({'detail': 'Invalid source.'}, status=400)


class UpdateAudioProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, audio_chapter_id):
        audio   = get_object_or_404(AudioChapter, pk=audio_chapter_id)
        progress, _ = AudioListenHistory.objects.get_or_create(
            user=request.user, audio_chapter=audio
        )
        progress.progress_secs = request.data.get('progress_secs', progress.progress_secs)
        progress.completed     = request.data.get('completed', progress.completed)
        progress.save()
        return Response({'detail': 'Progress saved.'})


# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('<slug:story_slug>/chapters/<int:chapter_number>/audio/',
         views.ChapterAudioView.as_view()),
    path('progress/<int:audio_chapter_id>/',
         views.UpdateAudioProgressView.as_view()),
]


# ── Ambient sounds ────────────────────────────────────────────────────────────

class AmbientSoundLibraryView(APIView):
    """GET /api/audio/ambient/ — active categories with their active sounds.
    The app calls this only when the sound library is opened."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db.models import Prefetch
        from .models import AmbientSound, AmbientSoundCategory
        cats = (AmbientSoundCategory.objects.filter(is_active=True)
                .prefetch_related(Prefetch('sounds', queryset=AmbientSound.objects.filter(is_active=True))))
        data = []
        for c in cats:
            sounds = [{
                'id':            s.pk,
                'title':         s.title,
                'icon':          s.icon,
                'url':           request.build_absolute_uri(s.audio.url) if s.audio else None,
                'duration_secs': s.duration_secs,
            } for s in c.sounds.all() if s.audio]
            if sounds:
                data.append({'id': c.pk, 'name': c.name, 'icon': c.icon, 'sounds': sounds})
        return Response({'categories': data})


class AmbientSoundPlayView(APIView):
    """POST /api/audio/ambient/<id>/play/ — counts a play (for the admin list)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        from django.db.models import F
        from .models import AmbientSound
        AmbientSound.objects.filter(pk=pk, is_active=True).update(plays=F('plays') + 1)
        return Response({'ok': True})
