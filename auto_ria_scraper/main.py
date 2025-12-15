import asyncio
import logging

from .db import init_db
from .scheduler import create_scheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started. Waiting for scheduled jobs.")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
