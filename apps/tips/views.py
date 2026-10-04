from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Tip, GIFTS, FLOWER, LABEL_BY_COINS
from .serializers import TipSerializer, SendTipSerializer, GiftIntentSerializer
from . import services
from apps.stories.models import Story
from apps.chapters.models import Chapter
from apps.notifications.services import on_tip_received

User = get_user_model()


def _find_chapter(story, data):
    if data.get('chapter_id'):
        return Chapter.objects.filter(pk=data['chapter_id'], story=story).first()
    if data.get('chapter_number'):
        return Chapter.objects.filter(story=story, chapter_number=data['chapter_number']).first()
    return None


class SendTipView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_slug):
        story      = get_object_or_404(Story, slug=story_slug)
        serializer = SendTipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data  = serializer.validated_data
        coins = data['coins_amount']
        label = data['gift_label']

        if request.user.pk == story.author_id:
            return Response({'detail': 'You cannot tip your own story.'}, status=400)

        chapter = _find_chapter(story, data)

        author_cut = 0
        with transaction.atomic():
            if coins:
                # Lock both rows so concurrent tips can't overspend or lose credits.
                users  = User.objects.select_for_update().in_bulk([request.user.pk, story.author_id])
                sender = users[request.user.pk]
                author = users[story.author_id]

                if not sender.deduct_coins(coins, reason=f'{label} for {story.title}'):
                    return Response({'detail': 'Insufficient coins.'}, status=402)

                author_cut = int(coins * settings.TIP_AUTHOR_SHARE)
                author.add_coins(author_cut, reason=f'{label} received for {story.title}')
                User.objects.filter(pk=author.pk).update(
                    total_tips_received=F('total_tips_received') + coins
                )

                if hasattr(author, 'author_profile'):
                    earned = Decimal(author_cut) / 100
                    type(author.author_profile).objects.filter(pk=author.author_profile.pk).update(
                        pending_payout=F('pending_payout') + earned,
                        total_earnings=F('total_earnings') + earned,
                    )

                Story.objects.filter(pk=story.pk).update(total_tips=F('total_tips') + coins)

            tip = Tip.objects.create(
                sender=request.user,
                recipient_id=story.author_id,
                story=story,
                chapter=chapter,
                coins_amount=coins,
                gift_label=label,
                message=data.get('message', ''),
            )

            transaction.on_commit(lambda: on_tip_received(
                author=story.author,
                tipper_name=request.user.username,
                gift_label=label,
                story_title=story.title,
            ))

        return Response({
            'detail':        f'You sent a {label}!',
            'tip_id':        tip.pk,
            'gift_label':    label,
            'coins_spent':   coins,
            'author_earned': author_cut,
        }, status=201)


class GiftIntentView(APIView):
    """POST /api/tips/<slug>/gift/ — start a real-money gift.

    Creates a pending Tip and returns the store product to buy. After the
    store purchase the app calls GiftConfirmView; if it never does, the
    RevenueCat webhook completes the newest pending intent instead.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_slug):
        story      = get_object_or_404(Story, slug=story_slug)
        serializer = GiftIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data  = serializer.validated_data
        label = data['gift_label']

        if request.user.pk == story.author_id:
            return Response({'detail': 'You cannot tip your own story.'}, status=400)

        tip = Tip.objects.create(
            sender=request.user,
            recipient_id=story.author_id,
            story=story,
            chapter=_find_chapter(story, data),
            coins_amount=0,
            gift_label=label,
            message=data.get('message', ''),
            status=Tip.STATUS_PENDING,
        )
        return Response({'intent_id': tip.pk, 'product_id': GIFTS[label].product_id}, status=201)


class GiftConfirmView(APIView):
    """POST /api/tips/gift/<id>/confirm/   — after the store purchase succeeds.
    DELETE /api/tips/gift/<id>/confirm/   — purchase cancelled/failed; drop the intent.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.coins.views import _fetch_rc_subscriber
        get_object_or_404(Tip, pk=pk, sender=request.user)

        subscriber = _fetch_rc_subscriber(str(request.user.pk))
        if subscriber is None:
            return Response({'detail': 'Could not verify purchase with RevenueCat'}, status=502)

        tip  = services.confirm_gift(pk, request.user, subscriber)
        done = tip.status == Tip.STATUS_COMPLETED
        return Response({
            'status':     tip.status,
            'gift_label': tip.gift_label,
            'detail':     f'You sent a {tip.gift_label}!' if done
                          else 'Payment received — your gift will appear shortly.',
        }, status=200 if done else 202)

    def delete(self, request, pk):
        Tip.objects.filter(pk=pk, sender=request.user, status=Tip.STATUS_PENDING).delete()
        return Response(status=204)


class StoryTopTippersView(APIView):
    """GET /api/tips/<slug>/top-tippers/

    One flat list. Each supporter appears up to twice:
      • a Gratuity entry (total_coins == gift_points > 0) ranked by gift_points
      • a Flowers entry  (total_coins == 0) ranked by count
    The app splits the two boards on total_coins, so older builds keep working.
    """
    permission_classes = [permissions.AllowAny]
    LIMIT = 20

    def get(self, request, story_slug):
        story = get_object_or_404(Story, slug=story_slug)
        rows  = (
            Tip.objects
            .filter(story=story, status=Tip.STATUS_COMPLETED)
            .values('sender', 'gift_label', 'coins_amount')
            .annotate(n=Sum('quantity'))
        )

        gratuity = defaultdict(lambda: {'gift_points': 0, 'count': 0})
        flowers  = defaultdict(int)
        for r in rows:
            label = r['gift_label'] or LABEL_BY_COINS.get(r['coins_amount'], '')
            if label not in GIFTS:
                continue
            if label == FLOWER:
                flowers[r['sender']] += r['n']
                continue
            g = gratuity[r['sender']]
            g['gift_points'] += GIFTS[label].points * r['n']
            g['count']       += r['n']

        top_gratuity = sorted(gratuity.items(),
                              key=lambda kv: kv[1]['gift_points'],
                              reverse=True)[:self.LIMIT]
        top_flowers  = sorted(flowers.items(), key=lambda kv: kv[1], reverse=True)[:self.LIMIT]

        user_ids = {uid for uid, _ in top_gratuity} | {uid for uid, _ in top_flowers}
        users    = User.objects.in_bulk(user_ids)

        def user_json(uid):
            u = users.get(uid)
            if u is None:
                return None
            return {
                'id':       u.pk,
                'username': u.username,
                'avatar':   request.build_absolute_uri(u.avatar.url) if u.avatar else '',
            }

        result = []
        for uid, g in top_gratuity:
            if (u := user_json(uid)):
                # Real-money gifts carry no coins, so total_coins mirrors the
                # points — older builds rank and label the board by it.
                result.append({'user': u, **g, 'total_coins': g['gift_points']})
        for uid, n in top_flowers:
            if (u := user_json(uid)):
                result.append({'user': u, 'total_coins': 0, 'gift_points': 0, 'count': n})
        return Response(result)


class MyTipsSentView(generics.ListAPIView):
    serializer_class   = TipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tip.objects.filter(sender=self.request.user).select_related('recipient', 'story')


class MyTipsReceivedView(generics.ListAPIView):
    serializer_class   = TipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tip.objects.filter(recipient=self.request.user).select_related('sender', 'story')
