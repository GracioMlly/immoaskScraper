import scrapy
from immoAskScraper.items import ImmoaskscraperItem


class IntendanceSpider(scrapy.Spider):
    name = "intendance"
    allowed_domains = ["intendance.tg"]
    start_urls = [
        "https://intendance.tg/en-vente/",
        "https://intendance.tg/locations/",
        "https://intendance.tg/villasmeubles/",
    ]

    def parse(self, response):
        # On récupère le liens des annonces sur la page
        offers_links = response.css(".property_listing h4 a::attr(href)").getall()

        # Pour chaque lien, on extrait les informations de l'annonce sur sa page correspondante
        for link in offers_links:
            yield response.follow(
                link,
                cb_kwargs={"originated_from": response.url},
                callback=self.parse_offer,
            )

    # Méthode utilisée pour l'extraction des informations d'une annonce
    def parse_offer(self, response, originated_from):
        offer = ImmoaskscraperItem()

        if (
            originated_from == self.start_urls[0]
            or originated_from == self.start_urls[1]
        ):
            offer["type"] = "Villa"
        else:
            offer["type"] = None

        offer["title"] = response.css(".entry-title.entry-prop::text").get()
        offer["price"] = response.css(".price_area::text").get()
        offer["surface"] = response.xpath(
            '//div[contains(strong/text(), "Property Size")]/text()'
        ).get()

        offer["localisation"] = {
            "city": response.xpath(
                '//div[contains(strong/text(), "City")]/a/text()'
            ).get(),
            "area": response.xpath(
                '//div[contains(strong/text(), "Area")]/a/text()'
            ).get(),
        }

        offer["description"] = response.css(
            "#wpestate_property_description_section p::text"
        ).get()
        offer["images"] = response.css("div[data-slider-no]::attr(style)").getall()
        offer["source"] = {"origin": self.name, "link": response.url}

        yield offer
