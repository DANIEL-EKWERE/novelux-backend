from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Task, UserTask

User = get_user_model()


class TaskEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='r@x.com', username='reader', password='x')
        # wait_seconds=0: these tests are about payouts, not the Go-then-wait rule
        self.once = Task.objects.create(title='Follow us', description='x', reward_coins=10, wait_seconds=0)
        self.daily = Task.objects.create(title='Share a book', description='x', reward_coins=5,
                                         is_repeatable=True, repeat_cooldown_hours=24, wait_seconds=0)
        self.answer = Task.objects.create(title='Favourite genre?', description='x', reward_coins=7,
                                          task_type=Task.TYPE_RESPONSE)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def complete(self, task, **body):
        return self.client.post(f'/api/coins/tasks/{task.pk}/complete/', body, format='json')

    def test_reward_goes_to_bonus_balance(self):
        res = self.complete(self.once)
        self.assertEqual(res.status_code, 200, res.data)
        self.user.refresh_from_db()
        self.assertEqual((self.user.coin_balance, self.user.bonus_balance), (0, 10))
        self.assertEqual(res.data['coins_earned'], 10)

    def test_one_time_task_pays_once(self):
        self.complete(self.once)
        res = self.complete(self.once)
        self.assertEqual(res.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonus_balance, 10)

    def test_repeatable_task_respects_cooldown(self):
        self.assertEqual(self.complete(self.daily).status_code, 200)
        res = self.complete(self.daily)                       # again straight away
        self.assertEqual(res.status_code, 400)
        self.assertIn('next_available_at', res.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonus_balance, 5)

        # Once the cooldown has passed it pays again
        UserTask.objects.filter(user=self.user, task=self.daily).update(
            claimed_at=timezone.now() - timedelta(hours=25))
        self.assertEqual(self.complete(self.daily).status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonus_balance, 10)

    def test_list_reopens_repeatable_task_after_cooldown(self):
        self.complete(self.daily)
        status = lambda: next(t for t in self.client.get('/api/coins/tasks/').data['results']
                              if t['id'] == self.daily.pk)
        self.assertEqual(status()['status'], 'claimed')
        self.assertIsNotNone(status()['next_available_at'])
        UserTask.objects.filter(user=self.user, task=self.daily).update(
            claimed_at=timezone.now() - timedelta(hours=25))
        self.assertEqual((status()['status'], status()['next_available_at']), ('pending', None))

    def test_response_task_needs_an_answer(self):
        self.assertEqual(self.complete(self.answer).status_code, 400)
        res = self.complete(self.answer, response='Romance')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(UserTask.objects.get(user=self.user, task=self.answer).response, 'Romance')

    def test_existing_pending_row_still_completes(self):
        # A row created earlier (e.g. by the old code) must not block claiming
        UserTask.objects.create(user=self.user, task=self.once)
        self.assertEqual(self.complete(self.once).status_code, 200)


class ResponseAndActionTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='r@x.com', username='reader', password='x')
        self.quiz = Task.objects.create(title='Who wrote Moonbound?', description='x', reward_coins=8,
                                        task_type=Task.TYPE_RESPONSE, correct_answer='Amaka Rose|amaka',
                                        launch_url='https://www.novelux.app/explore/moonbound/')
        self.follow = Task.objects.create(title='Follow us on Instagram', description='x', reward_coins=3,
                                          launch_url='https://instagram.com/huxnovel', wait_seconds=30)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def complete(self, task, **body):
        return self.client.post(f'/api/coins/tasks/{task.pk}/complete/', body, format='json')

    def test_answer_is_never_sent_to_the_app(self):
        data = self.client.get('/api/coins/tasks/').data['results']
        self.assertNotIn('Amaka', str(data))
        quiz = next(t for t in data if t['id'] == self.quiz.pk)
        self.assertEqual((quiz['launch_url'], quiz['attempts_left']),
                         ('https://www.novelux.app/explore/moonbound/', 5))

    def test_correct_answer_ignores_case_and_spacing(self):
        res = self.complete(self.quiz, response='  amaka   ROSE ')
        self.assertEqual(res.status_code, 200, res.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonus_balance, 8)

    def test_wrong_answers_count_down_then_lock(self):
        for left in (4, 3, 2, 1, 0):
            res = self.complete(self.quiz, response='nope')
            self.assertEqual((res.status_code, res.data['attempts_left']), (400, left))
        res = self.complete(self.quiz, response='amaka')          # right, but locked
        self.assertEqual(res.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonus_balance, 0)

    def test_action_task_needs_go_then_wait(self):
        self.assertEqual(self.complete(self.follow).data['detail'], 'Tap Go first.')
        start = self.client.post(f'/api/coins/tasks/{self.follow.pk}/start/')
        self.assertEqual(start.status_code, 200)
        self.assertIn('claim_available_at', self.complete(self.follow).data)   # too early
        UserTask.objects.filter(user=self.user, task=self.follow).update(
            started_at=timezone.now() - timedelta(seconds=31))
        self.assertEqual(self.complete(self.follow).status_code, 200)

    def test_retapping_go_does_not_restart_the_wait(self):
        self.client.post(f'/api/coins/tasks/{self.follow.pk}/start/')
        UserTask.objects.filter(user=self.user, task=self.follow).update(
            started_at=timezone.now() - timedelta(seconds=31))
        self.client.post(f'/api/coins/tasks/{self.follow.pk}/start/')         # Go again
        self.assertEqual(self.complete(self.follow).status_code, 200)


class RewardClaimTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='r@x.com', username='reader', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def claim(self, claim_type, **extra):
        return self.client.post('/api/coins/claim-reward/', {'claim_type': claim_type, **extra}, format='json')

    def bonus(self):
        self.user.refresh_from_db()
        return (self.user.coin_balance, self.user.bonus_balance)

    def test_signin_and_notification_pay_5_and_10_once(self):
        self.assertEqual(self.claim('signin', coins=999).data['coins_earned'], 5)   # app amount ignored
        self.assertEqual(self.claim('signin').status_code, 400)
        self.assertEqual(self.claim('notification').data['coins_earned'], 10)
        self.assertEqual(self.claim('notification').status_code, 400)
        self.assertEqual(self.bonus(), (0, 15))

    def test_ads_pay_1_each_up_to_10_a_day(self):
        for _ in range(10):
            self.assertEqual(self.claim('ad').status_code, 200)
        self.assertEqual(self.claim('ad').status_code, 400)
        self.assertEqual(self.bonus(), (0, 10))

    def test_checkin_ad_bonus_needs_checkin_and_pays_5_once(self):
        self.assertEqual(self.claim('checkin_ad').data['detail'], 'Check in first')
        self.assertEqual(self.client.post('/api/coins/checkin/').data['coins_earned'], 5)   # day 1
        self.assertEqual(self.claim('checkin_ad').data['coins_earned'], 5)
        self.assertEqual(self.claim('checkin_ad').status_code, 400)
        self.assertEqual(self.bonus(), (0, 10))      # check-in + ad bonus, all bonus balance

    def test_reading_is_capped_per_day(self):
        self.assertEqual(self.claim('reading', coins=100).data['coins_earned'], 100)
        self.assertEqual(self.claim('reading', coins=100).data['coins_earned'], 25)
        self.assertEqual(self.claim('reading', coins=5).status_code, 400)

    def test_old_checkin_claim_type_is_rejected(self):
        self.assertEqual(self.claim('checkin', coins=30).status_code, 400)

    def test_checkin_schedule_is_5_to_20(self):
        from .models import STREAK_REWARDS
        self.assertEqual((min(STREAK_REWARDS), max(STREAK_REWARDS)), (5, 20))
        self.assertEqual(self.client.get('/api/coins/checkin/status/').data['reward_schedule'], STREAK_REWARDS)


