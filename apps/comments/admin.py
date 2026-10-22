# apps/comments/admin.py
from django.contrib import admin
from .models import Comment, CommentLike


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ['user', 'story', 'content_preview', 'likes_count',
                     'is_pinned', 'is_flagged', 'created_at']
    list_filter   = ['is_flagged', 'is_pinned', 'is_author_reply']
    search_fields = ['user__username', 'content', 'story__title']
    actions       = ['pin_comments', 'unpin_comments', 'flag_comments', 'unflag_comments', 'delete_flagged']

    @admin.action(description='Pin selected comments')
    def pin_comments(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_pinned=True)} comment(s) updated.')

    @admin.action(description='Unpin selected comments')
    def unpin_comments(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_pinned=False)} comment(s) updated.')

    @admin.action(description='Flag selected comments')
    def flag_comments(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_flagged=True)} comment(s) updated.')

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = 'Content'

    def unflag_comments(self, request, queryset):
        queryset.update(is_flagged=False)
    unflag_comments.short_description = 'Unflag selected comments'

    def delete_flagged(self, request, queryset):
        queryset.filter(is_flagged=True).delete()
    delete_flagged.short_description = 'Delete flagged comments'
