from django.urls import path
from . import views

urlpatterns = [
    path('categories/',                        views.BlogCategoryListCreateView.as_view(), name='blog-category-list'),
    path('categories/<slug:slug>/',            views.BlogCategoryDetailView.as_view(),     name='blog-category-detail'),
    path('posts/',                             views.BlogPostListView.as_view(),            name='blog-post-list'),
    path('posts/create/',                      views.BlogPostCreateView.as_view(),          name='blog-post-create'),
    path('posts/<slug:slug>/',                 views.BlogPostDetailView.as_view(),          name='blog-post-detail'),
    path('posts/<slug:slug>/like/',            views.blog_toggle_like,                     name='blog-toggle-like'),
    path('posts/<slug:slug>/comments/',        views.BlogCommentListCreateView.as_view(),  name='blog-comments'),
    path('comments/<int:pk>/',                 views.blog_delete_comment,                  name='blog-delete-comment'),
    path('upload-image/',                      views.BlogImageUploadView.as_view(),        name='blog-image-upload'),
]
