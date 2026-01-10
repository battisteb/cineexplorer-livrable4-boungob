"""
script d'initialisation du replica set mongodb
execute ce script apres avoir demarre les 3 noeuds
"""

from pymongo import MongoClient
import time

def init_replica_set():
    """initialise le replica set avec 3 membres"""
    try:
        # connexion directe au noeud sans replica set
        client = MongoClient('localhost', 27017,
                           directConnection=True,
                           serverSelectionTimeoutMS=5000)

        config = {
            '_id': 'rs0',
            'members': [
                {'_id': 0, 'host': 'localhost:27017'},
                {'_id': 1, 'host': 'localhost:27018'},
                {'_id': 2, 'host': 'localhost:27019'}
            ]
        }

        print("initialisation du replica set rs0...")
        result = client.admin.command('replSetInitiate', config)
        print(f"resultat: {result}")

        print("\nattente de l'election du primary (10 secondes)...")
        time.sleep(10)

        status = client.admin.command('replSetGetStatus')
        print("\nstatut du replica set:")
        for member in status['members']:
            print(f"  - {member['name']}: {member['stateStr']}")

        client.close()
        print("\nreplica set initialise avec succes")

    except Exception as e:
        print(f"erreur lors de l'initialisation: {e}")

if __name__ == '__main__':
    init_replica_set()
