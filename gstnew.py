import re
import json
import base64
import time
import warnings
from pathlib import Path
import requests
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from transformers import pipeline
from logger import setup_logger
from utils import Helper
warnings.filterwarnings("ignore")

pipe = pipeline("automatic-speech-recognition",
                model=r"E:\AI_Models\whisper-medium")

BASE = "https://services.gst.gov.in/services/searchtp"
API = "https://services.gst.gov.in/services/api/search/taxpayerReturnDetails"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://services.gst.gov.in",
    "Referer": BASE,
}

WORD = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3",
    "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"
}

YEARS = [str(y) for y in range(2017, 2027)]


def wait_site(driver):
    WebDriverWait(driver, 20).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".dimmer-holder"))
    )


def normalize(text):
    out = []
    for t in re.findall(r"\w+", text.lower()):
        if t.isdigit():
            out.append(t)
        elif t in WORD:
            out.append(WORD[t])
    return "".join(out)


def create_session(driver, gstin, retries=5):
    driver.get(BASE)
    wait_site(driver)

    for _ in range(retries):

        box = driver.find_element(By.ID, "for_gstin")
        box.clear()
        box.send_keys(gstin)

        driver.find_element(
            By.XPATH,
            "//button[i[contains(@class,'fa-volume-up')]]"
        ).click()

        request_id = None
        for _ in range(20):
            time.sleep(.5)
            for e in driver.get_log("performance"):
                try:
                    m = json.loads(e["message"])["message"]
                    if m["method"] == "Network.responseReceived":
                        if "audiocaptcha" in m["params"]["response"]["url"]:
                            request_id = m["params"]["requestId"]
                            break
                except:
                    pass
            if request_id:
                break

        body = driver.execute_cdp_cmd(
            "Network.getResponseBody",
            {"requestId": request_id}
        )

        Path("captcha.wav").write_bytes(base64.b64decode(body["body"]))
        captcha = normalize(pipe("captcha.wav")["text"])

        cap = driver.find_element(By.ID, "fo-captcha")
        cap.clear()
        cap.send_keys(captcha)

        driver.find_element(By.ID, "lotsearch").click()
        time.sleep(2)

        if "Invalid Captcha" not in driver.page_source:
            s = requests.Session()
            for c in driver.get_cookies():
                s.cookies.set(c["name"], c["value"])
            return s

    raise Exception("Captcha failed")


def fetch_and_save(session, gstin, output_dir):
    data = []

    for fy in YEARS:
        try:
            r = session.post(
                API,
                json={"gstin": gstin, "fy": fy},
                headers=HEADERS,
                verify=False,
                timeout=30,
            )

            r.raise_for_status()
            res = r.json()

            if "filingStatus" in res and res["filingStatus"]:
                rows = res["filingStatus"][0]

                for row in rows:
                    row["gstin"] = gstin

                data.extend(rows)

            else:
                logger.warning(f"{gstin} {fy} empty.")
                data.append({
                    "fy": fy,
                    "taxp": "NA",
                    "mof": "NA",
                    "dof": "NA",
                    "rtntype": "NA",
                    "arn": "NA",
                    "status": "Data Not Found",
                    "gstin": gstin,
                })

        except Exception as e:
            logger.error(f"{gstin} failed request")
            data.append({
                "fy": fy,
                "taxp": "NA",
                "mof": "NA",
                "dof": "NA",
                "rtntype": "NA",
                "arn": "NA",
                "status": "Request Failed",
                "gstin": gstin,
                "error": str(e),
            })

            failed.append(gstin)
            utils.save_json(failed, failed_path)

    (output_dir / f"{gstin}.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":

    csv_path = r"PAN_NO_FILES.csv"
    logger = setup_logger(name="gstn_log")
    utils = Helper()

    out = Path("output/gstin_json")
    out.mkdir(parents=True, exist_ok=True)

    failed = []
    failed_path = out / "failed.json"
    utils.save_json(failed, failed_path)

    gstins = (
        pd.read_csv(csv_path)["gstin"]
        .dropna().astype(str).str.strip().tolist()
    )

    options = webdriver.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Network.enable", {})

    session = create_session(driver, gstins[0])
    driver.quit()

    logger.info(f"======= created output path =======")
    for idx, gstin in enumerate(gstins):
        data = fetch_and_save(session, gstin, out)
        # (out/f"{gstin}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"{idx + 1} : {gstin} done.")
        time.sleep(1)
