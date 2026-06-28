"""
settings.py — Configuration Scrapy + Playwright pour le projet Kayak.

Playwright est activé pour contourner le challenge AWS WAF de Booking
(qui exige l'exécution de JavaScript pour valider la session).
"""

BOT_NAME = "booking_scraper"

SPIDER_MODULES = ["booking_scraper.spiders"]
NEWSPIDER_MODULE = "booking_scraper.spiders"

# --- Politesse ---

# Booking bloque tout via robots.txt — choix conscient pour un projet pédagogique.
ROBOTSTXT_OBEY = False

# Avec Playwright, chaque requête est plus coûteuse (vrai navigateur). On reste prudent.
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# --- Identité ---

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# --- Robustesse ---

RETRY_ENABLED = True
RETRY_TIMES = 2
DOWNLOAD_TIMEOUT = 60  # plus long avec Playwright (chargement du navigateur)

# --- Confort ---

LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"
FEED_EXPORT_INDENT = 2

# ===========================================
# CONFIGURATION PLAYWRIGHT
# ===========================================

# 1. Reactor asyncio : indispensable pour scrapy-playwright.
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# 2. On remplace les downloaders HTTP par les downloaders Playwright.
#    Quand une requête a meta={"playwright": True}, c'est Playwright qui prend la main.
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# 3. Type de navigateur (chromium / firefox / webkit). Chromium = Chrome sans branding.
PLAYWRIGHT_BROWSER_TYPE = "chromium"

# 4. Options de lancement du navigateur.
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,        # True = sans interface graphique. Mets False pour debug visuel.
    "timeout": 30 * 1000,    # 30 secondes pour le démarrage du navigateur (en ms)
}

# 5. Timeout par page chargée (en ms). On laisse 30 s : suffisant pour le challenge JS.
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30 * 1000

# 6. Compatibilité Scrapy moderne.
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
