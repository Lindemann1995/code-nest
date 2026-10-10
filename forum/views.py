from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import Category, Section, Topic, Post, Reaction, Notification, Conversation, Message
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, TopicForm, PostForm, ProfileEditForm, TopicMoveForm
from django.http import JsonResponse
from django.utils import timezone


def index(request):
    """Главная страница — категории с разделами."""
    categories = Category.objects.all().prefetch_related('sections')

    # Для каждой категории — только корневые разделы (без родителя)
    categories_data = []
    for category in categories:
        root_sections = category.sections.filter(parent__isnull=True)
        categories_data.append({
            'category': category,
            'sections': root_sections,
        })

    return render(request, 'forum/index.html', {
        'categories_data': categories_data,
    })

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
        reaction.delete()
        liked = False
        author_profile.reputation -= 1
        # Удаляем уведомление
        Notification.objects.filter(
            user=post.author,
            sender=request.user,
            notification_type='like',
            post=post
        ).delete()
    else:
        liked = True
        author_profile.reputation += 1
        # Создаём уведомление
        Notification.objects.create(
            user=post.author,
            sender=request.user,
            notification_type='like',
            topic=post.topic,
            post=post,
            message=f"поставил 👍 вашему сообщению в теме «{post.topic.title}»"
        )

    author_profile.save(update_fields=['reputation'])

    return JsonResponse({
        'liked': liked,
        'count': post.reactions.count(),
    })

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
    """Страница категории — список всех разделов."""
    category = get_object_or_404(Category, slug=slug)
    sections = category.sections.filter(parent__isnull=True)
    return render(request, 'forum/category.html', {
        'category': category,
        'sections': sections,
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