"""/api/editorial/ce/insights/… — what the chief editor needs to oversee:
how active each senior editor is, the money their authors bring in, how
readers unlock chapters, and contracts by type.

Money: readers' coins are shown in coins and in dollars at 100 coins = $1
(the same rate VIP payouts use).
"""
from collections import defaultdict
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Max, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AuthorEditorLink
from .permissions import IsCE

COINS_PER_USD = 100
SESSION_GAP = timedelta(minutes=15)   # a pause longer than this ends a working session


def _days(request, default=30):
    try:
        return max(1, min(int(request.query_params.get('days', default)), 365))
    except ValueError:
        return default


def _usd(coins):
    return round((coins or 0) / COINS_PER_USD, 2)


def _active_minutes(stamps):
    """Working time from a sorted list of request times: back-to-back activity
    (gaps under 15 min) counts in full; each isolated burst counts 1 minute."""
    total = timedelta()
    start = prev = None
    for t in stamps:
        if prev is None or t - prev > SESSION_GAP:
            if start is not None:
                total += max(prev - start, timedelta(minutes=1))
            start = t
        prev = t
    if start is not None:
        total += max(prev - start, timedelta(minutes=1))
    return round(total.total_seconds() / 60)


# ── #3 Senior editors' activity ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCE])
def se_activity(request):
    """GET …/se-activity/?days=7 — time active, days worked and what they did."""
    from apps.analytics.models import PageVisit
    from apps.chapters.models import Chapter, ChapterUnlockEarning
    from .models import ContractApplication, SEPromotionRequest
    days = _days(request, 7)
    now = timezone.now()
    since = now - timedelta(days=days)
    ses = list(get_user_model().objects.filter(role='se', is_active=True).order_by('username'))
    ids = [s.pk for s in ses]

    stamps = defaultdict(list)
    for uid, t in (PageVisit.objects.filter(user_id__in=ids, created_at__gte=since)
                   .order_by('user_id', 'created_at').values_list('user_id', 'created_at')):
        stamps[uid].append(t)
    last_seen = dict(PageVisit.objects.filter(user_id__in=ids).values('user_id')
                     .annotate(t=Max('created_at')).values_list('user_id', 't'))

    def per(qs, field):
        return dict(qs.values(field).annotate(n=Count('id')).values_list(field, 'n'))
    reviewed = per(Chapter.objects.filter(reviewed_by_se_id__in=ids, reviewed_at__gte=since), 'reviewed_by_se_id')
    contract_reviews = per(ContractApplication.objects.filter(assigned_se_id__in=ids, se_reviewed_at__gte=since),
                           'assigned_se_id')
    contracts_sent = per(ContractApplication.objects.filter(ce_signed_by_id__in=ids, contract_sent_at__gte=since),
                         'ce_signed_by_id')
    released = per(ChapterUnlockEarning.objects.filter(released_by_id__in=ids, released_at__gte=since), 'released_by_id')
    promo = per(SEPromotionRequest.objects.filter(se_id__in=ids, created_at__gte=since), 'se_id')
    authors = per(AuthorEditorLink.objects.filter(assigned_se_id__in=ids), 'assigned_se_id')
    waiting = per(ContractApplication.objects.filter(assigned_se_id__in=ids, status__in=['pending', 'se_reviewing']),
                  'assigned_se_id')

    rows = []
    for se in ses:
        st = stamps.get(se.pk, [])
        by_day = defaultdict(list)
        for t in st:
            by_day[timezone.localtime(t).date()].append(t)
        daily = []
        for i in range(min(days, 31) - 1, -1, -1):
            d = (timezone.localtime(now) - timedelta(days=i)).date()
            daily.append({'date': d.isoformat(), 'minutes': _active_minutes(by_day.get(d, []))})
        minutes = sum(_active_minutes(v) for v in by_day.values())
        actions = (reviewed.get(se.pk, 0) + contract_reviews.get(se.pk, 0) + contracts_sent.get(se.pk, 0)
                   + released.get(se.pk, 0) + promo.get(se.pk, 0))
        seen = last_seen.get(se.pk)
        rows.append({
            'id': se.pk, 'username': se.username, 'name': se.get_full_name() or se.username,
            'active_minutes': minutes, 'active_days': len(by_day), 'avg_minutes_per_active_day':
                round(minutes / len(by_day)) if by_day else 0,
            'last_seen': seen.isoformat() if seen else None,
            'idle_days': (now - seen).days if seen else None,
            'chapters_reviewed': reviewed.get(se.pk, 0), 'contract_reviews': contract_reviews.get(se.pk, 0),
            'contracts_sent': contracts_sent.get(se.pk, 0), 'earnings_released': released.get(se.pk, 0),
            'promotion_requests': promo.get(se.pk, 0), 'actions': actions,
            'authors': authors.get(se.pk, 0), 'waiting_reviews': waiting.get(se.pk, 0),
            'daily': daily,
        })
    rows.sort(key=lambda r: -r['active_minutes'])
    return Response({'days': days, 'results': rows})


