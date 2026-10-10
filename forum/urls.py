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
    path('post/<int:post_id>/react/', views.toggle_reaction, name='toggle_reaction'),
    path('post/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    path('post/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    path('section/<slug:section_slug>/topic/<slug:slug>/delete/', views.topic_delete, name='topic_delete'),
    path('section/<slug:section_slug>/topic/<slug:slug>/toggle-close/', views.topic_toggle_close, name='topic_toggle_close'),
    path('section/<slug:section_slug>/topic/<slug:slug>/toggle-pin/', views.topic_toggle_pin, name='topic_toggle_pin'),
    path('section/<slug:section_slug>/topic/<slug:slug>/move/', views.topic_move, name='topic_move'),
    path('user/<str:username>/ban/', views.user_ban, name='user_ban'),
    path('user/<str:username>/unban/', views.user_unban, name='user_unban'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    path('search/', views.search, name='search'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notif_id>/read/', views.notification_read, name='notification_read'),
    path('notifications/read-all/', views.notifications_read_all, name='notifications_read_all'),
    path('messages/', views.conversations_list, name='conversations'),
    path('messages/<int:conv_id>/', views.conversation_detail, name='conversation'),
    path('messages/start/<str:username>/', views.start_conversation, name='start_conversation'),
]