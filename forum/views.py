from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import Category, Section, Topic, Post, Reaction, Notification, Conversation, Message
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, TopicForm, PostForm, ProfileEditForm, TopicMoveForm, TopicPrefixForm
from django.http import JsonResponse
from django.utils import timezone
from .utils import parse_mentions, linkify_mentions, render_markdown
from .achievements import check_user_achievements
import os
import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.views.decorators.http import require_POST


def index(request):
    """Главная страница — категории с разделами."""
    categories = Category.objects.all().prefetch_related('sections')

    categories_data = []
    for category in categories:
        root_sections = category.sections.filter(parent__isnull=True)

        # Считаем статистику по разделам
        sections_data = []
        for section in root_sections:
            sections_data.append({
                'section': section,
                'topics_count': section.total_topics_count(),
                'posts_count': section.total_posts_count(),
                'last_topic': section.topics.order_by('-updated_at').first(),
            })

        # Общая статистика категории
        total_topics = sum(s['topics_count'] for s in sections_data)
        total_posts = sum(s['posts_count'] for s in sections_data)

        categories_data.append({
            'category': category,
            'sections': sections_data,
            'total_topics': total_topics,
            'total_posts': total_posts,
        })

    return render(request, 'forum/index.html', {
        'categories_data': categories_data,
    })

def section_detail(request, slug):
    """Страница раздела — список тем + подразделы."""
    section = get_object_or_404(Section, slug=slug)
    subsections = section.children.all()

    # Разделяем темы на закреплённые и обычные
    pinned_topics = section.topics.filter(is_pinned=True).order_by('-updated_at')
    regular_topics = section.topics.filter(is_pinned=False).order_by('-updated_at')

    return render(request, 'forum/section.html', {
        'section': section,
        'subsections': subsections,
        'pinned_topics': pinned_topics,
        'regular_topics': regular_topics,
    })

