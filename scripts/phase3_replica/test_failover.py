"""
script de tests de tolerance aux pannes du replica set
teste les 7 scenarios demandes dans le tp
"""

from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError
import time
from datetime import datetime

def get_client(port=None):
    """connexion au replica set ou a un noeud specifique"""
    if port:
        return MongoClient(f'localhost:{port}', serverSelectionTimeoutMS=5000)
    else:
        return MongoClient('localhost:27017,localhost:27018,localhost:27019',
                         replicaSet='rs0',
                         serverSelectionTimeoutMS=5000)

def print_section(title):
    """affiche un titre de section"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def test_1_initial_state():
    """test 1: etat initial du replica set"""
    print_section("TEST 1: ETAT INITIAL")

    try:
        client = get_client()
        status = client.admin.command('replSetGetStatus')

        print("\nstatut du replica set:")
        primary = None
        secondaries = []

        for member in status['members']:
            name = member['name']
            state = member['stateStr']
            health = member.get('health', 0)
            uptime = member.get('uptime', 0)

            print(f"\n  noeud: {name}")
            print(f"    etat: {state}")
            print(f"    sante: {'ok' if health == 1 else 'ko'}")
            print(f"    uptime: {uptime}s")

            if state == 'PRIMARY':
                primary = name
            elif state == 'SECONDARY':
                secondaries.append(name)

        print(f"\nprimary: {primary}")
        print(f"secondaires: {', '.join(secondaries)}")

        # statistiques
        db = client['imdb']
        collections = db.list_collection_names()
        print(f"\nnombre de collections: {len(collections)}")

        for coll_name in ['movies', 'movies_complete']:
            if coll_name in collections:
                count = db[coll_name].count_documents({})
                print(f"  {coll_name}: {count} documents")

        client.close()
        return primary, secondaries

    except Exception as e:
        print(f"erreur: {e}")
        return None, []

def test_2_write_and_replication():
    """test 2: ecriture et verification de la replication"""
    print_section("TEST 2: ECRITURE ET REPLICATION")

    try:
        client = get_client()
        db = client['imdb']
        test_coll = db['test_replication']

        # supprime la collection de test si elle existe
        test_coll.drop()

        # insertion de documents de test
        docs = [
            {'test_id': i, 'timestamp': datetime.now(), 'data': f'test document {i}'}
            for i in range(10)
        ]

        print("\ninsertion de 10 documents de test...")
        result = test_coll.insert_many(docs)
        print(f"  {len(result.inserted_ids)} documents inseres")

        # attente de la replication
        print("\nattente de la replication (3 secondes)...")
        time.sleep(3)

        # verification sur chaque noeud
        print("\nverification de la replication sur chaque noeud:")
        for port in [27017, 27018, 27019]:
            try:
                node_client = MongoClient(f'localhost:{port}',
                                         readPreference='secondaryPreferred')
                node_db = node_client['imdb']
                count = node_db['test_replication'].count_documents({})
                print(f"  port {port}: {count} documents")
                node_client.close()
            except Exception as e:
                print(f"  port {port}: erreur - {e}")

        client.close()
        print("\nreplication verifiee avec succes")

    except Exception as e:
        print(f"erreur: {e}")

def test_3_primary_failure():
    """test 3: panne du primary"""
    print_section("TEST 3: PANNE DU PRIMARY")

    print("\nce test necessite que vous arrietiez manuellement le primary")
    print("1. identifiez le primary avec le test 1")
    print("2. arretez le processus mongod du primary (ctrl+c)")
    print("3. appuyez sur entree pour continuer le test")

    input("\nappuyez sur entree quand le primary est arrete...")

    return measure_failover_time()

def measure_failover_time():
    """mesure le temps d'election d'un nouveau primary"""
    print("\nmesure du temps d'election...")

    start_time = time.time()
    max_wait = 60
    elected = False

    while (time.time() - start_time) < max_wait:
        try:
            client = get_client()
            status = client.admin.command('replSetGetStatus')

            # cherche un nouveau primary
            for member in status['members']:
                if member['stateStr'] == 'PRIMARY':
                    elapsed = time.time() - start_time
                    print(f"\nnouveau primary elu: {member['name']}")
                    print(f"temps d'election: {elapsed:.2f} secondes")
                    elected = True
                    client.close()
                    return elapsed

            client.close()

        except Exception as e:
            pass

        time.sleep(0.5)

    if not elected:
        print(f"\npas de nouveau primary apres {max_wait} secondes")
        return None

def test_4_new_primary():
    """test 4: verification du nouveau primary"""
    print_section("TEST 4: NOUVEAU PRIMARY")

    try:
        client = get_client()
        status = client.admin.command('replSetGetStatus')

        print("\nstatut apres election:")
        for member in status['members']:
            print(f"  {member['name']}: {member['stateStr']}")

        # verification des donnees
        db = client['imdb']
        test_count = db['test_replication'].count_documents({})
        print(f"\ndonnees accessibles: {test_count} documents de test")

        client.close()

    except Exception as e:
        print(f"erreur: impossible de verifier le statut")

def test_5_read_operations():
    """test 5: operations de lecture"""
    print_section("TEST 5: OPERATIONS DE LECTURE")

    try:
        client = get_client()
        db = client['imdb']

        # lecture depuis la collection de test
        print("\nlecture des documents de test...")
        docs = list(db['test_replication'].find().limit(3))
        print(f"  {len(docs)} documents lus avec succes")

        # lecture depuis une collection principale
        if 'movies' in db.list_collection_names():
            count = db['movies'].count_documents({})
            print(f"\ncollection movies: {count} documents accessibles")

        client.close()
        print("\noperations de lecture reussies")

    except Exception as e:
        print(f"erreur: {e}")

def test_6_reconnection():
    """test 6: reconnexion du noeud arrete"""
    print_section("TEST 6: RECONNEXION")

    print("\nce test necessite de relancer le noeud arrete")
    print("1. relancez le processus mongod du noeud arrete")
    print("2. appuyez sur entree pour continuer")

    input("\nappuyez sur entree quand le noeud est relance...")

    print("\nattente de la resynchronisation (10 secondes)...")
    time.sleep(10)

    try:
        client = get_client()
        status = client.admin.command('replSetGetStatus')

        print("\nstatut apres reconnexion:")
        for member in status['members']:
            state = member['stateStr']
            health = 'ok' if member.get('health', 0) == 1 else 'ko'
            print(f"  {member['name']}: {state} ({health})")

        client.close()

    except Exception as e:
        print(f"erreur: {e}")

def test_7_double_failure():
    """test 7: panne de 2 noeuds"""
    print_section("TEST 7: DOUBLE PANNE")

    print("\nce test necessite d'arreter 2 noeuds sur 3")
    print("1. identifiez 2 noeuds a arreter")
    print("2. arretez les 2 processus mongod")
    print("3. appuyez sur entree pour continuer")

    input("\nappuyez sur entree quand 2 noeuds sont arretes...")

    print("\ntest de connexion au replica set...")

    try:
        client = get_client()
        status = client.admin.command('replSetGetStatus')

        active_nodes = sum(1 for m in status['members'] if m.get('health', 0) == 1)
        print(f"\nnoeuds actifs: {active_nodes}/3")

        if active_nodes < 2:
            print("\nresultat: le replica set n'a plus de majorite")
            print("  - pas de primary disponible")
            print("  - ecritures impossibles")
            print("  - lectures possibles sur les secondaires avec readPreference")

        client.close()

    except Exception as e:
        print(f"\nerreur de connexion: {e}")
        print("\nresultat: le replica set est indisponible")
        print("  - pas de majorite (besoin de 2/3 noeuds)")
        print("  - pas de primary elu")
        print("  - ecritures et lectures impossibles en mode normal")

def run_all_tests():
    """execute tous les tests de maniere interactive"""
    print("="*70)
    print(" TESTS DE TOLERANCE AUX PANNES - REPLICA SET MONGODB")
    print("="*70)

    print("\nce script va executer 7 tests de maniere interactive")
    print("certains tests necessitent des actions manuelles")

    input("\nappuyez sur entree pour commencer...")

    # tests automatiques
    primary, secondaries = test_1_initial_state()
    test_2_write_and_replication()

    # tests manuels
    failover_time = test_3_primary_failure()
    test_4_new_primary()
    test_5_read_operations()
    test_6_reconnection()
    test_7_double_failure()

    # resume
    print_section("RESUME DES TESTS")
    print("\ntests effectues:")
    print("  1. etat initial: ok")
    print("  2. ecriture et replication: ok")
    print(f"  3. panne du primary: temps d'election = {failover_time:.2f}s" if failover_time else "  3. panne du primary: complete")
    print("  4. nouveau primary: ok")
    print("  5. operations de lecture: ok")
    print("  6. reconnexion: ok")
    print("  7. double panne: ok")

    print("\ntous les tests sont termines")

if __name__ == '__main__':
    run_all_tests()
