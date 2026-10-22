"""Monthly VIP payout: pays authors for VIP reads of their locked chapters.

Per VIP reader, for the month:
  payment  = the reader's VIP subscription money for the month (spread over
             each plan's length), after store fees
  pool     = payment × AUTHOR_REVENUE_SHARE
  value    = what the chapters they read would have earned the authors as
             unlocks (coin price × AUTHOR_REVENUE_SHARE, 100 coins = $1)

  value ≤ pool → authors get the full value; the rest of the pool is NOT paid
                 out but recorded on the month's statement (excess_ignored_usd)
  value > pool → the pool is split between the chapters read, pro rata

Author totals become VipEarning rows held for SE approval.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

CENT = Decimal('0.01')


def month_bounds(month: date):
    start = month.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(start, time.min), tz),
            timezone.make_aware(datetime.combine(end, time.min), tz))


def vip_revenue_by_user(month: date):
    """Gross VIP subscription money attributable to `month`, per user (USD)."""
    from apps.coins.models import Purchase
    start, end = month_bounds(month)
    revenue = defaultdict(Decimal)
    purchases = (Purchase.objects
                 .filter(purchase_type=Purchase.TYPE_SUBSCRIPTION, status=Purchase.STATUS_COMPLETED,
                         completed_at__lt=end)
                 .select_related('subscription_plan'))
    for p in purchases:
        days = max((p.subscription_plan.duration_days if p.subscription_plan else 30), 1)
        p_start = p.completed_at
        p_end = p_start + timedelta(days=days)
        overlap = (min(p_end, end) - max(p_start, start)).total_seconds()
        if overlap > 0:
            revenue[p.user_id] += Decimal(p.amount_paid_usd) * Decimal(overlap) / Decimal(days * 86400)
    return revenue


def run_vip_payout(month: date):
    """Compute and store the payout for `month`. Returns the VipPayoutRun, or
    None if that month was already run."""
    from .models import VipChapterRead, VipEarning, VipPayoutRun
    month = month.replace(day=1)
    if VipPayoutRun.objects.filter(month=month).exists():
        return None

    share   = Decimal(str(settings.AUTHOR_REVENUE_SHARE))
    net     = Decimal(1) - Decimal(str(settings.STORE_FEE_RATE))
    revenue = vip_revenue_by_user(month)

    reads = defaultdict(list)          # reader → [(author_id, value_usd)]
    for r in VipChapterRead.objects.filter(month=month).values('user_id', 'author_id', 'coin_cost'):
        reads[r['user_id']].append((r['author_id'], Decimal(r['coin_cost']) * share / 100))

    author_usd   = defaultdict(Decimal)
    author_reads = defaultdict(int)
    totals = dict(revenue=Decimal(0), pool=Decimal(0), value=Decimal(0), paid=Decimal(0),
                  excess=Decimal(0), with_excess=0, scaled=0)

    for reader in set(revenue) | set(reads):
        pool  = revenue.get(reader, Decimal(0)) * net * share
        items = reads.get(reader, [])
        value = sum((v for _, v in items), Decimal(0))
        totals['revenue'] += revenue.get(reader, Decimal(0))
        totals['pool'] += pool
        totals['value'] += value
        if value <= pool:
            factor = Decimal(1)
            if pool - value > 0:
                totals['excess'] += pool - value
                totals['with_excess'] += 1
        else:
            factor = pool / value          # read more than they paid for
            totals['scaled'] += 1
        for author_id, v in items:
            author_usd[author_id] += v * factor
            author_reads[author_id] += 1

    with transaction.atomic():
        run = VipPayoutRun.objects.create(
            month=month,
            vip_readers=len(set(revenue) | set(reads)),
            vip_revenue_usd=totals['revenue'].quantize(CENT),
            author_pool_usd=totals['pool'].quantize(CENT),
            reads_value_usd=totals['value'].quantize(CENT),
            excess_ignored_usd=totals['excess'].quantize(CENT),
            readers_with_excess=totals['with_excess'],
            readers_scaled_down=totals['scaled'],
        )
        paid = Decimal(0)
        for author_id, usd in author_usd.items():
            coins = int((usd * 100).to_integral_value(rounding=ROUND_HALF_UP))
            if coins <= 0:
                continue
            VipEarning.objects.create(run=run, author_id=author_id, reads=author_reads[author_id],
                                      usd=usd.quantize(Decimal('0.0001')), coins=coins)
            paid += usd
        run.paid_to_authors_usd = paid.quantize(CENT)
        run.save(update_fields=['paid_to_authors_usd'])
    return run


def previous_month(today=None):
    today = today or timezone.localdate()
    return (today.replace(day=1) - timedelta(days=1)).replace(day=1)
