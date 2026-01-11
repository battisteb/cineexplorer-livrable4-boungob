# Guide de Test 
---

## Prérequis à installer

### 1. Python 3.8+

**Windows :**
```bash
# Télécharger depuis https://www.python.org/downloads/
# Ou via Microsoft Store : "Python 3.11"

# Vérifier l'installation
python --version
# Doit afficher : Python 3.8.x ou supérieur
```

### 2. MongoDB 4.4+

**Windows :**
```bash
# Télécharger depuis https://www.mongodb.com/try/download/community
# Installer MongoDB Community Edition

# Vérifier l'installation
mongod --version
# Doit afficher : db version v4.4.x ou supérieur
```

### 3. Git

**Windows :**
```bash
# Télécharger depuis https://git-scm.com/download/win

# Vérifier l'installation
git --version
```

---

## Phase 1 : Clonage et Installation

### Étape 1.1 : Cloner le projet

```bash
# Choisir un répertoire de travail
cd C:\Users\VotreNom\Documents

# Cloner le projet
git clone https://github.com/battisteb/cineexplorer-livrable4-boungob.git

# Entrer dans le projet
cd cineexplorer-livrable4-boungob
```

**Vérification :**
```bash
# Lister les fichiers
dir
# Doit afficher : manage.py, README.md, requirements.txt, etc.
```

### Étape 1.2 : Créer l'environnement virtuel

```bash
# Créer l'environnement
python -m venv venv

# Activer (Windows)
venv\Scripts\activate

# Vérifier l'activation
where python
# Doit afficher le chemin vers venv\Scripts\python.exe
```

### Étape 1.3 : Installer les dépendances

```bash
# Installer
pip install -r requirements.txt

# Vérifier
pip list
# Doit afficher : django, pymongo
```

**Résolution d'erreurs :**
- Si erreur "pip not found" : `python -m ensurepip --upgrade`
- Si erreur version pip : `python -m pip install --upgrade pip`

---

## Phase 2 : Récupération de la base SQLite

**IMPORTANT :** La base SQLite (data/imdb.db - 302 MB) n'est PAS incluse dans le repo Git (.gitignore).

### Option A : Récupérer le fichier (recommandé)

```bash
# Demander le fichier au professeur ou copier depuis votre PC actuel
# Placer imdb.db dans le dossier data/

# Vérifier
dir data\imdb.db
# Doit afficher : 302 MB environ
```

### Option B : Reconstruire depuis CSV (si nécessaire)

Si vous avez les fichiers CSV IMDB :
```bash
# Créer le dossier csv
mkdir data\csv

# Copier les fichiers CSV dans data/csv/
# Puis exécuter le script de création (à créer si besoin)
```

---

## Phase 3 : Configuration MongoDB Replica Set

### Étape 3.1 : Créer les répertoires MongoDB

```bash
# Créer les 3 répertoires pour le Replica Set
mkdir data\mongo\db-1
mkdir data\mongo\db-2
mkdir data\mongo\db-3
```

### Étape 3.2 : Démarrer le Replica Set

**Ouvrir 3 terminaux séparés** (PowerShell ou CMD) :

**Terminal 1 - Noeud primaire (27017) :**
```bash
cd C:\Users\VotreNom\Documents\cineexplorer-livrable4-boungob
mongod --replSet rs0 --port 27017 --dbpath .\data\mongo\db-1 --bind_ip localhost
```

**Terminal 2 - Noeud secondaire 1 (27018) :**
```bash
cd C:\Users\VotreNom\Documents\cineexplorer-livrable4-boungob
mongod --replSet rs0 --port 27018 --dbpath .\data\mongo\db-2 --bind_ip localhost
```

**Terminal 3 - Noeud secondaire 2 (27019) :**
```bash
cd C:\Users\VotreNom\Documents\cineexplorer-livrable4-boungob
mongod --replSet rs0 --port 27019 --dbpath .\data\mongo\db-3 --bind_ip localhost
```

