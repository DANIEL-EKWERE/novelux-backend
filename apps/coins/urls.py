# from django.urls import path
# from . import views
# from .views import (
#     VipStatusView,
#     CancelSubscriptionView,
#     ClaimDailyRewardView,
#     ReadingSessionView,
#     ReadingStatsView,
#     ReadingScheduleView,
# )
 

# urlpatterns = [
#     path('packages/',           views.CoinPackageListView.as_view()),
#     path('plans/',              views.SubscriptionPlanListView.as_view()),
#     path('checkout/',           views.CreateCheckoutSessionView.as_view()),
#     path('webhook/',            views.StripeWebhookView.as_view()),
#     path('balance/',            views.MyCoinBalanceView.as_view()),
#     path('transactions/',       views.CoinTransactionHistoryView.as_view()),
#     path('purchases/',          views.MyPurchaseHistoryView.as_view()),
#     path('payout/request/',     views.RequestPayoutView.as_view()),
#     path('history/',        views.ReadingHistoryView.as_view(),       name='reading-history'),
#     path('history/<int:pk>/', views.ReadingHistoryDetailView.as_view(), name='reading-history-detail'),
#     path('verify-purchases/', views.VerifyPurchaseView.as_view(), name='verify-purchase'),

# ]


# # Add to existing urlpatterns:
# new_patterns = [
#     path('vip-status/',          VipStatusView.as_view(),          name='vip-status'),
#     path('subscription/cancel/', CancelSubscriptionView.as_view(), name='cancel-sub'),
#     path('claim-reward/',        ClaimDailyRewardView.as_view(),   name='claim-reward'),
# ]
 
# # # Add to new apps/reading/urls.py (create this file):
# # reading_patterns = [
# #     path('session/', ReadingSessionView.as_view(),  name='reading-session'),
# #     path('stats/',   ReadingStatsView.as_view(),    name='reading-stats'),
# #     path('schedule/',ReadingScheduleView.as_view(), name='reading-schedule'),
# # ]

# urlpatterns += new_patterns
 
# # In config/urls.py add:
# # path('api/reading/', include('apps.coins.urls_reading')),
 



from django.urls import path
from . import views
from .views import (
    VipStatusView,
    CancelSubscriptionView,
    ClaimDailyRewardView,
    ReadingSessionView,
    ReadingStatsView,
    ReadingScheduleView,
)
 

urlpatterns = [
    path('packages/',           views.CoinPackageListView.as_view()),
    path('plans/',              views.SubscriptionPlanListView.as_view()),
    path('checkout/',           views.CreateCheckoutSessionView.as_view()),
    path('webhook/',            views.StripeWebhookView.as_view()),
    path('balance/',            views.MyCoinBalanceView.as_view()),
    path('transactions/',       views.CoinTransactionHistoryView.as_view()),
    path('purchases/',          views.MyPurchaseHistoryView.as_view()),
    path('payout/request/',     views.RequestPayoutView.as_view()),
    path('payouts/mine/',        views.AuthorPayoutListView.as_view()),
    path('history/',        views.ReadingHistoryView.as_view(),       name='reading-history'),
    path('history/<int:pk>/', views.ReadingHistoryDetailView.as_view(), name='reading-history-detail'),
    path('verify-purchases/', views.VerifyPurchaseView.as_view(), name='verify-purchase'),

]


# Add to existing urlpatterns:
new_patterns = [
    path('vip-status/',          VipStatusView.as_view(),          name='vip-status'),
    path('subscription/cancel/', CancelSubscriptionView.as_view(), name='cancel-sub'),
    path('claim-reward/',        ClaimDailyRewardView.as_view(),   name='claim-reward'),
]
 
# # Add to new apps/reading/urls.py (create this file):
# reading_patterns = [
#     path('session/', ReadingSessionView.as_view(),  name='reading-session'),
#     path('stats/',   ReadingStatsView.as_view(),    name='reading-stats'),
#     path('schedule/',ReadingScheduleView.as_view(), name='reading-schedule'),
# ]

urlpatterns += new_patterns
 
# In config/urls.py add:
# path('api/reading/', include('apps.coins.urls_reading')),