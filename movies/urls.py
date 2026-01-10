"""
configuration des routes url pour l'app movies
"""

from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    path('', views.home, name='home'),
    path('movies/', views.movies_list, name='movies_list'),
    path('movies/<str:movie_id>/', views.movie_detail, name='movie_detail'),
    path('search/', views.search, name='search'),
    path('stats/', views.statistics, name='stats'),
]
