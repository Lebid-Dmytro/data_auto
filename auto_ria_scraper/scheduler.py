import asyncio
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from .config import settings
from .scraper import scrape_all


async def run_dump() -> None:
    dumps_dir = "/app/dumps"
    os.makedirs(dumps_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(dumps_dir, f"dump_{timestamp}.sql")

    cmd = [
        "pg_dump",
        "-h",
        settings.postgres_host,
        "-p",
        str(settings.postgres_port),
        "-U",
        settings.postgres_user,
        "-d",
        settings.postgres_db,
        "-f",
        file_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        env={**os.environ, "PGPASSWORD": settings.postgres_password},
    )
    await proc.wait()


def _parse_time(time_str: str) -> tuple[int, int]:
    hour_str, minute_str = time_str.split(":")
    return int(hour_str), int(minute_str)


def create_scheduler() -> AsyncIOScheduler:
    try:
        tz = timezone(settings.timezone)
    except Exception:
        if settings.timezone == "Europe/Kyiv":
            tz = timezone("Europe/Kiev")
        else:
            raise
    scheduler = AsyncIOScheduler(timezone=tz)

    scrape_hour, scrape_minute = _parse_time(settings.scrape_time)
    dump_hour, dump_minute = _parse_time(settings.dump_time)

    scheduler.add_job(
        scrape_all,
        CronTrigger(hour=scrape_hour, minute=scrape_minute, timezone=tz),
        name="daily_scrape",
    )
    scheduler.add_job(
        run_dump,
        CronTrigger(hour=dump_hour, minute=dump_minute, timezone=tz),
        name="daily_dump",
    )

    return scheduler
