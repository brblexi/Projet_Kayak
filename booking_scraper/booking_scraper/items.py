"""
items.py — Définit la structure d'un hôtel scrapé.

En Scrapy, un "Item" est l'équivalent d'une ligne de données.
On déclare ici les champs qu'on souhaite extraire pour chaque hôtel.
C'est optionnel (on pourrait juste yield des dicts), mais ça documente
clairement le schéma attendu et facilite la validation.
"""

import scrapy


class HotelItem(scrapy.Item):
    city = scrapy.Field()         # ville recherchée (utile pour le merge ensuite)
    name = scrapy.Field()         # nom de l'hôtel
    url = scrapy.Field()          # URL de la fiche hôtel
    score = scrapy.Field()        # note Booking (sur 10)
    #description = scrapy.Field()  # description courte
    lat = scrapy.Field()          # latitude
    lon = scrapy.Field()          # longitude
