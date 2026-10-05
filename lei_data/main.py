import os
import time
import json
import logging
import requests
import pandas as pd
from utils import Helper
import warnings
import urllib3

warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    filename="lei_fetch.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

os.makedirs("success", exist_ok=True)
os.makedirs("errors", exist_ok=True)

df_links = pd.read_excel("SLINKS1.xlsx")
session = requests.Session()
session.get(
    "https://www.legalentityidentifier.in/leicert/",
    headers={"User-Agent": "Mozilla/5.0"}
)

utils = Helper()
failed_ids = []

total = len(df_links)

for idx, (_, row) in enumerate(df_links.iterrows(), 1):
    company = row["company"]
    lei = row["id"]

    logging.info("[%s/%s] Processing %s", idx, total, lei)
    print(f"[{idx}/{total}] Processing {company} | {lei}")

    try:
        url = f"https://api-india.companydata.io/api/v1/lei-records/{lei}"

        r = session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            verify=False
        )

        if r.status_code != 200:
            logging.error(
                "[%s/%s] LEI failed | %s | status=%s",
                idx, total, lei, r.status_code
            )
            failed_ids.append(lei)
            continue

        data = r.json()

        if not data:
            logging.error("[%s/%s] Empty JSON | %s", idx, total, lei)
            failed_ids.append(lei)

            with open(f"errors/{lei}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            continue

        with open(
            f"success/{str(company).replace('/', '_')}.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logging.info("[%s/%s] Success | %s", idx, total, lei)
        time.sleep(.5)

    except Exception as e:
        logging.exception(
            "[%s/%s] Error | %s | %s",
            idx, total, lei, e
        )
        failed_ids.append(lei)

with open("failed_id.json", "w", encoding="utf-8") as f:
    json.dump(failed_ids, f, indent=4)
