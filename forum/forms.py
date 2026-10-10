from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Topic, Post, Profile


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
    """Фома создания новой темы."""
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
        fields = ('title',)
        labels = {
            'title': 'Заголовок темы',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Кратко опишите суть вопроса',
                'maxlength': 200,
            })
        }

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
            'status': forms.Textarea(attrs={
                'placeholder': 'Короткий статус',
                'maxlength': 100,
            }),
            'bio': forms.Textarea(attrs={
                'placeholder': 'Расскажите о себе.',
                'rows': 5,
                'maxlength': 500,
            }),
            'signature': forms.Textarea(attrs={
                'placeholder': 'Подпись под сообщением.',
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
                'placeholder': 'https://vk.com/id',
            }),
            'github_url': forms.URLInput(attrs={
                'placeholder': 'https://github.com/ваш_профиль',
            }),
        }
        labels = {
            'status': 'Статус',
            'bio': 'О себе',
            'signature': 'Подпись',
            'city': 'Город',
            'age': 'Возраст',
            'vk_url': 'Вконтакте',
            'github_url': 'GitHub',
            'is_email_public': 'Показывать email в профиле',
            'is_online_public': 'Показывать онлайн-статус',
        }