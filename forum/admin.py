from django.contrib import admin
from .models import Section, Topic, Post, Profile, Reaction


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


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'city', 'reputation', 'last_activity', 'created_at')
    list_filter = ('role', 'created_at', 'is_email_public', 'is_online_public')
    search_fields = ('user__username', 'user__email', 'city', 'status')
    list_editable = ('role',)
    readonly_fields = ('created_at', 'updated_at', 'last_activity', 'reputation')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Пользователь', {
            'fields': ('user', 'role')
        }),
        ('Медиа', {
            'fields': ('avatar', 'banner'),
            'classes': ('collapse',)
        }),
        ('Публичная информация', {
            'fields': ('status', 'bio', 'signature', 'city', 'age')
        }),
        ('Соцсети', {
            'fields': ('vk_url', 'github_url'),
            'classes': ('collapse',)
        }),
        ('Активность', {
            'fields': ('last_activity', 'reputation'),
            'classes': ('collapse',)
        }),
        ('Приватность', {
            'fields': ('is_email_public', 'is_online_public')
        }),
        ('Служебное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    search_fields = ('user__username', 'post__content')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)