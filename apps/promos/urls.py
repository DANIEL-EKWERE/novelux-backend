from django.urls import path

from . import views

urlpatterns = [
    path('next/',                    views.next_promo),
    path('<int:pk>/<str:event>/',    views.promo_event),
    path('manage/',                  views.manage),
    path('manage/books/',            views.books),
    path('manage/<int:pk>/',         views.manage_detail),
]
