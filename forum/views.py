from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from .models import Section, Topic
from .forms import RegisterForm
from django.contrib.auth.decorators import login_required
from .forms import TopicForm, PostForm


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
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)
    # Увеличиваем счетчик просмотров
    topic.views += 1
    topic.save(update_fields=['views'])
    posts = topic.posts.all()
    return render(request, 'forum/topic.html', {
        'topic': topic,
        'posts': posts,
    })

def register(request):
    """Регистрация нового пользователя."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Автоматический вход после регистрации.
            return redirect('forum:index')
    else:
        form = RegisterForm()
    
    return render(request, 'forum/register.html', {'form': form})

@login_required
def topic_create(request, section_slug):
    """Создание новой темы в разделе."""
    section = get_object_or_404(Section, slug=section_slug)

    if request.method == 'POST':
        topic_form = TopicForm(request.POST)
        post_form = PostForm(request.POST)

        if topic_form.is_valid() and post_form.is_valid():
            # Создаем тему.
            topic = topic_form.save(commit=False)
            topic.section = section
            topic.author = request.user
            topic.save()

            # Создаем первое сообщение.
            post = post_form.save(commit=False)
            post.topic = topic
            post.author = request.user
            post.save()

            return redirect('forum:topic', section_slug=section_slug, slug=topic.slug)
    else:
        topic_form = TopicForm()
        post_form = PostForm()

    return render(request, 'forum/topic_create.html', {
        'section': section,
        'topic_form': topic_form,
        'post_form': post_form,
    })

@login_required
def post_create(request, section_slug, slug):
    """Ответ в теме."""
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)

    if topic.is_closed:
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.topic = topic
            post.author = request.user
            post.save()
            # Обновляем updated_at темы.
            topic.save()
            return redirect('forum:topic', section_slug=section_slug, slug=slug)
    else:
        form = PostForm()
    
    return render(request, 'forum/post_create.html', {
        'topic': topic,
        'form': form,
    })
