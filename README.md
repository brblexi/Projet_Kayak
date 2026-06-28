# Projet Kayak

Projet réalisé dans le cadre du Bootcamp Fullstack Data de Jedha — Bloc 1 (Construction et alimentation d'une infrastructure de gestion de données).

## Contexte

Kayak souhaite développer une application qui recommande des destinations en France à partir de deux signaux : la météo prévue et la qualité des hôtels disponibles. Le projet construit une pipeline complète qui récupère ces deux types de données, les croise, et les stocke à la fois en data lake (S3) et en data warehouse (PostgreSQL sur RDS).

Les 35 villes étudiées sont celles fournies par l'énoncé (cf. `00_enonce_jedha.ipynb`).

## Architecture

```
                        +-----------------------+
                        | API OpenWeatherMap    |
                        | (35 villes, 5 jours)  |
                        +-----------+-----------+
                                    |
                                    v
                          +---------------------+
                          | Score meteo         |
                          | + selection top 5   |
                          +----------+----------+
                                     |
                                     v
                +--------------------+--------------------+
                | Scrapy + Playwright (challenge AWS WAF) |
                | -> 100 hotels Booking                   |
                +--------------------+--------------------+
                                     |
                                     v
                          +---------------------+
                          | Jointure + score    |
                          | combine             |
                          +----+-----------+----+
                               |           |
                               v           v
                          +--------+   +---------+
                          |   S3   |   |   RDS   |
                          | (raw)  |   | (clean) |
                          +--------+   +---------+
                               |           |
                               +-----+-----+
                                     |
                                     v
                          +---------------------+
                          | Cartes Plotly       |
                          +---------------------+
```

## Stack technique

- Python 3.13, pandas, requests
- Scrapy 2.15 + scrapy-playwright + Chromium (pour contourner le challenge JS de Booking)
- Plotly Express pour les cartes
- boto3 pour S3
- SQLAlchemy 2.0 (compatible PostgreSQL via psycopg2-binary, et SQLite via la stdlib)
- python-dotenv pour les credentials

## Structure du projet

```
Projet_Kayak/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── 00_enonce_jedha.ipynb         # Énoncé original Jedha (lecture seule)
├── 01_meteo.ipynb                # API Nominatim + OpenWeatherMap, score météo
├── 02_visualisation_meteo.ipynb  # Cartes Plotly, extraction du top 5
├── 03_scraping.ipynb             # Pilotage du spider Scrapy, chargement résultats
├── 04_merge_viz.ipynb            # Fusion météo + hôtels, score combiné, cartes finales
├── 05_s3_upload.ipynb            # Upload des données dans S3
├── 06_rds_load.ipynb             # Chargement des données dans PostgreSQL RDS
│
├── booking_scraper/              # Projet Scrapy autonome
│   ├── scrapy.cfg
│   └── booking_scraper/
│       ├── items.py
│       ├── settings.py
│       └── spiders/booking_spider.py
│
└── data/                         # Fichiers générés
    ├── weather.csv               # 35 villes avec score météo
    ├── top5_cities.csv           # 5 meilleures destinations
    ├── hotels.jsonl              # 100 hôtels scrapés (format JSON Lines)
    ├── hotels.csv                # Hôtels nettoyés
    └── recommendations.csv       # Dataset final croisant météo + hôtels
```

## Détail des notebooks

### 01_meteo

Récupère les coordonnées GPS des 35 villes via Nominatim (1 requête/seconde pour respecter la politique d'usage), puis interroge l'endpoint `/forecast` d'OpenWeatherMap pour obtenir les prévisions sur 5 jours par tranches de 3h (40 points par ville).

Agrège ces 40 points en trois indicateurs synthétiques : température moyenne, pluie totale, couverture nuageuse moyenne. Calcule ensuite un score météo simple : `temp_avg - 0.5 * rain_total - 0.1 * clouds_avg`.

Sortie : `data/weather.csv`.

### 02_visualisation_meteo

Affiche les 35 villes sur une carte Plotly (`scatter_map` avec fond `carto-positron`), colorées selon leur score météo. Extrait les 5 meilleures villes via `df.nlargest(5, "weather_score")`.

Sortie : `data/top5_cities.csv` qui pilotera la phase de scraping.

### 03_scraping

Lance le spider Scrapy contenu dans `booking_scraper/`. Le spider lit `top5_cities.csv` et scrape les 20 premiers hôtels par ville sur Booking.com.

Particularité technique : Booking.com renvoie un HTTP 202 + un challenge JavaScript (AWS WAF) qui pose un cookie de session après exécution du JS. Scrapy seul ne pouvant pas exécuter de JavaScript, le projet utilise `scrapy-playwright` qui pilote un vrai navigateur Chromium en arrière-plan. Diagnostic initial fait via `scrapy shell`.

Le spider extrait pour chaque hôtel : nom, URL, note Booking, latitude, longitude. La description a été retirée du périmètre après diagnostic (timing de chargement JS imprévisible, champ non critique pour la suite).

Sortie : `data/hotels.jsonl` (format JSON Lines pour résister aux relances).

### 04_merge_viz

Joint `df_hotels` avec `df_weather` sur la colonne `city`. Normalise le score météo entre 0 et 10 (min-max scaling) pour pouvoir le combiner avec la note Booking déjà sur cette échelle. Construit un score combiné pondéré : `0.6 * score_booking + 0.4 * weather_score_norm`.

Produit les cartes finales : top 5 destinations et top 20 hôtels.

Sortie : `data/recommendations.csv`.

### 05_s3_upload

Charge les credentials AWS depuis `.env`, crée un client `boto3`, et uploade les fichiers dans le bucket S3 sous le préfixe `raw/` (convention médaillon bronze/silver/gold pour distinguer les données brutes).

### 06_rds_load

Charge les données nettoyées dans une base SQL relationnelle qui servira de data warehouse. La connexion utilise SQLAlchemy, ce qui rend le code indépendant du SGBD : la même logique fonctionne sur PostgreSQL (RDS) ou SQLite (local) en changeant uniquement la `DATABASE_URL`.

La démonstration de ce notebook tourne sur SQLite (`data/kayak.db`). L'architecture cible initiale était PostgreSQL sur AWS RDS (Free Tier, `db.t3.micro`, région `eu-north-1`) — la configuration correspondante reste documentée dans `.env.example` et le code n'aurait à changer que l'URL.

Le notebook effectue : test de connexion (`SELECT 1`), chargement des deux tables via `df.to_sql()`, puis trois requêtes SQL de vérification (`COUNT(*)`, top 5 par score combiné, agrégation `GROUP BY city`).

## Résultats

| Étape | Résultat |
|---|---|
| Villes scorées (météo) | 35/35 |
| Top 5 retenu | Strasbourg, Aix en Provence, Marseille, Lyon, Besançon |
| Hôtels scrapés | 100 (20 × 5 villes) |
| Réponses HTTP 200 vs 202 | 104 / 1 |
| Coordonnées GPS récupérées | 100/100 (100 %) |
| Notes Booking récupérées | 90/100 (10 hôtels sans note, probablement nouveaux établissements) |
| Note moyenne | 8.22 / 10 |
| Durée totale du scraping | 11 min 37 s |
| Volume téléchargé via Playwright | 162 MB (~33 000 sous-requêtes incluant scripts, CSS, images) |

Le score combiné `0.6 * note_booking + 0.4 * meteo_normalisée` met en avant les hôtels qui combinent la meilleure météo et la meilleure note. Sur ce run, le top 5 final est :

1. Studio terrasse (Aix en Provence) — score combiné 9.57
2. Residence Inn by Marriott Strasbourg — 9.28
3. K Hotel (Strasbourg) — 9.22
4. Hôtel Restaurant Athena Spa (Strasbourg) — 9.22
5. Le Grand Hotel By Stay Collection (Strasbourg) — 9.16

Le top 5 est dominé par Strasbourg (4 hôtels sur 5) qui combine la météo la plus favorable de la semaine et plusieurs hôtels bien notés, suivi d'Aix en Provence en tête grâce à un hôtel exceptionnellement bien noté (9.9/10).

## Reproduire le projet

Pré-requis :
- Python 3.13+
- Un compte AWS avec un bucket S3 et une instance RDS PostgreSQL
- Une clé API OpenWeatherMap (gratuite)

Installation :

```bash
git clone <url-du-repo>
cd Projet_Kayak

python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Renseigner les valeurs dans .env
```

Les notebooks doivent être exécutés dans l'ordre numérique (01 → 06).

## Choix techniques notables

**scrapy-playwright plutôt que Scrapy pur.** Scrapy pur reçoit un HTTP 202 sur Booking à cause du challenge JavaScript d'AWS WAF. Playwright pilote un vrai Chromium qui résout le challenge transparentement. Le coût (10× plus lent, 162 MB téléchargés) est acceptable pour le volume du projet.

**Projet Scrapy autonome plutôt qu'embarqué dans un notebook.** Scrapy utilise Twisted, qui a sa propre boucle d'événements incompatible avec celle de Jupyter. L'architecture recommandée par la doc Scrapy est un projet séparé, lancé en CLI, avec sortie dans un fichier que le notebook recharge.

**Format JSON Lines pour la sortie du spider.** Contrairement au JSON classique qui se corrompt si Scrapy append un nouveau run, le format JSON Lines (un objet par ligne) supporte nativement l'append. C'est aussi le format standard des pipelines de données modernes (Kafka, Spark, BigQuery).

**Sélecteurs `data-testid` pour le scraping.** Booking renomme régulièrement ses classes CSS pour casser les scrapers. Les attributs `data-testid` sont utilisés pour leurs tests automatisés internes et restent stables sur de longues périodes.

**Couche d'abstraction SQLAlchemy.** Le code de chargement en base passe par SQLAlchemy plutôt que par psycopg2 directement. Le code applicatif est ainsi indépendant du SGBD : la `DATABASE_URL` peut pointer vers SQLite, PostgreSQL ou MySQL, le reste du code reste identique. Cette flexibilité est mise à profit dans le notebook 6 qui tourne sur SQLite en local pour la démonstration, tandis que la configuration PostgreSQL/RDS reste documentée pour un déploiement cible.

**Security Group RDS limité à `My IP`.** Plutôt que d'exposer la base à `0.0.0.0/0`, seule l'IP de la machine de développement est autorisée à se connecter sur le port 5432.

**Utilisateur IAM dédié `kayak-user`.** Création d'un utilisateur AWS séparé du compte root, avec uniquement les permissions `AmazonS3FullAccess` et `AmazonRDSFullAccess`. Principe du moindre privilège : si les credentials fuitent, l'attaquant ne peut pas créer une instance EC2 de minage.

## Limites et améliorations possibles

- Pas de tests automatisés (pytest sur les fonctions pures + tests d'intégration mockés sur les APIs externes)
- Pas d'orchestration : exécution manuelle des notebooks, à faire évoluer vers Airflow ou Prefect pour des runs hebdomadaires
- Pas de retry logic robuste : si OpenWeatherMap a un hoquet, le notebook plante. À corriger via `tenacity` avec backoff exponentiel
- `if_exists="replace"` dans `to_sql()` écrase l'historique. En production il faudrait passer en `append` avec une colonne `loaded_at` pour conserver l'évolution dans le temps
- Score météo non validé empiriquement : la pondération `0.5 * pluie + 0.1 * nuages` est heuristique. À calibrer contre des données métier (taux de réservation par ville)
- Pas de monitoring : aucun log structuré, aucune alerte sur les runs vides
- Champ description abandonné : la description Booking est injectée par JavaScript avec un timing imprévisible. À récupérer via une autre approche si jugé nécessaire
