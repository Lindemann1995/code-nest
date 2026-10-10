from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import Section, Topic, Post, Reaction
from django.contrib.auth.decorators import login_required
from .forms import TopicForm, PostForm, ProfileEditForm, RegisterForm
from django.http import JsonResponse



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

def profile_detail(request, username):
    """Страница профиля пользователя."""
    user_obj = get_object_or_404(User, username=username)
    profile = user_obj.profile

    # Статистика
    topics_count = user_obj.topics.count()
    posts_count = user_obj.posts.count()

    # Последние темы пользователя (5 шт.)
    recent_topics = user_obj.topics.order_by('-created_at')[:5]
    # Последние сообщения (5 шт.)
    recent_posts = user_obj.posts.order_by('-created_at')[:5]
    
    return render(request, 'forum/profile.html', {
        'profile': profile,
        'profile_user': user_obj,
        'topics_count': topics_count,
        'posts_count': posts_count,
        'recent_topics': recent_topics,
        'recent_posts': recent_posts,
    })

@login_required
def profile_edit(request, username):
    user_obj = get_object_or_404(User, username=username)

    if request.user != user_obj:
        return redirect('forum:profile', username=username)

    profile = user_obj.profile

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('forum:profile', username=username)
    else:
        form = ProfileEditForm(instance=profile)

    return render(request, 'forum/profile_edit.html', {
        'form': form,
        'profile': profile,
        'profile_user': user_obj,
    })

@login_required
def toggle_reaction(request, post_id):
    """Поставить/снять лайк на пост."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    post = get_object_or_404(Post, id=post_id)

    # Свои лайки не считаем
    if post.author == request.user:
        return JsonResponse({
            'error': 'Нельзя лайкать свои посты',
            'liked': False,
            'count': post.reactions.count(),
        }, status=400)

    reaction, created = Reaction.objects.get_or_create(
        user=request.user,
        post=post,
        reaction_type='like'
    )

    # Профиль автора поста
    author_profile = post.author.profile

    if not created:
        # Уже была — удаляем
        reaction.delete()
        liked = False
        # Снимаем репутацию
        author_profile.reputation -= 1
    else:
        liked = True
        # Начисляем репутацию
        author_profile.reputation += 1

    author_profile.save(update_fields=['reputation'])

    return JsonResponse({
        'liked': liked,
        'count': post.reactions.count(),
    })
