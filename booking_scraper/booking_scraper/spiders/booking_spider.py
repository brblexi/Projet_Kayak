"""
booking_spider.py — Spider Scrapy + Playwright pour Booking.com

Différences avec la version Scrapy pure :
  - Chaque requête est lancée via Playwright (vrai navigateur Chromium).
  - On attend que les éléments d'hôtel soient présents dans le DOM avant de parser
    (PageMethod "wait_for_selector").
  - La méthode start() est async (compatible Scrapy 2.13+).

Pipeline en 2 étapes (inchangé par rapport à la version Scrapy pure) :
  1. parse()        — page de résultats : extrait nom, URL, score
  2. parse_hotel()  — page de détail   : extrait description et coordonnées GPS
"""

import csv
from pathlib import Path
from urllib.parse import quote_plus

import scrapy
from scrapy_playwright.page import PageMethod

from booking_scraper.items import HotelItem


class BookingSpider(scrapy.Spider):
    """Scrape les 20 premiers hôtels de chaque ville fournie en entrée."""

    name = "booking"
    allowed_domains = ["booking.com"]

    HOTELS_PER_CITY = 20

    # Meta Playwright commun à toutes les requêtes du spider.
    # On attend la présence des cartes d'hôtels avant de rendre la main au callback.
    PLAYWRIGHT_META_LIST = {
        "playwright": True,
        "playwright_page_methods": [
            # On attend qu'au moins une carte d'hôtel soit visible (max 15 s)
            PageMethod("wait_for_selector", 'div[data-testid="property-card"]', timeout=15000),
        ],
    }

    PLAYWRIGHT_META_HOTEL = {
        "playwright": True,
        "playwright_page_methods": [
            PageMethod("wait_for_selector", 'a[data-atlas-latlng]', timeout=15000),
        ],
    }

    async def start(self):
        """Point d'entrée asynchrone (Scrapy 2.13+).

        Génère une requête de recherche par ville à partir de top5_cities.csv.
        """
        csv_path = Path(__file__).resolve().parents[3] / "data" / "top5_cities.csv"

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cities = [row["city"] for row in reader]

        self.logger.info(f"Villes à scraper : {cities}")

        for city in cities:
            search_url = (
                f"https://www.booking.com/searchresults.fr.html"
                f"?ss={quote_plus(city)}"
                f"&order=popularity"
            )
            yield scrapy.Request(
                url=search_url,
                callback=self.parse,
                cb_kwargs={"city": city},
                meta=self.PLAYWRIGHT_META_LIST,
            )

    def parse(self, response, city):
        """Parse une page de résultats de recherche."""
        hotel_cards = response.css('div[data-testid="property-card"]')
        self.logger.info(f"[{city}] {len(hotel_cards)} hôtels trouvés sur la page")

        for card in hotel_cards[: self.HOTELS_PER_CITY]:
            name = card.css('div[data-testid="title"]::text').get()

            relative_url = card.css('a[data-testid="title-link"]::attr(href)').get()
            if not relative_url:
                continue
            hotel_url = response.urljoin(relative_url)

            score_raw = card.css('div[data-testid="review-score"] *::text').getall()
            score = self._extract_score(score_raw)

            yield scrapy.Request(
                url=hotel_url,
                callback=self.parse_hotel,
                cb_kwargs={
                    "city": city,
                    "name": name.strip() if name else None,
                    "score": score,
                    "url": hotel_url,
                },
                meta=self.PLAYWRIGHT_META_HOTEL,
            )

    def parse_hotel(self, response, city, name, score, url):
        """Parse une page de fiche hôtel : extraction des coordonnées GPS."""
        # Coordonnées GPS : exposées dans data-atlas-latlng sur le bouton "afficher la carte"
        latlng = response.css('a[data-atlas-latlng]::attr(data-atlas-latlng)').get()
        lat, lon = (None, None)
        if latlng and "," in latlng:
            try:
                lat_str, lon_str = latlng.split(",", 1)
                lat, lon = float(lat_str), float(lon_str)
            except ValueError:
                pass

        yield HotelItem(
            city=city,
            name=name,
            url=url,
            score=score,
            lat=lat,
            lon=lon,
        )

    @staticmethod
    def _extract_score(raw_texts):
        """Extrait un float depuis les fragments de texte du bloc note."""
        for txt in raw_texts:
            cleaned = txt.strip().replace(",", ".")
            try:
                value = float(cleaned)
                if 0 <= value <= 10:
                    return value
            except ValueError:
                continue
        return None
