# Projet Kayak

Projet du Bootcamp Fullstack Data de Jedha — Bloc 1 (Construction et alimentation d'une infrastructure de gestion de données).

## Objectif

Construire une pipeline de données qui recommande des destinations touristiques en France pour la semaine à venir, en croisant la météo prévue et la qualité des hôtels disponibles sur Booking.

Les 35 villes étudiées sont celles fournies par l'énoncé Jedha (cf. `00_enonce_jedha.ipynb`).

## Pipeline

```
    API OpenWeatherMap (35 villes)
              |
              v
    Score meteo + selection du top 5
              |
              v
    Scraping Booking (100 hotels)
              |
              v
    Fusion + score combine
         |         |
         v         v
      S3 (raw)   SQL (clean)
                    |
                    v
              Cartes Plotly
```

## Stack

- **Python 3.13**, pandas, requests
- **Scrapy 2.15 + Playwright** pour le scraping de Booking (défenses anti-bot)
- **Plotly Express** pour les cartes
- **boto3** pour AWS S3
- **SQLAlchemy 2.0** pour la base SQL (compatible PostgreSQL/RDS et SQLite)
- **python-dotenv** pour les credentials

## Structure du projet

```
Projet_Kayak/
├── 00_enonce_jedha.ipynb         Énoncé original Jedha
├── 01_meteo.ipynb                API météo + score
├── 02_visualisation_meteo.ipynb  Cartes + top 5 villes
├── 03_scraping.ipynb             Lance le spider Booking
├── 04_merge_viz.ipynb            Fusion et cartes finales
├── 05_s3_upload.ipynb            Upload S3
├── 06_rds_load.ipynb             Chargement base SQL
│
├── booking_scraper/              Projet Scrapy
├── data/                         CSV générés
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```

## Les notebooks

**01 — Météo.** Géocode les 35 villes via Nominatim (OpenStreetMap), récupère 5 jours de prévisions via OpenWeatherMap, calcule un score météo par ville.

**02 — Visualisation météo.** Carte Plotly des 35 villes colorées selon leur score, extraction du top 5 pour piloter le scraping.

**03 — Scraping.** Lance le spider Scrapy qui scrape 20 hôtels par ville sur Booking (100 hôtels au total). Utilise Playwright pour contourner le challenge JavaScript (AWS WAF) mis en place par Booking.

**04 — Fusion et cartes.** Joint météo et hôtels, calcule un score combiné (60% note hôtel, 40% météo normalisée), affiche les cartes des recommandations finales.

**05 — Upload S3.** Envoie les données brutes dans un bucket S3 sous le préfixe `raw/`.

**06 — Chargement SQL.** Charge les données propres dans une base SQL (démonstration sur SQLite, code compatible RDS PostgreSQL).

## Résultats

- **35 villes** analysées, top 5 retenu : Strasbourg, Aix en Provence, Marseille, Lyon, Besançon
- **100 hôtels** scrapés (20 par ville), dont 90 avec note Booking (moyenne 8.22/10)
- **Temps de scraping** : ~12 minutes
- **Top 3 final** : Studio terrasse à Aix en Provence (9.92), Maison Olea à Marseille (9.76), Résidence Du Vieux Port à Marseille (9.34)

## Reproduire le projet

Pré-requis : Python 3.13+, un compte AWS (S3 + RDS), une clé OpenWeatherMap (gratuite).

```bash
git clone <url-du-repo>
cd Projet_Kayak

python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Remplir .env avec les vraies valeurs
```

Puis lancer les notebooks dans l'ordre (01 → 06).

## Choix techniques principaux

**Playwright pour Booking.** Booking utilise un challenge JavaScript (AWS WAF) qui bloque Scrapy seul. Playwright pilote un vrai Chromium qui résout ce challenge automatiquement.

**Projet Scrapy séparé.** Scrapy (basé sur Twisted) est incompatible avec la boucle d'événements de Jupyter, d'où l'architecture recommandée : un projet Scrapy autonome lancé en CLI, dont le notebook lit ensuite la sortie.

**SQLAlchemy pour la base SQL.** L'abstraction SQLAlchemy permet au même code de tourner sur PostgreSQL (cible RDS) ou SQLite (démo locale) en changeant simplement l'URL de connexion.

**Architecture data lake + data warehouse.** Les données brutes sont archivées dans S3 (data lake), les données nettoyées sont chargées dans une base SQL (data warehouse). Séparation utile pour retraiter en aval si un bug est découvert.

**Sécurité.** Credentials dans `.env` (jamais commit), utilisateur IAM dédié avec permissions minimales, Security Group RDS restreint à l'IP de développement.

## Limites

Ce projet est un prototype pédagogique. Pour un usage en production il manquerait :

- Des tests automatisés (pytest sur les fonctions pures)
- Une orchestration (Airflow ou Prefect) pour des runs planifiés
- Une logique de retry sur les appels API (via `tenacity`)
- Une gestion d'historique en base (`append` + `loaded_at` au lieu de `replace`)
- Du monitoring et de l'alerting sur les runs vides
