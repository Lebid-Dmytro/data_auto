import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    postgres_db: str = os.getenv("POSTGRES_DB", "auto_ria")
    postgres_user: str = os.getenv("POSTGRES_USER", "auto_ria_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "auto_ria_password")
    postgres_host: str = os.getenv("POSTGRES_HOST", "db")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))

    scrape_time: str = os.getenv("SCRAPE_TIME", "12:00")
    dump_time: str = os.getenv("DUMP_TIME", "23:55")
    timezone: str = os.getenv("TIMEZONE", "Europe/Kyiv")

    base_url: str = os.getenv(
        "AUTO_RIA_BASE_URL",
        "https://auto.ria.com/uk/search/?indexName=auto&limit=100&page=0",
    )


settings = Settings()
