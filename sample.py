import time
import warnings
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup

from utils import Helper
from logger import setup_logger

url = "https://report.pmayg.dord.gov.in/netiay/DataAnalytics/PhysicalProgressRpt.aspx"

states = ["MEGHALAYA.json5"]

fin_years = {
    "2016-2017": "2016-2017",
    "2017-2018": "2017-2018",
    "2018-2019": "2018-2019",
    "2019-2020": "2019-2020",
    "2020-2021": "2020-2021",
    "2021-2022": "2021-2022",
    "2022-2023": "2022-2023",
    "2023-2024": "2023-2024",
    "2025-2026": "2025-2026",
    "2026-2027": "2026-2027",
}

MAX_RETRIES = 3
REQUEST_TIMEOUT = 60
WRITE_THRESHOLD = 1000

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

utils = Helper()

logger = setup_logger(
    name="pmayg",
    base_dir="logs",
    to_console=True,
    to_file=True,
)

session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Safari/537.36"
        )
    }
)


def get_hidden_fields(soup):
    fields = {}

    for tag in soup.find_all("input", type="hidden"):
        if tag.get("name"):
            fields[tag["name"]] = tag.get("value", "")

    return fields


def get_page_soup(response):
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def post_page(payload):
    response = session.post(
        url,
        data=payload,
        verify=False,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response


def empty_row(year, state, district, block, panchayat, status="No Data"):
    return pd.DataFrame(
        [{
            "Year": year,
            "State": state,
            "District": district,
            "Block": block,
            "Panchayat": panchayat,
            "Status": status,
            "Data": "NA",
        }]
    )


def parse_panchayat_table(
    html,
    state_name,
    district_name,
    block_name,
    panchayat_name,
    year_code,
):
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find(
        "table",
        id="ctl00_ContentPlaceHolder1_gvData",
    )

    if table is None:
        return empty_row(
            year_code,
            state_name,
            district_name,
            block_name,
            panchayat_name,
        )

    try:
        df = pd.read_html(StringIO(str(table)))[0]

    except Exception:
        return empty_row(
            year_code,
            state_name,
            district_name,
            block_name,
            panchayat_name,
        )

    if df.empty:
        return empty_row(
            year_code,
            state_name,
            district_name,
            block_name,
            panchayat_name,
        )

    df["Year"] = year_code
    df["State"] = state_name
    df["District"] = district_name
    df["Block"] = block_name
    df["Panchayat"] = panchayat_name
    df["Status"] = "Data Found"

    ahead = [
        "Year",
        "State",
        "District",
        "Block",
        "Panchayat",
        "Status",
    ]

    return df[
        ahead +
        [c for c in df.columns if c not in ahead]
    ]


def fetch_panchayat_data(
    year_code,
    state_code,
    district_code,
    block_code,
    panchayat_code,
    state_name,
    district_name,
    block_name,
    panchayat_name,
):
    response = session.get(
        url,
        verify=False,
        timeout=REQUEST_TIMEOUT,
    )

    soup = get_page_soup(response)
    hidden = get_hidden_fields(soup)

    payload_year = {
        **hidden,
        "ctl00$ContentPlaceHolder1$ddlFinYear": year_code,
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlFinYear",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
    }

    response = post_page(payload_year)
    soup = get_page_soup(response)
    hidden = get_hidden_fields(soup)

    payload_state = {
        **hidden,
        "ctl00$ContentPlaceHolder1$ddlFinYear": year_code,
        "ctl00$ContentPlaceHolder1$ddlState": state_code,
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlState",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
    }

    response = post_page(payload_state)
    soup = get_page_soup(response)
    hidden = get_hidden_fields(soup)

    payload_district = {
        **hidden,
        "ctl00$ContentPlaceHolder1$ddlFinYear": year_code,
        "ctl00$ContentPlaceHolder1$ddlState": state_code,
        "ctl00$ContentPlaceHolder1$ddlDistrict": district_code,
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlDistrict",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
    }

    response = post_page(payload_district)
    soup = get_page_soup(response)
    hidden = get_hidden_fields(soup)

    payload_block = {
        **hidden,
        "ctl00$ContentPlaceHolder1$ddlFinYear": year_code,
        "ctl00$ContentPlaceHolder1$ddlState": state_code,
        "ctl00$ContentPlaceHolder1$ddlDistrict": district_code,
        "ctl00$ContentPlaceHolder1$ddlBlock": block_code,
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlBlock",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
    }

    response = post_page(payload_block)
    soup = get_page_soup(response)
    hidden = get_hidden_fields(soup)

    payload_panchayat = {
        **hidden,
        "ctl00$ContentPlaceHolder1$ddlFinYear": year_code,
        "ctl00$ContentPlaceHolder1$ddlState": state_code,
        "ctl00$ContentPlaceHolder1$ddlDistrict": district_code,
        "ctl00$ContentPlaceHolder1$ddlBlock": block_code,
        "ctl00$ContentPlaceHolder1$ddlPanchayat": panchayat_code,
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlPanchayat",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
    }

    response = post_page(payload_panchayat)
    soup = get_page_soup(response)
    hidden = get_hidden_fields(soup)

    payload_submit = {
        **hidden,
        "ctl00$ContentPlaceHolder1$ddlFinYear": year_code,
        "ctl00$ContentPlaceHolder1$ddlState": state_code,
        "ctl00$ContentPlaceHolder1$ddlDistrict": district_code,
        "ctl00$ContentPlaceHolder1$ddlBlock": block_code,
        "ctl00$ContentPlaceHolder1$ddlPanchayat": panchayat_code,
        "ctl00$ContentPlaceHolder1$btnSubmit": "Submit",
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
    }

    response = post_page(payload_submit)

    return parse_panchayat_table(
        response.text,
        state_name,
        district_name,
        block_name,
        panchayat_name,
        year_code,
    )


def fetch_with_retry(
    year_code,
    state_code,
    district_code,
    block_code,
    panchayat_code,
    state_name,
    district_name,
    block_name,
    panchayat_name,
):
    value = (
        f"ATMPT 1/{MAX_RETRIES}->"
        f"{year_code}:{state_name[:3]}::{panchayat_name}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            value = (
                f"ATMPT {attempt}/{MAX_RETRIES}->"
                f"{year_code}:{state_name[:3]}::{panchayat_name}"
            )

            df = fetch_panchayat_data(
                year_code,
                state_code,
                district_code,
                block_code,
                panchayat_code,
                state_name,
                district_name,
                block_name,
                panchayat_name,
            )

            status = df.iloc[0]["Status"]

            if status == "No Data":
                logger.info(f"{value}\tN/A")
            else:
                logger.info(f"{value}\tData Found")

            return df

        except Exception:
            logger.warning(
                f"{value}\tAttempt {attempt} failed"
            )

            if attempt < MAX_RETRIES:
                time.sleep(2)

    logger.error(
        f"{value}\tFailed after {MAX_RETRIES} attempts"
    )

    return empty_row(
        year_code,
        state_name,
        district_name,
        block_name,
        panchayat_name,
        status="Failed",
    )


def main():
    for state_file in states:

        file_path = Path(state_file)
        config = utils.load_json5(state_file)

        output_file = f"{file_path.stem}.csv"

        if Path(output_file).exists():
            Path(output_file).unlink()

        buffer_dfs = []
        buffer_rows = 0
        total_rows = 0
        header_written = False

        logger.info(f"Started file: {state_file}")

        for year_code in fin_years:

            for state_code, state_data in config.items():

                state_name = state_data["name"]

                for district_code, district_data in state_data["districts"].items():

                    district_name = district_data["name"]

                    for block_code, block_data in district_data["blocks"].items():

                        block_name = block_data["name"]

                        for (
                            panchayat_code,
                            panchayat_name,
                        ) in block_data["panchayats"].items():

                            df = fetch_with_retry(
                                year_code,
                                state_code,
                                district_code,
                                block_code,
                                panchayat_code,
                                state_name,
                                district_name,
                                block_name,
                                panchayat_name,
                            )

                            buffer_dfs.append(df)
                            buffer_rows += len(df)
                            total_rows += len(df)

                            if buffer_rows >= WRITE_THRESHOLD:

                                chunk = pd.concat(
                                    buffer_dfs,
                                    ignore_index=True,
                                )

                                chunk.to_csv(
                                    output_file,
                                    mode="a",
                                    index=False,
                                    header=not header_written,
                                )

                                header_written = True

                                logger.info(
                                    f"Flushed {len(chunk)} rows | "
                                    f"Total={total_rows}"
                                )

                                buffer_dfs.clear()
                                buffer_rows = 0

                            time.sleep(0.4)

        if buffer_dfs:

            chunk = pd.concat(
                buffer_dfs,
                ignore_index=True,
            )

            chunk.to_csv(
                output_file,
                mode="a",
                index=False,
                header=not header_written,
            )

            total_rows += 0

            logger.info(
                f"Final Flush {len(chunk)} rows"
            )

        logger.info(
            f"Completed | File: {output_file} | "
            f"Total Rows: {total_rows}"
        )

        print(f"\nSaved: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception(
            "Program stopped due to an error"
        )
    finally:
        session.close()