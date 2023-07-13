import scrapy
from pymongo import MongoClient

class MedicamentSpider(scrapy.Spider):
    name = 'medicament_spider'
    start_urls = ['https://dmp.sante.gov.ma/recherche-medicaments']
    page_limit = 204

    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.database = self.client['maroc_medoc']
        self.collection = self.database['mr_medoc_collection']
        self.unprocessed_pages = []

    def parse(self, response):
        # Extract the card information
        cards = response.css('div.col-md-6.col-xl-4.mb-4.mt-4.cursor-pointer')

        for card in cards:
            card_id = card.attrib['onclick'].split("'")[1]
            modal_url = f'https://dmp.sante.gov.ma/getmedecinedata/{card_id}'

            # Request the modal URL to fetch the modal content
            yield scrapy.Request(modal_url, callback=self.parse_modal, meta={'card_id': card_id})

        # Find the URL of the next page
        next_page_url = response.css('a[aria-label="Next"][href]::attr(href)').get()

        if next_page_url:
            page_number = int(next_page_url.split('=')[-1])
            if page_number <= self.page_limit:
                yield response.follow(next_page_url, callback=self.parse)
            else:
                self.unprocessed_pages.append(next_page_url)
        else:
            self.unprocessed_pages.append(response.url)

    def parse_modal(self, response):
        card_id = response.meta['card_id']
        modal_content = response.text

        # Extract the desired information from the modal content
        nom_medicament = response.css('h3::text').get()
        substance_active = response.xpath('//li[span[contains(text(), "Substance active")]]/span[3]/text()').get()
        epi = response.xpath('//li[span[contains(text(), "EPI")]]/span[3]/text()').get()
        dosage = response.xpath('//li[span[contains(text(), "Dosage")]]/span[3]/text()').get()
        forme = response.xpath('//li[span[contains(text(), "Forme")]]/span[3]/text()').get()
        presentation = response.xpath('//li[span[contains(text(), "Présentation")]]/span[3]/text()').get()
        statut_commercialisation = response.xpath('//li[span[contains(text(), "Statut commercialisation")]]/span[3]/text()').get()
        ppv = response.xpath('//li[span[contains(text(), "PPV")]]/span[3]/text()').get()
        ph = response.xpath('//li/span[@class="fw-bold"][contains(text(), "PH")]/following-sibling::span[1]/text()').get()

        # Store the extracted information in MongoDB or process it as desired
        self.collection.insert_one({
            'Nom du médicament': nom_medicament.strip() if nom_medicament else None,
            'Substance active': substance_active.strip() if substance_active else None,
            'EPI': epi.strip() if epi else None,
            'Dosage': dosage.strip() if dosage else None,
            'Forme': forme.strip() if forme else None,
            'Présentation': presentation.strip() if presentation else None,
            'Statut commercialisation': statut_commercialisation.strip() if statut_commercialisation else None,
            'PPV': ppv.strip() if ppv else None,
            'PH': ph.strip() if ph else None
        })

    def closed(self, reason):
        self.client.close()
        if self.unprocessed_pages:
            print("The following pages were not processed due to an error:")
            for page_url in self.unprocessed_pages:
                print(page_url)
