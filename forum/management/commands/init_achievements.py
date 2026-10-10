from django.core.management.base import BaseCommand
from forum.achievements import ensure_achievements_exist


class Command(BaseCommand):
    help = 'Создаёт все награды в БД'

    def handle(self, *args, **kwargs):
        ensure_achievements_exist()
        self.stdout.write(self.style.SUCCESS('✅ Награды созданы'))