def topic_detail(request, section_slug, slug):
    """Страница темы - список сообщений."""
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)
    # Увеличиваем счетчик просмотров
    topic.views += 1
    topic.save(update_fields=['views'])

    # Рендерим контент каждого поста в HTML
    posts = list(topic.posts.all())
    for post in posts:
        post.content_html = render_markdown(post.content)

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

    # В разделе-контейнере могут писать только модераторы и выше
    if section.is_container and not request.user.profile.is_staff_role:
        return redirect('forum:section', slug=section_slug)

    if request.method == 'POST':
        topic_form = TopicForm(request.POST, user=request.user)
        post_form = PostForm(request.POST)

        if topic_form.is_valid() and post_form.is_valid():
            topic = topic_form.save(commit=False)
            topic.section = section
            topic.author = request.user
            topic.save()

            post = post_form.save(commit=False)
            post.topic = topic
            post.author = request.user
            post.save()

            # Парсим @упоминания в первом посте
            parse_mentions(post.content, sender=request.user, topic=topic, post=post)
            check_user_achievements(request.user)

            return redirect('forum:topic', section_slug=section_slug, slug=topic.slug)
    else:
        topic_form = TopicForm(user=request.user)
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
            topic.save()

            # Уведомление автору темы (если не сам себе)
            if topic.author != request.user:
                Notification.objects.create(
                    user=topic.author,
                    sender=request.user,
                    notification_type='reply',
                    topic=topic,
                    post=post,
                    message=f"ответил в вашей теме «{topic.title}»"
                )

            # Парсим @упоминания (ВНУТРИ if form.is_valid())
            parse_mentions(post.content, sender=request.user, topic=topic, post=post)
            check_user_achievements(request.user)

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
    """Поставить/изменить/снять реакцию на пост."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    post = get_object_or_404(Post, id=post_id)

    # Свои лайки не считаем
    if post.author == request.user:
        return JsonResponse({
            'error': 'Нельзя реагировать на свои посты',
            'reaction': None,
        }, status=400)

    reaction_type = request.POST.get('reaction_type', 'like')
    if reaction_type not in dict(Reaction.REACTION_CHOICES):
        reaction_type = 'like'

    author_profile = post.author.profile

    # Ищем существующую реакцию
    existing = Reaction.objects.filter(user=request.user, post=post).first()

    if existing:
        # Если та же реакция — удаляем (снимаем)
        if existing.reaction_type == reaction_type:
            # Снимаем репутацию
            author_profile.reputation -= Reaction.REACTION_WEIGHTS.get(existing.reaction_type, 1)
            existing.delete()
            author_profile.save(update_fields=['reputation'])

            # Удаляем уведомление
            Notification.objects.filter(
                user=post.author,
                sender=request.user,
                notification_type='like',
                post=post
            ).delete()

            return JsonResponse({
                'action': 'removed',
                'reaction': None,
                'counts': get_reaction_counts(post),
                'total': post.reactions.count(),
            })
        else:
            # Меняем реакцию
            # Снимаем старую репутацию
            author_profile.reputation -= Reaction.REACTION_WEIGHTS.get(existing.reaction_type, 1)
            # Меняем тип
            existing.reaction_type = reaction_type
            existing.save(update_fields=['reaction_type'])
            # Добавляем новую репутацию
            author_profile.reputation += Reaction.REACTION_WEIGHTS.get(reaction_type, 1)
            author_profile.save(update_fields=['reputation'])

            return JsonResponse({
                'action': 'changed',
                'reaction': reaction_type,
                'counts': get_reaction_counts(post),
                'total': post.reactions.count(),
            })
    else:
        # Создаём новую
        Reaction.objects.create(
            user=request.user,
            post=post,
            reaction_type=reaction_type
        )
        author_profile.reputation += Reaction.REACTION_WEIGHTS.get(reaction_type, 1)
        author_profile.save(update_fields=['reputation'])

        # Уведомление
        Notification.objects.create(
            user=post.author,
            sender=request.user,
            notification_type='like',
            topic=post.topic,
            post=post,
            message=f"поставил {Reaction.REACTION_ICONS.get(reaction_type, '👍')} вашему сообщению в теме «{post.topic.title}»"
        )

        return JsonResponse({
            'action': 'added',
            'reaction': reaction_type,
            'counts': get_reaction_counts(post),
            'total': post.reactions.count(),
        })


def get_reaction_counts(post):
    """Считает количество реакций каждого типа."""
    counts = {}
    for code, _ in Reaction.REACTION_CHOICES:
        counts[code] = post.reactions.filter(reaction_type=code).count()
    return counts

@login_required
def post_edit(request, post_id):
    """Редактирование поста."""
    post = get_object_or_404(Post, id=post_id)

    # Только автор или модератор.
    is_moderator = request.user.profile.is_staff_role
    if request.user != post.author and not is_moderator:
        return redirect('forum:topic',
        section_slug=post.topic.section.slug,
        slug=post.topic.slug)
    
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.is_edited = True
            edited.save()
            return redirect('forum:topic',
            section_slug=post.topic.section.slug,
            slug=post.topic.slug)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'forum/post_edit.html', {
        'form': form,
        'post': post,
    })

@login_required
def post_delete(request, post_id):
    """Удаление поста (автор или модер)."""
    post = get_object_or_404(Post, id=post_id)
    topic = post.topic

    is_moderator = request.user.profile.is_staff_role
    if request.user != post.author and not is_moderator:
        return redirect('forum:topic',
        section_slug=topic.section.slug,
        slug=topic.slug)
    
    if request.method == 'POST':
        # Нельзя удалить первый пост (он тело.)
        is_first_post = topic.posts.first().id == post.id
        if is_first_post and not is_moderator:
            return redirect('forum:topic',
            section_slug=topic.section.slug,
            slug=topic.slug)

        post.delete()

        # Если удалили первый пост - удаляем всю тему.
        if is_first_post:
            topic.delete()
            return redirect('forum:section', slug=topic.section.slug)
        return redirect('forum:topic',
        section_slug=topic.section.slug,
        slug=topic.slug)
    
    return render(request, 'forum/post_delete.html', {
        'post': post,
        'topic': topic,
    })

@login_required
def topic_delete(request, section_slug, slug):
    """Удаление темы (только модератор+)."""
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)

    if not request.user.profile.is_staff_role:
        return redirect('forum:topic',
                        section_slug=section_slug,
                        slug=slug)

    if request.method == 'POST':
        section_slug_saved = topic.section.slug
        topic.delete()
        return redirect('forum:section', slug=section_slug_saved)

    return render(request, 'forum/topic_delete.html', {
        'topic': topic,
    })

@login_required
def topic_toggle_close(request, section_slug, slug):
    """Закрыть/открыть тему. Автор темы или модератор+."""
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)

    is_moderator = request.user.profile.is_staff_role
    if request.user != topic.author and not is_moderator:
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    if request.method == 'POST':
        topic.is_closed = not topic.is_closed
        topic.save(update_fields=['is_closed'])
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    return render(request, 'forum/topic_toggle_close.html', {'topic': topic})

@login_required
def topic_toggle_pin(request, section_slug, slug):
    """Закрепить/открепить тему (только модератор+)."""
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)

    if not request.user.profile.is_staff_role:
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    if request.method == 'POST':
        topic.is_pinned = not topic.is_pinned
        topic.save(update_fields=['is_pinned'])
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    return render(request, 'forum/topic_toggle_pin.html', {'topic': topic})

@login_required
def topic_move(request, section_slug, slug):
    """Перенос темы в другой раздел (старший модератор+)."""
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)

    # Только старший модератор+
    if request.user.profile.role not in ('senior_mod', 'admin', 'manager', 'team'):
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    if request.method == 'POST':
        form = TopicMoveForm(request.POST)
        if form.is_valid():
            new_section = form.cleaned_data['new_section']
            topic.section = new_section
            topic.save(update_fields=['section'])
            return redirect('forum:topic',
                            section_slug=new_section.slug,
                            slug=topic.slug)
    else:
        form = TopicMoveForm(initial={'new_section': topic.section})

    return render(request, 'forum/topic_move.html', {
        'form': form,
        'topic': topic,
    })

@login_required
def user_ban(request, username):
    """Бан пользователя (руководитель+)."""
    target = get_object_or_404(User, username=username)

    # Только manager+ и team
    if request.user.profile.role not in ('manager', 'team'):
        return redirect('forum:profile', username=username)

    # Нельзя банить себя
    if request.user == target:
        return redirect('forum:profile', username=username)

    # Нельзя банить команду форума
    if target.profile.role in ('manager', 'team'):
        return redirect('forum:profile', username=username)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        target.profile.is_banned = True
        target.profile.ban_reason = reason
        target.profile.banned_at = timezone.now()
        target.profile.save(update_fields=['is_banned', 'ban_reason', 'banned_at'])
        return redirect('forum:profile', username=username)

    return render(request, 'forum/user_ban.html', {
        'target': target,
    })


@login_required
def user_unban(request, username):
    """Разбан пользователя (руководитель+)."""
    target = get_object_or_404(User, username=username)

    if request.user.profile.role not in ('manager', 'team'):
        return redirect('forum:profile', username=username)

    # Разбан сразу (без подтверждения)
    target.profile.is_banned = False
    target.profile.ban_reason = ''
    target.profile.banned_at = None
    target.profile.save(update_fields=['is_banned', 'ban_reason', 'banned_at'])

    return redirect('forum:profile', username=username)


def category_detail(request, slug):
    """Страница категории — список разделов."""
    category = get_object_or_404(Category, slug=slug)
    sections = category.sections.filter(parent__isnull=True)

    # Считаем статистику по каждому разделу
    sections_data = []
    for section in sections:
        sections_data.append({
            'section': section,
            'topics_count': section.total_topics_count(),
            'posts_count': section.total_posts_count(),
            'last_topic': section.topics.order_by('-updated_at').first(),
            'subsections': section.children.all(),
        })

    return render(request, 'forum/category.html', {
        'category': category,
        'sections_data': sections_data,
    })

def search(request):
    """Поиск по темам и сообщениям."""
    query = request.GET.get('q', '').strip()
    topics = []
    posts = []

    if query:
        # Ищем в темах
        topics = Topic.objects.filter(
            title__icontains=query
        ).select_related('author', 'section')[:30]

        # Ищем в сообщениях
        posts = Post.objects.filter(
            content__icontains=query
        ).select_related('author', 'topic', 'topic__section')[:30]

    return render(request, 'forum/search.html', {
        'query': query,
        'topics': topics,
        'posts': posts,
        'topics_count': len(topics),
        'posts_count': len(posts),
    })

@login_required
def notifications(request):
    """Страница уведомлений."""
    notifs = request.user.notifications.select_related(
        'sender', 'topic', 'post', 'topic__section'
    ).all()[:50]

    # Помечаем все как прочитанные при просмотре
    request.user.notifications.filter(is_read=False).update(is_read=True)

    return render(request, 'forum/notifications.html', {
        'notifications': notifs,
    })


@login_required
def notification_read(request, notif_id):
    """Пометить уведомление прочитанным и перейти к объекту."""
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return redirect(notif.get_url())


@login_required
def notifications_read_all(request):
    """Пометить все уведомления прочитанными."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('forum:notifications')

