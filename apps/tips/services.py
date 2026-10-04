"""Real-money gift fulfilment.

A paid gift is a store consumable bought through RevenueCat. The app first
creates a *pending* Tip (so we know which story/chapter it is for), buys the
product, then asks us to confirm. Two channels can complete the Tip:

  • confirm_gift()          — app call, verified against RevenueCat's REST API
  • handle_gift_webhook()   — RevenueCat webhook; also the only channel that
                              carries the USD price and the purchase quantity
                              (Google Play lets a reader buy several at once),
                              so earnings and quantity are settled here.

Both are idempotent: a store transaction id can complete at most one Tip.
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from apps.notifications.services import on_tip_received
from apps.stories.models import Story
from .models import Tip, GIFTS, LABEL_BY_PRODUCT

log = logging.getLogger('revenuecat')

# A webhook with no confirmed Tip attaches to the newest pending intent for the
# same product, but only one this recent — older intents were abandoned.
INTENT_TTL = timezone.timedelta(hours=24)


def _complete(tip, transaction_id):
    """Mark a locked pending Tip paid. Caller holds the row lock."""
    tip.status = Tip.STATUS_COMPLETED
    tip.iap_transaction_id = transaction_id
    tip.save(update_fields=['status', 'iap_transaction_id', 'quantity'])
    Story.objects.filter(pk=tip.story_id).update(
        total_tips=F('total_tips') + GIFTS[tip.gift_label].points * tip.quantity
    )
    transaction.on_commit(lambda: on_tip_received(
        author=tip.recipient,
        tipper_name=tip.sender.username,
        gift_label=tip.gift_label,
        story_title=tip.story.title,
    ))


def _attach(tip, transaction_id) -> Tip:
    """Complete `tip` with `transaction_id`, unless that transaction already
    completed another Tip — then return that one instead."""
    try:
        with transaction.atomic():
            _complete(tip, transaction_id)
        return tip
    except IntegrityError:
        return Tip.objects.get(iap_transaction_id=transaction_id)


def _set_quantity(tip, quantity):
    """Apply the webhook's quantity. The app-side confirm can't see it and
    completes the Tip as 1, so top up the story's points by the difference."""
    if quantity <= tip.quantity:
        return
    if tip.status == Tip.STATUS_COMPLETED:
        Story.objects.filter(pk=tip.story_id).update(
            total_tips=F('total_tips') + GIFTS[tip.gift_label].points * (quantity - tip.quantity)
        )
    tip.quantity = quantity
    tip.save(update_fields=['quantity'])


def _credit_earnings(tip, price_usd):
    """Credit the author once, from the store price RevenueCat reports
    (the whole transaction, so it already covers the quantity)."""
    if tip.author_earned_usd is not None or price_usd is None:
        return
    price  = Decimal(str(price_usd))
    earned = (price * Decimal(1 - settings.STORE_FEE_RATE)
              * Decimal(settings.GIFT_AUTHOR_SHARE)).quantize(Decimal('0.01'))  # payout ledger is cents
    tip.amount_usd = price
    tip.author_earned_usd = earned
    tip.save(update_fields=['amount_usd', 'author_earned_usd'])

    profile = getattr(tip.recipient, 'author_profile', None)
    if profile is not None:
        type(profile).objects.filter(pk=profile.pk).update(
            pending_payout=F('pending_payout') + earned,
            total_earnings=F('total_earnings') + earned,
        )


def find_rc_transactions(subscriber, product_id):
    """Store transaction ids RevenueCat has for this consumable, oldest first."""
    for pid, txs in (subscriber or {}).get('non_subscriptions', {}).items():
        if pid.split(':')[0] == product_id:
            txs = sorted(txs, key=lambda t: t.get('purchase_date') or '')
            return [t.get('store_transaction_id') or t.get('id') for t in txs
                    if t.get('store_transaction_id') or t.get('id')]
    return []


def confirm_gift(tip_id, user, subscriber):
    """App-side confirmation. Returns the Tip (completed or still pending)."""
    with transaction.atomic():
        tip = (Tip.objects.select_for_update()
               .select_related('sender', 'recipient', 'story')
               .get(pk=tip_id, sender=user))
        if tip.status != Tip.STATUS_PENDING:
            return tip

        product_id = GIFTS[tip.gift_label].product_id
        candidates = find_rc_transactions(subscriber, product_id)
        used = set(Tip.objects.filter(iap_transaction_id__in=candidates)
                   .values_list('iap_transaction_id', flat=True))
        fresh = [tx for tx in candidates if tx not in used]
        if not fresh:
            return tip   # RevenueCat hasn't seen it yet — the webhook will finish it
        return _attach(tip, fresh[-1])


def handle_gift_webhook(user, product_id, transaction_id, price_usd, quantity=1):
    """NON_RENEWING_PURCHASE for a gift product."""
    label = LABEL_BY_PRODUCT[product_id]
    with transaction.atomic():
        tip = (Tip.objects.select_for_update()
               .select_related('sender', 'recipient', 'story')
               .filter(iap_transaction_id=transaction_id).first())
        if tip is None:
            tip = (Tip.objects.select_for_update()
                   .select_related('sender', 'recipient', 'story')
                   .filter(sender=user, gift_label=label, status=Tip.STATUS_PENDING,
                           created_at__gte=timezone.now() - INTENT_TTL)
                   .order_by('-created_at').first())
            if tip is None:
                log.error('Gift purchase %s (%s) by user %s has no pending intent',
                          transaction_id, product_id, user.pk)
                return None
            tip.quantity = max(int(quantity or 1), 1)
            tip = _attach(tip, transaction_id)
        _set_quantity(tip, max(int(quantity or 1), 1))
        _credit_earnings(tip, price_usd)
        return tip


def refund_gift(transaction_id):
    """Store refund — pull the gift from the ranking and claw back earnings."""
    with transaction.atomic():
        tip = (Tip.objects.select_for_update().select_related('recipient')
               .filter(iap_transaction_id=transaction_id).first())
        if tip is None or tip.status == Tip.STATUS_REFUNDED:
            return
        tip.status = Tip.STATUS_REFUNDED
        tip.save(update_fields=['status'])
        Story.objects.filter(pk=tip.story_id).update(
            total_tips=Greatest(F('total_tips') - GIFTS[tip.gift_label].points * tip.quantity, 0)
        )
        profile = getattr(tip.recipient, 'author_profile', None)
        if tip.author_earned_usd and profile is not None:
            type(profile).objects.filter(pk=profile.pk).update(
                pending_payout=F('pending_payout') - tip.author_earned_usd,
                total_earnings=F('total_earnings') - tip.author_earned_usd,
            )
