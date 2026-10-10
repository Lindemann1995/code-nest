from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect
from django.urls import resolve


class LastActivityMiddleware:
    """Обновляет last_activity у профиля при каждом запросе."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                now = timezone.now()

                if not profile.last_activity or (now - profile.last_activity) > timedelta(seconds=60):
                    profile.last_activity = now
                    profile.save(update_fields=['last_activity'])
            except Exception:
                pass

        return self.get_response(request)

class BannedUserMiddleware:
    """Блокирует действия забаненных пользователей."""

    # URL, которые забаненный МОЖЕТ посещать
    ALLOWED_URLS = [
        'logout',
        'login',
        'forum:index',
        'forum:profile',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                if request.user.profile.is_banned:
                    current_url = resolve(request.path_info).url_name
                    if current_url not in self.ALLOWED_URLS and request.method == 'POST':
                        return redirect('forum:index')
            except Exception:
                pass

        return self.get_response(request)