from django.urls import path
from . import views
from .views import RegisterTokenView, AdminSendNotificationView

urlpatterns = [
    path('',                views.NotificationListView.as_view()),
    path('unread/',         views.UnreadNotificationCountView.as_view()),
    path('mark-all-read/',  views.MarkAllReadView.as_view()),
    path('<int:pk>/read/',  views.MarkNotificationReadView.as_view()),
    path('device/register/',    views.RegisterDeviceTokenView.as_view()),
    path('device/deregister/',  views.DeregisterDeviceTokenView.as_view()),
    # path('',                    ...,                           name='list'),
    path('register-token/',     RegisterTokenView.as_view(),  name='register-token'),
    path('admin/send/',         AdminSendNotificationView.as_view(), name='admin-send'),
]
