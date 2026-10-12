from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from unidecode import unidecode


class Category(models.Model):
    """Категория — верхний уровень иерархии (например, «Языки программирования»)."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Описание")
    icon = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Иконка",
        help_text="Эмодзи, например: 💻 😄 📚"
    )
    order = models.IntegerField(default=0, verbose_name="Порядок", help_text="Меньше — выше")
    is_pinned = models.BooleanField(default=False, verbose_name="Закреплена")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['-is_pinned', 'order', 'name']

    def __str__(self):
        return self.name


class Section(models.Model):
    """Раздел — внутри категории. Может содержать подразделы."""
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name="Категория"
    )
    is_container = models.BooleanField(
        default=False,
        verbose_name="Раздел-контейнер",
        help_text="Только для подразделов. Прямые темы запрещены."
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительский раздел",
        help_text="Если это подраздел — выберите родителя"
    )
    name = models.CharField(max_length=100, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Описание")
    order = models.IntegerField(default=0, verbose_name="Порядок", help_text="Меньше — выше")
    is_pinned = models.BooleanField(default=False, verbose_name="Закреплён")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "Раздел"
        verbose_name_plural = "Разделы"
        ordering = ['-is_pinned', 'order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.category} → {self.parent.name} → {self.name}"
        return f"{self.category} → {self.name}"

    def total_topics_count(self):
        """Считает темы в этом разделе + во всех подразделах (рекурсивно)."""
        count = self.topics.count()
        for child in self.children.all():
            count += child.total_topics_count()
        return count

    def total_posts_count(self):
        """Считает сообщения в этом разделе + во всех подразделах."""
        count = 0
        for topic in self.topics.all():
            count += topic.posts.count()
        for child in self.children.all():
            count += child.total_posts_count()
        return count
    
    def get_ancestors(self):
        """Возвращает список предков-разделов (от корня до родителя)."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_breadcrumb(self):
        """Возвращает полный путь: категория + предки + сам раздел."""
        crumbs = []
        if self.category:
            crumbs.append(self.category)
        crumbs.extend(self.get_ancestors())
        crumbs.append(self)
        return crumbs

class Topic(models.Model):
    """Тема в разделе."""
    PREFIX_CHOICES = [
        ('', '— Без префикса —'),
        ('rules', 'Правила'),
        ('recommend', 'Рекомендации'),
        ('solved', 'Решено'),
        ('bug', 'Баг'),
        ('help', 'Вопрос'),
        ('news', 'Новость'),
    ]

    PREFIX_COLORS = {
        '': None,
        'rules': '#ef4444',       # красный
        'recommend': '#22c55e',   # зелёный
        'solved': '#3b82f6',      # синий
        'bug': '#dc2626',         # тёмно-красный
        'help': '#f5a623',        # оранжевый
        'news': '#a855f7',        # фиолетовый
    }

    PREFIX_ICONS = {
        '': '',
        'rules': '📜',
        'recommend': '💡',
        'solved': '✅',
        'bug': '🐛',
        'help': '❓',
        'news': '📰',
    }
    prefix = models.CharField(
        max_length=20,
        choices=PREFIX_CHOICES,
        blank=True,
        default='',
        verbose_name="Префикс"
    )
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='topics')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False, help_text="Закреплённая тема")
    is_closed = models.BooleanField(default=False, help_text="Закрытая тема")
    views = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Тема"
        verbose_name_plural = "Темы"
        ordering = ['-is_pinned', '-updated_at']

    def __str__(self):
        return self.title

    def prefix_color(self):
        return self.PREFIX_COLORS.get(self.prefix) or None

    def prefix_icon(self):
        return self.PREFIX_ICONS.get(self.prefix, '')

    def prefix_label(self):
        return dict(self.PREFIX_CHOICES).get(self.prefix, '')

    def save(self, *args, **kwargs):
        """Автоматическая генерация из titile"""
        if not self.slug:
            base_slug = slugify(unidecode(self.title))
            slug = base_slug
            counter = 1
            # Проверка на уже существующий slug
            while Topic.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    

