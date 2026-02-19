import scrapy
from immoAskScraper.items import ImmoaskscraperItem


class CoinafriqueSpider(scrapy.Spider):
    name = "coinafrique"
    allowed_domains = ["tg.coinafrique.com"]
    start_urls = ["https://tg.coinafrique.com/categorie/immobilier"]

    def __init__(self, page_limit=2, offer_limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.page_limit = int(page_limit)
        self.offer_limit = int(offer_limit) if type(offer_limit) is str else offer_limit

    def parse(self, response):
        # On récupère le liens des annonces sur la page
        offers_links = response.css(
            '[data-view-origin="category-page-listing"] a.ad__card-image::attr(href)'
        ).getall()

        # On récupère le lien de la page suivante
        next_page_link = response.css(
            ".pagination-indicator.direction:last-child a::attr(href)"
        ).get()

        # Pour chaque lien, on extrait les informations de l'annonce sur sa page correspondante
        # avec un contrôle sur le nombre d'annonce à extraire
        for index, link in enumerate(offers_links):
            if self.offer_limit is None:
                yield response.follow(link, callback=self.parse_offer)
            elif self.offer_limit > index:
                yield response.follow(link, callback=self.parse_offer)
            else:
                break

        # Contrôle du nombre de page à parcourir
        if self.page_limit - 1 > 0 and next_page_link is not None:
            self.page_limit -= 1
            yield response.follow(next_page_link, callback=self.parse)

    # Méthode utilisée pour l'extraction des informations d'une annonce
    def parse_offer(self, response):
        offer = ImmoaskscraperItem()

        offer["type"] = response.css(
            "p.extras span[data-address] + span span::text"
        ).get()
        offer["title"] = response.css(".breadcrumb.cible::text").get()
        offer["price"] = response.css("p.price::text").get()
        offer["surface"] = response.xpath(
            '//li[span[contains(text(), "Superficie")]]/span[2]/text()'
        ).get()

        offer["localisation"] = {
            "city": response.css(
                "p.extras span[data-address]::attr(data-address)"
            ).get()
        }
        offer["description"] = response.css(
            ".ad__info__box-descriptions p:last-child::text"
        ).get()
        offer["images"] = response.css("#slider .swiper-slide::attr(style)").getall()
        offer["source"] = {"origin": self.name, "link": response.url}

        yield offer
