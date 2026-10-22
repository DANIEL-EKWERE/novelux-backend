"""Background jobs for coins."""
from celery import shared_task


@shared_task
def expire_bonus_coins():
    """Hourly: remove bonus coins older than BONUS_VALID_DAYS for everyone
    who has some. (Balances are also expired whenever they are read or spent,
    so readers never see or spend expired bonus even if this job is late.)"""
    from django.utils import timezone
    from apps.users.models import BonusGrant, User
    user_ids = (BonusGrant.objects.filter(remaining__gt=0, expires_at__lte=timezone.now())
                .values_list('user_id', flat=True).distinct())
    total = 0
    for user in User.objects.filter(pk__in=list(user_ids)):
        total += user.expire_bonus()
    return total
