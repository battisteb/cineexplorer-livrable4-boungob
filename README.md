# CineExplorer - Livrable 4

Application web Django pour explorer la base de donnees IMDB avec MongoDB Replica Set et SQLite.

## Table des matieres

- [Presentation](#presentation)
- [Prerequis](#prerequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Demarrage](#demarrage)
- [Utilisation](#utilisation)
- [Architecture](#architecture)
- [Fonctionnalites](#fonctionnalites)
- [Structure du projet](#structure-du-projet)
- [Tests](#tests)

## Presentation

CineExplorer est une application web Django permettant d'explorer une base de donnees de films IMDB. L'application utilise une strategie multi-bases combinant MongoDB (Replica Set a 3 noeuds) pour les donnees denormalisees et SQLite pour les requetes relationnelles complexes.

**Caracteristiques principales:**
- Interface web responsive avec Bootstrap 5
- Haute disponibilite grace au Replica Set MongoDB
- Filtrage et recherche performants
- Visualisation de statistiques avec Chart.js
- Architecture service-oriented pour la separation des preoccupations

## Prerequis

- Python 3.8 ou superieur
- MongoDB 4.4 ou superieur
- 500 Mo d'espace disque libre (pour les bases de donnees)
- 2 Go de RAM recommandes

## Installation

### 1. Cloner le depot

```bash
git clone <url-du-depot>
cd cineexplorer
```

### 2. Creer un environnement virtuel (recommande)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dependances

```bash
pip install -r requirements.txt
```

**Contenu de requirements.txt:**
- django>=4.2
- pymongo>=4.5

### 4. Verifier la base SQLite

La base SQLite `data/imdb.db` (302 MB) doit etre presente dans le projet.

## Configuration

### Configuration MongoDB

Le fichier `config/settings.py` contient la configuration MongoDB:

```python
MONGODB_SETTINGS = {
    'host': 'localhost:27017,localhost:27018,localhost:27019',
    'replica_set': 'rs0',
    'database': 'imdb',
    'timeout': 5000
}
```

Vous pouvez modifier ces parametres selon votre environnement.

### Initialisation des donnees MongoDB

Si MongoDB est vide, importez les donnees depuis SQLite:

```bash
python scripts/import_from_sqlite.py
```

Cette operation importe:
- 291,238 films
- 632,324 personnes
- 649,379 genres
- 291,238 notes
- 419,859 realisateurs
- 900,469 scenarists

**Duree estimee:** 3-5 minutes

## Demarrage

### Etape 1: Creer les repertoires pour MongoDB

```bash
mkdir -p data/mongo/db-1 data/mongo/db-2 data/mongo/db-3
```

### Etape 2: Demarrer le Replica Set MongoDB

Ouvrir **3 terminaux** et executer une commande par terminal:

**Terminal 1 (Noeud primaire):**
```bash
mongod --replSet rs0 --port 27017 --dbpath ./data/mongo/db-1 --bind_ip localhost
```

**Terminal 2 (Noeud secondaire 1):**
```bash
mongod --replSet rs0 --port 27018 --dbpath ./data/mongo/db-2 --bind_ip localhost
```

**Terminal 3 (Noeud secondaire 2):**
```bash
mongod --replSet rs0 --port 27019 --dbpath ./data/mongo/db-3 --bind_ip localhost
```

### Etape 3: Initialiser le Replica Set

**Une seule fois** lors de la premiere configuration:

```bash
python scripts/init_replica_set.py
```

Ce script:
- Configure le Replica Set avec 3 noeuds
- Verifie que le noeud primaire est elu
- Affiche le statut du Replica Set

### Etape 4: Lancer le serveur Django

```bash
python manage.py runserver
```

L'application est accessible sur: **http://localhost:8000**

## Utilisation

### Pages disponibles

#### 1. Page d'accueil (/)
- Statistiques generales (nombre de films, statut du Replica Set)
- Top 10 des films les mieux notes
- Films aleatoires a decouvrir
- Barre de recherche

#### 2. Liste des films (/movies/)
- Affichage pagine (20 films par page)
- Filtres:
  - Par genre (Drama, Comedy, Action, etc.)
  - Par annee (min/max)
  - Par note minimale
- Tri par annee, note, titre
- Reinitialisation des filtres

#### 3. Detail d'un film (/movies/<id>/)
- Titre, annee, note
- Genres
- Casting (10 premiers acteurs avec roles)
- Realisateurs
- Scenarists
- Films similaires (meme genre)

#### 4. Recherche (/search/)
- Recherche par titre de film
- Recherche par nom de personne (realisateur, scenarist)
- Resultats groupes:
  - Films (avec annee et note)
  - Personnes (avec nombre de films)

#### 5. Statistiques (/stats/)
Visualisation avec 4 graphiques Chart.js:
- **Films par genre** (bar chart) - Top 15 genres
- **Films par decennie** (line chart) - Evolution temporelle
- **Distribution des notes** (histogram) - Buckets 1-2, 2-3, ..., 10+
- **Top 10 realisateurs** (horizontal bar) - Les plus prolifiques

### Exemples d'utilisation

**Rechercher des films d'un genre specifique:**
1. Aller sur `/movies/`
2. Selectionner "Drama" dans le filtre Genre
3. Cliquer "Filtrer"

**Trouver les films les mieux notes des annees 2000:**
1. Aller sur `/movies/`
2. Entrer "2000" dans Annee min et "2009" dans Annee max
3. Entrer "8" dans Note min
4. Cliquer "Filtrer"

**Rechercher un realisateur:**
1. Aller sur `/search/`
2. Taper "Spielberg"
3. Consulter les resultats dans la section "Personnes"

## Architecture

### Schema general

```
[Client Web]
     |
     v
[Django Web Server]
     |
     +---> [Services Layer]
     |         |
     |         +---> [MongoService] ---> [MongoDB Replica Set]
     |         |                              |
     |         |                              +---> Noeud 1 (Primary)
     |         |                              +---> Noeud 2 (Secondary)
     |         |                              +---> Noeud 3 (Secondary)
     |         |
     |         +---> [SQLiteService] ---> [SQLite DB]
     |
     +---> [Templates (Bootstrap 5 + Chart.js)]
```

### Strategie multi-bases

| Fonctionnalite | Base utilisee | Justification |
|----------------|---------------|---------------|
| Liste films + filtres | SQLite | Requetes relationnelles avec WHERE, JOIN efficaces |
| Detail film complet | MongoDB | Lookups dynamiques pour enrichir les donnees |
| Recherche textuelle | SQLite | LIKE simple et rapide sur colonnes indexees |
| Stats agregees | SQLite + MongoDB | GROUP BY (SQLite), $bucket (MongoDB) |
| Films aleatoires | MongoDB | Aggregation $sample optimisee |
| Top films | MongoDB | Aggregation $lookup + $sort |

### Services metier

**MongoService** (`movies/services/mongo_service.py`):
- Connexion au Replica Set
- Requetes MongoDB avec aggregations
- Gestion du failover automatique

**SQLiteService** (`movies/services/sqlite_service.py`):
- Connexion a la base SQLite
- Requetes SQL complexes avec filtres dynamiques
- Statistiques avec GROUP BY

## Fonctionnalites

### Haute disponibilite

Le Replica Set MongoDB garantit:
- **Failover automatique** si le noeud primaire tombe
- **Lecture distribuee** sur les noeuds secondaires
- **Duplication des donnees** sur 3 noeuds

### Performance

- **Pagination** : 20 films par page pour limiter les requetes
- **Lookups dynamiques** : Evite de stocker des documents massifs
- **Indexes** : Sur les colonnes frequemment filtrees (genre, annee, note)

### Securite

- **Aucune injection SQL** : Requetes parametrees
- **Validation des entrees** : Filtres Django
- **Pas de donnees sensibles** : Base IMDB publique

## Structure du projet

```
cineexplorer/
├── config/                    # configuration django
│   ├── settings.py           # parametres (mongodb, databases)
│   ├── urls.py               # routes principales
│   └── wsgi.py
├── data/
│   ├── imdb.db               # base sqlite (302 mb)
│   └── mongo/                # repertoires mongodb (gitignored)
│       ├── db-1/
│       ├── db-2/
│       └── db-3/
├── movies/                    # application django principale
│   ├── services/
│   │   ├── mongo_service.py  # service mongodb
│   │   └── sqlite_service.py # service sqlite
│   ├── templates/movies/
│   │   ├── base.html         # template de base
│   │   ├── home.html         # page accueil
│   │   ├── list.html         # liste films
│   │   ├── detail.html       # detail film
│   │   ├── search.html       # recherche
│   │   └── stats.html        # statistiques
│   ├── templatetags/
│   │   └── movie_filters.py  # filtres personnalises
│   ├── views.py              # vues django
│   └── urls.py               # routes application
├── scripts/
│   ├── init_replica_set.py   # initialisation replica set
│   └── import_from_sqlite.py # import donnees dans mongodb
├── manage.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Tests

### Verifier le Replica Set

```bash
python scripts/init_replica_set.py
```

Sortie attendue:
```
statut du replica set:
  - localhost:27017: PRIMARY (ok)
  - localhost:27018: SECONDARY (ok)
  - localhost:27019: SECONDARY (ok)
```

### Tester une page

```bash
curl http://localhost:8000/
```

Doit retourner le HTML de la page d'accueil.

### Verifier les donnees MongoDB

```bash
python -c "from movies.services.mongo_service import MongoService; db = MongoService.get_database(); print(f'Films: {db.movies.count_documents({})}')"
```

Sortie attendue: `Films: 291238`

## Troubleshooting

### Erreur: "connexion au replica set impossible"

**Solution:**
1. Verifier que les 3 noeuds MongoDB sont demarres
2. Relancer `python scripts/init_replica_set.py`

### Erreur: "Film introuvable" sur toutes les pages de detail

**Solution:**
MongoDB est vide. Importez les donnees:
```bash
python scripts/import_from_sqlite.py
```

### Graphiques vides sur /stats/

**Solution:**
Verifier que les donnees existent dans MongoDB et SQLite.

## Auteurs

Projet realise dans le cadre du cours BDDA (Bases de Donnees Distribuees et Avancees).

## Licence

Projet academique - Dataset IMDB
