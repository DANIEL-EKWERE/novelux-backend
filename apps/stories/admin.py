from django.contrib import admin
from .models import (
    BookRequest, FeaturedAuthor, PlatformSettings, Story, Genre, Tag,
    Rating, Bookmark, PromoBanner, ReadingProgress, StoryDailyStats, UserStoryInteraction,
)


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display   = ['title', 'author', 'genre', 'status', 'language',
                      'total_views', 'total_chapters', 'average_rating',
                      'is_featured', 'is_editors_pick', 'free_until', 'created_at']
    list_filter    = ['status', 'language', 'is_featured', 'is_editors_pick', 'is_free_download', 'genre']
    search_fields  = ['title', 'author__username']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields= ['total_views', 'total_unlocks', 'total_chapters', 'target_word_count',
                      'average_rating', 'total_ratings', 'word_count']
    actions        = ['feature_stories', 'mark_editors_pick', 'unfeature_stories']

    def feature_stories(self, request, queryset):
        queryset.update(is_featured=True)
    feature_stories.short_description = 'Mark as featured'

    def mark_editors_pick(self, request, queryset):
        queryset.update(is_editors_pick=True)
    mark_editors_pick.short_description = "Mark as editor's pick"

    def unfeature_stories(self, request, queryset):
        queryset.update(is_featured=False, is_editors_pick=False)
    unfeature_stories.short_description = 'Remove from featured/picks'

#admin.site.register(PromoBanner)
admin.site.register(Bookmark)
admin.site.register(PlatformSettings)



@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


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