**Vérification :**
Chaque terminal doit afficher :
```
[initandlisten] waiting for connections on port 27017/27018/27019
```

**Résolution d'erreurs :**
- Si erreur "port already in use" : `taskkill /F /IM mongod.exe` puis relancer
- Si erreur "access denied" : Lancer PowerShell en mode Administrateur

### Étape 3.3 : Initialiser le Replica Set

**Ouvrir un 4ème terminal :**
```bash
cd C:\Users\VotreNom\Documents\cineexplorer-livrable4-boungob
venv\Scripts\activate
python scripts/init_replica_set.py
```

**Sortie attendue :**
```
statut du replica set:
  - localhost:27017: PRIMARY (ok)
  - localhost:27018: SECONDARY (ok)
  - localhost:27019: SECONDARY (ok)
```

**Si échec :**
- Attendre 10-15 secondes que les noeuds s'élisent
- Relancer le script

---

## Phase 4 : Import des données dans MongoDB

### Étape 4.1 : Lancer l'import

```bash
# Environnement virtuel déjà activé
python scripts/import_from_sqlite.py
```

**Durée estimée :** 3-5 minutes

**Progression attendue :**
```
import des donnees sqlite -> mongodb replica set
============================================================

connexion a sqlite...
  ok: ...\data\imdb.db

connexion au replica set mongodb...
  ok: rs0

============================================================
etape 1/2: import des collections plates
============================================================

migration de movies...
  10000/291238 documents inseres  20000/291238 documents inseres  ...
  291238 documents inseres en 16s

[... autres collections ...]

total: 3184507 documents migres en 195s

verification de la migration

table           sqlite          mongodb         status
------------------------------------------------------------
movies          291238          291238          ok
persons         632324          632324          ok
genres          649379          649379          ok
ratings         291238          291238          ok
directors       419859          419859          ok
writers         900469          900469          ok

migration reussie
```

**Résolution d'erreurs :**
- Si erreur "WriteConcernError: operation was interrupted" :
  1. Vérifier que le Replica Set est stable : `python scripts/init_replica_set.py`
  2. Attendre 30 secondes
  3. Relancer l'import

- Si barre de progression qui s'empile :
  - Utiliser PowerShell/CMD standard au lieu du terminal VS Code

---

## Phase 5 : Démarrage de l'application Django

### Étape 5.1 : Lancer le serveur

```bash
# Environnement virtuel activé
python manage.py runserver
```

**Sortie attendue :**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
January 11, 2026 - 16:30:00
Django version 4.2.x, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Étape 5.2 : Tester l'application

Ouvrir un navigateur web et tester **toutes les pages** :

#### 1. Page d'accueil (/)
```
http://localhost:8000/
```

**Vérifications :**
- [ ] Statistiques affichées (291,238 films)
- [ ] Top 10 films avec notes
- [ ] Films aléatoires visibles
- [ ] Barre de recherche présente

**Capture d'écran :** Prendre si besoin pour comparaison

---

#### 2. Liste des films (/movies/)
```
http://localhost:8000/movies/
```

**Vérifications :**
- [ ] Liste de 20 films affichée
- [ ] Filtres disponibles : Genre (dropdown avec options), Année min/max, Note min
- [ ] Pagination fonctionne (boutons Précédent/Suivant)

**Test des filtres :**
```
1. Sélectionner "Drama" dans Genre
2. Entrer "2009" dans Année min
3. Entrer "2010" dans Année max
4. Entrer "8" dans Note min
5. Cliquer "Filtrer"

Résultat attendu : Liste réduite de films Drama 2009-2010 avec note >= 8
```

---

#### 3. Détail d'un film (/movies/<id>/)
```
# Cliquer sur un film depuis la liste
# Ex: http://localhost:8000/movies/tt0111161/
```

**Vérifications :**
- [ ] Titre, année, note affichés
- [ ] Genres affichés sous forme de badges
- [ ] Casting (10 acteurs avec rôles)
- [ ] Réalisateurs listés
- [ ] Scénaristes listés
- [ ] Films similaires (6 films du même genre)

