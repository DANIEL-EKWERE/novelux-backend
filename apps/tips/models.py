# models.py
from collections import namedtuple

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Gift catalogue — must match `_gifts` in the app's reading_interface.dart.
#   coins      legacy coin price (builds before real-money gifts still send these)
#   points     ranking points — ₦10 of gift = 1 point
#   product_id store consumable (Play Console / App Store Connect / RevenueCat)
#   price_ngn  store price, for display/records only — the store is authoritative
# A Flower is free (ad-gated in the app) and counts on the Flowers board.
Gift = namedtuple('Gift', 'coins points product_id price_ngn')
GIFTS = {
    'Flower':     Gift(0,    0,    None,                     0),
    'Like':       Gift(10,   20,   'novelux_gift_like',      200),
    'Ice pop':    Gift(50,   200,  'novelux_gift_icepop',    2000),
    'Coffee':     Gift(100,  500,  'novelux_gift_coffee',    5000),
    'Champagne':  Gift(500,  1000, 'novelux_gift_champagne', 10000),
    'Luxury Car': Gift(1000, 3000, 'novelux_gift_luxurycar', 30000),
}
FLOWER = 'Flower'
TIP_AMOUNTS = sorted({g.coins for g in GIFTS.values()})
LABEL_BY_COINS = {g.coins: label for label, g in GIFTS.items()}
LABEL_BY_PRODUCT = {g.product_id: label for label, g in GIFTS.items() if g.product_id}


class Tip(models.Model):
    STATUS_PENDING   = 'pending'    # real-money gift: store purchase not seen yet
    STATUS_COMPLETED = 'completed'
    STATUS_REFUNDED  = 'refunded'
    STATUS_CHOICES   = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_REFUNDED,  'Refunded'),
    ]

    sender      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tips_sent')
    recipient   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tips_received')
    story       = models.ForeignKey('stories.Story', on_delete=models.CASCADE, related_name='tips')
    chapter     = models.ForeignKey('chapters.Chapter', on_delete=models.CASCADE,
                                    related_name='tips', null=True, blank=True)
    coins_amount= models.PositiveIntegerField()
    quantity    = models.PositiveSmallIntegerField(default=1)   # Play multi-quantity purchases
    gift_label  = models.CharField(max_length=32, blank=True)
    message     = models.CharField(max_length=255, blank=True)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_COMPLETED)

    # Real-money gifts only
    iap_transaction_id = models.CharField(max_length=200, null=True, blank=True, unique=True)
    amount_usd         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    author_earned_usd  = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tips'
        ordering = ['-created_at']

    @property
    def label(self) -> str:
        """Gift label, falling back to the coin amount for pre-label tips."""
        return self.gift_label or LABEL_BY_COINS.get(self.coins_amount, '')

    def __str__(self):
        return f'{self.sender.username} sent {self.label} to {self.recipient.username}'
