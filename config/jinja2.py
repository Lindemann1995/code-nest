from jinja2 import Environment
from django.urls import reverse
from django.template.context_processors import csrf
from django.utils.safestring import mark_safe


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'url': reverse,
    })
    return env


def user_context(request):
    from django.contrib.auth.models import AnonymousUser
    return {
        'user': getattr(request, 'user', AnonymousUser()),
    }


def csrf_context(request):
    """Возвращает HTML скрытого поля с CSRF-токеном."""
    csrf_token = csrf(request)['csrf_token']
    html = f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'
    return {
        'csrf_input': mark_safe(html),
    }

def unread_counts(request):
    """Счётчики непрочитанных уведомлений и ЛС."""
    if not request.user.is_authenticated:
        return {'unread_notifs': 0, 'unread_msgs': 0}

    unread_notifs = request.user.notifications.filter(is_read=False).count()

    unread_msgs = 0
    for conv in request.user.conversations.all():
        unread_msgs += conv.unread_count_for(request.user)

    return {
        'unread_notifs': unread_notifs,
        'unread_msgs': unread_msgs,
    }