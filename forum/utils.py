import re
import markdown
import bleach
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
    Не трогает содержимое <a>, <code>, <pre>.
    """
    parts = re.split(r'(<[^>]+>)', html)
    inside_skip = 0

    result = []
    for part in parts:
        if part.startswith('<'):
            tag_lower = part.lower()
            if re.match(r'<(a|code|pre)\b', tag_lower):
                inside_skip += 1
            elif re.match(r'</(a|code|pre)>', tag_lower):
                inside_skip = max(0, inside_skip - 1)
            result.append(part)
            continue

        if inside_skip > 0:
            result.append(part)
            continue

        def replacer(match):
            username = match.group(1)
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                return match.group(0)
            return f'<a href="/user/{username}/" class="mention">@{username}</a>'

        result.append(MENTION_PATTERN.sub(replacer, part))

    return ''.join(result)


# ============================================================
# Markdown-рендеринг
# ============================================================

ALLOWED_TAGS = [
    'p', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'del', 'ins',
    'blockquote', 'code', 'pre',
    'ul', 'ol', 'li',
    'a', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'span', 'div',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel', 'class'],
    'img': ['src', 'alt', 'title'],
    'code': ['class'],
    'pre': ['class'],
    'span': ['class'],
    'div': ['class'],
    '*': ['id'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def render_markdown(text):
    """
    Markdown → HTML → linkify_mentions → bleach.
    """
    if not text:
        return ''

    html = markdown.markdown(
        text,
        extensions=[
            'fenced_code',   # ```code``` блоки
            'tables',        # таблицы
            'nl2br',         # одиночный перенос строки → <br>
            'sane_lists',    # нормальные списки
            'codehilite',    # НЕ для подсветки, а для правильного <pre><code>
            'attr_list',     # {#id .class} в конце абзацев
            'def_list',      # определения
            'footnotes',     # сноски
            'md_in_html',    # markdown внутри <div>
            'toc',           # заголовки → якоря
            'pymdownx.tilde',
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'guess_lang': False,
                'use_pygments': False,   # highlight.js подхватит на клиенте
            },
        },
    )
    html = linkify_mentions(html)
    clean = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return clean