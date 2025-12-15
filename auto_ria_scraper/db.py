import asyncio
from typing import Any, Dict, Optional

import asyncpg

from .config import settings


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    price_usd NUMERIC,
    odometer BIGINT,
    username TEXT,
    phone_number TEXT,
    image_url TEXT,
    images_count INT,
    car_number TEXT,
    car_vin TEXT,
    datetime_found TIMESTAMPTZ DEFAULT NOW()
);
"""


class Database:
    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                host=settings.postgres_host,
                port=settings.postgres_port,
            )
            async with self._pool.acquire() as conn:
                await conn.execute(CREATE_TABLE_SQL)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def upsert_car(self, data: Dict[str, Any]) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cars (
                    url,
                    title,
                    price_usd,
                    odometer,
                    username,
                    phone_number,
                    image_url,
                    images_count,
                    car_number,
                    car_vin,
                    datetime_found
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW()
                )
                ON CONFLICT (url) DO UPDATE
                SET
                    title = EXCLUDED.title,
                    price_usd = EXCLUDED.price_usd,
                    odometer = EXCLUDED.odometer,
                    username = EXCLUDED.username,
                    phone_number = EXCLUDED.phone_number,
                    image_url = EXCLUDED.image_url,
                    images_count = EXCLUDED.images_count,
                    car_number = EXCLUDED.car_number,
                    car_vin = EXCLUDED.car_vin,
                    datetime_found = NOW();
                """,
                data.get("url"),
                data.get("title"),
                data.get("price_usd"),
                data.get("odometer"),
                data.get("username"),
                data.get("phone_number"),
                data.get("image_url"),
                data.get("images_count"),
                data.get("car_number"),
                data.get("car_vin"),
            )


db = Database()


async def init_db() -> None:
    await db.connect()


if __name__ == "__main__":
    asyncio.run(init_db())
