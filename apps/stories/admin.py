from django.contrib import admin
from .models import (
    BookRequest, ContentReport, FeaturedAuthor, PlatformSettings, Story, Genre, Tag,
    Rating, Bookmark, PromoBanner, ReadingProgress, StoryDailyStats, UserStoryInteraction,
)


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display  = ['story', 'reason', 'chapter_number', 'reporter', 'status', 'created_at']
    list_filter   = ['reason', 'status']
    list_editable = ['status']
    search_fields = ['story__title', 'details']
    actions       = ['mark_reviewed', 'mark_pending']

    @admin.action(description='Mark selected reports as reviewed')
    def mark_reviewed(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=ContentReport.STATUS_REVIEWED)} report(s) updated.')

    @admin.action(description='Mark selected reports as pending')
    def mark_pending(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=ContentReport.STATUS_PENDING)} report(s) updated.')
    readonly_fields = ['story', 'chapter_number', 'reporter', 'reason', 'details', 'created_at']


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display   = ['title', 'author', 'genre', 'status', 'language',
                      'total_views', 'total_chapters', 'average_rating',
                      'is_featured', 'is_library_banner', 'is_editors_pick', 'free_until', 'created_at']
    list_filter    = ['status', 'language', 'is_featured', 'is_library_banner', 'is_editors_pick', 'is_free_download', 'genre']
    search_fields  = ['title', 'author__username']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields= ['total_views', 'total_unlocks', 'total_chapters', 'target_word_count',
                      'average_rating', 'total_ratings', 'total_likes', 'word_count']
    actions        = ['feature_stories', 'mark_editors_pick', 'remove_editors_pick',
                      'add_to_library_banner', 'remove_from_library_banner', 'unfeature_stories',
                      'mark_ongoing', 'mark_completed', 'mark_paused',
                      'mark_explicit', 'mark_not_explicit',
                      'enable_free_download', 'disable_free_download',
                      'lock_all_chapters', 'unlock_all_chapters', 'reapply_lock_rule',
                      'recount_chapters']

    def feature_stories(self, request, queryset):
        queryset.update(is_featured=True)
    feature_stories.short_description = 'Mark as featured'

    def mark_editors_pick(self, request, queryset):
        queryset.update(is_editors_pick=True)
    mark_editors_pick.short_description = "Mark as editor's pick"

    def add_to_library_banner(self, request, queryset):
        queryset.update(is_library_banner=True)
    add_to_library_banner.short_description = 'Add to library banner'

    def remove_from_library_banner(self, request, queryset):
        queryset.update(is_library_banner=False)
    remove_from_library_banner.short_description = 'Remove from library banner'

    def unfeature_stories(self, request, queryset):
        queryset.update(is_featured=False, is_editors_pick=False)
    unfeature_stories.short_description = 'Remove from featured/picks'

    @admin.action(description="Remove editor's pick")
    def remove_editors_pick(self, request, queryset):
        self.message_user(request, f"Removed {queryset.update(is_editors_pick=False)} story(ies) from editor's pick.")

    @admin.action(description='Mark as ongoing')
    def mark_ongoing(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=Story.STATUS_ONGOING)} story(ies) marked ongoing.')

    @admin.action(description='Mark as completed')
    def mark_completed(self, request, queryset):
        n = queryset.update(status=Story.STATUS_COMPLETED, is_completed=True)
        self.message_user(request, f'{n} story(ies) marked completed.')

    @admin.action(description='Mark as paused')
    def mark_paused(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=Story.STATUS_PAUSED)} story(ies) paused.')

    @admin.action(description='Mark as explicit (18+)')
    def mark_explicit(self, request, queryset):
        n = queryset.update(is_explicit=True, age_rating='18+')
        self.message_user(request, f'{n} story(ies) marked explicit. They are hidden while '
                                   f'"show explicit content" is off.')

    @admin.action(description='Mark as not explicit')
    def mark_not_explicit(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_explicit=False)} story(ies) marked not explicit.')

    @admin.action(description='Turn on free download')
    def enable_free_download(self, request, queryset):
        self.message_user(request, f'Free download on for {queryset.update(is_free_download=True)} story(ies).')

    @admin.action(description='Turn off free download')
    def disable_free_download(self, request, queryset):
        self.message_user(request, f'Free download off for {queryset.update(is_free_download=False)} story(ies).')

    @admin.action(description='Lock all chapters (lock from chapter 1)')
    def lock_all_chapters(self, request, queryset):
        from apps.chapters.models import apply_lock_from_chapter
        for story in queryset:
            story.lock_from_chapter = 1
            story.save(update_fields=['lock_from_chapter'])
            apply_lock_from_chapter(story)
        self.message_user(request, f'All chapters locked in {queryset.count()} story(ies).')

    @admin.action(description='Unlock all chapters (remove lock setting)')
    def unlock_all_chapters(self, request, queryset):
        from apps.chapters.models import apply_lock_from_chapter
        for story in queryset:
            story.lock_from_chapter = None
            story.save(update_fields=['lock_from_chapter'])
            apply_lock_from_chapter(story)
        self.message_user(request, f'All chapters unlocked in {queryset.count()} story(ies).')

    @admin.action(description='Re-apply "lock from chapter N" to all chapters')
    def reapply_lock_rule(self, request, queryset):
        from apps.chapters.models import apply_lock_from_chapter
        stories = queryset.filter(lock_from_chapter__isnull=False)
        for story in stories:
            apply_lock_from_chapter(story)
        self.message_user(request, f'Re-applied the lock rule for {stories.count()} story(ies) '
                                   f'(stories without a lock setting were skipped).')

    @admin.action(description='Recount chapters and words')
    def recount_chapters(self, request, queryset):
        from django.db.models import Count, Sum
        for story in queryset.annotate(n=Count('chapters'), w=Sum('chapters__word_count')):
            Story.objects.filter(pk=story.pk).update(total_chapters=story.n, word_count=story.w or 0)
        self.message_user(request, f'Recounted {queryset.count()} story(ies).')

