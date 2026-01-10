"""
vues de l'application movies
gere les requetes http et renvoie les templates avec les donnees
"""

from django.shortcuts import render
from .services.mongo_service import MongoService
from .services.sqlite_service import SQLiteService
import json


def home(request):
    """page accueil avec stats, top 10 et recherche"""
    context = {
        'stats': MongoService.get_statistics(),
        'top_movies': MongoService.get_top_movies(limit=10),
        'random_movies': MongoService.get_random_movies(limit=6),
    }
    return render(request, 'movies/home.html', context)


def movies_list(request):
    """liste films avec filtres, tri, pagination"""
    # recuperer parametres GET
    genre = request.GET.get('genre', '')
    year_min = request.GET.get('year_min', '')
    year_max = request.GET.get('year_max', '')
    rating_min = request.GET.get('rating_min', '')
    sort_by = request.GET.get('sort_by', 'year')
    sort_order = request.GET.get('sort_order', 'desc')
    page = int(request.GET.get('page', 1))

    # construire filtres
    filters = {}
    if genre:
        filters['genre'] = genre
    if year_min:
        filters['year'] = {'$gte': int(year_min)}
    if year_max:
        if 'year' in filters:
            filters['year']['$lte'] = int(year_max)
        else:
            filters['year'] = {'$lte': int(year_max)}
    if rating_min:
        filters['rating'] = {'$gte': float(rating_min)}

    # appeler service (utilise SQLite pour filtrage efficace)
    movies = SQLiteService.get_movies_filtered(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=20,
        offset=(page-1)*20
    )

    context = {
        'movies': movies,
        'genres': SQLiteService.get_genres(),
        'page': page,
        'filters': request.GET,
    }
    return render(request, 'movies/list.html', context)


def movie_detail(request, movie_id):
    """detail complet film depuis mongodb"""
    movie = MongoService.get_movie_by_id(movie_id)
    similar_movies = MongoService.get_similar_movies(movie_id, limit=6)

    context = {
        'movie': movie,
        'similar_movies': similar_movies,
    }
    return render(request, 'movies/detail.html', context)


def search(request):
    """recherche par titre ou personne"""
    query = request.GET.get('q', '')

    if not query:
        context = {'query': '', 'movies': [], 'persons': []}
        return render(request, 'movies/search.html', context)

    # recherche films
    movies = SQLiteService.search_movies(query, limit=20)

    # recherche personnes (acteurs + realisateurs)
    persons = SQLiteService.search_persons(query, limit=10)

    context = {
        'query': query,
        'movies': movies,
        'persons': persons,
    }
    return render(request, 'movies/search.html', context)


def statistics(request):
    """stats avec donnees pour chart.js"""
    # films par genre
    genres_data = SQLiteService.get_stats_by_genre()

    # films par decennie
    decades_data = SQLiteService.get_stats_by_decade()

    # distribution notes (mongodb aggregation)
    ratings_data = MongoService.get_ratings_distribution()

    # top acteurs
    actors_data = SQLiteService.get_top_actors(limit=10)

    context = {
        'genres': json.dumps(genres_data),
        'decades': json.dumps(decades_data),
        'ratings': json.dumps(ratings_data),
        'actors': json.dumps(actors_data),
    }
    return render(request, 'movies/stats.html', context)
