"""
Management command to seed the database with initial genres, tags, and coin packages.
Run with: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Seed initial platform data: genres, tags, coin packages, subscription plans'

    def handle(self, *args, **options):
        self._seed_genres()
        self._seed_tags()
        self._seed_coin_packages()
        self._seed_subscription_plans()
        self.stdout.write(self.style.SUCCESS('✅ Seed data loaded successfully!'))

    def _seed_genres(self):
        from apps.stories.models import Genre
        genres = [
            'Romance', 'Fantasy', 'Sci-Fi', 'Thriller', 'Mystery',
            'Horror', 'Action', 'Drama', 'Billionaire', 'Werewolf',
            'Urban', 'Historical', 'Comedy', 'LGBT+', 'African Fiction',
            'Nollywood', 'Afroromance', 'Young Adult', 'Paranormal', 'Western',
        ]
        created = 0
        for name in genres:
            _, c = Genre.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
            if c:
                created += 1
        self.stdout.write(f'  Genres: {created} created')

    def _seed_tags(self):
        from apps.stories.models import Tag
        tags = [
            'enemies-to-lovers', 'slow-burn', 'second-chance', 'forbidden-love',
            'alpha-male', 'strong-female-lead', 'revenge', 'redemption',
            'magic-system', 'portal-fantasy', 'dystopia', 'apocalypse',
            'mafia', 'CEO', 'arranged-marriage', 'royal-family', 'time-travel',
            'mystery-thriller', 'supernatural', 'found-family', 'coming-of-age',
            'war', 'survival', 'harem', 'reverse-harem', 'slice-of-life',
        ]
        created = 0
        for name in tags:
            _, c = Tag.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
            if c:
                created += 1
        self.stdout.write(f'  Tags: {created} created')

    def _seed_coin_packages(self):
        from apps.coins.models import CoinPackage
        packages = [
            {'package_id': 'coins_100',  'label': '100 Coins',   'coins': 100,  'price_usd': 0.99,  'bonus_coins': 0},
            {'package_id': 'coins_500',  'label': '500 Coins',   'coins': 500,  'price_usd': 3.99,  'bonus_coins': 50},
            {'package_id': 'coins_1200', 'label': '1200 Coins',  'coins': 1200, 'price_usd': 8.99,  'bonus_coins': 200},
            {'package_id': 'coins_2500', 'label': '2500 Coins',  'coins': 2500, 'price_usd': 14.99, 'bonus_coins': 500},
            {'package_id': 'coins_5000', 'label': '5000 Coins',  'coins': 5000, 'price_usd': 24.99, 'bonus_coins': 1000},
        ]
        created = 0
        for p in packages:
            _, c = CoinPackage.objects.get_or_create(package_id=p['package_id'], defaults=p)
            if c:
                created += 1
        self.stdout.write(f'  Coin packages: {created} created')

    def _seed_subscription_plans(self):
        from apps.coins.models import SubscriptionPlan
        plans = [
            {
                'plan_id': 'vip_monthly', 'label': 'VIP Monthly',
                'price_usd': 9.99, 'coins_per_month': 1000,
                'discount_pct': 20, 'duration_days': 30,
                'sub_title': 'Best for regular readers','is_primary': True,
                'badge' : 'Most Popular',
            },
            {
                'plan_id': 'vip_yearly', 'label': 'VIP Yearly',
                'price_usd': 89.99, 'coins_per_month': 1200,
                'discount_pct': 30, 'duration_days': 365,
                'sub_title': 'Best for dedicated fans', 'is_primary': False,
                'badge' : 'Best Value',
            },
        ]
        created = 0
        for p in plans:
            _, c = SubscriptionPlan.objects.get_or_create(plan_id=p['plan_id'], defaults=p)
            if c:
                created += 1
        self.stdout.write(f'  Subscription plans: {created} created')