#admin.site.register(PromoBanner)
admin.site.register(Bookmark)
admin.site.register(PlatformSettings)



@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug', 'is_active']
    list_editable       = ['is_active']
    list_filter         = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    actions             = ['activate_genres', 'deactivate_genres']

    @admin.action(description='Activate selected genres')
    def activate_genres(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=True)} genre(s) updated.')

    @admin.action(description='Deactivate selected genres (hides their stories)')
    def deactivate_genres(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} genre(s) updated.')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display  = ['user', 'story', 'score', 'created_at']
    list_filter   = ['score']
    search_fields = ['user__username', 'story__title']

# @admin.register(PromoBanner)
# class PromoBannerAdmin(admin.ModelAdmin):
#     list_display  = ['title', 'slug', 'image_url', 'order', 'is_active', 'created_at']
#     list_filter   = ['is_active','title','created_at']
#     search_fields = ['title', 'slug']

@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display  = ['title', 'slug', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter   = ['is_active']

@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display  = ['user', 'story', 'last_chapter', 'last_paragraph', 'updated_at']
    search_fields = ['user__username', 'story__title']    


@admin.register(BookRequest)
class BookRequestAdmin(admin.ModelAdmin):
    list_display  = ['title', 'author', 'requested_by', 'created_at']
    search_fields = ['title', 'author']
    readonly_fields = ['created_at']


@admin.register(FeaturedAuthor)
class FeaturedAuthorAdmin(admin.ModelAdmin):
    list_display  = ['user', 'headline', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    search_fields = ['user__username', 'headline']
    list_filter   = ['is_active']


@admin.register(StoryDailyStats)
class StoryDailyStatsAdmin(admin.ModelAdmin):
    list_display  = ['story', 'date', 'views', 'unlocks']
    list_filter   = ['date']
    search_fields = ['story__title']
    readonly_fields = ['story', 'date', 'views', 'unlocks']


@admin.register(UserStoryInteraction)
class UserStoryInteractionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'story', 'viewed', 'bookmarked', 'unlocked', 'rated', 'completed', 'last_seen']
    list_filter   = ['viewed', 'bookmarked', 'unlocked', 'completed']
    search_fields = ['user__username', 'story__title']
    readonly_fields = ['last_seen']


from .models import StoryCoverRequest

@admin.register(StoryCoverRequest)
class StoryCoverRequestAdmin(admin.ModelAdmin):
    list_display    = ['story', 'author', 'status', 'reviewed_by', 'submitted_at', 'reviewed_at']
    list_filter     = ['status']
    search_fields   = ['author__username', 'story__title']
    readonly_fields = ['submitted_at', 'reviewed_at', 'author', 'story', 'pending_cover']
    raw_id_fields   = ['reviewed_by']