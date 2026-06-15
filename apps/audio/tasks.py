from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_tts_audio(audio_chapter_id: int):
    """
    Generate TTS audio for a chapter using a TTS service.
    Supports: Google TTS, Amazon Polly, or ElevenLabs.
    Configure TTS_PROVIDER in settings: 'google' | 'polly' | 'elevenlabs'
    """
    from django.conf import settings
    from .models import AudioChapter

    try:
        audio = AudioChapter.objects.select_related('chapter').get(pk=audio_chapter_id)
    except AudioChapter.DoesNotExist:
        logger.error(f'AudioChapter {audio_chapter_id} not found')
        return

    text     = audio.chapter.content
    provider = getattr(settings, 'TTS_PROVIDER', 'google')

    try:
        if provider == 'google':
            audio_url = _generate_google_tts(text, audio)
        elif provider == 'polly':
            audio_url = _generate_polly_tts(text, audio)
        elif provider == 'elevenlabs':
            audio_url = _generate_elevenlabs_tts(text, audio)
        else:
            raise ValueError(f'Unknown TTS provider: {provider}')

        audio.audio_url = audio_url
        audio.is_ready  = True
        audio.save(update_fields=['audio_url', 'is_ready'])
        logger.info(f'TTS generated for AudioChapter {audio_chapter_id}')

    except Exception as e:
        logger.error(f'TTS generation failed for {audio_chapter_id}: {e}')


def _generate_google_tts(text: str, audio) -> str:
    """Google Cloud Text-to-Speech."""
    from google.cloud import texttospeech
    from django.core.files.base import ContentFile
    import django.core.files.storage as fs

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text[:5000])
    voice = texttospeech.VoiceSelectionParams(
        language_code='en-US',
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    filename = f'audio/chapters/chapter_{audio.chapter_id}.mp3'
    audio.audio_file.save(filename, ContentFile(response.audio_content), save=False)
    return audio.audio_file.url


def _generate_polly_tts(text: str, audio) -> str:
    """Amazon Polly TTS."""
    import boto3
    from django.conf import settings
    from django.core.files.base import ContentFile

    polly  = boto3.client('polly', region_name=settings.AWS_S3_REGION_NAME)
    resp   = polly.synthesize_speech(
        Text=text[:3000],
        OutputFormat='mp3',
        VoiceId='Joanna',
    )
    audio_data = resp['AudioStream'].read()
    filename   = f'audio/chapters/chapter_{audio.chapter_id}.mp3'
    audio.audio_file.save(filename, ContentFile(audio_data), save=False)
    return audio.audio_file.url


def _generate_elevenlabs_tts(text: str, audio) -> str:
    """ElevenLabs TTS."""
    import requests
    from django.conf import settings
    from django.core.files.base import ContentFile

    api_key = settings.ELEVENLABS_API_KEY
    voice_id= getattr(settings, 'ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
    url     = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    headers = {'xi-api-key': api_key, 'Content-Type': 'application/json'}
    payload = {'text': text[:2500], 'model_id': 'eleven_monolingual_v1'}
    resp    = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    filename = f'audio/chapters/chapter_{audio.chapter_id}.mp3'
    audio.audio_file.save(filename, ContentFile(resp.content), save=False)
    return audio.audio_file.url
