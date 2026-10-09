from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
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
