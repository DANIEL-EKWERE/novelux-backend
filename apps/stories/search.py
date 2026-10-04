"""Ranked story search.

DRF's SearchFilter matches each *word* against any field and doesn't rank, so
"alpha's bride" returned every story whose synopsis happened to contain
"alpha" and "bride", in date order. This filter only matches on meaningful
signals and orders by how good the match is:

    book code  >  exact title  >  title prefix  >  title phrase  >
    all words in title  >  author  >  tag  >  phrase in synopsis

Ties break on popularity. Pass ?ordering=... to override the rank order.
"""
from functools import reduce
from operator import and_

from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Value, When
from rest_framework.filters import BaseFilterBackend

from .models import Tag


class RankedSearchFilter(BaseFilterBackend):
    param = 'search'

    def filter_queryset(self, request, queryset, view):
        phrase = ' '.join(request.query_params.get(self.param, '').split())
        if not phrase:
            return queryset
        words = phrase.split(' ')

        title_has_all = reduce(and_, (Q(title__icontains=w) for w in words))
        tags = Tag.objects.filter(stories=OuterRef('pk'))
        tag_exact    = Exists(tags.filter(name__iexact=phrase))
        tag_contains = Exists(tags.filter(name__icontains=phrase))
        author_exact = (Q(author__username__iexact=phrase)
                        | Q(author__author_profile__pen_name__iexact=phrase))
        author_contains = (Q(author__username__icontains=phrase)
                           | Q(author__author_profile__pen_name__icontains=phrase))
        code = Q(book_code__iexact=phrase) | Q(author__author_code__iexact=phrase)
        # The synopsis only counts as a whole phrase, and not for 1–3 letters
        synopsis = Q(description__icontains=phrase) if len(phrase) >= 4 else Q(pk__in=[])

        queryset = queryset.annotate(
            _tag_exact=tag_exact, _tag_contains=tag_contains,
        ).annotate(search_rank=Case(
            When(code,                           then=Value(1000)),
            When(title__iexact=phrase,           then=Value(900)),
            When(title__istartswith=phrase,      then=Value(700)),
            When(title__icontains=phrase,        then=Value(500)),
            When(title_has_all,                  then=Value(300)),
            When(author_exact,                   then=Value(250)),
            When(author_contains,                then=Value(150)),
            When(_tag_exact=True,                then=Value(120)),
            When(_tag_contains=True,             then=Value(80)),
            When(synopsis,                       then=Value(20)),
            default=Value(0),
            output_field=IntegerField(),
        )).filter(search_rank__gt=0)

        if request.query_params.get('ordering'):
            return queryset          # OrderingFilter already applied the client's order
        return queryset.order_by('-search_rank', '-total_views', '-created_at')
