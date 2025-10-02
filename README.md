# Healthcare Professionals Scraper

Automated Selenium-based scraper for https://annuaire.sante.fr collecting medical professional profile data with robust error handling and structured outputs.

## Key Features
- Interactive keyword & location prompt (if not supplied via CLI or environment)
- Robust Selenium interactions with retries and defensive waits (see `utils/utils.py`)
- Structured JSON Lines output + aggregated pretty JSON array
- CSV export with UTF-8 BOM (Excel friendly)
- Idempotent runs using per-search done file (RPPS tracking)
- Per-profile retry logic with statistics (processed / skipped / failed)
- Normalizes SIREN before API calls
- Optional SIREN API first, fallback to Papers API (if SIREN unavailable)
- Graceful handling of keyboard interrupts & fatal errors
- Logging to console + file `logs/scraper.log`
- CLI arguments & .env overrides

## Output Files (example for keyword `Médecin` and location `bordeaux`)
```
scraped_data/
  Médecin_bordeaux.csv    # flat tabular data
  Médecin_bordeaux.jsonl  # one structured JSON object per line
  Médecin_bordeaux.json   # aggregated pretty JSON array

done/
  Médecin_bordeaux.txt    # list of processed RPPS numbers
```

## Structured JSON Schema (each record)
```json
{
  "identification": {
    "name": "string|null",
    "rpps_number": "string|null",
    "specialty": "string|null",
    "finess_id": "string|null",
    "siren": "string|null",
    "siret": "string|null",
    "naf_ape_code": "string|null",
    "date_creation": "string|null"
  },
  "contact": {"phone": "string|null", "fax": "string|null"},
  "address": {"raw": "string|null", "postal_code": "string|null", "city": "string|null", "region": "string|null"},
  "meta": {"source_url": "string", "scraped_at": "ISO-8601 UTC timestamp"}
}
```

## Environment Variables (.env)
| Variable | Purpose | Default |
|----------|---------|---------|
| PAPERS_API_KEY | Key for Papers fallback API | (none) |
| SIREN_API_KEY  | Key for SIREN API | (none) |
| SCRAPER_KEYWORD | Default search keyword (used if CLI missing) | (none -> prompt) |
| SCRAPER_LOCATION | Default search location (used if CLI missing) | (none -> prompt) |
| SCRAPER_HEADLESS | Run browser headless (true/false) | false |

If `SCRAPER_KEYWORD` or `SCRAPER_LOCATION` are not set and not passed as CLI args, you will be prompted interactively (with defaults `Médecin` / `bordeaux`).

## Installation
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
Run with interactive prompts (if env/CLI not set):
```cmd
python -m automation.main
```
Specify keyword & location explicitly:
```cmd
python -m automation.main -k Medecin -l paris --headless --profile-retry 3
```
Environment + partial CLI (example, only location override):
```cmd
set SCRAPER_KEYWORD=Médecin
python -m automation.main -l lyon
```

## Error Handling & Stability
- Retries on element interactions lives inside helper utility functions
- Defensive checks before writing outputs
- Aggregates JSON only after browser closes (in `finally` block)
- Skips malformed JSONL lines gracefully when building pretty JSON
- Catches and logs unexpected exceptions per profile and per workflow

## Extending
1. Add field extraction in `process_profile`.
2. Include it in `flat_record`.
3. Map it into `build_structured_record` for nested JSON.
4. (Optional) Add API enrichment logic in `fetch_company_data`.

## Practical Notes
- Respect site terms and rate limits; adjust implicit waits / throttling if needed.
- Headless mode can behave differently on some dynamic pages; test both modes.
- The RPPS done file lets you resume without duplicating records.

## License
MIT
