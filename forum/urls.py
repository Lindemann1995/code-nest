from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.index, name='index'),
    path('section/<slug:slug>/', views.section_detail, name='section'),
    path('section/<slug:section_slug>/topic/<slug:slug>/', views.topic_detail, name='topic'),
]