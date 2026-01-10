"""
script d'import des donnees depuis sqlite vers le replica set mongodb
"""

import sqlite3
from pymongo import MongoClient
from pathlib import Path
import time

# configuration
SQLITE_DB = Path(__file__).parent.parent / "data" / "imdb.db"
REPLICA_SET_HOSTS = "localhost:27017,localhost:27018,localhost:27019"
REPLICA_SET_NAME = "rs0"
MONGO_DB = "imdb"

def get_sqlite_connection():
    """connexion a sqlite"""
    if not SQLITE_DB.exists():
        raise FileNotFoundError(f"base sqlite introuvable: {SQLITE_DB}")
    return sqlite3.connect(str(SQLITE_DB))

def get_mongo_client():
    """connexion au replica set mongodb"""
    return MongoClient(REPLICA_SET_HOSTS, replicaSet=REPLICA_SET_NAME)

def migrate_table_to_collection(sqlite_conn, mongo_db, table_name):
    """
    migrer une table sqlite vers une collection mongodb

    args:
        sqlite_conn: connexion sqlite
        mongo_db: base mongodb
        table_name: nom de la table sqlite

    returns:
        nombre de documents inseres
    """
    print(f"\nmigration de {table_name}...")

    # extraire les donnees de sqlite
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")

    # recuperer les noms de colonnes
    columns = [description[0] for description in cursor.description]

    # convertir les lignes en dictionnaires
    documents = []
    for row in cursor.fetchall():
        doc = {}
        for i, value in enumerate(row):
            column_name = columns[i]

            # utiliser mid comme _id pour movies
            if table_name == 'movies' and column_name == 'mid':
                doc['_id'] = value
            # utiliser pid comme _id pour persons
            elif table_name == 'persons' and column_name == 'pid':
                doc['_id'] = value
            # utiliser mid comme _id pour ratings
            elif table_name == 'ratings' and column_name == 'mid':
                doc['_id'] = value
            else:
                doc[column_name] = value

        documents.append(doc)

    # vider la collection si elle existe
    mongo_db[table_name].drop()

    # inserer dans mongodb par batch
    if documents:
        start_time = time.time()

        # inserer par lots de 10000
        batch_size = 10000
        total_inserted = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            result = mongo_db[table_name].insert_many(batch, ordered=False)
            total_inserted += len(result.inserted_ids)
            print(f"  {total_inserted}/{len(documents)} documents inseres", end='\r')

        elapsed = time.time() - start_time
        print(f"\n  {total_inserted} documents inseres en {elapsed:.2f}s")
        return total_inserted
    else:
        print(f"  table vide, aucun document insere")
        return 0

def create_movies_complete(mongo_db):
    """
    creer la collection movies_complete avec documents structures

    utilise un pipeline d'agregation pour construire des documents denormalises
    """
    print("\ncreation de la collection movies_complete...")

    # pipeline d'agregation
    pipeline = [
        # lookup genres
        {
            '$lookup': {
                'from': 'genres',
                'localField': '_id',
                'foreignField': 'mid',
                'as': 'genres_data'
            }
        },
        # lookup ratings
        {
            '$lookup': {
                'from': 'ratings',
                'localField': '_id',
                'foreignField': '_id',
                'as': 'rating_data'
            }
        },
        # lookup directors
        {
            '$lookup': {
                'from': 'directors',
                'localField': '_id',
                'foreignField': 'mid',
                'as': 'directors_data'
            }
        },
        # lookup writers
        {
            '$lookup': {
                'from': 'writers',
                'localField': '_id',
                'foreignField': 'mid',
                'as': 'writers_data'
            }
        },
        # projeter le document final
        {
            '$project': {
                '_id': 1,
                'titleType': '$titleType',
                'title': '$primaryTitle',
                'originalTitle': '$originalTitle',
                'isAdult': '$isAdult',
                'year': '$startYear',
                'endYear': '$endYear',
                'runtimeMinutes': '$runtimeMinutes',
                # extraire uniquement les noms de genres
                'genres': '$genres_data.genre',
                # extraire la note
                'rating': {
                    '$cond': [
                        {'$gt': [{'$size': '$rating_data'}, 0]},
                        {'$arrayElemAt': ['$rating_data.averageRating', 0]},
                        None
                    ]
                },
                'numVotes': {
                    '$cond': [
                        {'$gt': [{'$size': '$rating_data'}, 0]},
                        {'$arrayElemAt': ['$rating_data.numVotes', 0]},
                        None
                    ]
                },
                # stocker les pids pour enrichissement ulterieur
                'directors_pids': '$directors_data.pid',
                'writers_pids': '$writers_data.pid'
            }
        },
        # ecrire dans movies_complete
        {'$out': 'movies_complete'}
    ]

    # supprimer l'ancienne collection
    mongo_db.movies_complete.drop()

    # executer le pipeline
    print("  execution du pipeline (peut prendre quelques minutes)...")
    start_time = time.time()
    mongo_db.movies.aggregate(pipeline, allowDiskUse=True)
    elapsed = time.time() - start_time

    count = mongo_db.movies_complete.count_documents({})
    print(f"  {count} documents crees en {elapsed:.2f}s")

    # enrichir avec les noms des personnes
    enrich_persons_data(mongo_db)

