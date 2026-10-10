from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('section/<slug:slug>/', views.section_detail, name='section'),
    path('section/<slug:section_slug>/topic/<slug:slug>/', views.topic_detail, name='topic'),
    path('section/<slug:section_slug>/create/', views.topic_create, name='topic_create'),
    path('section/<slug:section_slug>/topic/<slug:slug>/reply/', views.post_create, name='post_create'),
    path('user/<str:username>/', views.profile_detail, name='profile'),
    path('user/<str:username>/edit/', views.profile_edit, name='profile_edit'),
]