# ⛽ Suivi des prix des carburants

Pipeline quotidien qui télécharge les prix de toutes les stations-service de France, les archive dans une base MySQL normalisée, et affiche la station la moins chère autour de chez vous — avec notification mobile, carte interactive et dashboard web.

Projet pédagogique construit pas à pas : CSV brut → modélisation relationnelle → automatisation → visualisation.

## Sommaire

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Configuration](#configuration)
- [Automatisation quotidienne](#automatisation-quotidienne)
- [Structure du dépôt](#structure-du-dépôt)
- [Source des données](#source-des-données)

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│ data.economie.gouv.fr│────▶│  carburants_table     │────▶│    station      │
│   (export CSV)       │     │  (table de transit,   │     │  (9800 lignes,  │
└─────────────────────┘     │   vidée à chaque run)  │     │   jamais vidée) │
                             └──────────────────────┘     └────────┬────────┘
                                                                    │
                                                           ┌────────▼────────┐
                                                           │     releve      │
                                                           │ (historique,    │
                                                           │  1 ligne par    │
                                                           │  station/jour/  │
                                                           │  carburant)     │
                                                           └─────────────────┘
```

- **`carburants_table`** : table de transit, recréée à chaque téléchargement. Ne contient que le snapshot du jour.
- **`station`** : données stables (adresse, coordonnées). Une ligne par station, jamais dupliquée.
- **`releve`** : historique des prix. Clé primaire composite `(station_id, carburant, jour)`, garantissant un seul prix par station/carburant/jour.

## Prérequis

- macOS (ou Linux), Python 3.10+
- MySQL ou MariaDB 8.0+ (pour les fonctions fenêtre `ROW_NUMBER()`/`LAG()` et les CTE)
- Un compte [ntfy.sh](https://ntfy.sh) (aucune inscription requise) si vous voulez les notifications

## Installation

```bash
git clone https://github.com/<votre-pseudo>/<votre-depot>.git
cd <votre-depot>

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Base de données

```bash
mysql -uroot -e "CREATE DATABASE prixcarburants;"
mysql -uroot prixcarburants < sql/schema.sql
```

Le fichier `sql/schema.sql` doit contenir vos `CREATE TABLE station` et `CREATE TABLE releve` validés.

### Variables d'environnement

Copiez le modèle et renseignez vos propres valeurs :

```bash
cp .env.example .env
```

```ini
# .env (ne jamais committer ce fichier — il est dans .gitignore)
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=prixcarburants
```

**Pourquoi un fichier `.env` plutôt que des identifiants écrits en dur dans le code** : ce fichier n'est jamais versionné (voir `.gitignore`), donc vos identifiants ne se retrouvent jamais sur GitHub, même dans l'historique des commits. Le fichier `.env.example`, lui, est versionné et sert de modèle vide pour quiconque clone le dépôt.

### Activer `local_infile` côté serveur MySQL

```sql
SET GLOBAL local_infile = 1;
```

Pour que ce réglage survive à un redémarrage du serveur, ajoutez `local_infile=1` sous la section `[mysqld]` de votre fichier `my.cnf` (souvent `/opt/homebrew/etc/my.cnf` via Homebrew sur Apple Silicon).

## Utilisation

```bash
# Pipeline complet : télécharge, charge en base, affiche le Top 5 et la tendance,
# envoie une notification
python carburant.py

# Génère une carte HTML colorée par prix (dégradé vert → rouge)
python carte.py

# Lance le dashboard web interactif
streamlit run dashboard.py
```

## Configuration

Le carburant suivi, le rayon de recherche et les coordonnées du domicile sont actuellement définis directement dans le code de chaque script — il n'y a pas d'options en ligne de commande. Voici où modifier chacun d'eux.

### `carburant.py` — le pipeline quotidien

Tout en bas du fichier, dans le bloc `if __name__ == "__main__":` :

```python
resultats = top5(conn, carburant="Gazole", rayon=15)
```

```python
for jour, moyenne, veille, variation in tendance(conn, "Gazole", 15):
```

Remplacez `"Gazole"` par l'un des six carburants disponibles (`"SP95"`, `"SP98"`, `"E10"`, `"E85"`, `"GPLc"`), et `15` par le rayon souhaité, en kilomètres.

Les coordonnées du domicile sont, elles, écrites en dur dans les requêtes SQL des fonctions `top5()` et `tendance()` elles-mêmes (`48.8566` et `2.7800`) — pour les changer, recherchez ces deux valeurs dans `carburant.py` et remplacez-les par votre latitude/longitude (trouvables sur Google Maps : clic droit sur votre position → les coordonnées s'affichent en haut du menu contextuel).

### `carte.py` — la carte HTML

Dans le bloc principal, en bas du fichier :

```python
stations = recuperer_stations(conn, carburant="Gazole")
```

Changez `"Gazole"` pour générer la carte d'un autre carburant. Le nom du fichier de sortie (`carte_gazole.html`) reste fixe — pensez à l'adapter aussi si vous changez de carburant, pour ne pas écraser une carte précédente par erreur.

### `dashboard.py` — le dashboard Streamlit

C'est le seul endroit où le carburant **n'a pas besoin d'être modifié dans le code** : le menu déroulant (`st.selectbox`) permet de le choisir directement dans l'interface, à chaque visite.

Le rayon (`rayon=15`, dans l'appel à `tendance(conn, carburant=carburant, rayon=15)`) reste en revanche fixé dans le code pour l'instant — pour le rendre réglable depuis l'interface sans toucher au code à chaque fois, on peut le remplacer par un curseur Streamlit :

```python
rayon = st.slider("Rayon de recherche (km)", min_value=2, max_value=60, value=15)
```

puis utiliser cette variable `rayon` partout où `15` était écrit en dur.

## Automatisation quotidienne

Une tâche `cron` lance `carburant.py` chaque matin :

```bash
crontab -e
```

```cron
30 7 * * * cd /chemin/vers/le/projet && /chemin/vers/le/projet/.venv/bin/python3 /chemin/vers/le/projet/carburant.py >> /chemin/vers/le/projet/data/log.txt 2>&1
```

**Limite connue sur un portable** : si le Mac est en veille à l'heure programmée (clapet fermé, écran éteint), `cron` ne se déclenche pas — il ne rattrape pas l'exécution manquée après coup. Sur un usage mobile, pensez à ouvrir le Mac un peu avant l'heure programmée, ou à décaler l'horaire sur un moment où la machine est généralement éveillée.

## Structure du dépôt

```
.
├── carburant.py          # Pipeline principal : téléchargement, chargement, requêtes, notification
├── carte.py              # Génère une carte HTML colorée par prix
├── dashboard.py          # Dashboard Streamlit interactif
├── sql/
│   └── schema.sql        # CREATE TABLE station, releve
├── data/
│   └── snapshots/        # CSV téléchargés quotidiennement (non versionné)
├── requirements.txt
├── .env.example           # Modèle de configuration (sans vraies valeurs)
├── .gitignore
└── README.md
```

## Source des données

Export CSV généré par [data.economie.gouv.fr](https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2/), dérivé du flux officiel brut (XML) publié par [donnees.roulez-eco.fr](https://donnees.roulez-eco.fr), sous licence ouverte.
