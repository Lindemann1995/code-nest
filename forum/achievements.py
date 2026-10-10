from .models import Achievement, UserAchievement, Topic, Post


# Список всех наград
ACHIEVEMENTS_DATA = [
    # code, name, icon, description, order
    ('first_message', 'Первый шаг', '🎯', 'Написать первое сообщение', 1),
    ('messages_10', 'Активист', '📝', 'Написать 10 сообщений', 2),
    ('messages_50', 'Оратор', '💬', 'Написать 50 сообщений', 3),
    ('messages_500', 'Легенда', '👑', 'Написать 500 сообщений', 4),
    ('first_topic', 'Автор', '✍️', 'Создать первую тему', 5),
    ('topics_10', 'Создатель', '📚', 'Создать 10 тем', 6),
    ('reputation_100', 'Любимец', '⭐', 'Получить 100 репутации', 7),
    ('reputation_500', 'Уважаемый', '🌟', 'Получить 500 репутации', 8),
]


def ensure_achievements_exist():
    """Создаёт все награды в БД, если их нет."""
    for code, name, icon, description, order in ACHIEVEMENTS_DATA:
        Achievement.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'icon': icon,
                'description': description,
                'order': order,
            }
        )


def give_achievement(user, code):
    """Выдаёт награду пользователю, если её ещё нет."""
    try:
        achievement = Achievement.objects.get(code=code)
    except Achievement.DoesNotExist:
        return False

    _, created = UserAchievement.objects.get_or_create(
        user=user,
        achievement=achievement
    )
    return created


def check_user_achievements(user):
    """Проверяет все условия и выдаёт награды."""
    posts_count = user.posts.count()
    topics_count = user.topics.count()

    try:
        reputation = user.profile.reputation
    except Exception:
        reputation = 0

    # Сообщения
    if posts_count >= 1:
        give_achievement(user, 'first_message')
    if posts_count >= 10:
        give_achievement(user, 'messages_10')
    if posts_count >= 50:
        give_achievement(user, 'messages_50')
    if posts_count >= 500:
        give_achievement(user, 'messages_500')

    # Темы
    if topics_count >= 1:
        give_achievement(user, 'first_topic')
    if topics_count >= 10:
        give_achievement(user, 'topics_10')

    # Репутация
    if reputation >= 100:
        give_achievement(user, 'reputation_100')
    if reputation >= 500:
        give_achievement(user, 'reputation_500')