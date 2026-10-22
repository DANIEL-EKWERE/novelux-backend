"""Background jobs for chapters."""
from celery import shared_task


@shared_task
def run_monthly_vip_payout():
    """Daily: pay out last month's VIP reads if that hasn't happened yet.
    Running daily (not once on the 1st) means a missed day catches up."""
    from .vip_payouts import previous_month, run_vip_payout
    run = run_vip_payout(previous_month())
    return str(run) if run else 'already paid'
