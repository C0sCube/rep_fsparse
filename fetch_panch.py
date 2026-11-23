from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
import undetected_chromedriver as uc
import time
import json5

driver = uc.Chrome(version_main=158)
wait = WebDriverWait(driver, 20)

driver.get("https://report.pmayg.dord.gov.in/netiay/DataAnalytics/PhysicalProgressRpt.aspx")

indian_regions = [
    "JHARKHAND",
]

def wait_postback():
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(1)

def get_options_with_codes(dropdown_id):
    """Return dict {value: text} for each option."""
    sel = Select(driver.find_element(By.ID, dropdown_id))

    return {
        opt.get_attribute("value"): opt.text.strip()
        for opt in sel.options
        if opt.get_attribute("value") and opt.get_attribute("value") != "0"
    }


all_codes = {}

states = get_options_with_codes("ctl00_ContentPlaceHolder1_ddlState")

for state_code, state_name in states.items():

    if state_name not in indian_regions:
        continue

    print("STATE:", state_name)

    Select(
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlState")
    ).select_by_value(state_code)

    wait_postback()

    districts = get_options_with_codes(
        "ctl00_ContentPlaceHolder1_ddlDistrict"
    )

    all_codes[state_code] = {
        "name": state_name,
        "districts": {}
    }

    for district_code, district_name in districts.items():

        print("  DISTRICT:", district_name)

        Select(
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlDistrict")
        ).select_by_value(district_code)

        wait_postback()

        blocks = get_options_with_codes(
            "ctl00_ContentPlaceHolder1_ddlBlock"
        )

        all_codes[state_code]["districts"][district_code] = {
            "name": district_name,
            "blocks": {}
        }

        for block_code, block_name in blocks.items():

            print("    BLOCK:", block_name)

            Select(
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlBlock")
            ).select_by_value(block_code)

            wait_postback()

            panchayats = get_options_with_codes(
                "ctl00_ContentPlaceHolder1_ddlPanchayat"
            )

            print("      PANCHAYATS:", len(panchayats))

            all_codes[state_code]["districts"][district_code]["blocks"][block_code] = {
                "name": block_name,
                "panchayats": panchayats
            }


driver.quit()


# Save as JSON5
with open(f"{state_name}.json5", "w", encoding="utf-8") as f:
    json5.dump(
        all_codes,
        f,
        indent=2,
        ensure_ascii=False,
        quote_keys=True
    )

print("Saved: pmayg_config.json5")