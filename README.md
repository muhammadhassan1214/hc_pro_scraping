# Medical Directory Scraper

Automated scraper for https://annuaire.sante.fr collecting medical professional profiles.

## Key Features
- Robust Selenium interactions with retries and defensive waits
- Structured JSON Lines output + aggregated pretty JSON array
- CSV export with UTF-8 BOM (Excel friendly)
- Idempotent runs using per-search done file (RPPS tracking)
- Per-profile retry logic with statistics (processed / skipped / failed)
- Normalizes SIREN before API calls
- Optional SIREN vs Papers API fallback
- Graceful handling of keyboard interrupts & fatal errors
- Logging to console and rotating file `logs/scraper.log`
- CLI arguments & .env overrides

## Output Files (for keyword/location example `Médecin` / `bordeaux`)
```
scraped_data/
  Médecin_bordeaux.csv           # flat tabular data
  Médecin_bordeaux.jsonl         # one JSON object per line (structured)
  Médecin_bordeaux.json          # aggregated pretty JSON array

done/
  Médecin_bordeaux.txt           # list of processed RPPS numbers
```

## Structured JSON Schema (each record)
```json
{
  "identification": {
    "name": "string|null",
    "rpps_number": "string|null",
    "specialty": "string|null",
    "finess_id": "string|null",
    "siren": "string|null",   // first 9 digits if available
    "siret": "string|null",
    "naf_ape_code": "string|null",
    "date_creation": "string|null"  // as provided by API
  },
  "contact": {
    "phone": "string|null",
    "fax": "string|null"
  },
  "address": {
    "raw": "string|null",
    "postal_code": "string|null",
    "city": "string|null",
    "region": "string|null"
  },
  "meta": {
    "source_url": "string",
    "scraped_at": "ISO-8601 UTC timestamp"
  }
}
```

## Environment Variables (.env)
| Variable | Purpose | Default |
|----------|---------|---------|
| PAPERS_API_KEY | Key for Papers fallback API | (none) |
| SIREN_API_KEY  | Key for SIREN API | (none) |
| SCRAPER_KEYWORD | Default search keyword | Médecin |
| SCRAPER_LOCATION | Default search location | bordeaux |
| SCRAPER_HEADLESS | Run browser headless (true/false) | false |
| SCRAPER_DISABLE_JS | Force disabling JS (not recommended) | false |

## Installation
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
Basic (uses defaults / .env):
```cmd
python -m automation.main
```
Custom run:
```cmd
python -m automation.main -k Médecin -l paris --headless --profile-retry 3
```

## Error Handling & Stability
- Retries on navigation & element interaction
- Defensive checks before writing outputs
- Aggregates JSON only after browser closes
- Normalizes SIREN digits to avoid API errors
- Skips malformed JSONL lines gracefully

## Updating / Extending
- Add new fields: extract in `process_profile`, add to `flat_record`, map in `build_structured_record`.
- Additional APIs: extend `fetch_company_data` with new conditional branches.

## Notes
- Disabling JavaScript will likely break dynamic content; only set `SCRAPER_DISABLE_JS=true` for controlled tests.
- Respect target site terms of service and rate limits.

## License
Internal / client project (no explicit OSS license). Update if distribution is intended.
