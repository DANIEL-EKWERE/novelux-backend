from django.contrib import admin
from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_by', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display  = ['title', 'author', 'category', 'status', 'views', 'read_time', 'created_at']
    list_filter   = ['status', 'category']
    search_fields = ['title', 'author__username', 'tags']
    prepopulated_fields = {'slug': ('title',)}
