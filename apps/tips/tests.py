from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.stories.models import Story
from .models import Tip
from . import services

User = get_user_model()


@mock.patch('apps.tips.views.on_tip_received')
class SendTipTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x')
        self.reader = User.objects.create_user(email='r@x.com', username='reader', password='x',
                                               coin_balance=600)
        self.story  = Story.objects.create(author=self.author, title='Tale', slug='tale')
        self.client = APIClient()
        self.client.force_authenticate(self.reader)

    def tip(self, **body):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post('/api/tips/tale/tip/', body, format='json')

    def test_flower_is_free_and_recorded(self, notify):
        res = self.tip(coins_amount=0, gift_label='Flower')
        self.assertEqual(res.status_code, 201, res.data)
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.coin_balance, 600)
        self.assertEqual(Tip.objects.get().gift_label, 'Flower')
        self.assertEqual(notify.call_args.kwargs['gift_label'], 'Flower')

    def test_paid_gift_moves_coins(self, notify):
        res = self.tip(coins_amount=500, gift_label='Champagne', chapter_number=99)
        self.assertEqual(res.status_code, 201, res.data)
        self.reader.refresh_from_db(); self.author.refresh_from_db(); self.story.refresh_from_db()
        self.assertEqual(self.reader.coin_balance, 100)
        self.assertEqual(self.story.total_tips, 500)
        self.assertEqual(notify.call_args.kwargs['gift_label'], 'Champagne')

        # The author's share is held until their SE approves it
        tip = Tip.objects.get()
        self.assertEqual((self.author.coin_balance, tip.earning_status), (0, Tip.EARNING_HELD))
        self.assertTrue(services.release_tip_earning(tip.pk))
        self.assertFalse(services.release_tip_earning(tip.pk))   # can't pay twice
        self.author.refresh_from_db()
        self.assertEqual(self.author.coin_balance, res.data['author_earned'])

    def test_label_inferred_from_amount_for_old_clients(self, notify):
        self.assertEqual(self.tip(coins_amount=100).status_code, 201)
        self.assertEqual(Tip.objects.get().gift_label, 'Coffee')

    def test_price_mismatch_rejected(self, notify):
        self.assertEqual(self.tip(coins_amount=10, gift_label='Luxury Car').status_code, 400)
        self.assertEqual(self.tip(coins_amount=7).status_code, 400)

    def test_insufficient_coins_changes_nothing(self, notify):
        self.assertEqual(self.tip(coins_amount=1000).status_code, 402)
        self.assertFalse(Tip.objects.exists())
        notify.assert_not_called()

    def test_ranking_splits_gratuity_and_flowers(self, notify):
        for body in ({'coins_amount': 50}, {'coins_amount': 50}, {'coins_amount': 0},
                     {'coins_amount': 0}, {'coins_amount': 0}):
            self.tip(**body)
        res = APIClient().get('/api/tips/tale/top-tippers/')
        self.assertEqual(res.status_code, 200)
        gratuity, flowers = res.data
        self.assertEqual(gratuity['user']['username'], 'reader')
        self.assertEqual((gratuity['gift_points'], gratuity['count']), (400, 2))
        self.assertEqual((flowers['total_coins'], flowers['count']), (0, 3))


WEBHOOK = '/api/coins/revenuecat-webhook/'


def rc_subscriber(*tx_ids, product='novelux_gift_coffee'):
    return {'non_subscriptions': {product: [
        {'store_transaction_id': t, 'purchase_date': f'2026-10-04T00:00:0{i}Z'}
        for i, t in enumerate(tx_ids)
    ]}}


