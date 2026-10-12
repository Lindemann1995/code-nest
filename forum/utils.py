import re
import markdown
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
# :smile: → 😄 (не трогая <code>, <pre>, <a>)
# ============================================================
EMOJI_CODE_PATTERN = re.compile(r':([a-zA-Z0-9_+\-]+):')


def emojize_html(html):
    """Заменяет :smile: на 😄 в HTML, не трогая <code>, <pre>, <a>."""
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
            # Если не сконвертилось — emoji вернёт исходную строку
            if converted == f':{code}:':
                return match.group(0)
            return converted

        result.append(EMOJI_CODE_PATTERN.sub(replacer, part))

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
    'span': ['class', 'style'],
    'div': ['class', 'style'],
    'p': ['style'],
    '*': ['id'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


# ---- CSS-санитайзер ----
# Разрешённые CSS-свойства (только эти могут быть в style="...")
ALLOWED_CSS_PROPERTIES = {
    'text-align',
    'color',
    'font-size',
    'font-family',
    'background-color',
}

# Разрешённые значения для text-align
ALLOWED_TEXT_ALIGN = {'left', 'right', 'center', 'justify'}

# Разрешённые значения для font-family (в нижнем регистре)
ALLOWED_FONT_FAMILIES = {
    'inter',
    'georgia',
    'consolas',
    'jetbrains mono',
    'times new roman',
    'arial',
    'serif',
    'sans-serif',
    'monospace',
}

# Цвет: #hex, rgb(), rgba(), или простое имя
COLOR_RE = re.compile(
    r'^(#[0-9a-fA-F]{3,8}|rgba?\([\d.,\s%]+\)|[a-zA-Z]{3,20})$'
)

# Размер: 10-48 px
FONT_SIZE_RE = re.compile(r'^(\d{1,2}(?:\.\d+)?)px$')

# Поиск style="..." в HTML
STYLE_ATTR_RE = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE)


def _validate_css_value(prop, value):
    """Проверяет значение CSS-свойства. None — если небезопасно."""
    prop = prop.strip().lower()
    value = value.strip()
    v_lower = value.lower()

    if prop == 'text-align':
        return value if v_lower in ALLOWED_TEXT_ALIGN else None

    if prop in ('color', 'background-color'):
        return value if COLOR_RE.match(value) else None

    if prop == 'font-size':
        m = FONT_SIZE_RE.match(v_lower)
        if not m:
            return None
        size = float(m.group(1))
        if 10 <= size <= 48:
            return value
        return None

    if prop == 'font-family':
        cleaned = v_lower.strip('"\' ')
        return value if cleaned in ALLOWED_FONT_FAMILIES else None

    return None


def _sanitize_style_string(style_str):
    """Очищает строку style="..." — оставляет только разрешённое."""
    parts = []
    for chunk in style_str.split(';'):
        if ':' not in chunk:
            continue
        prop, _, value = chunk.partition(':')
        prop = prop.strip().lower()
        if prop not in ALLOWED_CSS_PROPERTIES:
            continue
        safe_value = _validate_css_value(prop, value)
        if safe_value is None:
            continue
        parts.append(f'{prop}: {safe_value}')
    return '; '.join(parts)


def clean_css_styles(html):
    """Проходит по всем style="..." и чистит их."""
    def replacer(match):
        cleaned = _sanitize_style_string(match.group(1))
        return f'style="{cleaned}"' if cleaned else ''

    cleaned = STYLE_ATTR_RE.sub(replacer, html)
    cleaned = re.sub(r'\s*style\s*=\s*"\s*"', '', cleaned)
    return cleaned


def render_markdown(text):
    """
    Markdown → HTML → linkify_mentions → emojize_html
    → bleach → clean_css_styles.
    """
    if not text:
        return ''

    html = markdown.markdown(
        text,
        extensions=[
            'fenced_code',
            'tables',
            'nl2br',
            'sane_lists',
            'codehilite',
            'attr_list',
            'def_list',
            'footnotes',
            'md_in_html',
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

    # 2. @username → <a class="mention">
    html = linkify_mentions(html)

    # 3. :smile: → 😄
    html = emojize_html(html)

      # 4. Чистим HTML от опасных тегов
    css_sanitizer = CSSSanitizer(allowed_css_properties=[
        'text-align', 'color', 'font-size', 'font-family', 'background-color',
    ])

    clean = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        css_sanitizer=css_sanitizer,
    )

    # 5. Чистим inline style="..."
    clean = clean_css_styles(clean)

    return clean