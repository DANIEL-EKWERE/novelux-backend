# filters.py
import django_filters
from django.db.models import Q
from .models import Story


class StoryFilter(django_filters.FilterSet):
    genre    = django_filters.CharFilter(method='filter_genre')
    subgenre = django_filters.CharFilter(field_name='subgenre__slug')
    tag      = django_filters.CharFilter(field_name='tags__slug')
    language = django_filters.CharFilter(field_name='language')
    status   = django_filters.CharFilter(field_name='status')
    author   = django_filters.CharFilter(field_name='author__username')

    class Meta:
        model  = Story
        fields = ['genre', 'subgenre', 'tag', 'language', 'status', 'author', 'is_featured']

    def filter_genre(self, queryset, name, value):
        """
        Match stories that either:
        - belong directly to the genre (genre__slug = value), OR
        - have a subgenre that belongs to the genre (subgenre__genre__slug = value)
        """
        return queryset.filter(
            Q(genre__slug=value) | Q(subgenre__genre__slug=value)
        ).distinct()