class Post(models.Model):
    """Сообщение в теме."""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ['created_at']

    def __str__(self):
        return f"Сообщение от {self.author.username} в {self.topic.title}"

    @property
    def reactions_count(self):
        """Сколько лайков у поста."""
        return self.reactions.count()
    
    def user_reaction(self, user):
        """Возвращает реакцию пользователя на этот пост (или None)."""
        if not user.is_authenticated:
            return None
        reaction = self.reactions.filter(user=user).first()
        return reaction.reaction_type if reaction else None

    def reaction_counts(self):
        """Возвращает dict со счётчиками по типам."""
        counts = {}
        for code, _ in Reaction.REACTION_CHOICES:
            counts[code] = self.reactions.filter(reaction_type=code).count()
        return counts

    def reaction_icons_list(self):
        """Возвращает список активных иконок + количество."""
        result = []
        for code, _ in Reaction.REACTION_CHOICES:
            count = self.reactions.filter(reaction_type=code).count()
            if count > 0:
                result.append({
                    'icon': Reaction.REACTION_ICONS[code],
                    'count': count,
                    'code': code,
                })
        return result
    
    def content_with_mentions(self):
        """Рендерит Markdown + подставляет @упоминания + чистит HTML."""
        from .utils import render_markdown
        return render_markdown(self.content)

class Profile(models.Model):
    """Профиль пользователя - расширение стандартной модели User."""

    ROLE_CHOICES = [
        ('user', 'Пользователь'),
        ('moderator', 'Модератор'),
        ('senior_mod', 'Старший модератор'),
        ('admin', 'Администратор'),
        ('manager', 'Руководитель форума'),
        ('team', 'Команда форума'),
    ]

    ROLE_COLORS = {
        'user': '#666666',
        'moderator': '#22c55e',
        'senior_mod': '#3b82f6',
        'admin': '#ef4444',
        'manager': '#a855f7',
        'team': '#f5a623',
    }

    ROLE_ICONS = {
        'user': '',
        'moderator': '🛡️',
        'senior_mod': '⚔️',
        'admin': '👑',
        'manager': '🎖️',
        'team': '⭐',
    }

    # Связь с User (один к одному).
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # Роль
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name="Роль"
    )

    # Медиа (позже с облаком).
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )
    banner = models.ImageField(
        upload_to='banners/',
        blank=True,
        null=True,
        verbose_name="Баннер"
    )

    # Публичная информация
    status = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Статус",
        help_text="Короткий статус (до 100 символов)"
    )

    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="О себе",
        help_text="Подпись под сообщениями (до 500 символов)"
    )

    signature = models.TextField(
        max_length=300,
        blank=True,
        verbose_name="Подпись",
        help_text="Подпись под сообщениями (до 300 символов)"
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Город'
    )

    age = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Возраст",
        help_text="Указывается по желанию."
    )

    vk_url = models.URLField(
        blank=True,
        verbose_name="Вконтакте",
        help_text="Ссылка на ваш профиль Вконтакте."
    )

    github_url = models.URLField(
        blank=True,
        verbose_name="GitHub",
        help_text="Ссылка на ваш профиль GitHub",
    )

    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Последняя активность"
    )

    
    reputation = models.IntegerField(
        default=0,
        verbose_name="Репутация",
        help_text="Будет разработано в ближайшее время."
    )

    is_email_public = models.BooleanField(
        default=False,
        verbose_name="Показывать email"
    )
    is_online_public = models.BooleanField(
        default=True,
        verbose_name="Показывать онлайн-статус"
    )
    
    is_banned = models.BooleanField(
        default=False,
        verbose_name="Заблокирован"
    )
    ban_reason = models.TextField(
        blank=True,
        verbose_name="Причина бана"
    )
    banned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата бана"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создан"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлён"
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Профиль {self.user.username}"

    # Методы для отображения
    @property
    def role_name(self):
        """Название роли на русском."""
        return dict(self.ROLE_CHOICES).get(self.role, 'Пользователь')
    
    def role_color(self):
        """Цвет роли (HEX)."""
        return self.ROLE_COLORS.get(self.role, '#666666')

    @property
    def role_icon(self):
        """Значок роли (эмодзи)."""
        return self.ROLE_ICONS.get(self.role, '')
    
    @property
    def is_online(self):
        """Онлайн, если активность меньше 5 минут назад."""
        if not self.last_activity:
            return False
        
        return timezone.now() - self.last_activity < timedelta(minutes=5)

    @property
    def is_staff_role(self):
        """Есть ли права модератора и выше."""
        return self.role in ('moderator', 'senior_mod', 'admin', 'manager', 'team')

    @property
    def topics_count(self):
        """Сколько тем создал пользователь."""
        return self.user.topics.count()
    
    @property
    def posts_count(self):
        """Сколько сообщений написал пользователь."""
        return self.user.posts.count()

    @property
    def last_seen_display(self):
        """Человеку понятное отображение последней активности"""
        if not self.last_activity:
            return "Не был(а) в сети"
        delta = timezone.now() - self.last_activity
        if delta < timedelta(minutes=5):
            return "Онлайн"
        elif delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() / 60)
            return f"Был(а) {minutes} мин. назад"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"Был(а) {hours} ч. назад"
        elif delta < timedelta(days=30):
            days = delta.days
            return f"Был(а) {days} дн. назад"
        else:
            return f"Был(а) {self.last_activity.strftime('%d.%m.%Y')}"
    
    @property
    def unread_messages_count(self):
        """Сколько непрочитанных ЛС у пользователя."""
        count = 0
        for conv in self.user.conversations.all():
            count += conv.unread_count_for(self.user)
        return count