@mock.patch('apps.tips.services.on_tip_received')
@mock.patch('apps.coins.views._fetch_rc_subscriber')
class PaidGiftTests(TestCase):
    def setUp(self):
        from apps.users.models import AuthorProfile
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x')
        self.profile = AuthorProfile.objects.create(user=self.author)
        self.reader = User.objects.create_user(email='r@x.com', username='reader', password='x')
        self.story  = Story.objects.create(author=self.author, title='Tale', slug='tale')
        self.client = APIClient()
        self.client.force_authenticate(self.reader)

    def intent(self, label='Coffee'):
        res = self.client.post('/api/tips/tale/gift/', {'gift_label': label}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        return res.data

    def confirm(self, intent_id):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(f'/api/tips/gift/{intent_id}/confirm/')

    def webhook(self, event):
        with self.settings(REVENUECAT_WEBHOOK_AUTH='secret'), \
                self.captureOnCommitCallbacks(execute=True):
            return APIClient().post(WEBHOOK, {'event': {
                'app_user_id': str(self.reader.pk), **event}},
                format='json', HTTP_AUTHORIZATION='secret')

    def test_intent_returns_product_and_is_hidden_until_paid(self, rc, notify):
        data = self.intent()
        self.assertEqual(data['product_id'], 'novelux_gift_coffee')
        self.assertEqual(APIClient().get('/api/tips/tale/top-tippers/').data, [])

    def test_flower_cannot_be_bought(self, rc, notify):
        res = self.client.post('/api/tips/tale/gift/', {'gift_label': 'Flower'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_confirm_then_webhook_credits_once(self, rc, notify):
        intent_id = self.intent()['intent_id']
        rc.return_value = rc_subscriber('GPA.1')
        res = self.confirm(intent_id)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(notify.call_args.kwargs['gift_label'], 'Coffee')

        board = APIClient().get('/api/tips/tale/top-tippers/').data
        self.assertEqual((board[0]['gift_points'], board[0]['total_coins']), (500, 500))

        for _ in range(2):   # RevenueCat retries must not double-credit
            self.webhook({'type': 'NON_RENEWING_PURCHASE', 'product_id': 'novelux_gift_coffee',
                          'transaction_id': 'GPA.1', 'price': 3.40})
        self.profile.refresh_from_db()
        self.assertEqual(str(self.profile.pending_payout), '0.00')   # held for SE approval
        self.assertEqual(notify.call_count, 1)

        tip = Tip.objects.get(iap_transaction_id='GPA.1')
        self.assertTrue(services.release_tip_earning(tip.pk))
        self.assertFalse(services.release_tip_earning(tip.pk))
        self.profile.refresh_from_db()
        # 3.40 × (1 − 0.15) × 0.25 = 0.7225 → 0.72
        self.assertEqual(str(self.profile.pending_payout), '0.72')

    def test_refund_after_approval_claws_back(self, rc, notify):
        rc.return_value = rc_subscriber('GPA.1')
        self.confirm(self.intent()['intent_id'])
        self.webhook({'type': 'NON_RENEWING_PURCHASE', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.1', 'price': 3.40})
        services.release_tip_earning(Tip.objects.get(iap_transaction_id='GPA.1').pk)
        self.webhook({'type': 'CANCELLATION', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.1'})
        self.profile.refresh_from_db()
        self.assertEqual(str(self.profile.pending_payout), '0.00')

    def test_webhook_alone_completes_newest_intent(self, rc, notify):
        self.intent()
        newest = self.intent()['intent_id']
        self.webhook({'type': 'NON_RENEWING_PURCHASE', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.2', 'price': 3.40})
        self.assertEqual(Tip.objects.get(iap_transaction_id='GPA.2').pk, newest)

    def test_transaction_cannot_be_replayed_for_second_gift(self, rc, notify):
        rc.return_value = rc_subscriber('GPA.1')
        self.assertEqual(self.confirm(self.intent()['intent_id']).status_code, 200)
        second = self.confirm(self.intent()['intent_id'])
        self.assertEqual(second.status_code, 202)
        self.assertEqual(Tip.objects.filter(status=Tip.STATUS_COMPLETED).count(), 1)

    def test_refund_reverses_gift(self, rc, notify):
        rc.return_value = rc_subscriber('GPA.1')
        self.confirm(self.intent()['intent_id'])
        self.webhook({'type': 'NON_RENEWING_PURCHASE', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.1', 'price': 3.40})
        self.webhook({'type': 'CANCELLATION', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.1'})
        self.profile.refresh_from_db(); self.story.refresh_from_db()
        self.assertEqual(str(self.profile.pending_payout), '0.00')
        self.assertEqual(self.story.total_tips, 0)
        # Refunded before approval — it can never be approved afterwards
        tip = Tip.objects.get(iap_transaction_id='GPA.1')
        self.assertEqual(tip.earning_status, Tip.EARNING_REJECTED)
        self.assertFalse(services.release_tip_earning(tip.pk))
        self.assertEqual(APIClient().get('/api/tips/tale/top-tippers/').data, [])

    def test_cancelled_purchase_drops_intent(self, rc, notify):
        intent_id = self.intent()['intent_id']
        self.assertEqual(self.client.delete(f'/api/tips/gift/{intent_id}/confirm/').status_code, 204)
        self.assertFalse(Tip.objects.exists())

    def test_multi_quantity_after_confirm(self, rc, notify):
        rc.return_value = rc_subscriber('GPA.1')
        self.confirm(self.intent()['intent_id'])          # app can't see quantity → 1
        self.webhook({'type': 'NON_RENEWING_PURCHASE', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.1', 'price': 10.20, 'quantity': 3})
        self.story.refresh_from_db()
        self.assertEqual(self.story.total_tips, 1500)
        board = APIClient().get('/api/tips/tale/top-tippers/').data
        self.assertEqual((board[0]['gift_points'], board[0]['count']), (1500, 3))

    def test_multi_quantity_webhook_only_and_refund(self, rc, notify):
        self.intent()
        self.webhook({'type': 'NON_RENEWING_PURCHASE', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.1', 'price': 10.20, 'quantity': 3})
        self.story.refresh_from_db()
        self.assertEqual(self.story.total_tips, 1500)
        self.webhook({'type': 'CANCELLATION', 'product_id': 'novelux_gift_coffee',
                      'transaction_id': 'GPA.1'})
        self.story.refresh_from_db(); self.profile.refresh_from_db()
        self.assertEqual((self.story.total_tips, str(self.profile.pending_payout)), (0, '0.00'))