# ── #6 Money from each SE's authors ───────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCE])
def se_revenue(request):
    """GET …/se-revenue/?days=30 — what readers spent on each SE's authors and
    who earns the most."""
    from apps.chapters.models import ChapterUnlock, ChapterUnlockEarning, VipChapterRead, VipEarning
    from apps.tips.models import Tip
    days = _days(request)
    since = timezone.now() - timedelta(days=days)
    User = get_user_model()
    links = dict(AuthorEditorLink.objects.filter(assigned_se__isnull=False).values_list('author_id', 'assigned_se_id'))

    spend = defaultdict(lambda: {'unlocks': 0, 'coins': 0, 'bonus': 0, 'paid_known': 0})
    for aid, n, coins, bonus, paid_known in (
            ChapterUnlock.objects.filter(created_at__gte=since, coins_spent__gt=0)
            .values('chapter__story__author_id')
            .annotate(n=Count('id'), coins=Sum('coins_spent'), bonus=Sum('bonus_spent'),
                      paid_known=Sum('coins_spent', filter=Q(bonus_spent__isnull=False)))
            .values_list('chapter__story__author_id', 'n', 'coins', 'bonus', 'paid_known')):
        spend[aid] = {'unlocks': n, 'coins': coins or 0, 'bonus': bonus or 0, 'paid_known': paid_known or 0}
    tips = dict(Tip.objects.filter(created_at__gte=since).values('recipient_id')
                .annotate(c=Sum('coins_amount')).values_list('recipient_id', 'c'))
    vip_reads = dict(VipChapterRead.objects.filter(created_at__gte=since).values('author_id')
                     .annotate(n=Count('id')).values_list('author_id', 'n'))
    earned = defaultdict(int)   # the author's own share, in coins
    for aid, c in (ChapterUnlockEarning.objects.filter(created_at__gte=since).exclude(status='rejected')
                   .values('author_id').annotate(c=Sum('coins')).values_list('author_id', 'c')):
        earned[aid] += c or 0
    for aid, c in (Tip.objects.filter(created_at__gte=since).values('recipient_id')
                   .annotate(c=Sum('author_coins_earned')).values_list('recipient_id', 'c')):
        earned[aid] += c or 0
    for aid, c in (VipEarning.objects.filter(run__created_at__gte=since).exclude(status='rejected')
                   .values('author_id').annotate(c=Sum('coins')).values_list('author_id', 'c')):
        earned[aid] += c or 0

    author_ids = set(spend) | set(tips) | set(vip_reads) | set(earned)
    names = dict(User.objects.filter(pk__in=author_ids).values_list('pk', 'username'))

    def author_row(aid):
        sp = spend.get(aid, {'unlocks': 0, 'coins': 0, 'bonus': 0, 'paid_known': 0})
        reader_coins = sp['coins'] + (tips.get(aid) or 0)
        return {'id': aid, 'username': names.get(aid, '?'), 'unlocks': sp['unlocks'],
                'unlock_coins': sp['coins'], 'bonus_coins': sp['bonus'],
                'paid_coins': max(sp['paid_known'] - sp['bonus'], 0),
                'tips_coins': tips.get(aid) or 0, 'vip_reads': vip_reads.get(aid, 0),
                'reader_coins': reader_coins, 'reader_usd': _usd(reader_coins),
                'author_earned_coins': earned.get(aid, 0), 'author_earned_usd': _usd(earned.get(aid, 0))}

    per_se = defaultdict(list)
    for aid in author_ids:
        per_se[links.get(aid)].append(author_row(aid))
    ses = {s.pk: s for s in User.objects.filter(role='se')}
    out = []
    for se_id, rows in per_se.items():
        rows.sort(key=lambda r: -r['reader_coins'])
        tot = {k: sum(r[k] for r in rows) for k in ('unlocks', 'unlock_coins', 'paid_coins', 'bonus_coins',
                                                    'tips_coins', 'vip_reads', 'reader_coins', 'author_earned_coins')}
        se = ses.get(se_id)
        out.append({'se_id': se_id, 'se': (se.get_full_name() or se.username) if se else 'No editor',
                    'se_active': bool(se and se.is_active), 'authors_earning': len(rows), **tot,
                    'reader_usd': _usd(tot['reader_coins']), 'author_earned_usd': _usd(tot['author_earned_coins']),
                    'top_authors': rows[:5]})
    out.sort(key=lambda r: -r['reader_coins'])
    top = sorted((author_row(a) for a in author_ids), key=lambda r: -r['author_earned_coins'])[:10]
    for r in top:
        se = ses.get(links.get(r['id']))
        r['se'] = (se.get_full_name() or se.username) if se else 'No editor'
    return Response({'days': days, 'coins_per_usd': COINS_PER_USD, 'by_se': out, 'top_authors': top})