class Reaction(models.Model):
    """Реакция пользователя на пост (Like)."""

    REACTION_CHOICES = [
        ('like', '👍 Нравится'),
        ('love', '❤️ Люблю'),
        ('fire', '🔥 Огонь'),
        ('target', '🎯 В точку'),
        ('funny', '😄 Смешно'),
    ]

    REACTION_WEIGHTS = {
        'like': 1,
        'love': 2,
        'fire': 3,
        'target': 2,
        'funny': 1,
    }

    REACTION_ICONS = {
        'like': '👍',
        'love': '❤️',
        'fire': '🔥',
        'target': '🎯',
        'funny': '😄',
    }

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name='Пользователь'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name='Пост'
    )
    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_CHOICES,
        default='like',
        verbose_name="Тип реакции"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата"
    )

    class Meta:
        verbose_name = "Реакция"
        verbose_name_plural = "Реакции"
        unique_together = ('user', 'post')  # один юзер — одна реакция на пост
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} → {self.reaction_type} → пост #{self.post.id}"

class Notification(models.Model):
    """Уведомление для пользователя."""

    TYPE_CHOICES = [
        ('like', '👍 Лайк'),
        ('reply', '💬 Ответ'),
        ('mention', '📣 Упоминание'),
        ('moderation', '🛡️ Модерация'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Получатель"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        verbose_name="Отправитель",
        null=True,
        blank=True
    )
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name="Тип"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Тема"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Сообщение"
    )
    message = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Текст"
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="Прочитано"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ← {self.notification_type}"

    def get_url(self):
        """Ссылка на объект уведомления."""
        if self.topic:
            return f"/section/{self.topic.section.slug}/topic/{self.topic.slug}/"
        return '/'

class Conversation(models.Model):
    """Диалог между двумя пользователями."""
    participants = models.ManyToManyField(
        User,
        related_name='conversations',
        verbose_name="Участники"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Диалог"
        verbose_name_plural = "Диалоги"
        ordering = ['-updated_at']

    def __str__(self):
        users = ', '.join([u.username for u in self.participants.all()])
        return f"Диалог: {users}"

    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(author=user).count()

    def other_user(self, user):
        return self.participants.exclude(id=user.id).first()


class Message(models.Model):
    """Сообщение в диалоге."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Диалог"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="Отправитель"
    )
    content = models.TextField(verbose_name="Сообщение")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}"

class Achievement(models.Model):
    """Награда (бейдж), которую можно получить."""
    code = models.SlugField(max_length=50, unique=True, verbose_name="Код")
    name = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    icon = models.CharField(max_length=10, verbose_name="Иконка (эмодзи)")
    order = models.IntegerField(default=0, verbose_name="Порядок")

    class Meta:
        verbose_name = "Награда"
        verbose_name_plural = "Награды"
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class UserAchievement(models.Model):
    """Полученная пользователем награда."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='achievements',
        verbose_name="Пользователь"
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        verbose_name="Награда"
    )
    received_at = models.DateTimeField(auto_now_add=True, verbose_name="Получена")

    class Meta:
        verbose_name = "Награда пользователя"
        verbose_name_plural = "Награды пользователей"
        unique_together = ('user', 'achievement')
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.user.username} → {self.achievement.name}"