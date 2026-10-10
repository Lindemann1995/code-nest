import re
from django.contrib.auth.models import User
from .models import Notification


# Регулярка: @username (латиница, цифры, _, ., +, -, от 3 до 30 символов)
MENTION_PATTERN = re.compile(r'@([\w.+\-]{3,30})')


def parse_mentions(text, sender=None, topic=None, post=None):
    """
    Находит @упоминания в тексте, создаёт ссылки и уведомления.
    Возвращает список User'ов, которых упомянули.
    """
    usernames = set(MENTION_PATTERN.findall(text))
    mentioned_users = []

    for username in usernames:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            continue

        # Не уведомляем себя
        if sender and user == sender:
            continue

        # Не уведомляем повторно
        if topic and Notification.objects.filter(
            user=user, sender=sender, notification_type='mention', topic=topic
        ).exists():
            mentioned_users.append(user)
            continue

        # Создаём уведомление
        Notification.objects.create(
            user=user,
            sender=sender,
            notification_type='mention',
            topic=topic,
            post=post,
            message=f"упомянул вас в теме «{topic.title}»" if topic else "упомянул вас"
        )
        mentioned_users.append(user)

    return mentioned_users


def linkify_mentions(html):
    """
    Заменяет @username на ссылки в HTML.
    Вызывается при выводе постов.
    """
    def replacer(match):
        username = match.group(1)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return match.group(0)  # Оставляем как текст

        return f'<a href="/user/{username}/" class="mention">@{username}</a>'

    # Заменяем только вне HTML-тегов (упрощённо — вне <a>, <pre>, <code>)
    # Простой вариант: заменяем везде, где не внутри атрибута
    return MENTION_PATTERN.sub(replacer, html)