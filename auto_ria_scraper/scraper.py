import asyncio
from dataclasses import dataclass
from typing import List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import Browser, async_playwright

from .config import settings
from .db import db


REAL_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/143.0.0.0 Safari/537.36"
)


@dataclass
class CarData:
    url: str
    title: Optional[str]
    price_usd: Optional[float]
    odometer: Optional[int]
    username: Optional[str]
    phone_number: Optional[str]
    image_url: Optional[str]
    images_count: Optional[int]
    car_number: Optional[str]
    car_vin: Optional[str]


def _extract_auto_id_from_url(url: str) -> Optional[int]:
    try:
        tail = url.rstrip("/").split("_")[-1]
        auto_id_str = tail.split(".")[0]
        return int(auto_id_str)
    except Exception:
        return None


async def _fetch_final_page_data(
    session: aiohttp.ClientSession, auto_id: int
) -> Optional[dict]:
    url = (
        f"https://auto.ria.com/bff/final-page/public/{auto_id}"
        "?langId=4&device=desktop-web&ssr=0"
    )
    headers = {
        "accept": "*/*",
        "user-agent": REAL_BROWSER_UA,
    }
    try:
        async with session.get(url, headers=headers, timeout=15) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
    except Exception:
        return None


async def _fetch_contact_from_popup(
    session: aiohttp.ClientSession, auto_id: int, referer: str
) -> Tuple[Optional[str], Optional[str]]:
    url = "https://auto.ria.com/bff/final-page/public/auto/popUp/"

    payload = {
        "autoId": auto_id,
        "type": "UsedAuto",
        "langId": 4,
        "popUpId": "autoPhone",
    }

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://auto.ria.com",
        "referer": referer,
        "user-agent": REAL_BROWSER_UA,
        "x-ria-source": "vue3",
    }

    try:
        async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                return None, None
            data = await resp.json()
    except Exception:
        return None, None

    username: Optional[str] = None
    phone: Optional[str] = None

    for tmpl in data.get("templates", []):
        if tmpl.get("id") == "autoPhoneMainInfoName":
            elems = tmpl.get("elements") or []
            if elems:
                username = (elems[0].get("content") or "").strip()

        if tmpl.get("id") == "autoPhoneCallRequest":
            params = (tmpl.get("actionData") or {}).get("params") or {}
            raw_phone = str(params.get("phone") or "")
            digits = "".join(ch for ch in raw_phone if ch.isdigit())
            if digits:
                if digits.startswith("0"):
                    digits = "38" + digits
                if not digits.startswith("38"):
                    digits = "38" + digits
                phone = digits

    if not phone:
        add_params = data.get("additionalParams") or {}
        raw = add_params.get("phoneStr") or ""
        if raw:
            digits = "".join(ch for ch in raw if ch.isdigit())
            if digits:
                if digits.startswith("0"):
                    digits = "38" + digits
                if not digits.startswith("38"):
                    digits = "38" + digits
                phone = digits

    return username, phone


async def fetch_car_data(
    session: aiohttp.ClientSession, detail_url: str
) -> Optional[CarData]:
    auto_id = _extract_auto_id_from_url(detail_url)
    if auto_id is None:
        return None

    final_data = await _fetch_final_page_data(session, auto_id)
    if not final_data:
        return None

    auto_data = final_data.get("autoData") or {}
    price_info = final_data.get("priceInfo") or {}

    title = auto_data.get("title") or auto_data.get("titleAuto")

    price_usd: Optional[float] = None
    price_val = price_info.get("price") or auto_data.get("USD")
    if price_val is not None:
        try:
            price_usd = float(price_val)
        except (TypeError, ValueError):
            price_usd = None

    odometer: Optional[int] = None
    race = auto_data.get("raceInt") or auto_data.get("race")
    if race is not None:
        try:
            odometer = int(str(race).replace(" ", ""))
        except ValueError:
            odometer = None

    main_photo = (final_data.get("photoData") or {}).get("seoLinkM") or ""
    image_url = main_photo or None

    images_count: Optional[int] = None
    photos = (final_data.get("photoData") or {}).get("photos") or []
    try:
        images_count = len(photos)
    except TypeError:
        images_count = None

    car_number = auto_data.get("number") or auto_data.get("stateNumber")
    if car_number:
        car_number = str(car_number).strip()

    car_vin = auto_data.get("VIN") or auto_data.get("vin")
    if car_vin:
        car_vin = str(car_vin).strip()

    username, phone_number = await _fetch_contact_from_popup(
        session, auto_id, referer=detail_url
    )

    return CarData(
        url=detail_url,
        title=title,
        price_usd=price_usd,
        odometer=odometer,
        username=username,
        phone_number=phone_number,
        image_url=image_url,
        images_count=images_count,
        car_number=car_number,
        car_vin=car_vin,
    )


async def scrape_search_page(browser: Browser, base_url: str, max_pages: int | None = None) -> List[str]:
    all_links: List[str] = []
    page_index = 0

    while True:
        page = await browser.new_page()
        if "page=" in base_url:
            url = base_url.split("page=")[0] + f"page={page_index}"
        else:
            sep = "&" if "?" in base_url else "?"
            url = f"{base_url}{sep}page={page_index}"
        try:
            await page.goto(url, wait_until="load", timeout=30000)
            await page.wait_for_load_state("networkidle")
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            print(f"failed to load search page {url}: {exc}")
            await page.close()
            break

        links: List[str] = []
        for title_div in soup.select(
            "div.common-text.size-16-20.titleS.fw-bold.mb-4"
        ):
            parent_a = title_div.find_parent("a")
            href = parent_a.get("href") if parent_a else None
            if not href:
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://auto.ria.com" + href
            links.append(href)

        print(f"page {page_index}: found {len(links)} car links")

        if not links:
            break

        all_links.extend(links)
        page_index += 1

        await page.close()

        if max_pages is not None and page_index >= max_pages:
            break

    return all_links


async def scrape_all() -> None:
    await db.connect()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            car_urls = await scrape_search_page(browser, settings.base_url)
            print(f"total car urls found: {len(car_urls)}")
        finally:
            await browser.close()

    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(5)

        async def process_car(url: str) -> None:
            async with sem:
                car = await fetch_car_data(session, url)
                if car:
                    await db.upsert_car(car.__dict__)

        await asyncio.gather(*(process_car(u) for u in car_urls))
