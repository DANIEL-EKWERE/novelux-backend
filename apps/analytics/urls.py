from django.urls import path

from . import master

urlpatterns = [
    path('overview/',               master.overview),
    path('realtime/',               master.realtime),
    path('audience/',               master.audience),
    path('users/',                  master.users),
    path('users/<int:user_id>/',    master.user_detail),
    path('users/<int:user_id>/replay/', master.replay),
    path('team/',                   master.team),
    path('team/<int:editor_id>/',   master.team_member),
    path('books/',                  master.books),
    path('revenue/',                master.revenue),
]