def enrich_persons_data(mongo_db):
    """
    enrichir les documents avec les noms des personnes

    remplace les listes de pids par des objets contenant pid et name
    """
    print("\nenrichissement avec les donnees des personnes...")

    total = mongo_db.movies_complete.count_documents({})
    processed = 0
    start_time = time.time()

    # traiter par lots
    batch_size = 100

    for i in range(0, total, batch_size):
        movies = mongo_db.movies_complete.find().skip(i).limit(batch_size)

        for movie in movies:
            # recuperer les directors
            directors = []
            for pid in movie.get('directors_pids', []):
                person = mongo_db.persons.find_one({'_id': pid}, {'primaryName': 1})
                if person:
                    directors.append({
                        'pid': pid,
                        'name': person.get('primaryName')
                    })

            # recuperer les writers
            writers = []
            for pid in movie.get('writers_pids', []):
                person = mongo_db.persons.find_one({'_id': pid}, {'primaryName': 1})
                if person:
                    writers.append({
                        'pid': pid,
                        'name': person.get('primaryName')
                    })

            # mettre a jour le document
            mongo_db.movies_complete.update_one(
                {'_id': movie['_id']},
                {
                    '$set': {
                        'directors': directors,
                        'writers': writers
                    },
                    '$unset': {
                        'directors_pids': '',
                        'writers_pids': ''
                    }
                }
            )

            processed += 1
            if processed % 100 == 0:
                progress = (processed / total) * 100
                print(f"  {processed}/{total} ({progress:.1f}%)", end='\r')

    elapsed = time.time() - start_time
    print(f"\n  {processed} documents enrichis en {elapsed:.2f}s")

def verify_migration(sqlite_conn, mongo_db):
    """verifier que les comptages correspondent"""
    print("\nverification de la migration")

    tables = ['movies', 'persons', 'genres', 'ratings', 'directors', 'writers']

    print(f"\n{'table':<15} {'sqlite':<15} {'mongodb':<15} {'status':<10}")
    print("-" * 60)

    all_ok = True
    for table in tables:
        # compter dans sqlite
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        sqlite_count = cursor.fetchone()[0]

        # compter dans mongodb
        mongo_count = mongo_db[table].count_documents({})

        # verifier
        status = "ok" if sqlite_count == mongo_count else "erreur"
        if sqlite_count != mongo_count:
            all_ok = False

        print(f"{table:<15} {sqlite_count:<15} {mongo_count:<15} {status:<10}")

    print()
    if all_ok:
        print("migration reussie - tous les comptages correspondent")
    else:
        print("migration incomplete - verifiez les erreurs")

def main():
    """fonction principale"""
    print("\nimport des donnees sqlite -> mongodb replica set")
    print("="*60)

    # connexions
    print("\nconnexion a sqlite...")
    sqlite_conn = get_sqlite_connection()
    print(f"  ok: {SQLITE_DB}")

    print("\nconnexion au replica set mongodb...")
    mongo_client = get_mongo_client()
    mongo_db = mongo_client[MONGO_DB]
    print(f"  ok: {REPLICA_SET_NAME}")

    # migrer toutes les tables
    tables = ['movies', 'persons', 'genres', 'ratings', 'directors', 'writers']

    total_start = time.time()
    total_docs = 0

    print("\n" + "="*60)
    print("etape 1/2: import des collections plates")
    print("="*60)

    for table in tables:
        count = migrate_table_to_collection(sqlite_conn, mongo_db, table)
        total_docs += count

    total_elapsed = time.time() - total_start
    print(f"\ntotal: {total_docs} documents migres en {total_elapsed:.2f}s")

    # verification
    verify_migration(sqlite_conn, mongo_db)

    # creer movies_complete
    print("\n" + "="*60)
    print("etape 2/2: creation de movies_complete")
    print("="*60)

    create_movies_complete(mongo_db)

    # afficher un exemple
    print("\nexemple de document dans movies_complete:")
    print("-" * 60)
    example = mongo_db.movies_complete.find_one({'genres': {'$exists': True, '$ne': []}})
    if example:
        import json
        display = {
            '_id': example.get('_id'),
            'title': example.get('title'),
            'year': example.get('year'),
            'genres': example.get('genres', []),
            'rating': example.get('rating'),
            'directors': example.get('directors', [])[:2]
        }
        print(json.dumps(display, indent=2, ensure_ascii=False))
    print("-" * 60)

    print("\nimport termine avec succes!")

    # fermer les connexions
    sqlite_conn.close()
    mongo_client.close()

if __name__ == "__main__":
    main()