# ── #13 How readers unlock chapters ───────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCE])
def unlock_methods(request):
    """GET …/unlocks/?days=30"""
    from apps.chapters.models import ChapterAdAccess, ChapterUnlock, VipChapterRead
    days = _days(request)
    since = timezone.now() - timedelta(days=days)
    u = ChapterUnlock.objects.filter(created_at__gte=since)
    paid_only = u.filter(coins_spent__gt=0, bonus_spent=0).exclude(method='download')
    bonus_only = u.filter(coins_spent__gt=0, bonus_spent__isnull=False).filter(bonus_spent=F('coins_spent'))
    mixed = u.filter(coins_spent__gt=0, bonus_spent__gt=0).exclude(bonus_spent=F('coins_spent'))
    old = u.filter(coins_spent__gt=0, bonus_spent__isnull=True)
    methods = [
        {'key': 'paid', 'label': 'Purchased coins', 'count': paid_only.count()},
        {'key': 'bonus', 'label': 'Bonus coins', 'count': bonus_only.count()},
        {'key': 'mixed', 'label': 'Bonus + purchased coins', 'count': mixed.count()},
        {'key': 'coins_unsplit', 'label': 'Coins (before the split was recorded)', 'count': old.count()},
        {'key': 'download', 'label': 'Bought the whole book', 'count': u.filter(method='download').count()},
        {'key': 'vip', 'label': 'VIP (included)', 'count': VipChapterRead.objects.filter(created_at__gte=since).count()},
        {'key': 'ads', 'label': 'Watched an ad', 'count': ChapterAdAccess.objects.filter(created_at__gte=since).count()},
        {'key': 'free_daily', 'label': 'Daily free chapter', 'count': u.filter(coins_spent=0).count()},
    ]
    total = sum(m['count'] for m in methods)
    for m in methods:
        m['pct'] = round(m['count'] / total * 100, 1) if total else 0
    coins = u.aggregate(all=Sum('coins_spent'), bonus=Sum('bonus_spent'),
                        known=Sum('coins_spent', filter=Q(bonus_spent__isnull=False)))
    bonus_c = coins['bonus'] or 0
    paid_c = max((coins['known'] or 0) - bonus_c, 0)

    # Day by day
    series = defaultdict(lambda: defaultdict(int))

    def add(qs, key, field='created_at'):
        for d, n in (qs.extra(select={'d': f'date({field})'}).values('d').annotate(n=Count('id')).values_list('d', 'n')):
            series[str(d)][key] += n
    add(u.filter(coins_spent__gt=0), 'coins')
    add(u.filter(coins_spent=0), 'free_daily')
    add(VipChapterRead.objects.filter(created_at__gte=since), 'vip')
    add(ChapterAdAccess.objects.filter(created_at__gte=since), 'ads')
    daily = [{'date': d, **v} for d, v in sorted(series.items())]

    top = (u.values('chapter__story__title', 'chapter__story__slug').annotate(n=Count('id'), coins=Sum('coins_spent'))
           .order_by('-n')[:10])
    return Response({
        'days': days, 'total': total, 'methods': methods,
        'coins': {'total': coins['all'] or 0, 'paid': paid_c, 'bonus': bonus_c,
                  'unsplit': (coins['all'] or 0) - (coins['known'] or 0), 'paid_usd': _usd(paid_c)},
        'daily': daily,
        'top_books': [{'title': t['chapter__story__title'], 'slug': t['chapter__story__slug'],
                       'unlocks': t['n'], 'coins': t['coins'] or 0} for t in top],
    })


# ── #14 Contracts by type ─────────────────────────────────────────────────────

CONTRACT_TYPES = [('exclusive', 'Exclusive'), ('non_exclusive', 'Non-exclusive'), ('buyout', 'Buyout')]
CONTRACT_STAGES = [('signed', 'Signed'), ('contract_sent', 'Sent — awaiting signature'),
                   ('review', 'In review'), ('rejected', 'Rejected')]


@api_view(['GET'])
@permission_classes([IsCE])
def contract_types(request):
    """GET …/contracts/ — books by contract type and stage, overall and per SE."""
    from .models import ContractApplication
    stage = {'signed': 'signed', 'contract_sent': 'contract_sent', 'rejected': 'rejected'}
    grid = {t: {s: 0 for s, _ in CONTRACT_STAGES} for t, _ in CONTRACT_TYPES}
    per_se = defaultdict(lambda: {t: 0 for t, _ in CONTRACT_TYPES})
    names = {}
    for ctype, status, se_id, se_name in ContractApplication.objects.values_list(
            'contract_type', 'status', 'assigned_se_id', 'assigned_se__username'):
        t = ctype if ctype in grid else 'non_exclusive'
        grid[t][stage.get(status, 'review')] += 1
        if status == 'signed':
            per_se[se_id][t] += 1
            names[se_id] = se_name or 'No editor'
    return Response({
        'types': [{'key': t, 'label': l, **grid[t], 'total': sum(grid[t].values())} for t, l in CONTRACT_TYPES],
        'stages': [{'key': s, 'label': l} for s, l in CONTRACT_STAGES],
        'signed_by_se': [{'se': names[k], **v} for k, v in per_se.items()],
        'note': 'HuxNovel currently offers non-exclusive contracts; buyout is not offered yet.',
    })