class AdRewardTaskTests(TestCase):
    def setUp(self):
        from .models import AdRewardTask
        self.user = User.objects.create_user(email='r@x.com', username='reader', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.tasks = list(AdRewardTask.objects.all())

    def watched(self, task):
        return self.client.post(f'/api/coins/ad-tasks/{task.pk}/watched/')

    def test_six_seeded_tasks(self):
        data = self.client.get('/api/coins/ad-tasks/').data['results']
        self.assertEqual([(t['ads_required'], t['reward_coins']) for t in data],
                         [(1, 1), (2, 1), (3, 2), (1, 1), (2, 1), (3, 2)])
        self.assertTrue(all(t['ads_watched'] == 0 and t['valid_days'] == 7 for t in data))

    def test_one_ad_task_pays_immediately(self):
        res = self.watched(self.tasks[0])
        self.assertEqual((res.data['completed'], res.data['coins_earned']), (True, 1))
        self.user.refresh_from_db()
        self.assertEqual((self.user.coin_balance, self.user.bonus_balance), (0, 1))

    def test_three_ad_task_pays_on_the_last_ad(self):
        three = self.tasks[2]
        for n in (1, 2):
            res = self.watched(three)
            self.assertEqual((res.data['ads_watched'], res.data['completed'], res.data['coins_earned']),
                             (n, False, 0))
        res = self.watched(three)
        self.assertEqual((res.data['ads_watched'], res.data['completed'], res.data['coins_earned']), (3, True, 2))
        self.assertEqual(self.watched(three).status_code, 400)      # done for today
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonus_balance, 2)

    def test_resets_the_next_day(self):
        from .models import AdTaskProgress
        self.watched(self.tasks[0])
        AdTaskProgress.objects.update(date=timezone.localdate() - timedelta(days=1))
        self.assertEqual(self.watched(self.tasks[0]).data['coins_earned'], 1)


class BonusExpiryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='r@x.com', username='reader', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def age(self, days):
        """Pretend every grant was earned `days` ago."""
        from apps.users.models import BonusGrant
        for g in BonusGrant.objects.filter(user=self.user):
            BonusGrant.objects.filter(pk=g.pk).update(expires_at=g.expires_at - timedelta(days=days))

    def test_reward_expires_after_7_days(self):
        from apps.users.models import BonusGrant
        self.user.add_bonus(10, 'Check-in')
        g = BonusGrant.objects.get(user=self.user)
        self.assertAlmostEqual((g.expires_at - timezone.now()).total_seconds(), 7 * 86400, delta=60)

        data = self.client.get('/api/coins/balance/').data
        self.assertEqual((data['bonus_balance'], data['bonus_expiring']['amount']), (10, 10))

        self.age(7)
        data = self.client.get('/api/coins/balance/').data
        self.assertEqual((data['bonus_balance'], data['bonus_expiring']), (0, None))
        self.assertTrue(self.user.coin_transactions.filter(transaction_type='expire', amount=10).exists())

    def test_spending_uses_soonest_expiring_first(self):
        from apps.users.models import BonusGrant
        self.user.add_bonus(5, 'old')
        self.age(5)                        # the 5 now expire in 2 days
        self.user.add_bonus(8, 'new')      # these expire in 7 days
        self.user.refresh_from_db()
        self.assertTrue(self.user.deduct_coins(3, 'Unlock'))
        left = dict(BonusGrant.objects.filter(user=self.user).values_list('reason', 'remaining'))
        self.assertEqual(left, {'old': 2, 'new': 8})

        self.age(3)                        # the old grant passes 7 days
        self.user.refresh_from_db()
        self.assertEqual(self.user.expire_bonus(), 2)
        self.assertEqual(self.user.bonus_balance, 8)

    def test_expired_bonus_cannot_be_spent(self):
        self.user.add_bonus(10, 'x')
        self.age(8)
        self.user.refresh_from_db()
        self.assertFalse(self.user.deduct_coins(5, 'Unlock'))   # nothing left to spend

    def test_hourly_job_expires_everyone(self):
        from .tasks import expire_bonus_coins
        other = User.objects.create_user(email='o@x.com', username='other', password='x')
        self.user.add_bonus(4, 'x'); other.add_bonus(6, 'y')
        from apps.users.models import BonusGrant
        BonusGrant.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(expire_bonus_coins(), 10)
        self.user.refresh_from_db(); other.refresh_from_db()
        self.assertEqual((self.user.bonus_balance, other.bonus_balance), (0, 0))

    def test_existing_balances_get_7_days(self):
        import importlib
        from django.apps import apps as django_apps
        from apps.users.models import BonusGrant
        migration = importlib.import_module('apps.users.migrations.0014_bonus_grants')
        User.objects.filter(pk=self.user.pk).update(bonus_balance=40)   # earned before expiry existed
        migration.grant_existing_bonus(django_apps, None)
        g = BonusGrant.objects.get(user=self.user)
        self.assertEqual((g.amount, g.remaining), (40, 40))
        self.assertAlmostEqual((g.expires_at - timezone.now()).total_seconds(), 7 * 86400, delta=60)
