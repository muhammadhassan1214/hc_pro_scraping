import os
import json
import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
import argparse

import pandas as pd
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from utils.apis.siren_api import get_data_from_siren_api
from utils.apis.papers_api import get_data_from_papers_api
from utils.utils import (
    get_undetected_driver,
    input_element, click_element_by_js,
    get_element_text, safe_navigate_to_url,
    wait_while_element_is_displaying,
    check_element_exists
)
from utils.functions import (
    extract_postal_code_and_city,
    xpath_of_text, _read_done_set
)

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'scraper.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def append_json_record(path: str, record: Dict[str, Any]) -> None:
    """Append a single JSON record (as JSON Lines) to the specified file."""
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except OSError as e:
        logger.error(f"Failed to append JSON record to {path}: {e}")


def build_structured_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Transform flat raw data into a structured hierarchical JSON document."""
    return {
        "identification": {
            "name": raw.get("Name"),
            "rpps_number": raw.get("RPPS Number"),
            "specialty": raw.get("Specialty"),
            "finess_id": raw.get("Finess ID"),
            "siren": (raw.get("Siren/Siret") or '').split('/')[:1][0] or None,
            "siret": (raw.get("Siren/Siret") or '').split('/')[1] if raw.get("Siren/Siret") and '/' in raw.get("Siren/Siret") else None,
            "naf_ape_code": raw.get("NAF/APE CODE"),
            "date_creation": raw.get("Date Creation"),
        },
        "contact": {
            "phone": raw.get("Phone Number"),
            "fax": raw.get("FAX Number"),
        },
        "address": {
            "raw": raw.get("Address"),
            "postal_code": raw.get("Postal Code"),
            "city": raw.get("City"),
            "region": raw.get("Region"),
        },
        "meta": {
            "source_url": raw.get("Source URL"),
            "scraped_at": datetime.now(UTC).isoformat(timespec='seconds')
        }
    }


def write_csv_row(output_file: str, data: Dict[str, Any], header_written_cache: Dict[str, bool]) -> None:
    """Write a single row to a CSV file, creating file with header if needed."""
    try:
        df = pd.DataFrame([data])
        if not header_written_cache.get(output_file) and not os.path.exists(output_file):
            df.to_csv(output_file, mode='w', header=True, index=False, encoding='utf-8-sig', lineterminator='\n')
            header_written_cache[output_file] = True
        else:
            df.to_csv(output_file, mode='a', header=False, index=False, encoding='utf-8-sig', lineterminator='\n')
    except Exception as e:
        logger.error(f"Failed writing CSV row: {e}")


def _normalize_siren(raw: Optional[str]) -> Optional[str]:
    """Helper to normalize SIREN (first 9 digits)."""
    if not raw:
        return None
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 9:
        return digits[:9]
    return None


def fetch_company_data(name: str, siren: Optional[str]) -> Dict[str, Any]:
    """Fetch company-related data using SIREN first if available, otherwise fallback to external service."""
    papers_api_key = os.getenv("PAPERS_API_KEY")
    siren_api_key = os.getenv("SIREN_API_KEY")

    normalized_siren = _normalize_siren(siren)

    try:
        if normalized_siren:
            if not siren_api_key:
                logger.warning("SIREN provided but SIREN_API_KEY not set; skipping SIREN API call.")
                return {}
            return get_data_from_siren_api(normalized_siren, siren_api_key) or {}
        else:
            if not papers_api_key:
                logger.warning("No valid SIREN and PAPERS_API_KEY not set; skipping Papers API call.")
                return {}
            return get_data_from_papers_api(name, papers_api_key) or {}
    except Exception as e:
        logger.error(f"Error fetching company data (siren={normalized_siren}): {e}")
        return {}


def finalize_json(jsonl_path: str, pretty_json_path: str) -> None:
    """Convert a JSONL file of records into a single pretty formatted JSON array."""
    if not os.path.exists(jsonl_path):
        logger.info(f"JSONL file {jsonl_path} not found; skipping pretty JSON aggregation.")
        return
    try:
        records: List[Dict[str, Any]] = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping malformed JSONL line: {e}")
        with open(pretty_json_path, 'w', encoding='utf-8') as out:
            json.dump(records, out, ensure_ascii=False, indent=2)
        logger.info(f"Wrote aggregated pretty JSON to {pretty_json_path} ({len(records)} records)")
    except Exception as e:
        logger.error(f"Failed to produce pretty JSON: {e}")

# ---------------------------------------------------------------------------
# Core Scraping Logic
# ---------------------------------------------------------------------------

def process_profile(driver, href: str, loading_selector, done_rpps: set, jsonl_path: str, csv_path: str, done_file: str, header_cache: Dict[str, bool]) -> Optional[str]:
    """Process a single profile page. Returns RPPS if successfully processed, else None."""
    try:
        if not safe_navigate_to_url(driver, href):
            logger.warning(f"Navigation failed for {href}")
            return None

        wait_while_element_is_displaying(driver, loading_selector)
        no_data_shown = check_element_exists(
            driver,
            (By.XPATH, """//div[@class= 'blocs_details_infos_identif']/span[text()= "Pas d'information renseignée dans cette rubrique"]"""),
        )
        if no_data_shown:
            logger.info(f"No data found for URL: {href}")
            return None

        name = get_element_text(driver, (By.CSS_SELECTOR, "div[class='details_entete_synthese'] > div[class='nom_prenom']"), timeout=3)
        rpps_number_text = get_element_text(driver, (By.CSS_SELECTOR, "div[class='rpps'] > span"), timeout=3)
        rpps_number = rpps_number_text.split(':', 1)[1].strip() if ':' in rpps_number_text else None

        if rpps_number and rpps_number in done_rpps:
            logger.info(f"RPPS {rpps_number} already processed (detected post-load); skipping.")
            return None

        phone_number = get_element_text(driver, (By.XPATH, xpath_of_text('Téléphone')), timeout=2)
        fax_number = get_element_text(driver, (By.XPATH, xpath_of_text('Fax')), timeout=2)
        finess_id = get_element_text(driver, (By.XPATH, xpath_of_text('Identifiant FINESS')), timeout=2)
        siren_annuaire = get_element_text(driver, (By.XPATH, xpath_of_text('SIREN')), timeout=2)
        address = get_element_text(driver, (By.XPATH, xpath_of_text('Adresse :')), timeout=2)
        adress_2_selector = (By.XPATH, "//span[contains(@class, 'label FINESS')]/following-sibling::span[1]")
        address_2 = get_element_text(driver, adress_2_selector, timeout=2)
        postal_code, city = extract_postal_code_and_city(address_2) if address_2 else (None, None)
        region = get_element_text(driver, (By.XPATH, xpath_of_text('Région')), timeout=2)
        specialty = get_element_text(driver, (By.CSS_SELECTOR, "div[class='ico_etat_main'] ~ div"), timeout=2)

        fetched_data = fetch_company_data(name, siren_annuaire)

        flat_record = {
            "Name": name,
            "RPPS Number": rpps_number,
            "Phone Number": phone_number,
            "FAX Number": fax_number,
            "Finess ID": finess_id,
            "Address": address,
            "Postal Code": postal_code,
            "City": city,
            "Region": region,
            "Specialty": specialty,
            "Siren/Siret": f"{fetched_data.get('siren')}/{fetched_data.get('siret')}" if fetched_data.get('siren') and fetched_data.get('siret') else (fetched_data.get('siren') or fetched_data.get('siret')),
            "Date Creation": fetched_data.get("date_creation"),
            "NAF/APE CODE": fetched_data.get("naf_ape_code"),
            "Source URL": href,
        }

        structured = build_structured_record(flat_record)

        if not rpps_number:
            logger.warning(f"RPPS number missing for {href}; skipping persistence.")
            return None

        # Persist CSV + JSON
        write_csv_row(csv_path, flat_record, header_cache)
        append_json_record(jsonl_path, structured)

        # Mark as done
        try:
            with open(done_file, 'a', encoding='utf-8') as f:
                f.write(f"{rpps_number}\n")
        except OSError as e:
            logger.error(f"Failed to write RPPS to done file: {e}")
        else:
            done_rpps.add(rpps_number)

        logger.info(f"Processed RPPS {rpps_number}")
        return rpps_number

    except Exception as e:
        logger.error(f"Unhandled error processing profile {href}: {e}")
        return None