---

#### 4. Recherche (/search/)
```
http://localhost:8000/search/?q=Spielberg
```

**Vérifications :**
- [ ] Section "Films" avec résultats
- [ ] Section "Personnes" avec nom + nombre de films
- [ ] Recherche fonctionne pour différents termes

**Tests supplémentaires :**
```
- ?q=Matrix
- ?q=Nolan
- ?q=Inception
```

---

#### 5. Statistiques (/stats/)
```
http://localhost:8000/stats/
```

**Vérifications :**
- [ ] Graphique 1 : Films par genre (bar chart horizontal)
- [ ] Graphique 2 : Films par décennie (line chart)
- [ ] Graphique 3 : Distribution des notes (histogram)
- [ ] Graphique 4 : Top 10 réalisateurs (bar chart)

**Tous les graphiques doivent être interactifs et afficher des données.**

---

## Phase 6 : Tests de robustesse

### Test 1 : Vérifier les données MongoDB

```bash
python -c "from movies.services.mongo_service import MongoService; db = MongoService.get_database(); print(f'Films: {db.movies.count_documents({})}')"
```

**Résultat attendu :** `Films: 291238`

### Test 2 : Vérifier le Replica Set

```bash
python scripts/init_replica_set.py
```

**Résultat attendu :**
```
statut du replica set:
  - localhost:27017: PRIMARY (ok)
  - localhost:27018: SECONDARY (ok)
  - localhost:27019: SECONDARY (ok)
```

### Test 3 : Test de charge simple

Ouvrir plusieurs onglets et naviguer rapidement entre les pages pour vérifier la stabilité.

---

## Phase 7 : Validation finale

### Checklist complète

**Infrastructure :**
- [ ] Python 3.8+ installé et fonctionnel
- [ ] MongoDB 4.4+ installé et fonctionnel
- [ ] Environnement virtuel créé et activé
- [ ] Dépendances installées (django, pymongo)

**Données :**
- [ ] Base SQLite (data/imdb.db) présente (302 MB)
- [ ] MongoDB Replica Set initialisé (3 noeuds)
- [ ] Données importées dans MongoDB (3,184,507 documents)

**Application :**
- [ ] Django démarre sans erreur
- [ ] Page 1 (/) : Accueil fonctionne
- [ ] Page 2 (/movies/) : Liste + filtres fonctionnent
- [ ] Page 3 (/movies/<id>/) : Détail complet affiché
- [ ] Page 4 (/search/) : Recherche retourne résultats
- [ ] Page 5 (/stats/) : 4 graphiques affichés

**Performance :**
- [ ] Toutes les pages se chargent en < 3 secondes
- [ ] Aucune erreur dans le terminal Django
- [ ] Aucune erreur dans les terminaux MongoDB

---

## Résolution de problèmes courants

### Erreur : "ModuleNotFoundError: No module named 'pymongo'"

**Cause :** Environnement virtuel non activé

**Solution :**
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

---

### Erreur : "sqlite3.OperationalError: unable to open database file"

**Cause :** Fichier data/imdb.db manquant

**Solution :**
```bash
# Vérifier
dir data\imdb.db

# Si absent, récupérer le fichier (302 MB) depuis votre PC actuel
# ou depuis une source externe
```

---

### Erreur : "ConnectionRefusedError: [Errno 111]"

**Cause :** MongoDB non démarré

**Solution :**
```bash
# Vérifier les processus
tasklist | findstr mongod

# Si aucun résultat, redémarrer les 3 noeuds (voir Phase 3)
```

---

### Erreur : "Address already in use" (port 27017)

**Cause :** MongoDB déjà en cours sur ce port

**Solution :**
```bash
# Tuer tous les processus MongoDB
taskkill /F /IM mongod.exe

# Relancer les 3 noeuds
```

---

### Erreur : Django "CSRF verification failed"

**Cause :** Cookies bloqués ou cache

**Solution :**
```bash
# Vider le cache du navigateur (Ctrl+Shift+Del)
```