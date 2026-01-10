"""
service d'acces aux donnees mongodb
gere la connexion au replica set et les requetes
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from django.conf import settings


class MongoService:
    """service de connexion et requetes mongodb"""

    _client = None
    _db = None

    @classmethod
    def get_client(cls):
        """obtient ou cree la connexion au replica set"""
        if cls._client is None:
            mongo_settings = settings.MONGODB_SETTINGS
            cls._client = MongoClient(
                mongo_settings['host'],
                replicaSet=mongo_settings['replica_set'],
                serverSelectionTimeoutMS=mongo_settings['timeout']
            )
        return cls._client

    @classmethod
    def get_database(cls):
        """obtient la base de donnees imdb"""
        if cls._db is None:
            client = cls.get_client()
            cls._db = client[settings.MONGODB_SETTINGS['database']]
        return cls._db

    @classmethod
    def test_connection(cls):
        """teste la connexion au replica set"""
        try:
            client = cls.get_client()
            client.admin.command('ping')
            return True, "connexion reussie"
        except ConnectionFailure:
            return False, "echec de connexion au replica set"
        except ServerSelectionTimeoutError:
            return False, "timeout de connexion"
        except Exception as e:
            return False, f"erreur: {str(e)}"

    @classmethod
    def get_statistics(cls):
        """obtient des statistiques sur les donnees"""
        try:
            db = cls.get_database()
            stats = {
                'collections': {},
                'total_documents': 0,
                'replica_status': None
            }

            # nombre de documents par collection
            collections = ['movies', 'persons', 'genres', 'ratings', 'directors', 'writers']

            for coll_name in collections:
                if coll_name in db.list_collection_names():
                    count = db[coll_name].count_documents({})
                    stats['collections'][coll_name] = count
                    # compter uniquement movies pour le total (eviter de compter les relations)
                    if coll_name == 'movies':
                        stats['total_documents'] = count

            # statut du replica set
            try:
                client = cls.get_client()
                rs_status = client.admin.command('replSetGetStatus')
                stats['replica_status'] = {
                    'set': rs_status['set'],
                    'members': []
                }

                for member in rs_status['members']:
                    stats['replica_status']['members'].append({
                        'name': member['name'],
                        'state': member['stateStr'],
                        'health': 'ok' if member.get('health', 0) == 1 else 'ko'
                    })

            except Exception:
                stats['replica_status'] = None

            return stats

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def get_movies(cls, limit=100, skip=0, filters=None):
        """obtient une liste de films"""
        try:
            db = cls.get_database()
            collection = db['movies_complete'] if 'movies_complete' in db.list_collection_names() else db['movies']

            query = filters if filters else {}
            cursor = collection.find(query).skip(skip).limit(limit)

            return list(cursor)

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def get_movie_by_id(cls, movie_id):
        """obtient un film par son id avec details complets"""
        try:
            db = cls.get_database()

            # chercher le film de base
            movie = db['movies'].find_one({'_id': movie_id})
            if not movie:
                return None

            # enrichir avec les details
            movie['title'] = movie.get('primaryTitle')
            movie['year'] = movie.get('startYear')

            # recuperer les genres
            genres_docs = db['genres'].find({'mid': movie_id})
            movie['genres'] = [g['genre'] for g in genres_docs]

            # recuperer la note
            rating_doc = db['ratings'].find_one({'_id': movie_id})
            if rating_doc:
                movie['rating'] = rating_doc.get('averageRating')
                movie['numVotes'] = rating_doc.get('numVotes')

            # recuperer les realisateurs avec noms
            directors_docs = db['directors'].find({'mid': movie_id})
            directors = []
            for d in directors_docs:
                person = db['persons'].find_one({'_id': d['pid']}, {'primaryName': 1})
                if person:
                    directors.append({'pid': d['pid'], 'name': person.get('primaryName')})
            movie['directors'] = directors

            # recuperer les scenarists avec noms
            writers_docs = db['writers'].find({'mid': movie_id})
            writers = []
            for w in writers_docs:
                person = db['persons'].find_one({'_id': w['pid']}, {'primaryName': 1})
                if person:
                    writers.append({'pid': w['pid'], 'name': person.get('primaryName')})
            movie['writers'] = writers

            return movie

        except Exception as e:
            return None

    @classmethod
    def search_movies(cls, query, limit=50):
        """recherche des films par titre"""
        try:
            db = cls.get_database()
            collection = db['movies_complete'] if 'movies_complete' in db.list_collection_names() else db['movies']

            # recherche textuelle simple
            regex = {'$regex': query, '$options': 'i'}
            cursor = collection.find({'title': regex}).limit(limit)

            return list(cursor)

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def get_top_movies(cls, limit=20):
        """obtient les films les mieux notes"""
        try:
            db = cls.get_database()

            # utiliser aggregation pour joindre movies et ratings
            pipeline = [
                # joindre avec ratings
                {
                    '$lookup': {
                        'from': 'ratings',
                        'localField': '_id',
                        'foreignField': '_id',
                        'as': 'rating_data'
                    }
                },
                # filtrer uniquement les films avec note
                {
                    '$match': {
                        'rating_data': {'$ne': []}
                    }
                },
                # projeter les champs necessaires
                {
                    '$project': {
                        '_id': 1,
                        'title': '$primaryTitle',
                        'year': '$startYear',
                        'rating': {'$arrayElemAt': ['$rating_data.averageRating', 0]}
                    }
                },
                # trier par note decroissante
                {'$sort': {'rating': -1}},
                # limiter
                {'$limit': limit}
            ]

            return list(db['movies'].aggregate(pipeline))

        except Exception as e:
            return []

    @classmethod
    def get_random_movies(cls, limit=6):
        """films aleatoires via aggregation sample"""
        try:
            db = cls.get_database()
            pipeline = [
                {'$sample': {'size': limit}},
                {
                    '$project': {
                        '_id': 1,
                        'title': '$primaryTitle',
                        'year': '$startYear'
                    }
                }
            ]
            return list(db['movies'].aggregate(pipeline))
        except Exception as e:
            return []

    @classmethod
    def get_similar_movies(cls, movie_id, limit=6):
        """films similaires (meme genre ou realisateur)"""
        try:
            db = cls.get_database()

            # recuperer les genres du film actuel
            genres_docs = db['genres'].find({'mid': movie_id})
            genres = [g['genre'] for g in genres_docs]

            if not genres:
                return []

            # chercher films avec au moins un genre en commun
            similar_mids = db['genres'].distinct('mid', {'genre': {'$in': genres}, 'mid': {'$ne': movie_id}})

            # recuperer les films correspondants
            movies = db['movies'].find(
                {'_id': {'$in': similar_mids[:limit]}},
                {'_id': 1, 'primaryTitle': 1, 'startYear': 1}
            ).limit(limit)

            result = []
            for m in movies:
                result.append({
                    '_id': m['_id'],
                    'title': m.get('primaryTitle'),
                    'year': m.get('startYear')
                })

            return result

        except Exception as e:
            return []

    @classmethod
    def get_ratings_distribution(cls):
        """distribution des notes (buckets 0-1, 1-2, ..., 9-10)"""
        try:
            db = cls.get_database()

            pipeline = [
                {'$match': {'averageRating': {'$exists': True, '$ne': None}}},
                {'$bucket': {
                    'groupBy': '$averageRating',
                    'boundaries': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                    'output': {'count': {'$sum': 1}}
                }}
            ]

            results = list(db['ratings'].aggregate(pipeline))
            formatted = []
            for r in results:
                bucket_id = r['_id']
                if bucket_id < 10:
                    label = f"{bucket_id}-{bucket_id+1}"
                else:
                    label = "10+"
                formatted.append({'label': label, 'value': r['count']})

            return formatted

        except Exception as e:
            return []

    @classmethod
    def close_connection(cls):
        """ferme la connexion mongodb"""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None
