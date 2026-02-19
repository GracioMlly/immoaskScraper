import scrapy
from immoAskScraper.items import ImmoaskscraperItem


class IgoeimmobilierSpider(scrapy.Spider):
    name = "igoeimmobilier"
    allowed_domains = ["igoeimmobilier.com"]
    start_urls = ["https://www.igoeimmobilier.com/les-annonces/"]

    def parse(self, response):
        # On récupère le liens des annonces sur la page
        offers_links = response.css(".epl-archive-entry-image a::attr(href)").getall()

        # Pour chaque lien, on extrait les informations de l'annonce sur sa page correspondante
        for link in offers_links:
            yield response.follow(link, callback=self.parse_offer)

    # Méthode utilisée pour l'extraction des informations d'une annonce
    def parse_offer(self, response):
        offer = ImmoaskscraperItem()

        offer["type"] = response.css("li.property-category::text").get()
        offer["title"] = response.css("h1.post-title::text").get()
        offer["price"] = response.css("span.page-price::text").get()
        offer["localisation"] = response.css(
            "h3.secondary-heading span.suburb::text"
        ).get()
        offer["description"] = response.css(
            "div.epl-section-description .tab-content p::text"
        ).get()
        offer["images"] = response.css("dt.gallery-icon a::attr(href)").getall()
        offer["source"] = {"origin": self.name, "link": response.url}

        yield offer
