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
        request.user.expire_bonus()
        expiring = request.user.bonus_expiring
        return Response({
            'coin_balance':  request.user.coin_balance,
            'bonus_balance': request.user.bonus_balance,
            'total_balance': request.user.total_balance,
            # Soonest-expiring bonus, e.g. {"amount": 12, "expires_at": "…"}
            'bonus_expiring': ({'amount': expiring['amount'],
                                'expires_at': expiring['expires_at'].isoformat()}
                               if expiring else None),
            'bonus_valid_days': 7,
            'is_vip':        request.user.is_vip,
            'vip_expires':   request.user.vip_expires,
        })


class CoinTransactionHistoryView(generics.ListAPIView):
    serializer_class   = CoinTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        return CoinTransaction.objects.filter(
            user=self.request.user,
            created_at__gte=cutoff,
        ).order_by('-created_at')


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
        now  = timezone.now()
        is_vip = bool(user.vip_expires and user.vip_expires > now)
        # Only report a plan while that subscription is what's actually
        # giving VIP — VIP redeemed with coins has no plan, and an old,
        # expired subscription must not be shown as the current one.
        sub_active = bool(
            sub and sub.is_active and sub.plan
            and sub.expires_at and sub.expires_at > now
        )

        return Response({
            'is_vip':      is_vip,
            'plan':        sub.plan.plan_id if sub_active else None,
            'plan_label':  sub.plan.label if sub_active else None,
            'source':      ('subscription' if sub_active else 'coins') if is_vip else None,
            'expires_at':  user.vip_expires if is_vip else None,
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
    Body: { "claim_type": "signin" | "notification" | "ad" | "checkin_ad" | "reading",
            "coins": <only used for "reading"> }

    Amounts are set here, not by the app (except reading milestones, which are
    capped per day). All rewards go to the bonus balance. Daily check-ins use
    POST /api/coins/checkin/ instead.
    """
    permission_classes = [permissions.IsAuthenticated]

    #   fixed      — coins paid (None = amount from the request, capped)
    #   once_ever  — one claim per account
    #   per_day    — claims allowed per day
    #   daily_cap  — most coins per day (for request-supplied amounts)
    REWARDS = {
        'signin':       {'fixed': 5,    'once_ever': True},
        'notification': {'fixed': 10,   'once_ever': True},
        'ad':           {'fixed': 1,    'per_day': 10},
        'checkin_ad':   {'fixed': 5,    'per_day': 1, 'needs_checkin': True},
        'reading':      {'fixed': None, 'daily_cap': 125},
    }

    def post(self, request):
        from django.db import transaction
        from django.db.models import Sum
        from apps.coins.models import DailyRewardClaim, CheckinStreak

        claim_type = request.data.get('claim_type', '')
        rules = self.REWARDS.get(claim_type)
        if rules is None:
            return Response({'detail': 'Invalid claim type'}, status=status.HTTP_400_BAD_REQUEST)

        today = date.today()
        with transaction.atomic():
            # Lock the user row so parallel taps can't each pass the limits.
            user = type(request.user).objects.select_for_update().get(pk=request.user.pk)
            claims = DailyRewardClaim.objects.filter(user=user, claim_type=claim_type)

            if rules.get('once_ever') and claims.exists():
                return Response({'detail': 'Already claimed'}, status=status.HTTP_400_BAD_REQUEST)
            if rules.get('per_day') and claims.filter(claimed_at=today).count() >= rules['per_day']:
                return Response({'detail': 'Daily limit reached — come back tomorrow'},
                                status=status.HTTP_400_BAD_REQUEST)
            if rules.get('needs_checkin') and not CheckinStreak.objects.filter(
                    user=user, last_checkin=today).exists():
                return Response({'detail': 'Check in first'}, status=status.HTTP_400_BAD_REQUEST)

            coins = rules['fixed']
            if coins is None:
                try:
                    coins = int(request.data.get('coins', 0))
                except (TypeError, ValueError):
                    coins = 0
                used = claims.filter(claimed_at=today).aggregate(t=Sum('coins'))['t'] or 0
                coins = min(coins, rules['daily_cap'] - used)
                if coins <= 0:
                    return Response({'detail': 'Daily limit reached — come back tomorrow'},
                                    status=status.HTTP_400_BAD_REQUEST)

            user.add_bonus(coins, reason=f'Reward: {claim_type}')
            DailyRewardClaim.objects.create(user=user, claim_type=claim_type, coins=coins)

        claimed_today = DailyRewardClaim.objects.filter(
            user=user, claim_type=claim_type, claimed_at=today).count()
        return Response({
            'success':       True,
            'claim_type':    claim_type,
            'coins_earned':  coins,
            'bonus_added':   coins,
            'claimed_today': claimed_today,
            'bonus_balance': user.bonus_balance,
            'coin_balance':  user.coin_balance,
        })


def _get_or_create_streak(user):
    from apps.coins.models import CheckinStreak
    streak, _ = CheckinStreak.objects.get_or_create(user=user)
    return streak


class CheckinStatusView(APIView):
    """
    GET /api/coins/checkin/
    Returns today's check-in state and streak info — call this on app open.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.coins.models import STREAK_REWARDS
        today  = date.today()
        streak = _get_or_create_streak(request.user)

        claimed_today = streak.last_checkin == today

        # If last checkin was 2+ days ago, streak would reset on next claim
        if streak.last_checkin and streak.last_checkin < today - timedelta(days=1):
            effective_streak = 0
        else:
            effective_streak = streak.current_streak

        next_reward = STREAK_REWARDS[effective_streak % len(STREAK_REWARDS)]

        return Response({
            'claimed_today':   claimed_today,
            'current_streak':  effective_streak,
            'longest_streak':  streak.longest_streak,
            'total_checkins':  streak.total_checkins,
            'next_reward':     next_reward,
            'reward_schedule': STREAK_REWARDS,
        })


class CheckinView(APIView):
    """
    POST /api/coins/checkin/
    Claims today's check-in reward. Streak increments if yesterday was claimed,
    resets to 1 if a day was missed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.coins.models import CheckinStreak, DailyRewardClaim, STREAK_REWARDS
        user  = request.user
        today = date.today()

        streak = _get_or_create_streak(user)

        if streak.last_checkin == today:
            return Response({'detail': 'Already checked in today.'}, status=400)

        # Determine new streak value
        yesterday = today - timedelta(days=1)
        if streak.last_checkin == yesterday:
            new_streak = streak.current_streak + 1
        else:
            new_streak = 1  # missed a day — reset

        reward = STREAK_REWARDS[(new_streak - 1) % len(STREAK_REWARDS)]

        # Update streak record
        streak.current_streak = new_streak
        streak.longest_streak = max(streak.longest_streak, new_streak)
        streak.last_checkin   = today
        streak.total_checkins += 1
        streak.save()

        user.add_bonus(reward, reason=f'Daily check-in (day {new_streak})')

        # Record in claim history
        DailyRewardClaim.objects.create(user=user, claim_type='checkin', coins=reward)

        return Response({
            'success':        True,
            'coins_earned':   reward,
            'current_streak': new_streak,
            'longest_streak': streak.longest_streak,
            'total_checkins': streak.total_checkins,
            'bonus_balance':  user.bonus_balance,
            'coin_balance':   user.coin_balance,
            'next_reward':    STREAK_REWARDS[new_streak % len(STREAK_REWARDS)],
        })


# ── Tasks ─────────────────────────────────────────────────────────────────────

MAX_TASK_ATTEMPTS = 5   # wrong answers allowed on a response task


def _answer_matches(given, expected):
    """Case- and spacing-insensitive match against the admin's answer(s),
    separated by |. A blank expected answer accepts any answer."""
    norm = lambda v: ' '.join(str(v).lower().split())
    accepted = [norm(a) for a in (expected or '').split('|') if norm(a)]
    return not accepted or norm(given) in accepted


BONUS_VALID_DAYS = 7   # shown with ad rewards ("valid for 7 days")


def _ad_task_payload(task, progress):
    watched = progress.ads_watched if progress else 0
    return {
        'id':           task.id,
        'title':        task.title,
        'ads_required': task.ads_required,
        'ads_watched':  min(watched, task.ads_required),
        'reward_coins': task.reward_coins,
        'completed':    bool(progress and progress.claimed_at),
        'valid_days':   BONUS_VALID_DAYS,
    }


class AdTaskListView(APIView):
    """GET /api/coins/ad-tasks/ — the ad tasks with today's progress."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.coins.models import AdRewardTask, AdTaskProgress
        tasks = list(AdRewardTask.objects.filter(is_active=True))
        progress = {p.task_id: p for p in AdTaskProgress.objects.filter(
            user=request.user, task__in=tasks, date=date.today())}
        return Response({'results': [_ad_task_payload(t, progress.get(t.id)) for t in tasks]})


class AdTaskWatchedView(APIView):
    """
    POST /api/coins/ad-tasks/<id>/watched/
    Call after each rewarded ad finishes. Counts one ad toward the task; when
    the last required ad is watched the bonus is paid (once a day per task).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from django.db import transaction
        from apps.coins.models import AdRewardTask, AdTaskProgress
        task = AdRewardTask.objects.filter(pk=pk, is_active=True).first()
        if task is None:
            return Response({'detail': 'Task not found.'}, status=404)

        with transaction.atomic():
            progress, _ = AdTaskProgress.objects.select_for_update().get_or_create(
                user=request.user, task=task, date=date.today())
            if progress.claimed_at:
                return Response({'detail': 'Already completed today — come back tomorrow.',
                                 **_ad_task_payload(task, progress)}, status=400)
            progress.ads_watched += 1
            coins_earned = 0
            if progress.ads_watched >= task.ads_required:
                progress.claimed_at = timezone.now()
                coins_earned = task.reward_coins
                request.user.add_bonus(coins_earned, reason=f'Ad reward: {task.ads_required} ad(s)')
            progress.save()

        return Response({**_ad_task_payload(task, progress), 'coins_earned': coins_earned,
                         'bonus_balance': request.user.bonus_balance})


class TaskStartView(APIView):
    """
    POST /api/coins/tasks/<id>/start/
    Action tasks (General benefits): records that the reader tapped Go.
    Claim unlocks `wait_seconds` later (see TaskCompleteView).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.coins.models import Task, UserTask
        task = Task.objects.filter(pk=pk, is_active=True, task_type=Task.TYPE_ACTION).first()
        if task is None:
            return Response({'detail': 'Task not found.'}, status=404)
        now = timezone.now()
        ut, _ = UserTask.objects.get_or_create(user=request.user, task=task)
        if ut.status == UserTask.STATUS_CLAIMED:
            reopen = (task.is_repeatable and ut.claimed_at and
                      ut.claimed_at + timedelta(hours=task.repeat_cooldown_hours) <= now)
            if not reopen:
                return Response({'detail': 'Task already completed.'}, status=400)
            ut.status = UserTask.STATUS_PENDING
        # Start the wait on the first Go of this round. Re-tapping Go keeps the
        # original time, so it can't restart or extend the wait.
        if ut.started_at is None or (ut.claimed_at and ut.started_at <= ut.claimed_at):
            ut.started_at = now
        ut.save(update_fields=['status', 'started_at'])
        return Response({
            'started_at': ut.started_at.isoformat(),
            'claim_available_at': (ut.started_at + timedelta(seconds=task.wait_seconds)).isoformat(),
            'wait_seconds': task.wait_seconds,
        })


class TaskListView(APIView):
    """
    GET /api/coins/tasks/
    Returns all active tasks with the current user's completion status.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.coins.models import Task, UserTask
        from django.utils import timezone
        from django.db.models import Q

        now = timezone.now()
        tasks = Task.objects.filter(is_active=True).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )

        # Fetch this user's completions in one query
        user_task_map = {
            ut.task_id: ut
            for ut in UserTask.objects.filter(user=request.user, task__in=tasks)
        }

        data = []
        for t in tasks:
            ut = user_task_map.get(t.id)
            status, available_at = (ut.status if ut else 'pending'), None
            if ut and t.is_repeatable and ut.claimed_at:
                available_at = ut.claimed_at + timedelta(hours=t.repeat_cooldown_hours)
                if available_at <= now:
                    status, available_at = 'pending', None   # can be done again
            data.append({
                'id':           t.id,
                'title':        t.title,
                'description':  t.description,
                'task_type':    t.task_type,
                'reward_coins': t.reward_coins,
                'icon':         t.icon,
                'is_repeatable':t.is_repeatable,
                'expires_at':   t.expires_at.isoformat() if t.expires_at else None,
                'status':       status,
                'next_available_at': available_at.isoformat() if available_at else None,
                'launch_url':   t.launch_url,
                'wait_seconds': t.wait_seconds if t.task_type == Task.TYPE_ACTION else 0,
                'attempts_left': (max(MAX_TASK_ATTEMPTS - (ut.attempts if ut else 0), 0)
                                  if t.task_type == Task.TYPE_RESPONSE else None),
                'claim_available_at': (
                    (ut.started_at + timedelta(seconds=t.wait_seconds)).isoformat()
                    if ut and ut.started_at and status == 'pending' and t.task_type == Task.TYPE_ACTION
                    else None),
                'repeat_cooldown_hours': t.repeat_cooldown_hours if t.is_repeatable else None,
                'response':     ut.response if ut else '',
                'completed_at': ut.completed_at.isoformat() if ut and ut.completed_at else None,
                'claimed_at':   ut.claimed_at.isoformat() if ut and ut.claimed_at else None,
            })

        return Response({'count': len(data), 'results': data})


class TaskCompleteView(APIView):
    """
    POST /api/coins/tasks/<id>/complete/
    Marks a task as completed and immediately awards the coins.

    For action tasks:  body can be empty — just POST to mark done.
    For response tasks: body must include { "response": "..." }

    Reward is credited on completion. claimed status is set simultaneously.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.coins.models import Task, UserTask
        from django.db import IntegrityError, transaction
        from django.utils import timezone

        try:
            task = Task.objects.get(pk=pk, is_active=True)
        except Task.DoesNotExist:
            return Response({'detail': 'Task not found.'}, status=404)

        now = timezone.now()
        if task.expires_at and task.expires_at < now:
            return Response({'detail': 'This task has expired.'}, status=400)

        if task.task_type == Task.TYPE_RESPONSE:
            response_text = str(request.data.get('response', '')).strip()
            if not response_text:
                return Response({'detail': 'A response is required for this task.'}, status=400)
        else:
            response_text = ''

        user = request.user
        with transaction.atomic():
            # Lock this user's row for the task so two simultaneous requests
            # (a double tap) can't both pass the checks and pay twice.
            try:
                UserTask.objects.get_or_create(user=user, task=task)
            except IntegrityError:
                pass   # created by a concurrent request — lock it below
            ut = UserTask.objects.select_for_update().get(user=user, task=task)

            if ut.status in (UserTask.STATUS_COMPLETED, UserTask.STATUS_CLAIMED):
                if not task.is_repeatable:
                    return Response({'detail': 'Task already completed.'}, status=400)
                next_at = (ut.claimed_at or now) + timedelta(hours=task.repeat_cooldown_hours)
                if next_at > now:
                    return Response({
                        'detail': 'You can do this task again later.',
                        'next_available_at': next_at.isoformat(),
                    }, status=400)
                # A new round of a repeatable task
                ut.attempts, ut.started_at = 0, None

            if task.task_type == Task.TYPE_RESPONSE:
                if ut.attempts >= MAX_TASK_ATTEMPTS:
                    return Response({'detail': 'No tries left for this task.', 'attempts_left': 0}, status=400)
                if not _answer_matches(response_text, task.correct_answer):
                    ut.attempts += 1
                    ut.save(update_fields=['attempts'])
                    left = MAX_TASK_ATTEMPTS - ut.attempts
                    return Response({
                        'detail': ("That's not the right answer. " +
                                   (f'{left} tr{"y" if left == 1 else "ies"} left.' if left else 'No tries left.')),
                        'attempts_left': left,
                    }, status=400)
            elif task.wait_seconds:
                # Action tasks: the reader must tap Go, then wait before claiming
                if not ut.started_at:
                    return Response({'detail': 'Tap Go first.'}, status=400)
                ready_at = ut.started_at + timedelta(seconds=task.wait_seconds)
                if ready_at > now:
                    return Response({'detail': 'Almost there — you can claim in a moment.',
                                     'claim_available_at': ready_at.isoformat()}, status=400)

            ut.status       = UserTask.STATUS_CLAIMED
            ut.response     = response_text
            ut.completed_at = now
            ut.claimed_at   = now
            ut.save()

            # Rewards go to the bonus balance (like daily check-ins and ads),
            # not the purchased-coin balance.
            user.add_bonus(task.reward_coins, reason=f'Task: {task.title}')

        next_at = now + timedelta(hours=task.repeat_cooldown_hours) if task.is_repeatable else None
        return Response({
            'success':       True,
            'task_id':       task.id,
            'coins_earned':  task.reward_coins,
            'coin_balance':  user.coin_balance,
            'bonus_balance': user.bonus_balance,
            'total_balance': user.total_balance,
            'next_available_at': next_at.isoformat() if next_at else None,
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



# ── RevenueCat helpers ────────────────────────────────────────────────────────

RC_API_BASE = 'https://api.revenuecat.com/v1'


def _rc_base_id(product_id):
    """Google subs may arrive as 'productId:basePlanId' — strip the base plan."""
    return (product_id or '').split(':')[0]


def _parse_rc_date(value):
    """RevenueCat dates are ISO-8601 strings like '2026-07-08T12:00:00Z'."""
    if not value:
        return None
    from django.utils.dateparse import parse_datetime
    return parse_datetime(value.replace('Z', '+00:00'))


def _fetch_rc_subscriber(app_user_id):
    """GET the subscriber from RevenueCat's REST API. Returns dict or None."""
    import logging
    import requests as req
    from urllib.parse import quote
    log = logging.getLogger('revenuecat')
    if not settings.REVENUECAT_SECRET_KEY:
        log.error('REVENUECAT_SECRET_KEY is not set — cannot verify purchases')
        return None
    try:
        r = req.get(
            f'{RC_API_BASE}/subscribers/{quote(app_user_id, safe="")}',
            headers={'Authorization': f'Bearer {settings.REVENUECAT_SECRET_KEY}'},
            timeout=15,
        )
        # 200 = existing subscriber; 201 = RevenueCat auto-created one
        # (i.e. this app_user_id had no purchases yet — still a valid response)
        if r.status_code in (200, 201):
            return r.json().get('subscriber', {})
        log.error(
            'RevenueCat subscriber lookup for %r failed: HTTP %s %s',
            app_user_id, r.status_code, r.text[:300],
        )
    except Exception:
        log.exception('RevenueCat subscriber lookup for %r raised', app_user_id)
    return None


class VerifyPurchaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Maps store product_id → coin pack details
    COIN_PRODUCTS = {
        'novelux_coins_100':  {'coins': 100,  'price': 0.99},
        'novelux_coins_500':  {'coins': 500,  'price': 4.99},
        'novelux_coins_1000': {'coins': 1000, 'price': 9.99},
        'novelux_coins_2500': {'coins': 2500, 'price': 24.99},
        'novelux_coins_5000': {'coins': 5000, 'price': 49.99},
    }

    # Maps store product_id → SubscriptionPlan.plan_id
    VIP_PRODUCTS = {
        'novelux_vip_weekly':    'vip_weekly',
        'novelux_vip_monthly':   'vip_monthly',
        'novelux_vip_quarterly': 'vip_quarterly',
        'novelux_vip_yearly':    'vip_yearly',
    }

    def post(self, request):
        product_id = _rc_base_id(request.data.get('product_id', ''))
        platform   = request.data.get('platform', '').lower()

        if not product_id or platform not in ('ios', 'android'):
            return Response(
                {'error': 'product_id and platform (ios/android) are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The app purchases through RevenueCat, which verifies receipts with
        # Apple/Google itself. We confirm the purchase against RevenueCat's
        # REST API for the *authenticated* user — the app logs in to RevenueCat
        # with our user id, so this lookup is server-authoritative and ignores
        # whatever ids the client sent.
        subscriber = _fetch_rc_subscriber(str(request.user.pk))
        if subscriber is None:
            return Response(
                {'error': 'Could not verify purchase with RevenueCat'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if product_id in self.COIN_PRODUCTS:
            return self._handle_rc_coins(request.user, product_id, subscriber)
        if product_id in self.VIP_PRODUCTS:
            return self._handle_rc_vip(request.user, product_id, subscriber)

        return Response(
            {'error': f'Unknown product: {product_id}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── RevenueCat verification ───────────────────────────────────────────────

    def _handle_rc_coins(self, user, product_id, subscriber):
        transactions = None
        for pid, txs in subscriber.get('non_subscriptions', {}).items():
            if _rc_base_id(pid) == product_id:
                transactions = txs
                break
        if not transactions:
            return Response(
                {'error': 'Purchase not found on RevenueCat'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The array ordering from RevenueCat isn't guaranteed, and a stale
        # response may not include the newest receipt yet — so instead of
        # assuming transactions[-1] is the new purchase, grant the newest
        # transaction we haven't redeemed yet. If everything is already
        # redeemed (usually because our webhook granted it first), fall
        # through with the newest transaction — _grant answers idempotently.
        pairs = [
            (tx, tx.get('store_transaction_id') or tx.get('id', ''))
            for tx in transactions
        ]
        pairs = [(tx, tx_id) for tx, tx_id in pairs if tx_id]
        if not pairs:
            return Response(
                {'error': 'Purchase not found on RevenueCat'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pairs.sort(key=lambda pair: pair[0].get('purchase_date') or '')

        redeemed = set(
            Purchase.objects.filter(iap_transaction_id__in=[i for _, i in pairs])
            .values_list('iap_transaction_id', flat=True)
        )
        unredeemed = [pair for pair in pairs if pair[1] not in redeemed]
        _, transaction_id = (unredeemed or pairs)[-1]
        return self._grant(user, product_id, transaction_id)

    def _handle_rc_vip(self, user, product_id, subscriber):
        sub = None
        for pid, data in subscriber.get('subscriptions', {}).items():
            if _rc_base_id(pid) == product_id:
                sub = data
                break
        if sub is None:
            return Response(
                {'error': 'Subscription not found on RevenueCat'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expires_at = _parse_rc_date(sub.get('expires_date'))
        if expires_at is None or expires_at <= timezone.now():
            return Response(
                {'error': 'Subscription is not active'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_id = (
            sub.get('store_transaction_id')
            or f'rc:{user.pk}:{product_id}:{sub.get("purchase_date", "")}'
        )
        return self._grant(user, product_id, transaction_id, expires_at=expires_at)

    # ── Grant ─────────────────────────────────────────────────────────────────

    def _grant(self, user, product_id, transaction_id, expires_at=None):
        # Replay protection. A transaction we already processed for THIS user
        # is not an error — the webhook usually grants before the app verifies,
        # so answer idempotently with the current state. Only a transaction
        # redeemed by a DIFFERENT account is rejected.
        existing = (
            Purchase.objects.filter(iap_transaction_id=transaction_id).first()
            if transaction_id else None
        )
        if existing:
            if existing.user_id != user.pk:
                return Response(
                    {'error': 'This purchase has already been redeemed'},
                    status=status.HTTP_409_CONFLICT,
                )
            user.refresh_from_db()
            if product_id in self.COIN_PRODUCTS:
                return Response({
                    'coins_granted': existing.coins_granted,
                    'new_balance': user.coin_balance,
                    'already_granted': True,
                })
            return Response({
                'is_vip': user.is_vip,
                'plan_id': self.VIP_PRODUCTS.get(product_id),
                'expires_at': user.vip_expires.isoformat() if user.vip_expires else None,
                'coins_granted': existing.coins_granted,
                'already_granted': True,
            })

        if product_id in self.COIN_PRODUCTS:
            return self._grant_coins(user, product_id, transaction_id)
        if product_id in self.VIP_PRODUCTS:
            return self._grant_vip(user, product_id, transaction_id, expires_at=expires_at)

        return Response(
            {'error': f'Unknown product: {product_id}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _grant_coins(self, user, product_id, transaction_id):
        meta = self.COIN_PRODUCTS[product_id]
        Purchase.objects.create(
            user=user,
            purchase_type=Purchase.TYPE_COIN_PACK,
            coins_granted=meta['coins'],
            amount_paid_usd=meta['price'],
            iap_transaction_id=transaction_id,
            status=Purchase.STATUS_COMPLETED,
            completed_at=timezone.now(),
        )
        user.add_coins(meta['coins'], reason=f'IAP coin pack: {product_id}')
        return Response({
            'coins_granted': meta['coins'],
            'new_balance': user.coin_balance,
        })

    def _grant_vip(self, user, product_id, transaction_id, expires_at=None):
        from datetime import timedelta
        plan_id = self.VIP_PRODUCTS[product_id]
        try:
            plan = SubscriptionPlan.objects.get(plan_id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Subscription plan not found'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if expires_at is None:
            expires_at = timezone.now() + timedelta(days=plan.duration_days)

        # Same billing period already granted (e.g. webhook and app verify
        # racing each other with different transaction ids) — don't credit twice
        existing = getattr(user, 'subscription', None)
        if (existing and existing.is_active and existing.plan_id == plan.pk
                and existing.expires_at is not None
                and abs((existing.expires_at - expires_at).total_seconds()) < 120):
            return Response({
                'is_vip': True,
                'plan_id': plan_id,
                'expires_at': expires_at.isoformat(),
                'coins_granted': 0,
            })

        total_coins = plan.coins_per_month + plan.bonus_coins

        Purchase.objects.create(
            user=user,
            purchase_type=Purchase.TYPE_SUBSCRIPTION,
            subscription_plan=plan,
            coins_granted=total_coins,
            amount_paid_usd=plan.price_usd,
            iap_transaction_id=transaction_id,
            status=Purchase.STATUS_COMPLETED,
            completed_at=timezone.now(),
        )
        Subscription.objects.update_or_create(
            user=user,
            defaults={
                'plan': plan,
                'expires_at': expires_at,
                'is_active': True,
                'auto_renew': True,
            },
        )
        user.is_vip    = True
        user.vip_expires = expires_at
        user.save(update_fields=['is_vip', 'vip_expires'])
        user.add_coins(total_coins, reason=f'IAP VIP: {plan.label}')

        return Response({
            'is_vip': True,
            'plan_id': plan_id,
            'expires_at': expires_at.isoformat(),
            'coins_granted': total_coins,
        })


# ── RevenueCat Webhook ────────────────────────────────────────────────────────
class RedeemView(APIView):
    """
    GET  /api/coins/redeem/  — list available packages
    POST /api/coins/redeem/  — redeem a package by key
    Body: { "package": "vip_30m" }
    """
    permission_classes = [permissions.IsAuthenticated]

    PACKAGES = {
        'vip_30m':       {'benefit': 'vip',       'minutes': 30,  'cost': 300,  'label': '30 Mins of VIP',        'desc': 'Unlock VIP instantly.'},
        'vip_1h':        {'benefit': 'vip',       'minutes': 60,  'cost': 570,  'label': '1 Hour of VIP',         'desc': 'Unlock VIP instantly.'},
        'vip_2h':        {'benefit': 'vip',       'minutes': 120, 'cost': 1000, 'label': '2 Hours of VIP',        'desc': 'Unlock VIP instantly.'},
        'adfree_30m':    {'benefit': 'ad_free',   'minutes': 30,  'cost': 100,  'label': '30 Mins of Ad-Free',    'desc': 'Enjoy Ad-Free reading instantly.'},
        'adfree_1h':     {'benefit': 'ad_free',   'minutes': 60,  'cost': 190,  'label': '1 Hour of Ad-Free',     'desc': 'Enjoy Ad-Free reading instantly.'},
        'adfree_2h':     {'benefit': 'ad_free',   'minutes': 120, 'cost': 330,  'label': '2 Hours of Ad-Free',    'desc': 'Enjoy Ad-Free reading instantly.'},
        'audiobook_30m': {'benefit': 'audiobook', 'minutes': 30,  'cost': 60,   'label': '30 Mins of Audiobooks', 'desc': 'Listen to audiobooks instantly.'},
        'audiobook_1h':  {'benefit': 'audiobook', 'minutes': 60,  'cost': 110,  'label': '1 Hour of Audiobooks',  'desc': 'Listen to audiobooks instantly.'},
        'audiobook_2h':  {'benefit': 'audiobook', 'minutes': 120, 'cost': 200,  'label': '2 Hours of Audiobooks', 'desc': 'Listen to audiobooks instantly.'},
    }

    def get(self, request):
        return Response({'success': True, 'packages': [
            {'key': k, **v} for k, v in self.PACKAGES.items()
        ]})

    def post(self, request):
        key = request.data.get('package', '')
        pkg = self.PACKAGES.get(key)
        if not pkg:
            return Response({'error': 'Invalid package.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        cost = pkg['cost']
        if user.total_balance < cost:
            return Response({'error': 'Insufficient coins.'}, status=status.HTTP_400_BAD_REQUEST)

        user.deduct_coins(cost, reason=f'Redeem: {pkg["label"]}')

        benefit  = pkg['benefit']
        minutes  = pkg['minutes']
        if benefit == 'vip':
            user.add_vip_time(minutes)
            expires = user.vip_expires
        elif benefit == 'ad_free':
            user.add_ad_free_time(minutes)
            expires = user.ad_free_expires
        else:
            user.add_audiobook_time(minutes)
            expires = user.audiobook_expires

        return Response({
            'success':    True,
            'label':      pkg['label'],
            'expires_at': expires,
            'coin_balance': user.coin_balance,
            'bonus_balance': user.bonus_balance,
        })


class RevenueCatWebhookView(APIView):
    """POST /api/coins/revenuecat-webhook/

    Configure in RevenueCat → Project settings → Integrations → Webhooks with
    the Authorization header value set to REVENUECAT_WEBHOOK_AUTH. This is the
    reliable channel for granting coins/VIP — it fires even if the app dies
    right after the store dialog.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        expected = settings.REVENUECAT_WEBHOOK_AUTH
        if not expected or request.headers.get('Authorization') != expected:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        event = request.data.get('event') or {}
        event_type = event.get('type', '')
        app_user_id = event.get('app_user_id') or ''
        product_id = _rc_base_id(event.get('product_id'))
        transaction_id = event.get('transaction_id') or event.get('id') or ''

        # Purchases made before login live on an anonymous RevenueCat id;
        # a TRANSFER event re-delivers them once the user logs in.
        if app_user_id.startswith('$RCAnonymousID:'):
            return Response({'ok': True})

        user = self._find_user(app_user_id)
        if user is None:
            # 200 so RevenueCat doesn't retry forever on unknown users
            return Response({'ok': True, 'detail': 'user not found'})

        granter = VerifyPurchaseView()

        from apps.tips.models import LABEL_BY_PRODUCT
        from apps.tips import services as gift_services

        if product_id in LABEL_BY_PRODUCT:
            # Real-money gift to an author (store consumable)
            if event_type == 'NON_RENEWING_PURCHASE':
                gift_services.handle_gift_webhook(
                    user, product_id, transaction_id, event.get('price'),
                    quantity=event.get('quantity') or 1)
            elif event_type == 'CANCELLATION':   # refund of a one-time purchase
                gift_services.refund_gift(transaction_id)

        elif (event_type == 'NON_RENEWING_PURCHASE'
                and product_id in VerifyPurchaseView.COIN_PRODUCTS):
            granter._grant(user, product_id, transaction_id)

        elif event_type in ('INITIAL_PURCHASE', 'RENEWAL', 'UNCANCELLATION',
                            'PRODUCT_CHANGE', 'TRANSFER'):
            new_product = _rc_base_id(event.get('new_product_id')) or product_id
            if new_product in VerifyPurchaseView.VIP_PRODUCTS:
                expires_at = None
                expires_ms = event.get('expiration_at_ms')
                if expires_ms:
                    from datetime import datetime, timezone as dt_timezone
                    expires_at = datetime.fromtimestamp(
                        expires_ms / 1000, tz=dt_timezone.utc)
                granter._grant(user, new_product, transaction_id,
                               expires_at=expires_at)

        elif event_type == 'CANCELLATION':
            # Auto-renew turned off — access continues until EXPIRATION
            sub = getattr(user, 'subscription', None)
            if sub:
                sub.auto_renew = False
                sub.cancelled_at = timezone.now()
                sub.save(update_fields=['auto_renew', 'cancelled_at'])

        elif event_type == 'EXPIRATION':
            sub = getattr(user, 'subscription', None)
            if sub:
                sub.is_active = False
                sub.save(update_fields=['is_active'])
            user.is_vip = False
            user.save(update_fields=['is_vip'])

        return Response({'ok': True})

    @staticmethod
    def _find_user(app_user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if app_user_id.isdigit():
            return User.objects.filter(pk=int(app_user_id)).first()
        return User.objects.filter(username=app_user_id).first()