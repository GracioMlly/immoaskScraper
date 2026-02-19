import scrapy


# Schéma correspondant à une annonce à scrapper sur un site
class ImmoaskscraperItem(scrapy.Item):
    type = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
    surface = scrapy.Field()
    localisation = scrapy.Field()
    description = scrapy.Field()
    images = scrapy.Field()
    source = scrapy.Field()
