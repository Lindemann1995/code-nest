from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Topic, Post


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
