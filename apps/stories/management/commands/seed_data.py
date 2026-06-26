"""
Management command to seed the database with genres, subgenres, tropes/tags,
coin packages, and subscription plans.
Run with: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify


# ── Full taxonomy ──────────────────────────────────────────────────────────
#
# Structure:
#   TAXONOMY = {
#     'Genre Name': {
#       'subgenres': [...],
#       'tropes':    [...],
#     },
#     ...
#   }
#
TAXONOMY = {
    'Romance': {
        'subgenres': [
            'Contemporary Romance', 'Billionaire Romance', 'CEO Romance',
            'Mafia Romance', 'Dark Romance', 'Historical Romance',
            'Regency Romance', 'Small Town Romance', 'Sports Romance',
            'Military Romance', 'Romantic Comedy', 'New Adult Romance',
            'Young Adult Romance', 'LGBTQ+ Romance', 'BL (Boys Love)',
            'GL (Girls Love)', 'Fantasy Romance', 'Paranormal Romance',
            'Sci-Fi Romance', 'Steamy Romance', 'Mature Romance',
            'Clean Romance', 'Christian Romance', 'Erotic Romance',
        ],
        'tropes': [
            'Enemies to Lovers', 'Friends to Lovers', 'Lovers to Enemies',
            'Second Chance Romance', 'Fake Dating', 'Fake Marriage',
            'Contract Marriage', 'Arranged Marriage', 'Marriage of Convenience',
            'Forced Proximity', 'Forbidden Love', 'Secret Baby',
            'Accidental Pregnancy', 'Single Parent', 'Love Triangle',
            'Opposites Attract', 'Grumpy x Sunshine', 'Alpha Male',
            'Possessive Hero', 'Slow Burn', 'Instalove', 'Workplace Romance',
            'Age Gap Romance', "Best Friend's Brother", "Brother's Best Friend",
            'Rich Boy Poor Girl', 'Hidden Identity', 'Boss x Employee',
            'Bodyguard Romance',
        ],
    },
    'Werewolf': {
        'subgenres': [
            'Werewolf Romance', 'Lycan Romance', 'Alpha Romance',
            'Omega Romance', 'Shifter Romance', 'Dragon Shifter',
            'Tiger Shifter', 'Bear Shifter', 'Wolf Pack Fiction',
        ],
        'tropes': [
            'Fated Mates', 'Rejected Mate', 'Chosen Mate', 'Alpha King',
            'Alpha Female', 'Rogue Wolf', 'Pack Politics', 'Mate Bond',
            'Forced Mate', 'Secret Heir', 'Cursed Alpha', 'Lost Princess',
            'Powerful Luna', 'Lycan King',
        ],
    },
    'Paranormal': {
        'subgenres': [
            'Vampire Romance', 'Witch Fiction', 'Demon Romance',
            'Angel Romance', 'Ghost Stories', 'Supernatural Academy',
            'Urban Fantasy', 'Paranormal Mystery',
        ],
        'tropes': [
            'Immortal Love', 'Forbidden Magic', 'Fallen Angel',
            'Demon Contract', 'Witch Coven', 'Vampire King',
            'Ancient Curse', 'Hidden Powers',
        ],
    },
    'Fantasy': {
        'subgenres': [
            'High Fantasy', 'Epic Fantasy', 'Dark Fantasy', 'Urban Fantasy',
            'Sword and Sorcery', 'Fantasy Romance', 'YA Fantasy',
            'Portal Fantasy', 'Fairy Tale Retelling', 'Mythological Fantasy',
            'Magical Academy', 'Kingdom Fantasy', 'Dragon Fantasy',
        ],
        'tropes': [
            'Chosen One', 'Hidden Royalty', 'Lost Princess', 'Dragon Rider',
            'Magical School', 'Ancient Prophecy', 'Evil King',
            'Rebel Princess', 'Quest Journey', 'Magic System', 'Found Family',
        ],
    },
    'Sci-Fi': {
        'subgenres': [
            'Space Opera', 'Cyberpunk', 'Dystopian', 'Utopian',
            'Time Travel', 'Alien Romance', 'Military Sci-Fi',
            'AI Fiction', 'Futuristic Romance', 'Post-Apocalyptic',
        ],
        'tropes': [
            'Time Loop', 'Alien Invasion', 'Space Empire',
            'Artificial Intelligence', 'End of the World',
            'Human Experimentation', 'Parallel Universe', 'Reincarnation',
        ],
    },
    'Apocalyptic': {
        'subgenres': [
            'Post-Apocalyptic', 'Zombie Apocalypse', 'System Apocalypse',
            'Dystopian Survival', 'Monster Apocalypse',
        ],
        'tropes': [
            'Last Survivor', 'End of the World', 'Survival', 'Rebuild Civilization',
            'Zombie Horde', 'System Interface', 'Level Up',
        ],
    },
    'Action': {
        'subgenres': [
            'Action Thriller', 'Survival Adventure', 'Military Action',
            'Treasure Hunt', 'Spy Fiction', 'Expedition Fiction',
        ],
        'tropes': [
            'Secret Mission', 'Chosen Hero', 'Revenge Quest',
            'Lost Treasure', 'Last Survivor', 'Escape Story',
        ],
    },
    'Mystery': {
        'subgenres': [
            'Mystery', 'Detective Fiction', 'Crime Fiction',
            'Psychological Thriller', 'Legal Thriller', 'Political Thriller',
            'Suspense', 'Noir',
        ],
        'tropes': [
            'Serial Killer', 'Cold Case', 'Missing Person',
            'Wrongly Accused', 'Unreliable Narrator',
            'Locked Room Mystery', 'Secret Society',
        ],
    },
    'Thriller': {
        'subgenres': [
            'Psychological Thriller', 'Legal Thriller', 'Political Thriller',
            'Action Thriller', 'Spy Thriller', 'Crime Thriller',
        ],
        'tropes': [
            'Serial Killer', 'Conspiracy', 'Wrongly Accused',
            'Race Against Time', 'Double Agent', 'Unreliable Narrator',
        ],
    },
    'Horror': {
        'subgenres': [
            'Gothic Horror', 'Paranormal Horror', 'Psychological Horror',
            'Survival Horror', 'Monster Horror', 'Occult Horror',
        ],
        'tropes': [
            'Haunted House', 'Ancient Evil', 'Possession',
            'Cult Ritual', 'Monster Attack', 'Psychological Breakdown',
        ],
    },
    'Historical': {
        'subgenres': [
            'Historical Romance', 'Regency Romance', 'Victorian Fiction',
            'Medieval Fiction', 'Ancient Civilization', 'War Fiction',
        ],
        'tropes': [
            'Forbidden Noble Love', 'Royal Court Politics',
            'Arranged Marriage', 'War Hero', 'Secret Heir',
        ],
    },
    'Young Adult': {
        'subgenres': [
            'YA Romance', 'YA Fantasy', 'YA Paranormal',
            'YA Adventure', 'YA Sci-Fi', 'YA Mystery',
        ],
        'tropes': [
            'Coming of Age', 'First Love', 'School Rivalry',
            'Magical Academy', 'Teen Hero', 'Friendship Group',
        ],
    },
    'New Adult': {
        'subgenres': [
            'College Romance', 'Sports Romance',
            'Contemporary NA', 'Fantasy NA',
        ],
        'tropes': [
            'Self Discovery', 'Campus Romance', 'Roommates',
            'First Independence', 'Professional Athlete Romance',
        ],
    },
    "Women's Fiction": {
        'subgenres': [
            'Family Drama', 'Friendship Fiction',
            "Contemporary Women's Fiction", 'Emotional Fiction',
        ],
        'tropes': [
            'Family Secrets', 'Personal Growth', 'Motherhood',
            'Career Success', 'Healing Journey',
        ],
    },
    'Literary Fiction': {
        'subgenres': [
            'Contemporary Literary', 'Historical Literary', 'Experimental Fiction',
        ],
        'tropes': [
            'Character Study', 'Social Commentary',
            'Human Condition', 'Identity Crisis',
        ],
    },
    'General Fiction': {
        'subgenres': [
            'Drama', 'Slice of Life', 'Family Saga',
            'Coming-of-Age', 'Contemporary Fiction',
        ],
        'tropes': [
            'Family Conflict', 'Friendship', 'Personal Growth', 'Life Lessons',
        ],
    },
    'GameLit & Progression': {
        'subgenres': [
            'LitRPG', 'GameLit', 'Dungeon Core', 'Cultivation',
            'System Novel', 'VRMMORPG', 'Progression Fantasy',
        ],
        'tropes': [
            'Level Up', 'System Interface', 'Dungeon Raid', 'OP Protagonist',
            'Rebirth', 'Regression', 'Cheat Ability', 'Hidden Class',
        ],
    },
    'LGBTQ+': {
        'subgenres': [
            'BL (Boys Love)', 'GL (Girls Love)', 'LGBT Romance',
            'LGBTQ+ Contemporary', 'LGBTQ+ Fantasy',
            'LGBTQ+ Paranormal', 'LGBTQ+ Historical',
        ],
        'tropes': [
            'Coming Out', 'Found Family', 'Best Friends to Lovers',
            'Secret Relationship', 'Rivals to Lovers', 'Slow Burn',
        ],
    },
    # Platform-specific genres (no subgenres — keep as-is)
    'Billionaire':      {'subgenres': [], 'tropes': ['Billionaire CEO', 'Boss x Employee', 'Rich Boy Poor Girl', 'Contract Marriage']},
    'Drama':            {'subgenres': [], 'tropes': ['Family Conflict', 'Betrayal', 'Redemption', 'Forbidden Love']},
    'Comedy':           {'subgenres': [], 'tropes': ['Romantic Comedy', 'Misunderstanding', 'Opposites Attract']},
    'African Fiction':  {'subgenres': [], 'tropes': ['Family Drama', 'Cultural Identity', 'Village Life', 'Urban Migration']},
    'Nollywood':        {'subgenres': [], 'tropes': ['Family Secrets', 'Betrayal', 'Juju', 'Arranged Marriage']},
    'Afroromance':      {'subgenres': [], 'tropes': ['Forbidden Love', 'Cultural Clash', 'Second Chance Romance']},
    'Western':          {'subgenres': [], 'tropes': ['Frontier Justice', 'Outlaw', 'Gold Rush', 'Lone Ranger']},
    'Urban':            {'subgenres': [], 'tropes': ['Street Life', 'Hustle', 'Loyalty', 'Redemption']},
    'Male Lead':        {'subgenres': [], 'tropes': ['OP Protagonist', 'Revenge', 'Alpha Male', 'Hidden Identity']},
    'Female Lead':      {'subgenres': [], 'tropes': ['Strong Female Lead', 'Villainess Rebirth', 'Rebel Princess']},
    'Young Teen':       {'subgenres': [], 'tropes': ['First Love', 'School Rivalry', 'Coming of Age', 'Friendship Group']},
}

# Global / cross-genre tropes (not tied to a specific genre)
GLOBAL_TROPES = [
    'Billionaire CEO', 'Mafia Boss', 'Alpha King', 'Rejected Mate',
    'Fated Mates', 'Secret Baby', 'Hidden Heir', 'Revenge',
    'Contract Marriage', 'Forced Marriage', 'Possessive Hero',
    'Love Triangle', 'Enemies to Lovers', 'Fake Dating',
    'Grumpy x Sunshine', 'Strong Female Lead', 'Villainess Rebirth',
    'Time Travel', 'Reincarnation', 'Academy Life', 'Found Family',
    'Chosen One', 'Dragon Rider', 'Magical Academy', 'Kingdom Politics',
    'Slow Burn Romance', 'Second Chance Love', 'Marriage of Convenience',
    'Arranged Marriage', 'Boss x Employee', 'Bodyguard Romance',
    'Harem', 'Reverse Harem', 'Slice of Life', 'Rebirth', 'Betrayal',
    'Redemption', 'Survival', 'Mafia', 'Crime', 'Mob',
]


class Command(BaseCommand):
    help = 'Seed initial platform data: genres, subgenres, tropes/tags, coin packages, subscription plans'

    def handle(self, *args, **options):
        self._seed_taxonomy()
        self._seed_coin_packages()
        self._seed_subscription_plans()
        self.stdout.write(self.style.SUCCESS('Seed data loaded successfully!'))

    def _seed_taxonomy(self):
        from apps.stories.models import Genre, Subgenre, Tag

        genre_created = subgenre_created = tag_created = 0

        for genre_name, data in TAXONOMY.items():
            slug = slugify(genre_name)
            genre, gc = Genre.objects.get_or_create(slug=slug, defaults={'name': genre_name})
            if gc:
                genre_created += 1

            # Subgenres
            for sg_name in data.get('subgenres', []):
                sg_slug = slugify(sg_name)
                _, sc = Subgenre.objects.get_or_create(
                    slug=sg_slug,
                    defaults={'name': sg_name, 'genre': genre},
                )
                if sc:
                    subgenre_created += 1

            # Genre-specific tropes (linked to this genre)
            for trope in data.get('tropes', []):
                t_slug = slugify(trope)
                _, tc = Tag.objects.get_or_create(
                    slug=t_slug,
                    defaults={'name': trope, 'genre': genre},
                )
                if not tc:
                    # Tag exists but may lack genre link — set if missing
                    Tag.objects.filter(slug=t_slug, genre__isnull=True).update(genre=genre)
                else:
                    tag_created += 1

        # Global tropes (no genre link)
        for trope in GLOBAL_TROPES:
            t_slug = slugify(trope)
            _, tc = Tag.objects.get_or_create(slug=t_slug, defaults={'name': trope})
            if tc:
                tag_created += 1

        self.stdout.write(
            f'  Genres: {genre_created} created | '
            f'Subgenres: {subgenre_created} created | '
            f'Tropes/Tags: {tag_created} created'
        )

    def _seed_coin_packages(self):
        from apps.coins.models import CoinPackage
        packages = [
            {'package_id': 'coins_100',  'label': '100 Coins',   'coins': 100,  'price_usd': 0.99,  'bonus_coins': 0},
            {'package_id': 'coins_500',  'label': '500 Coins',   'coins': 500,  'price_usd': 4.99,  'bonus_coins': 0},
            {'package_id': 'coins_1000', 'label': '1,000 Coins', 'coins': 1000, 'price_usd': 9.99,  'bonus_coins': 0},
            {'package_id': 'coins_2500', 'label': '2,500 Coins', 'coins': 2500, 'price_usd': 24.99, 'bonus_coins': 0},
            {'package_id': 'coins_5000', 'label': '5,000 Coins', 'coins': 5000, 'price_usd': 49.99, 'bonus_coins': 0},
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
                'plan_id': 'vip_weekly', 'label': 'VIP Weekly',
                'price_usd': 10.99, 'original_price_usd': 12.25,
                'coins_per_month': 1375, 'bonus_coins': 25,
                'discount_pct': 10, 'duration_days': 7,
                'sub_title': 'Try VIP for a week', 'is_primary': False,
                'badge': None,
            },
            {
                'plan_id': 'vip_monthly', 'label': 'VIP Monthly',
                'price_usd': 43.99, 'original_price_usd': 48.99,
                'coins_per_month': 5500, 'bonus_coins': 100,
                'discount_pct': 10, 'duration_days': 30,
                'sub_title': 'Best for regular readers', 'is_primary': True,
                'badge': 'Most Popular',
            },
            {
                'plan_id': 'vip_quarterly', 'label': 'VIP Quarterly',
                'price_usd': 260.99, 'original_price_usd': 263.94,
                'coins_per_month': 33000, 'bonus_coins': 200,
                'discount_pct': 1, 'duration_days': 90,
                'sub_title': 'Best for avid readers', 'is_primary': False,
                'badge': None,
            },
            {
                'plan_id': 'vip_yearly', 'label': 'VIP Yearly',
                'price_usd': 479.99, 'original_price_usd': 587.88,
                'coins_per_month': 66000, 'bonus_coins': 300,
                'discount_pct': 18, 'duration_days': 365,
                'sub_title': 'Best for dedicated fans', 'is_primary': False,
                'badge': 'Best Value',
            },
        ]
        created = 0
        for p in plans:
            _, c = SubscriptionPlan.objects.get_or_create(plan_id=p['plan_id'], defaults=p)
            if c:
                created += 1
        self.stdout.write(f'  Subscription plans: {created} created')