@login_required
def conversations_list(request):
    """Список диалогов пользователя."""
    conversations = request.user.conversations.prefetch_related(
        'participants', 'messages'
    ).all()

    # Готовим данные для шаблона
    conv_data = []
    for conv in conversations:
        conv_data.append({
            'conversation': conv,
            'other_user': conv.other_user(request.user),
            'last_message': conv.last_message(),
            'unread': conv.unread_count_for(request.user),
        })

    return render(request, 'forum/conversations.html', {
        'conv_data': conv_data,
    })


@login_required
def conversation_detail(request, conv_id):
    """Страница диалога."""
    conversation = get_object_or_404(Conversation, id=conv_id)

    # Проверяем, что пользователь участвует
    if request.user not in conversation.participants.all():
        return redirect('forum:conversations')

    other = conversation.other_user(request.user)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                conversation=conversation,
                author=request.user,
                content=content
            )
            conversation.save()  # обновить updated_at

            # Уведомление другому участнику
            if other:
                Notification.objects.create(
                    user=other,
                    sender=request.user,
                    notification_type='mention',
                    message=f"отправил вам личное сообщение"
                )

            return redirect('forum:conversation', conv_id=conv_id)

    # Помечаем сообщения как прочитанные
    conversation.messages.filter(is_read=False).exclude(author=request.user).update(is_read=True)

    messages_list = conversation.messages.select_related('author').all()

    return render(request, 'forum/conversation.html', {
        'conversation': conversation,
        'other_user': other,
        'messages_list': messages_list,
    })


