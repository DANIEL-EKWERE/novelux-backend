# filters.py
import django_filters
from .models import Story


class StoryFilter(django_filters.FilterSet):
    genre    = django_filters.CharFilter(field_name='genre__slug')
    tag      = django_filters.CharFilter(field_name='tags__slug')
    language = django_filters.CharFilter(field_name='language')
    status   = django_filters.CharFilter(field_name='status')
    author   = django_filters.CharFilter(field_name='author__username')

    class Meta:
        model  = Story
        fields = ['genre', 'tag', 'language', 'status', 'author', 'is_featured']
