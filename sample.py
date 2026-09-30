import asyncio
import re
import time
import warnings
from pathlib import Path

import pandas as pd
import requests
from playwright.async_api import async_playwright

from logger import setup_logger
from utils import Helper

warnings.filterwarnings("ignore")

logger = setup_logger("gstn_log")
utils = Helper()

BASE_URL = "https://services.gst.gov.in/services/searchtp"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://services.gst.gov.in",
    "Referer": BASE_URL,
}

gstins = [
    "30AAACL0140P3ZU",
    "12AAACL0140P2ZT",
    "24AAACL0140PBZF",
    "33AAACL0140P5ZM",
    "06AAACL0140P4ZK",
    "27AAACL0140P1ZJ",
    "16AAACL0140P1ZM",
    "37AAACL0140P5ZE",
    "33AAACL0140PCZF",
    "27AAACL0140P4ZG",
    "27AAACL0140PAZA",
    "30AAACL0140P2ZV",
    "34AAACL0140P1CZ",
    "33AAACL0140P1C1",
    "97AAACL0140P1ZC",
    "07AAACL0140P5ZH",
    "09AAACL0140P6ZC",
    "08AAACL0140P1CU",
    "03AAACL0140P3ZR",
    "06AAACL0140P2ZM",
    "08AAACL0140PAZA",
    "07AAACL0140P4ZI",
    "06AAACL0140P5ZJ",
    "20AAACL0140P2ZW",
    "23AAACL0140P7ZL",
    "10AAACL0140P7ZS",
    "06AAACL0140P3ZL",
    "17AAACL0140P3ZI",
    "22AAACL0140P6ZO",
    "11AAACL0140P3ZU",
    "27AAACL0140PIZ2",
    "29AAACL0140P1CQ",
    "19AAACL0140P7ZA",
    "18AAACL0140P7ZC",
    "38AAACL0140P1ZG",
]

audio_dir = Path("output/gstn_audio")
output_dir = Path("output/gstin_json")
audio_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)


def save_failed_gstin(gstin):
    with open("failed.txt", "a", encoding="utf-8") as f:
        f.write(f"{gstin}\n")


def fetch_apis(gstin, captcha, cookies):
    session = requests.Session()

    for c in cookies:
        session.cookies.set(
            c["name"], c["value"], domain=c.get("domain"), path=c.get("path", "/")
        )

    apis = {
        "taxpayerDetails": (
            "https://services.gst.gov.in/services/api/search/" "taxpayerDetails"
        ),
        "taxpayerReturnDetails": (
            "https://services.gst.gov.in/services/api/search/" "taxpayerReturnDetails"
        ),
        "goodservice": (
            f"https://services.gst.gov.in/services/api/search/"
            f"goodservice?gstin={gstin}"
        ),
        "dropdownfinyear": (
            f"https://services.gst.gov.in/services/api/"
            f"dropdownfinyear?gstin={gstin}"
        ),
    }

    out = output_dir / gstin
    out.mkdir(parents=True, exist_ok=True)
    timings = {}

    for name, url in apis.items():
        start = time.perf_counter()

        try:
            if "?" in url:
                r = session.get(url, headers=HEADERS, verify=False, timeout=30)
            else:
                r = session.post(
                    url,
                    json={"gstin": gstin, "captcha": captcha},
                    headers=HEADERS,
                    verify=False,
                    timeout=30,
                )

            timings[name] = time.perf_counter() - start

            logger.info(
                f"{gstin} | {name} | HTTP {r.status_code} | " f"{timings[name]:.2f}s"
            )

            if not r.ok:
                raise Exception(f"{name} failed - HTTP {r.status_code}")

            utils.save_json(r.json(), out / f"{name}.json")

        except Exception:
            timings[name] = time.perf_counter() - start
            logger.exception(f"{gstin} | {name} failed")

    return timings


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, args=["--disable-dev-shm-usage"]
        )

        context = await browser.new_context()
        page = await context.new_page()

        page.on(
            "request",
            lambda r: (
                logger.info(f">>> {r.method} {r.url}")
                if "/services/api/" in r.url
                else None
            ),
        )

        page.on(
            "response",
            lambda r: (
                logger.info(f"<<< {r.status} {r.url}")
                if "/services/api/" in r.url
                else None
            ),
        )

        start = time.perf_counter()
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60_000)

        logger.info(f"Page load: {time.perf_counter() - start:.2f}s")

        try:
            await page.locator(".dimmer-holder").wait_for(
                state="hidden", timeout=20_000
            )
        except Exception:
            pass

        pd.read_csv("FETCH.csv")

        for count, gstin in enumerate(gstins, 1):
            total_start = time.perf_counter()

            try:
                logger.info(f"{count}/{len(gstins)} | {gstin}")

                start = time.perf_counter()

                textbox = page.locator("#for_gstin")
                await textbox.wait_for(state="visible", timeout=20_000)
                await textbox.fill(gstin)

                logger.info(f"{gstin} | Input: " f"{time.perf_counter() - start:.2f}s")

                start = time.perf_counter()

                button = page.locator("button:has(i.fa-volume-up)")
                await button.wait_for(state="visible", timeout=20_000)
                await button.click()

                logger.info(
                    f"{gstin} | Audio click: " f"{time.perf_counter() - start:.2f}s"
                )

                print(f"\nGSTIN: {gstin}")
                captcha = input("CAPTCHA: ").strip()
                captcha = re.sub(r"[^0-9]", "", captcha)

                if not captcha:
                    raise Exception("Invalid CAPTCHA")

                cookies = await context.cookies()

                start = time.perf_counter()

                timings = fetch_apis(gstin, captcha, cookies)

                logger.info(
                    f"{gstin} | API total: " f"{time.perf_counter() - start:.2f}s"
                )

                button = page.locator("button:has(i.fa-refresh)")

                try:
                    await button.wait_for(state="visible", timeout=10_000)
                    await button.click()
                    await page.wait_for_timeout(300)
                except Exception:
                    logger.exception(f"{gstin} | Refresh failed")

                total = time.perf_counter() - total_start

                logger.info(
                    f"{gstin} | TOTAL: {total:.2f}s | "
                    + " | ".join(f"{k}: {v:.2f}s" for k, v in timings.items())
                )

            except Exception:
                logger.exception(f"Failed GSTIN {gstin}")
                save_failed_gstin(gstin)

                try:
                    button = page.locator("button:has(i.fa-refresh)")
                    if await button.is_visible():
                        await button.click()
                        await page.wait_for_timeout(300)
                except Exception:
                    pass

        await browser.close()
        logger.info("Execution completed")


if __name__ == "__main__":
    asyncio.run(main())
