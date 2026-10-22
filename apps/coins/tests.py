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
        self.once = Task.objects.create(title='Follow us', description='x', reward_coins=10)
        self.daily = Task.objects.create(title='Share a book', description='x', reward_coins=5,
                                         is_repeatable=True, repeat_cooldown_hours=24)
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
