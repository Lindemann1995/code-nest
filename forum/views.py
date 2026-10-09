from django.shortcuts import render, get_object_or_404
from .models import Section, Topic


def index(request):
    """Главная страница - список корневых разделов."""
    sections = Section.objects.filter(parent__isnull=True)
    return render(request, 'forum/index.html', {'sections': sections})

def section_detail(request, slug):
    """Страница раздела - список тем + подразделы."""
    section = get_object_or_404(Section, slug=slug)
    topics = section.topics.all()
    subsections = section.children.all()
    return render(request, 'forum/section.html', {
        'section': section,
        'topics': topics,
        'subsections': subsections,
    })

def topic_detail(request, section_slug, slug):
    """Страница темы - список сообщений."""
    topic = get_object_or_404(Topic, slug=slug, section_slug=section_slug)
    # Увеличиваем счетчик просмотров
    topic.views += 1
    topic.save(update_fields['views'])
    posts = topic.posts.all()
    return render(request, 'topic.html', {
        'topic': topic,
        'posts': posts,
    })
