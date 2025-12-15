## data_auto – AutoRia scraper

Застосунок для періодичного асинхронного скрапінгу б/у авто з платформи `AUTO.RIA` з
збереженням даних у PostgreSQL, щоденним дампом бази та розгортанням через `docker-compose`.

### Запуск

```bash
git clone https://github.com/Lebid-Dmytro/data_auto.git
cd data_auto
cp env.example .env
docker-compose up --build
```

Скрапінг та дамп виконуються щодня у час, заданий в `.env` (`SCRAPE_TIME` та `DUMP_TIME`).
