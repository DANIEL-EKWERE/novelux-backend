from django.urls import path

from . import views, views_more

urlpatterns = [
    path('overview/',                    views.overview),
    path('books/',                       views.books),
    path('books/<int:pk>/',              views.book_detail),
    path('genres/',                      views.genres),
    path('shelves/',                     views.shelves),
    path('shelves/<int:pk>/',            views.shelf_detail),
    path('shelves/<int:pk>/reorder/',    views.reorder),
    path('schedule/',                    views.schedule),
    path('rotation/',                    views.rotation),
    path('placements/',                  views.placements),
    path('placements/<int:pk>/',         views.placement_detail),
    path('calendar/',                    views.calendar),
    path('requests/',                    views.requests_list),
    path('requests/<int:pk>/review/',    views.request_review),
    path('history/',                     views.history),
    path('tasks/',                       views_more.tasks),
    path('tasks/<int:pk>/',              views_more.task_detail),
    path('my-tasks/',                    views_more.my_tasks),
    path('my-tasks/<int:pk>/respond/',   views_more.my_task_respond),
    path('analytics/movers/',            views_more.movers),
    path('analytics/books/<int:pk>/',    views_more.book_trend),
    path('analytics/promotions/',        views_more.promotion_results),
]
