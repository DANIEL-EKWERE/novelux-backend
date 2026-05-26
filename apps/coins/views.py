import stripe
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CoinPackage, SubscriptionPlan, Purchase, Subscription, AuthorPayout
''' added this new code for handling coin purchases and subscriptions '''
from django.utils import timezone
from django.db.models import Sum
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import date, timedelta
import json
 
''' end of new code '''

from rest_framework.views   import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.stories.models  import Story
from .models     import ReadingHistory
from .serializers import ReadingHistorySerializer
from rest_framework.parsers import JSONParser
 
 
import json
from rest_framework.views    import APIView
from rest_framework.response import Response
from rest_framework          import permissions, status
from django.shortcuts        import get_object_or_404
 
 
class ReadingHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    PAGE_SIZE = 30
 
    # ── Helper: safely parse request.data ────────────────────────────────────
    def _get_data(self, request) -> dict:
        # \"\"\"
        # DRF sets request.data to a string when the body is plain JSON
        # but the Content-Type header is wrong/missing.
        # This helper normalises it to a dict every time.
        # \"\"\"
        data = request.data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                data = {}
        if not isinstance(data, dict):
            data = {}
        return data
 
    # ── GET /api/reading/history/ ─────────────────────────────────────────────
    def get(self, request):
        from .models      import ReadingHistory
        from .serializers import ReadingHistorySerializer
 
        history = ReadingHistory.objects.filter(
            user=request.user
        ).select_related('story', 'story__genre')
 
        page  = int(request.query_params.get('page', 1))
        start = (page - 1) * self.PAGE_SIZE
        end   = page * self.PAGE_SIZE
        items = history[start:end]
 
        serializer = ReadingHistorySerializer(
            items, many=True, context={'request': request})
        return Response({
            'results':  serializer.data,
            'count':    history.count(),
            'page':     page,
            'has_next': history.count() > end,
        })
 
    # ── POST /api/reading/history/ ────────────────────────────────────────────
    def post(self, request):
        from apps.stories.models import Story
        from .models             import ReadingHistory
        from .serializers        import ReadingHistorySerializer
 
        # ← THE FIX: use _get_data() instead of request.data directly
        data = self._get_data(request)
 
        # Accept both field name variants Flutter may send
        slug = (
            data.get('story_slug') or
            data.get('story')      or
            ''
        ).strip()
 
        chapter_number = int(data.get('chapter_number', 1) or 1)
        chapter_title  = str(data.get('chapter_title',  '') or '')
 
        if not slug:
            return Response(
                {'detail': 'story_slug is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
 
        try:
            story = Story.objects.get(slug=slug)
        except Story.DoesNotExist:
            return Response(
                {'detail': f'Story with slug "{slug}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
 
        entry, created = ReadingHistory.objects.update_or_create(
            user=request.user,
            story=story,
            defaults={
                'chapter_number': chapter_number,
                'chapter_title':  chapter_title,
            }
        )
 
        serializer = ReadingHistorySerializer(
            entry, context={'request': request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
 
    # ── DELETE /api/reading/history/ ──────────────────────────────────────────
    def delete(self, request):
        from .models import ReadingHistory
        ReadingHistory.objects.filter(user=request.user).delete()
        return Response(
            {'detail': 'History cleared.'},
            status=status.HTTP_204_NO_CONTENT
        )
 
 
class ReadingHistoryDetailView(APIView):
    # \"\"\"DELETE /api/reading/history/<id>/\"\"\"
    permission_classes = [permissions.IsAuthenticated]
 
    def delete(self, request, pk):
        from .models import ReadingHistory
        entry = get_object_or_404(ReadingHistory, pk=pk, user=request.user)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
 
 
# class ReadingHistoryDetailView(APIView):
#     # \"\"\"
#     # DELETE /api/reading/history/<id>/    remove a single entry
#     # \"\"\"
#     permission_classes = [permissions.IsAuthenticated]
 
#     def delete(self, request, pk):
#         entry = get_object_or_404(ReadingHistory,
#                                   pk=pk, user=request.user)
#         entry.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


from .serializers import (
    CoinPackageSerializer, SubscriptionPlanSerializer, PurchaseSerializer,
    SubscriptionSerializer, CoinTransactionSerializer, AuthorPayoutRequestSerializer,
    CreateCheckoutSessionSerializer
)
from apps.users.models import CoinTransaction

stripe.api_key = settings.STRIPE_SECRET_KEY


class CoinPackageListView(generics.ListAPIView):
    serializer_class = CoinPackageSerializer
    queryset         = CoinPackage.objects.filter(is_active=True)
    pagination_class = None


class SubscriptionPlanListView(generics.ListAPIView):
    serializer_class = SubscriptionPlanSerializer
    queryset         = SubscriptionPlan.objects.filter(is_active=True)
    pagination_class = None


class CreateCheckoutSessionView(APIView):
    """Create a Stripe Checkout session for coin pack or subscription."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateCheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        purchase_type = data['purchase_type']

        if purchase_type == 'coin_pack':
            package = get_object_or_404(CoinPackage, package_id=data['package_id'], is_active=True)
            amount  = int(package.price_usd * 100)
            name    = package.label

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': amount,
                        'product_data': {'name': name},
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{settings.FRONTEND_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{settings.FRONTEND_URL}/purchase/cancel',
                metadata={
                    'user_id':      str(request.user.id),
                    'purchase_type': 'coin_pack',
                    'package_id':   package.package_id,
                    'coins':        str(package.total_coins),
                }
            )

            Purchase.objects.create(
                user=request.user,
                purchase_type='coin_pack',
                coin_package=package,
                coins_granted=package.total_coins,
                amount_paid_usd=package.price_usd,
                stripe_session_id=session.id,
            )

        else:  # subscription
            plan = get_object_or_404(SubscriptionPlan, plan_id=data['plan_id'], is_active=True)

            if plan.stripe_price_id:
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
                    mode='subscription',
                    success_url=f'{settings.FRONTEND_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}',
                    cancel_url=f'{settings.FRONTEND_URL}/purchase/cancel',
                    metadata={
                        'user_id':      str(request.user.id),
                        'purchase_type': 'subscription',
                        'plan_id':      plan.plan_id,
                    }
                )
            else:
                return Response({'detail': 'Plan not configured for payments.'}, status=400)

            Purchase.objects.create(
                user=request.user,
                purchase_type='subscription',
                subscription_plan=plan,
                coins_granted=plan.coins_per_month,
                amount_paid_usd=plan.price_usd,
                stripe_session_id=session.id,
            )

        return Response({'checkout_url': session.url}, status=200)


class StripeWebhookView(APIView):
    """Handle Stripe webhook events."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload    = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=400)

        if event['type'] == 'checkout.session.completed':
            self._handle_checkout_completed(event['data']['object'])

        elif event['type'] == 'invoice.payment_succeeded':
            self._handle_subscription_renewal(event['data']['object'])

        elif event['type'] == 'customer.subscription.deleted':
            self._handle_subscription_cancelled(event['data']['object'])

        return Response({'status': 'ok'})

    def _handle_checkout_completed(self, session):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        meta          = session.get('metadata', {})
        user_id       = meta.get('user_id')
        purchase_type = meta.get('purchase_type')

        try:
            user     = User.objects.get(id=user_id)
            purchase = Purchase.objects.get(stripe_session_id=session['id'])
        except (User.DoesNotExist, Purchase.DoesNotExist):
            return

        purchase.status       = Purchase.STATUS_COMPLETED
        purchase.completed_at = timezone.now()
        purchase.stripe_payment_id = session.get('payment_intent', '')
        purchase.save()

        if purchase_type == 'coin_pack':
            coins = int(meta.get('coins', 0))
            user.add_coins(coins, reason=f'Coin pack purchase: {meta.get("package_id")}')

        elif purchase_type == 'subscription':
            plan = get_object_or_404(SubscriptionPlan, plan_id=meta.get('plan_id'))
            expires = timezone.now() + timezone.timedelta(days=plan.duration_days)
            Subscription.objects.update_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'expires_at': expires,
                    'is_active': True,
                    'stripe_sub_id': session.get('subscription', ''),
                }
            )
            user.is_vip     = True
            user.vip_expires= expires
            user.save(update_fields=['is_vip', 'vip_expires'])
            user.add_coins(plan.coins_per_month, reason=f'VIP subscription: {plan.label}')

    def _handle_subscription_renewal(self, invoice):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        stripe_sub_id = invoice.get('subscription')
        try:
            sub  = Subscription.objects.get(stripe_sub_id=stripe_sub_id)
            sub.expires_at = timezone.now() + timezone.timedelta(days=sub.plan.duration_days)
            sub.save()
            sub.user.add_coins(sub.plan.coins_per_month, reason='Monthly VIP coin renewal')
        except Subscription.DoesNotExist:
            pass

    def _handle_subscription_cancelled(self, stripe_sub):
        try:
            sub            = Subscription.objects.get(stripe_sub_id=stripe_sub['id'])
            sub.is_active  = False
            sub.cancelled_at = timezone.now()
            sub.save()
            sub.user.is_vip = False
            sub.user.save(update_fields=['is_vip'])
        except Subscription.DoesNotExist:
            pass


class MyCoinBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'coin_balance':  request.user.coin_balance,
            'is_vip':        request.user.is_vip,
            'vip_expires':   request.user.vip_expires,
        })


class CoinTransactionHistoryView(generics.ListAPIView):
    serializer_class   = CoinTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CoinTransaction.objects.filter(user=self.request.user)


class MyPurchaseHistoryView(generics.ListAPIView):
    serializer_class   = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Purchase.objects.filter(user=self.request.user, status=Purchase.STATUS_COMPLETED)


class RequestPayoutView(generics.CreateAPIView):
    serializer_class   = AuthorPayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_author:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only authors can request payouts.')
        profile = user.author_profile
        if profile.pending_payout <= 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('No pending payout available.')
        serializer.save(
            author=user,
            amount_usd=profile.pending_payout,
            coins_total=user.coin_balance,
        )
        profile.pending_payout = 0
        profile.save(update_fields=['pending_payout'])


class AuthorPayoutListView(generics.ListAPIView):
    """GET /api/coins/payouts/mine/ — list the current author's payout history."""
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        from .models import AuthorPayout
        from .serializers import AuthorPayoutRequestSerializer
        qs = AuthorPayout.objects.filter(author=request.user).order_by('-requested_at')[:50]
        data = [
            {
                'id':            p.id,
                'amount_usd':    str(p.amount_usd),
                'status':        p.status,
                'payout_method': p.payout_method or '',
                'requested_at':  p.requested_at.isoformat() if p.requested_at else None,
                'processed_at':  p.processed_at.isoformat() if hasattr(p, 'processed_at') and p.processed_at else None,
            }
            for p in qs
        ]
        return Response(data)


''' beginning of recently added code for handling coin purchases and subscriptions '''


# ── VIP Status ────────────────────────────────────────────────────────────────
class VipStatusView(APIView):
    """GET /api/coins/vip-status/"""
    permission_classes = [permissions.IsAuthenticated]
 
    def get(self, request):
        user = request.user
        sub  = getattr(user, 'subscription', None)
 
        return Response({
            'is_vip':      user.is_vip if hasattr(user, 'is_vip') else False,
            'plan':        sub.plan_name if sub else None,
            'expires_at':  sub.expires_at if sub else None,
            'coin_balance': user.coin_balance,
        })
 
 
# ── Cancel Subscription ───────────────────────────────────────────────────────
class CancelSubscriptionView(APIView):
    """POST /api/coins/subscription/cancel/"""
    permission_classes = [permissions.IsAuthenticated]
 
    def post(self, request):
        sub = getattr(request.user, 'subscription', None)
        if not sub:
            return Response({'detail': 'No active subscription'},
                            status=status.HTTP_400_BAD_REQUEST)
        # Cancel at period end (don't revoke immediately)
        sub.cancel_at_period_end = True
        sub.save()
        return Response({'detail': 'Subscription will cancel at period end.',
                         'expires_at': sub.expires_at})
 
 
# ── Claim Daily Reward ────────────────────────────────────────────────────────
class ClaimDailyRewardView(APIView):
    """
    POST /api/coins/claim-reward/
    Body: { "coins": 5, "claim_type": "checkin" }
    """
    permission_classes = [permissions.IsAuthenticated]
 
    ALLOWED_TYPES = {
        'checkin':      {'max_coins': 40,  'once_daily': True},
        'reading':      {'max_coins': 50,  'once_daily': True},
        'ad':           {'max_coins': 20,  'once_daily': False, 'max_per_day': 5},
        'signin':       {'max_coins': 30,  'once_daily': False, 'once_ever': True},
        'notification': {'max_coins': 200, 'once_daily': False, 'once_ever': True},
    }
 
    def post(self, request):
        coins      = int(request.data.get('coins', 0))
        claim_type = request.data.get('claim_type', 'checkin')
        user       = request.user
        today      = date.today()
 
        if claim_type not in self.ALLOWED_TYPES:
            return Response({'detail': 'Invalid claim type'},
                            status=status.HTTP_400_BAD_REQUEST)
 
        rules = self.ALLOWED_TYPES[claim_type]
 
        # Validate coin amount
        if coins > rules['max_coins'] or coins <= 0:
            return Response({'detail': f'Invalid coin amount for {claim_type}'},
                            status=status.HTTP_400_BAD_REQUEST)
 
        # Check once-ever claims
        if rules.get('once_ever'):
            from apps.coins.models import DailyRewardClaim
            if DailyRewardClaim.objects.filter(
                    user=user, claim_type=claim_type).exists():
                return Response({'detail': 'Already claimed'},
                                status=status.HTTP_400_BAD_REQUEST)
 
        # Check once-daily
        if rules.get('once_daily'):
            from apps.coins.models import DailyRewardClaim
            if DailyRewardClaim.objects.filter(
                    user=user, claim_type=claim_type,
                    claimed_at=today).exists():
                return Response({'detail': 'Already claimed today'},
                                status=status.HTTP_400_BAD_REQUEST)
 
        # Check max per day for ads
        if rules.get('max_per_day'):
            from apps.coins.models import DailyRewardClaim
            count = DailyRewardClaim.objects.filter(
                user=user, claim_type=claim_type, claimed_at=today).count()
            if count >= rules['max_per_day']:
                return Response({'detail': 'Daily limit reached'},
                                status=status.HTTP_400_BAD_REQUEST)
 
        # Add coins
        user.add_coins(coins)
 
        # Record claim
        from apps.coins.models import DailyRewardClaim
        DailyRewardClaim.objects.create(
            user=user, claim_type=claim_type, coins=coins)
 
        return Response({
            'success':     True,
            'coins_added': coins,
            'new_balance': user.coin_balance,
        })
 
 
# ── Reading Session ───────────────────────────────────────────────────────────
class ReadingSessionView(APIView):
    """
    POST /api/reading/session/
    Body: { "story_slug": "...", "chapter": 1, "minutes": 15 }
    """
    permission_classes = [permissions.IsAuthenticated]
 
    def post(self, request):
        from apps.stories.models import Story
        from apps.coins.models import DailyRewardClaim
 
        slug    = request.data.get('story_slug')
        chapter = int(request.data.get('chapter', 1))
        minutes = int(request.data.get('minutes', 0))
        user    = request.user
        today   = date.today()
 
        if minutes <= 0:
            return Response({'detail': 'Invalid minutes'},
                            status=status.HTTP_400_BAD_REQUEST)
 
        # Record session
        from apps.coins.models import ReadingSession
        story = Story.objects.filter(slug=slug).first() if slug else None
        session, _ = ReadingSession.objects.get_or_create(
            user=user, date=today,
            defaults={'story': story, 'chapter': chapter, 'minutes': 0})
        session.minutes += minutes
        session.save()
 
        # Check reading milestones and award coins
        milestones = [
            (5, 5), (10, 5), (30, 10), (60, 20), (120, 35), (180, 50)
        ]
        coins_awarded = 0
        total_today = session.minutes
 
        for mins, coins in milestones:
            # Check if milestone newly crossed
            prev_total = total_today - minutes
            if prev_total < mins <= total_today:
                # Award if not already claimed today
                key = f'reading_{mins}'
                if not DailyRewardClaim.objects.filter(
                        user=user, claim_type=key, claimed_at=today).exists():
                    user.add_coins(coins)
                    DailyRewardClaim.objects.create(
                        user=user, claim_type=key, coins=coins)
                    coins_awarded += coins
 
        return Response({
            'total_minutes_today': total_today,
            'coins_awarded':       coins_awarded,
            'new_balance':         user.coin_balance,
        })
 
 
# ── Reading Stats ─────────────────────────────────────────────────────────────
class ReadingStatsView(APIView):
    """GET /api/reading/stats/"""
    permission_classes = [permissions.IsAuthenticated]
 
    def get(self, request):
        from apps.coins.models import ReadingSession
        user  = request.user
        today = date.today()
 
        # Last 7 days
        week_stats = []
        streak = 0
        goal   = int(request.query_params.get('goal', 30))
 
        for i in range(6, -1, -1):
            d    = today - timedelta(days=i)
            mins = ReadingSession.objects.filter(
                user=user, date=d).aggregate(
                    t=Sum('minutes'))['t'] or 0
            week_stats.append({
                'date':    str(d),
                'minutes': mins,
                'met_goal': mins >= goal,
            })
 
        # Calculate current streak
        check = today
        while True:
            mins = ReadingSession.objects.filter(
                user=user, date=check).aggregate(
                    t=Sum('minutes'))['t'] or 0
            if mins >= goal:
                streak += 1
                check  -= timedelta(days=1)
            else:
                break
 
        today_mins = ReadingSession.objects.filter(
            user=user, date=today).aggregate(
                t=Sum('minutes'))['t'] or 0
 
        return Response({
            'today_minutes': today_mins,
            'streak':        streak,
            'week':          week_stats,
            'goal_met':      today_mins >= goal,
        })
 
 
# ── Reading Schedule ──────────────────────────────────────────────────────────
class ReadingScheduleView(APIView):
    """
    GET  /api/reading/schedule/  — get user's schedule
    POST /api/reading/schedule/  — save schedule
    """
    permission_classes = [permissions.IsAuthenticated]
 
    def get(self, request):
        from apps.coins.models import ReadingSchedule
        sched = ReadingSchedule.objects.filter(
            user=request.user).first()
        if not sched:
            return Response({
                'enabled': False, 'hour': 21, 'minute': 0,
                'days': [True]*7, 'goal_minutes': 30,
                'goal_reminder': True,
            })
        return Response({
            'enabled':       sched.enabled,
            'hour':          sched.hour,
            'minute':        sched.minute,
            'days':          sched.days,
            'goal_minutes':  sched.goal_minutes,
            'goal_reminder': sched.goal_reminder,
        })
 
    def post(self, request):
        from apps.coins.models import ReadingSchedule
        sched, _ = ReadingSchedule.objects.get_or_create(
            user=request.user)
        sched.enabled       = request.data.get('enabled', False)
        sched.hour          = int(request.data.get('hour', 21))
        sched.minute        = int(request.data.get('minute', 0))
        sched.days          = request.data.get('days', [True]*7)
        sched.goal_minutes  = int(request.data.get('goal_minutes', 30))
        sched.goal_reminder = request.data.get('goal_reminder', True)
        sched.save()
        return Response({'success': True})



class VerifyPurchaseView(APIView):
     permission_classes = [permissions.IsAuthenticated]

     def post(self, request):
         product_id  = request.data.get('product_id')
         receipt     = request.data.get('receipt')
         platform    = request.data.get('platform', 'android')
         purchase_id = request.data.get('purchase_id', '')

         # For subscriptions: activate VIP
         if product_id in ['novelux_vip_monthly', 'novelux_vip_yearly', 'novelux_vip_weekly']:
             request.user.is_vip = True
             request.user.vip_plan = product_id
             request.user.save()
             return Response({'is_vip': True, 'plan_id': product_id})

         # For coin packs: credit coins
         coin_map = {
             'novelux_coins_100':  100,
             'novelux_coins_500':  500,
             'novelux_coins_1200': 1200,
             'novelux_coins_3000': 3000,
         }
         coins = coin_map.get(product_id, 0)
         if coins > 0:
             request.user.add_coins(coins)
         return Response({'coins_granted': coins})