from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from unidecode import unidecode


class Section(models.Model):
    """Раздел форума с поддержкой вложенности.
    
    Пример:
    - Программирование (родитель: None)
      - Pawn (родитель: Программирование)
        - Помощь (родитель: Pawn)
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Родительский раздел (если есть)"
    )
    order = models.IntegerField(default=0, help_text="Порядок вывода (меньше — выше)")
    is_pinned = models.BooleanField(default=False, help_text="Закреплённый раздел")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Раздел"
        verbose_name_plural = "Разделы"
        ordering = ['order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent} → {self.name}"
        return self.name


class Topic(models.Model):
    """Тема в разделе."""
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
