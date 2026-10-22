from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.chapters.vip_payouts import previous_month, run_vip_payout


class Command(BaseCommand):
    help = "Pay authors for last month's VIP reads (held for SE approval). Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument('--month', help='YYYY-MM (default: last month)')

    def handle(self, *args, **opts):
        if opts['month']:
            try:
                y, m = map(int, opts['month'].split('-'))
                month = date(y, m, 1)
            except ValueError:
                raise CommandError('--month must look like 2026-10')
        else:
            month = previous_month()
        run = run_vip_payout(month)
        if run is None:
            self.stdout.write(f'{month:%B %Y} was already paid out — nothing to do.')
            return
        self.stdout.write(self.style.SUCCESS(
            f'{month:%B %Y}: {run.vip_readers} VIP readers, revenue ${run.vip_revenue_usd}, '
            f'paid to authors ${run.paid_to_authors_usd} (held for SE approval), '
            f'excess not paid ${run.excess_ignored_usd} from {run.readers_with_excess} readers.'))
