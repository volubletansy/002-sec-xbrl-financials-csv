# SEC XBRL Company Financials → Tidy CSV

Turn the official **SEC EDGAR XBRL** data into a clean, spreadsheet-ready table:
**one row per (company, concept, unit, period)**. No raw-JSON wrangling.

- **Marketplace:** Apify Store (actor) · pay-per-result
- **Repo:** https://github.com/volubletansy/002-sec-xbrl-financials-csv
- **Data source:** official SEC EDGAR `companyfacts` API + the SEC ticker map.
  U.S. government public-domain data; descriptive User-Agent and ~<10 req/s
  throttle honored per SEC fair-access policy. **ToS-clean.**
- **Status:** draft (not yet published)

## The one job

Given tickers or CIKs, fetch each company's XBRL facts and emit a tidy CSV of
curated fundamentals (or any concepts you ask for), deduplicated to one row per
reporting period.

## Input (`.actor/input_schema.json`)

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `companies` *(required)* | string[] | — | Tickers (`AAPL`) or CIKs (`320193` / `0000320193`) |
| `concepts` | string[] | curated set | us-gaap/dei concept names; `["all"]` for everything |
| `taxonomies` | string[] | `["us-gaap","dei"]` | Which XBRL taxonomies to read |
| `dateFrom` / `dateTo` | string | — | Filter on `period_end` (`YYYY-MM-DD`, inclusive) |
| `dedupe` | boolean | `true` | Keep the latest-filed value per period |
| `userAgentEmail` | string | — | Optional contact for the SEC User-Agent |

Curated default concepts: Revenues, RevenueFromContractWithCustomer…, GrossProfit,
OperatingIncomeLoss, NetIncomeLoss, EPS (basic/diluted), Assets, Liabilities,
StockholdersEquity, Cash…, R&D expense.

## Output schema (CSV columns — stable contract)

`ticker, cik, entity_name, taxonomy, concept, label, unit, period_start,
period_end, fiscal_year, fiscal_period, value, form, filed, frame, accession`

**Period semantics (important):** XBRL duration facts (income-statement items)
report both year-to-date and discrete-quarter figures that can share a
`period_end`; they are kept as separate rows, distinguished by `period_start`.
Balance-sheet (instant) facts have an empty `period_start`. `fiscal_year` /
`fiscal_period` describe the *filing*, so the same economic datapoint is **not**
duplicated across later comparative filings — dedupe keys on the period, keeping
the most recently `filed` value.

## Run

On Apify: set input, run; export the dataset as CSV/JSON/Excel.

Locally (stdlib only — no install needed for the core):

```bash
python3 -c "import sys; sys.path.insert(0,'src'); import io, sec_xbrl as sx; \
rows=sx.company_rows('AAPL', concepts=['NetIncomeLoss']); \
sx.write_csv(rows, io.StringIO()) "
```

## Test & health

- `test/test_shape.py` — **live** test against the real SEC API; verifies row
  shape, exact CSV header, numeric values, and the dedupe invariant.
- `./health-check` — a quick live pull (CIK 320193, one metric); exits non-zero
  on failure or output-shape change. Wired into repo `scripts/health-check` once
  `STATUS` is `live`.

## Layout

```
src/sec_xbrl.py   # dependency-free core: fetch + flatten + dedupe + CSV
src/main.py       # Apify actor wrapper (reads input, pushes dataset rows)
src/__main__.py   # `python3 -m src` entrypoint
.actor/           # actor.json, input_schema.json, dataset_schema.json
Dockerfile        # apify/actor-python:3.12
test/             # live output-shape test
health-check      # executable quick live check
```
