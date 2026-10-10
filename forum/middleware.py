from django.utils import timezone
from datetime import timedelta


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