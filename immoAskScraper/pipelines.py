import psycopg2
import json
import os
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from itemadapter import ItemAdapter
from huggingface_hub import InferenceClient

load_dotenv()


# Pipeline Générique
class ImmoaskscraperPipeline:
    def process_item(self, item):
        return item


# Pipeline du site igoeimmobilier
class IgoeimmobilierPipeline:
    name = "igoeimmobilier"

    def process_item(self, item):
        adapter = ItemAdapter(item)

        if adapter["source"]["origin"] == self.name:
            if ":" in adapter["price"]:
                adapter["price"] = (
                    adapter["price"].split(":")[1].strip()[:-6].replace(".", "")
                    + " XOF"
                )

            else:
                adapter["price"] = None

            area = adapter["localisation"].strip()[2:].title()
            adapter["localisation"] = {"city": "Lomé", "area": area}

        return item


# Pipeline du site intendance
class IntendancePipeline:
    name = "intendance"

    def process_item(self, item):
        adapter = ItemAdapter(item)

        if adapter["source"]["origin"] == self.name:
            if not adapter.get("type"):
                type_choices = [word.lower() for word in adapter["title"].split()]

                if "villa" in type_choices:
                    adapter["type"] = "Villa"

                elif "studio" in type_choices:
                    adapter["type"] = "Studio"

                else:
                    adapter["type"] = "Appartement"

            if adapter.get("price"):
                adapter["price"] = (
                    adapter["price"].strip()[:-5].replace(" ", "") + " XOF"
                )

            if adapter.get("surface"):
                adapter["surface"] = adapter["surface"].strip()[:-2] + " m²"

            adapter["images"] = [image.strip()[21:-1] for image in adapter["images"]]

        return item


# Pipeline du site coinafrique
class CoinafriquePipeline:
    name = "coinafrique"

    def process_item(self, item):
        adapter = ItemAdapter(item)

        if adapter["source"]["origin"] == self.name:
            adapter["type"] = adapter["type"][:-1]

            if adapter.get("price"):
                adapter["price"] = adapter["price"][:-4].replace(" ", "") + " XOF"

            if adapter.get("surface"):
                adapter["surface"] = adapter["surface"].replace("m2", "m²")

            if adapter["localisation"]["city"] != "":
                adapter["localisation"]["city"] = adapter["localisation"]["city"].split(
                    ","
                )[0]
            else:
                adapter["localisation"]["city"] = None

            adapter["images"] = [image.strip()[21:-1] for image in adapter["images"]]

        return item


# Pipeline pour la sauvegarde en base de données
# PostgreSQL
class PostgresPipeline:

    # Méthode pour accéder aux settings
    # du fichier Settings.py
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings

        # On récupère les données de connexions
        # défini dans soi même dans le fichier settings.py
        # ou défini automatiquement par un service cloud (exemple : Zyte)
        hostname_from_custom_settings = settings.get("DB_HOSTNAME")
        user_from_custom_settings = settings.get("DB_USER")
        password_from_custom_settings = settings.get("DB_PASSWORD")
        database_from_custom_settings = settings.get("DB_NAME")
        hugging_face_token_from_custom_settings = settings.get("HF_TOKEN")

        # Instanciation de la pipeline
        return cls(
            hostname=hostname_from_custom_settings,
            user=user_from_custom_settings,
            password=password_from_custom_settings,
            database=database_from_custom_settings,
            hugging_face_token=hugging_face_token_from_custom_settings,
        )

    def __init__(self, hostname, user, password, database, hugging_face_token):
        hostname = os.getenv("DB_HOSTNAME") or hostname
        user = os.getenv("DB_USER") or user
        password = os.getenv("DB_PASSWORD") or password
        database = os.getenv("DB_NAME") or database
        hf_token = os.getenv("HF_TOKEN") or hugging_face_token

        # Connexion à la base de données
        self.connection = psycopg2.connect(
            host=hostname, user=user, password=password, dbname=database
        )

        # Création d'un curseur pour l'exécution de commande
        self.cursor = self.connection.cursor(cursor_factory=DictCursor)

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS offers(
            offer_id SERIAL PRIMARY KEY,
            type VARCHAR(255),
            title VARCHAR(255),
            price VARCHAR(255),
            surface VARCHAR(255),
            localisation JSON,
            description VARCHAR,
            images VARCHAR [],
            source JSON NOT NULL,
            embedding VECTOR(1024)
            )    
            """
        )

        # Initialisation du client hugging_face
        self.hf_client = InferenceClient(
            provider="auto",
            api_key=hf_token,
        )

    def process_item(self, item):
        self.cursor.execute(
            "SELECT * FROM offers WHERE type = %s AND title = %s AND description = %s",
            [
                item.get("type"),
                item.get("title"),
                item.get("description"),
            ],
        )

        result = self.cursor.fetchone()

        if result is None:
            query = """INSERT INTO offers(type, title, price, surface, localisation, description, images, source, embedding)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)                
            """

            # Vectorisation de la description/titre d'une annonce
            # à partir d'un modèle de hugging face
            embedding = self.hf_client.feature_extraction(
                item.get("description") or item.get("title") or "",
                model="intfloat/multilingual-e5-large-instruct",
            )

            values = [
                item.get("type"),
                item.get("title"),
                item.get("price"),
                item.get("surface"),
                json.dumps(item.get("localisation")),
                item.get("description"),
                item.get("images"),
                json.dumps(item.get("source")),
                embedding.tolist(),
            ]

            # Exécution de la requête
            self.cursor.execute(query, values)

            # Validation des changements
            self.connection.commit()

        return item

    # Terminaison des connexions à la base de données
    # à la fermeture du spider
    def close_spider(self):
        self.cursor.close()
        self.connection.close()
