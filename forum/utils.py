import re
import bleach
import emoji
from bleach.css_sanitizer import CSSSanitizer
from django.contrib.auth.models import User
from .models import Notification


# ============================================================
# Регулярка для @упоминаний
# ============================================================
MENTION_PATTERN = re.compile(r'@([\w.+\-]{3,30})')


def parse_mentions(text, sender=None, topic=None, post=None):
    """Находит @упоминания, создаёт уведомления."""
    usernames = set(MENTION_PATTERN.findall(text))
    mentioned_users = []

    for username in usernames:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            continue

        if sender and user == sender:
            continue

        if topic and Notification.objects.filter(
            user=user, sender=sender, notification_type='mention', topic=topic
        ).exists():
            mentioned_users.append(user)
            continue

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
    """Заменяет @username на ссылки в HTML (не трогая <a>, <code>, <pre>)."""
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
# :smile: → 😄
# ============================================================
EMOJI_CODE_PATTERN = re.compile(r':([a-zA-Z0-9_+\-]+):')


def emojize_html(html):
    """Заменяет :smile: на 😄 (не трогая <a>, <code>, <pre>)."""
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
            code = match.group(1)
            converted = emoji.emojize(f':{code}:', language='alias')
            if converted == f':{code}:':
                return match.group(0)
            return converted

        result.append(EMOJI_CODE_PATTERN.sub(replacer, part))

    return ''.join(result)


# ============================================================
# Whitelist тегов и атрибутов (под CKEditor 5)
# ============================================================

ALLOWED_TAGS = [
    'p', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'del', 'ins', 'sub', 'sup',
    'blockquote', 'code', 'pre',
    'ul', 'ol', 'li',
    'a', 'img', 'figure', 'figcaption',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
    'span', 'div',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel', 'class', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'class'],
    'code': ['class'],
    'pre': ['class'],
    'span': ['class', 'style'],
    'div': ['class', 'style'],
    'p': ['style'],
    'h1': ['style'], 'h2': ['style'], 'h3': ['style'],
    'h4': ['style'], 'h5': ['style'], 'h6': ['style'],
    'figure': ['class'],
    'figcaption': ['class'],
    'table': ['class'],
    'td': ['colspan', 'rowspan', 'style'],
    'th': ['colspan', 'rowspan', 'style'],
    'ol': ['start', 'type'],
    '*': ['id'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# CSS whitelist (CKEditor 5 использует эти свойства для alignment/font)
ALLOWED_CSS_PROPERTIES = [
    'text-align',
    'color',
    'background-color',
    'font-size',
    'font-family',
    'font-weight',
    'font-style',
    'text-decoration',
]


# ============================================================
# Рендер HTML (для постов от CKEditor 5)
# ============================================================
def render_html(raw_html):
    """
    Принимает HTML от CKEditor 5, чистит через Bleach,
    прогоняет меншены и эмодзи.
    """
    if not raw_html:
        return ''

    # @username → ссылка
    html = linkify_mentions(raw_html)

    # :smile: → 😄
    html = emojize_html(html)

    css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)

    clean = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        css_sanitizer=css_sanitizer,
    )

    return clean


# ============================================================
# Обратная совместимость — старые markdown-посты
# ============================================================
def render_markdown(text):
    """
    Оставлено для совместимости со старыми постами (markdown).
    НЕ используется для новых постов от CKEditor.
    """
    import markdown
    if not text:
        return ''

    text = text.replace('\r\n', '\n').replace('\r', '\n')

    html = markdown.markdown(
        text,
        extensions=[
            'fenced_code',
            'tables',
            'sane_lists',
            'codehilite',
            'attr_list',
            'def_list',
            'footnotes',
            'toc',
            'pymdownx.tilde',
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'guess_lang': False,
                'use_pygments': False,
            },
        },
    )

    return render_html(html)