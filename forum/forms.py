from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Section, Topic, Post, Profile, Reaction


class RegisterForm(UserCreationForm):
    """Форма регистрации пользователя."""
    email = forms.EmailField(
        required=True,
        label='Email',
        help_text="Нужен для восстановления пароля"
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Имя пользователя',
        }
        help_texts = {
            'username': 'Обязательно! До 150 символов. Буквы, цифры и @/./+/-/_',
        }

class TopicForm(forms.ModelForm):
    """Форма создания новой темы."""

    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'editor',
            'rows': 15,
            'placeholder': 'Опишите вашу тему...'
        }),
        label="Сообщение"
    )

    class Meta:
        model = Topic
        fields = ('prefix', 'title')
        labels = {
            'prefix': 'Префикс',
            'title': 'Заголовок темы',
        }
        widgets = {
            'prefix': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'placeholder': 'Кратко опишите суть вопроса',
                'maxlength': 200,
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Показываем префикс только модераторам+
        if user and not user.profile.is_staff_role:
            self.fields.pop('prefix', None)

class PostForm(forms.ModelForm):
    """Форма ответа в теме."""
    class Meta:
        model = Post
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'editor',
                'rows': 10,
                'placeholder': 'Напишите ответ...',
            })
        }
        labels = {
            'content': '',
        }


class ProfileEditForm(forms.ModelForm):
    """Форма редактирования профиля."""

    class Meta:
        model = Profile
        fields = (
            'avatar',       # ← ДОБАВИЛИ
            'banner',       # ← ДОБАВИЛИ
            'status',
            'bio',
            'signature',
            'city',
            'age',
            'vk_url',
            'github_url',
            'is_email_public',
            'is_online_public',
        )
        widgets = {
            'status': forms.TextInput(attrs={
                'placeholder': 'Короткий статус',
                'maxlength': 100,
            }),
            'bio': forms.Textarea(attrs={
                'placeholder': 'Расскажите о себе...',
                'rows': 5,
                'maxlength': 500,
            }),
            'signature': forms.Textarea(attrs={
                'placeholder': 'Подпись под сообщениями...',
                'rows': 3,
                'maxlength': 300,
            }),
            'city': forms.TextInput(attrs={
                'placeholder': 'Ваш город',
            }),
            'age': forms.NumberInput(attrs={
                'placeholder': 'Возраст',
                'min': 1,
                'max': 120,
            }),
            'vk_url': forms.URLInput(attrs={
                'placeholder': 'https://vk.com/ваш_профиль',
            }),
            'github_url': forms.URLInput(attrs={
                'placeholder': 'https://github.com/ваш_профиль',
            }),
        }
        labels = {
            'avatar': 'Аватар',
            'banner': 'Баннер',
            'status': 'Статус',
            'bio': 'О себе',
            'signature': 'Подпись',
            'city': 'Город',
            'age': 'Возраст',
            'vk_url': 'ВКонтакте',
            'github_url': 'GitHub',
            'is_email_public': 'Показывать email в профиле',
            'is_online_public': 'Показывать онлайн-статус',
        }

class TopicMoveForm(forms.Form):
    """Форма переноса темы в другой раздел."""
    new_section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        label="Новый раздел",
        empty_label="— Выберите раздел —",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class TopicPrefixForm(forms.ModelForm):
    """Форма смены префикса темы."""
    class Meta:
        model = Topic
        fields = ('prefix',)
        labels = {
            'prefix': 'Префикс',
        }
        widgets = {
            'prefix': forms.Select(attrs={'class': 'form-select'}),
        }