@login_required
def start_conversation(request, username):
    """Начать новый диалог с пользователем."""
    if username == request.user.username:
        return redirect('forum:profile', username=username)

    other = get_object_or_404(User, username=username)

    # Ищем существующий диалог
    existing = Conversation.objects.filter(
        participants=request.user
    ).filter(participants=other).first()

    if existing:
        return redirect('forum:conversation', conv_id=existing.id)

    # Создаём новый
    conv = Conversation.objects.create()
    conv.participants.add(request.user, other)

    return redirect('forum:conversation', conv_id=conv.id)

@login_required
def topic_set_prefix(request, section_slug, slug):
    """Смена префикса темы (модератор+)."""
    topic = get_object_or_404(Topic, slug=slug, section__slug=section_slug)

    if not request.user.profile.is_staff_role:
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    if request.method == 'POST':
        prefix = request.POST.get('prefix', '')
        valid_prefixes = [c[0] for c in Topic.PREFIX_CHOICES]
        if prefix in valid_prefixes:
            topic.prefix = prefix
            topic.save(update_fields=['prefix'])
        return redirect('forum:topic', section_slug=section_slug, slug=slug)

    return render(request, 'forum/topic_set_prefix.html', {
        'topic': topic,
    })

def users_search(request):
    """AJAX-поиск юзеров для автодополнения @username."""
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse({'users': []})

    users = (
        User.objects
        .filter(username__istartswith=q)
        .exclude(is_active=False)
        .select_related('profile')[:8]
    )

    return JsonResponse({
        'users': [
            {
                'username': u.username,
                'avatar': u.profile.avatar.url if u.profile.avatar else None,
            }
            for u in users
        ]
    })

ALLOWED_IMAGE_TYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'image/webp': 'webp',
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 МБ


@login_required
@require_POST
def upload_image(request):
    """Загрузка картинки в пост. Возвращает {url: '...'}."""
    file = request.FILES.get('image')
    if not file:
        return JsonResponse({'error': 'Файл не передан'}, status=400)

    if file.size > MAX_IMAGE_SIZE:
        return JsonResponse(
            {'error': 'Файл больше 5 МБ'},
            status=400
        )

    content_type = file.content_type or ''
    if content_type not in ALLOWED_IMAGE_TYPES:
        return JsonResponse(
            {'error': 'Разрешены только JPEG, PNG, GIF, WEBP'},
            status=400
        )

    ext = ALLOWED_IMAGE_TYPES[content_type]
    filename = f"{uuid.uuid4().hex}.{ext}"

    # Сохраняем через default_storage (Yandex Object Storage)
    # Путь: uploads/YYYY/MM/<uuid>.<ext>
    now = timezone.now()
    path = f"uploads/{now.year}/{now.month:02d}/{filename}"

    saved_path = default_storage.save(path, ContentFile(file.read()))
    url = default_storage.url(saved_path)

    return JsonResponse({'url': url})