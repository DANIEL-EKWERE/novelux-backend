from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Tip
from .serializers import TipSerializer, SendTipSerializer
from apps.stories.models import Story
from apps.chapters.models import Chapter
from apps.notifications.tasks import notify_tip_received


from apps.notifications.services import on_tip_received


class SendTipView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_slug):
        story      = get_object_or_404(Story, slug=story_slug)
        author     = story.author
        serializer = SendTipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if request.user == author:
            return Response({'detail': 'You cannot tip your own story.'}, status=400)

        coins = data['coins_amount']
        if not request.user.deduct_coins(coins, reason=f'Tip for {story.title}'):

            return Response({'detail': 'Insufficient coins.'}, status=402)

        # Author gets TIP_AUTHOR_SHARE (85%)
        author_cut = int(coins * settings.TIP_AUTHOR_SHARE)
        author.add_coins(author_cut, reason=f'Tip received for {story.title}')
        author.total_tips_received += coins
        author.save(update_fields=['total_tips_received'])
        

        # Update author profile earnings
        from decimal import Decimal
        if hasattr(author, 'author_profile'):
            author.author_profile.pending_payout += Decimal(author_cut) / 100
            author.author_profile.total_earnings  += Decimal(author_cut) / 100
            author.author_profile.save(update_fields=['pending_payout', 'total_earnings'])

        chapter = None
        if data.get('chapter_id'):
            chapter = Chapter.objects.filter(pk=data['chapter_id'], story=story).first()

        tip = Tip.objects.create(
            sender=request.user,
            recipient=author,
            story=story,
            chapter=chapter,
            coins_amount=coins,
            message=data.get('message', ''),
        )

        Story.objects.filter(pk=story.pk).update(total_tips=Story.total_tips.__class__('total_tips') if False else __import__('django.db.models', fromlist=['F']).F('total_tips') + coins)
        notify_tip_received.delay(tip.id)
        on_tip_received(
        author=story.author,
        tipper_name=request.user.username,
        gift_label='gift_label',
        story_title=story.title,
        )

        return Response({
            'detail':       f'You tipped {coins} coins!',
            'coins_spent':  coins,
            'author_earned': author_cut,
        }, status=201)


class StoryTopTippersView(generics.ListAPIView):
    """Leaderboard of top tippers for a story."""
    permission_classes = [permissions.AllowAny]

    def list(self, request, story_slug):
        story = get_object_or_404(Story, slug=story_slug)
        top   = (
            Tip.objects
            .filter(story=story)
            .values('sender__id', 'sender__username', 'sender__avatar')
            .annotate(total=Sum('coins_amount'))
            .order_by('-total')[:10]
        )
        return Response(list(top))


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


class TopTippersView(APIView):
    # \"\"\"GET /api/tips/<slug>/top-tippers/\"\"\"
    permission_classes = [permissions.AllowAny]
 
    def get(self, request, slug):
        from apps.stories.models import Story
        story = get_object_or_404(Story, slug=slug)
 
        # Aggregate tips per user for this story
        tippers = (
            Tip.objects
            .filter(story=story)
            .values('sender')
            .annotate(total_coins=Sum('coins_amount'))
            .order_by('-total_coins')[:20]
        )
 
        result = []
        for t in tippers:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(pk=t['sender'])
                avatar = ''
                if hasattr(user, 'avatar') and user.avatar:
                    avatar = request.build_absolute_uri(user.avatar.url)
                result.append({
                    'user': {
                        'id':       user.pk,
                        'username': user.username,
                        'avatar':   avatar,
                    },
                    'total_coins': t['total_coins'],
                })
            except Exception:
                continue
 
        return Response(result)