def scrape(search_keyword: str = 'Médecin', search_location: str = 'bordeaux', headless: bool = False, profile_retry: int = 2) -> None:
    """Main scraping workflow with improved resilience and structured JSON output.

    Args:
        search_keyword: Profession / keyword to search.
        search_location: City or location filter.
        headless: Whether to run browser in headless mode.
        profile_retry: Number of attempts per profile on transient failure.
    """
    output_dir = 'scraped_data'
    done_dir = 'done'
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(done_dir, exist_ok=True)

    csv_output = os.path.join(output_dir, f"{search_keyword}_{search_location}.csv")
    jsonl_output = os.path.join(output_dir, f"{search_keyword}_{search_location}.jsonl")
    pretty_json_output = os.path.join(output_dir, f"{search_keyword}_{search_location}.json")
    done_file = os.path.join(done_dir, f"{search_keyword}_{search_location}.txt")

    done_rpps = _read_done_set(done_file)
    header_cache: Dict[str, bool] = {}

    url = "https://annuaire.sante.fr/"
    driver = get_undetected_driver(headless=headless)

    if driver is None:
        logger.critical("Failed to initialize WebDriver. Aborting scrape.")
        return

    loading_selector = (By.XPATH, "//img[contains(@src, 'loading')]")

    processed_count = 0
    skipped_count = 0
    failed_count = 0

    try:
        if not safe_navigate_to_url(driver, url):
            logger.error("Initial navigation failed; aborting.")
            return

        logger.info("Driver initialized and at start URL")

        # Initial search interaction
        if not click_element_by_js(driver, (By.CLASS_NAME, 'champ_submit')):
            logger.warning("Initial search focus click failed")
        input_element(driver, (By.CSS_SELECTOR, "input[id='_rechercheportlet_INSTANCE_ctPdpHA24ctE_texttofind']"), search_keyword)
        input_element(driver, (By.CSS_SELECTOR, "input[id='_rechercheportlet_INSTANCE_ctPdpHA24ctE_adresse']"), search_location)
        click_element_by_js(driver, (By.CLASS_NAME, 'champ_submit'))
        logger.info("Search submitted")

        wait_while_element_is_displaying(driver, loading_selector)
        logger.info("Search results loaded")

        page_index = 1
        while True:
            # Collect result links
            try:
                results = driver.find_elements(By.CSS_SELECTOR, "div[class='nom_prenom'] > a")
            except WebDriverException as e:
                logger.error(f"Failed retrieving result links on page {page_index}: {e}")
                results = []

            if not results:
                logger.info(f"No results found on page {page_index}; ending pagination loop.")
                break

            result_hrefs: List[str] = [r.get_attribute('href') for r in results if r.get_attribute('href')]
            logger.info(f"Page {page_index}: Found {len(result_hrefs)} profile links")

            # Open a new tab for profile processing
            try:
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
            except Exception as e:
                logger.error(f"Failed to open new tab for profiles: {e}")
                break

            for href in result_hrefs:
                if any(rpps in href for rpps in done_rpps):  # Pre-filter if RPPS embedded in URL
                    skipped_count += 1
                    logger.info(f"Skipping (URL indicates already processed): {href}")
                    continue
                last_result = None
                for attempt in range(1, profile_retry + 1):
                    last_result = process_profile(
                        driver=driver,
                        href=href,
                        loading_selector=loading_selector,
                        done_rpps=done_rpps,
                        jsonl_path=jsonl_output,
                        csv_path=csv_output,
                        done_file=done_file,
                        header_cache=header_cache
                    )
                    if last_result:
                        processed_count += 1
                        break
                    else:
                        logger.warning(f"Attempt {attempt} failed for {href}")
                if not last_result:
                    failed_count += 1

            # Close profile tab and return to listing
            try:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                logger.warning(f"Error switching back to results tab: {e}")
                if not driver.window_handles:
                    logger.error("No browser windows remaining; aborting.")
                    break

            # Pagination handling
            has_next = check_element_exists(driver, (By.CSS_SELECTOR, "a[title='Suivant']"))
            if has_next:
                logger.info(f"Navigating to next page (current index {page_index})")
                click_element_by_js(driver, (By.CSS_SELECTOR, "a[title='Suivant']"))
                wait_while_element_is_displaying(driver, loading_selector)
                page_index += 1
            else:
                logger.info("No more pages to process.")
                break

    except KeyboardInterrupt:
        logger.warning("Scrape interrupted by user (KeyboardInterrupt). Partial results preserved.")
    except Exception as e:
        logger.exception(f"Fatal error in scrape workflow: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        # Produce aggregated pretty JSON
        try:
            finalize_json(jsonl_output, pretty_json_output)
        except Exception as e:
            logger.error(f"Failed final JSON aggregation: {e}")
        logger.info(
            f"Scrape finished. Stats => processed: {processed_count}, skipped(pre-existing): {skipped_count}, failed: {failed_count}. Resources cleaned up."
        )


def parse_args(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Medical directory scraper")
    parser.add_argument('-k', '--keyword', default=os.getenv('SCRAPER_KEYWORD', 'Médecin'), help='Search keyword')
    parser.add_argument('-l', '--location', default=os.getenv('SCRAPER_LOCATION', 'bordeaux'), help='Search location / city')
    parser.add_argument('--headless', action='store_true', default=os.getenv('SCRAPER_HEADLESS', 'false').lower() == 'true', help='Run browser in headless mode')
    parser.add_argument('--profile-retry', type=int, default=2, help='Retries per profile before marking failed')
    return parser.parse_args(argv)


def main():  # Retain original entrypoint name
    args = parse_args()
    scrape(
        search_keyword=args.keyword,
        search_location=args.location,
        headless=args.headless,
        profile_retry=args.profile_retry
    )


if __name__ == "__main__":
    main()
