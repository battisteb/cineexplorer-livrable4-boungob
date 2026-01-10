"""
service d'acces aux donnees sqlite
gere la connexion a la base sqlite et les requetes
"""

import sqlite3
from pathlib import Path


class SQLiteService:
    """service de connexion et requetes sqlite"""

    # chemin vers la base sqlite locale
    DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'imdb.db'

    @classmethod
    def get_connection(cls):
        """obtient une connexion a la base sqlite"""
        if not cls.DB_PATH.exists():
            raise FileNotFoundError(f"base sqlite introuvable: {cls.DB_PATH}")
        return sqlite3.connect(str(cls.DB_PATH))

    @classmethod
    def test_connection(cls):
        """teste la connexion a la base sqlite"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True, "connexion reussie"
        except FileNotFoundError as e:
            return False, str(e)
        except Exception as e:
            return False, f"erreur: {str(e)}"

    @classmethod
    def get_statistics(cls):
        """obtient des statistiques sur les donnees"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()

            stats = {
                'tables': {},
                'total_rows': 0
            }

            # liste des tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # compte les lignes par table
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats['tables'][table] = count
                stats['total_rows'] += count

            conn.close()
            return stats

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def get_movies(cls, limit=100, offset=0):
        """obtient une liste de films"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT movie_id, title, year, rating
                FROM movies
                ORDER BY year DESC
                LIMIT ? OFFSET ?
            """

            cursor.execute(query, (limit, offset))
            rows = cursor.fetchall()

            # convertit en liste de dictionnaires
            movies = [dict(row) for row in rows]

            conn.close()
            return movies

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def get_movie_by_id(cls, movie_id):
        """obtient un film par son id"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT movie_id, title, year, rating
                FROM movies
                WHERE movie_id = ?
            """, (movie_id,))

            row = cursor.fetchone()
            movie = dict(row) if row else None

            conn.close()
            return movie

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def search_movies(cls, query, limit=50):
        """recherche des films par titre"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT m.mid, m.primaryTitle as title, m.startYear as year, r.averageRating as rating
                FROM movies m
                LEFT JOIN ratings r ON m.mid = r.mid
                WHERE m.primaryTitle LIKE ?
                LIMIT ?
            """, (f'%{query}%', limit))

            rows = cursor.fetchall()
            movies = [dict(row) for row in rows]

            conn.close()
            return movies

        except Exception as e:
            return []

    @classmethod
    def get_top_movies(cls, limit=20):
        """obtient les films les mieux notes"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT m.mid, m.primaryTitle as title, m.startYear as year, r.averageRating as rating
                FROM movies m
                JOIN ratings r ON m.mid = r.mid
                WHERE r.averageRating IS NOT NULL
                ORDER BY r.averageRating DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            movies = [dict(row) for row in rows]

            conn.close()
            return movies

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def get_movie_with_details(cls, movie_id):
        """obtient un film avec ses acteurs, realisateurs et genres"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # film
            cursor.execute("""
                SELECT movie_id, title, year, rating
                FROM movies
                WHERE movie_id = ?
            """, (movie_id,))

            movie_row = cursor.fetchone()
            if not movie_row:
                conn.close()
                return None

            movie = dict(movie_row)

            # acteurs
            cursor.execute("""
                SELECT a.actor_id, a.name
                FROM actors a
                JOIN movie_actors ma ON a.actor_id = ma.actor_id
                WHERE ma.movie_id = ?
            """, (movie_id,))
            movie['actors'] = [dict(row) for row in cursor.fetchall()]

            # realisateurs
            cursor.execute("""
                SELECT d.director_id, d.name
                FROM directors d
                JOIN movie_directors md ON d.director_id = md.director_id
                WHERE md.movie_id = ?
            """, (movie_id,))
            movie['directors'] = [dict(row) for row in cursor.fetchall()]

            # genres
            cursor.execute("""
                SELECT g.genre_id, g.name
                FROM genres g
                JOIN movie_genres mg ON g.genre_id = mg.genre_id
                WHERE mg.movie_id = ?
            """, (movie_id,))
            movie['genres'] = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return movie

        except Exception as e:
            return {'error': str(e)}

    @classmethod
    def get_movies_filtered(cls, filters, sort_by='year', sort_order='desc', limit=20, offset=0):
        """liste films avec filtres dynamiques"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # construire query dynamiquement
            query = "SELECT m.mid, m.primaryTitle as title, m.startYear as year, r.averageRating as rating FROM movies m LEFT JOIN ratings r ON m.mid = r.mid"
            where_clauses = []
            params = []

            if 'genre' in filters and filters['genre']:
                query += " JOIN genres g ON m.mid = g.mid"
                where_clauses.append("g.genre = ?")
                params.append(filters['genre'])

            if 'year' in filters:
                if '$gte' in filters['year']:
                    where_clauses.append("m.startYear >= ?")
                    params.append(filters['year']['$gte'])
                if '$lte' in filters['year']:
                    where_clauses.append("m.startYear <= ?")
                    params.append(filters['year']['$lte'])

            if 'rating' in filters and '$gte' in filters['rating']:
                where_clauses.append("r.averageRating >= ?")
                params.append(filters['rating']['$gte'])

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            # tri
            order = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            return []

    @classmethod
    def get_genres(cls):
        """liste des genres"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT genre FROM genres ORDER BY genre")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            return []

    @classmethod
    def get_stats_by_genre(cls):
        """nombre films par genre (top 15)"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT genre, COUNT(*) as count
                FROM genres
                GROUP BY genre
                ORDER BY count DESC
                LIMIT 15
            """)
            return [{'label': row[0], 'value': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            return []

    @classmethod
    def get_stats_by_decade(cls):
        """nombre films par decennie"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT (startYear / 10) * 10 as decade, COUNT(*) as count
                FROM movies
                WHERE startYear IS NOT NULL
                GROUP BY decade
                ORDER BY decade
            """)
            return [{'label': f"{int(row[0])}s", 'value': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            return []

    @classmethod
    def get_top_actors(cls, limit=10):
        """realisateurs les plus prolifiques"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.primaryName, COUNT(*) as count
                FROM persons p
                JOIN directors d ON p.pid = d.pid
                GROUP BY p.pid
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
            return [{'label': row[0], 'value': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            return []

    @classmethod
    def search_persons(cls, query, limit=10):
        """recherche realisateurs et scenarists"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT p.pid, p.primaryName as name, COUNT(DISTINCT d.mid) as movie_count
                FROM persons p
                LEFT JOIN directors d ON p.pid = d.pid
                WHERE p.primaryName LIKE ?
                GROUP BY p.pid
                ORDER BY movie_count DESC
                LIMIT ?
            """, (f'%{query}%', limit))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            return []
