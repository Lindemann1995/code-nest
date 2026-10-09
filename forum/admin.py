from django.contrib import admin
from .models import Section, Topic, Post


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'order', 'is_pinned', 'created_at')
    list_editable = ('order', 'is_pinned')
    list_filter = ('parent', 'is_pinned')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'author', 'created_at', 'is_pinned', 'is_closed', 'views')
    list_filter = ('section', 'is_pinned', 'is_closed', 'created_at')
    search_fields = ('title', 'author__username')
    list_editable = ('is_pinned', 'is_closed')
    date_hierarchy = 'created_at'
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('topic', 'author', 'created_at', 'is_edited')
    list_filter = ('created_at', 'is_edited')
    search_fields = ('content', 'author__username', 'topic__titile')
    date_hierarchy = 'created_at'