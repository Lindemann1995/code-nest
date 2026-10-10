from django.contrib import admin
from .models import Category, Section, Topic, Post, Profile, Reaction, Notification, Conversation, Message
from .models import Achievement, UserAchievement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'slug', 'order', 'is_pinned', 'created_at')
    list_editable = ('order', 'is_pinned')
    list_filter = ('is_pinned',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'parent', 'slug', 'order', 'is_pinned', 'created_at')
    list_editable = ('order', 'is_pinned')
    list_filter = ('category', 'parent', 'is_pinned')
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
        ('Блокировка', {
            'fields': ('is_banned', 'ban_reason', 'banned_at'),
            'classes': ('collapse',)
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

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'sender', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'sender__username', 'message')
    list_editable = ('is_read',)
    date_hierarchy = 'created_at'

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('author', 'content', 'is_read', 'created_at')
    can_delete = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'created_at', 'updated_at')
    filter_horizontal = ('participants',)
    inlines = [MessageInline]
    date_hierarchy = 'created_at'

    def get_participants(self, obj):
        return ', '.join([u.username for u in obj.participants.all()])
    get_participants.short_description = "Участники"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'conversation', 'content_short', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('content', 'author__username')
    date_hierarchy = 'created_at'

    def content_short(self, obj):
        return obj.content[:60]
    content_short.short_description = "Сообщение"

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'code', 'order')
    list_editable = ('order',)
    search_fields = ('name', 'description', 'code')


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'received_at')
    list_filter = ('achievement', 'received_at')
    search_fields = ('user__username', 'achievement__name')
    date_hierarchy = 'received_at'