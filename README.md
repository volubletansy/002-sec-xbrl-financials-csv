# SEC EDGAR Financials Scraper — Company Fundamentals to CSV

**Extract any US public company's financials — revenue, net income, EPS, assets,
liabilities and more — from official SEC EDGAR XBRL data into a tidy CSV. One row
per metric per period. No API keys, no raw JSON, no scraping tricks.**

Point it at tickers or CIKs and get a clean, spreadsheet-ready table you can open
in Excel, Google Sheets, or pandas in seconds.

---

## What you get

- **Tidy output** — one row per `(company, metric, unit, period)`, deduplicated to
  the latest filing, so you get a clean time series instead of restated, nested XBRL.
- **Official, ToS-clean source** — reads the SEC EDGAR `companyfacts` XBRL API
  directly. Public-domain U.S. government data; no logins, no anti-bot games.
- **Curated or custom metrics** — a sensible default set of fundamentals, or pass
  your own XBRL concepts (or `["all"]` for everything a company reports).
- **Reliable by design** — mandatory User-Agent, request throttling, and retries.

## Example input

```json
{
  "companies": ["AAPL", "MSFT"],
  "concepts": ["Revenues", "NetIncomeLoss", "EarningsPerShareDiluted"],
  "dateFrom": "2021-01-01"
}
```

## Example output

| ticker | concept | unit | period_end | fiscal_period | value | form | filed |
|---|---|---|---|---|---|---|---|
| AAPL | NetIncomeLoss | USD | 2023-09-30 | FY | 96995000000 | 10-K | 2023-11-03 |
| MSFT | EarningsPerShareDiluted | USD/shares | 2023-06-30 | FY | 9.68 | 10-K | 2023-07-27 |

Full columns: `ticker, cik, entity_name, taxonomy, concept, label, unit,
period_start, period_end, fiscal_year, fiscal_period, value, form, filed, frame,
accession`. Export as CSV, JSON, or Excel.

## Input reference

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `companies` *(required)* | string[] | — | Tickers (`AAPL`) or CIKs (`320193`) |
| `concepts` | string[] | curated set | XBRL concept names, or `["all"]` |
| `taxonomies` | string[] | `["us-gaap","dei"]` | Which taxonomies to read |
| `dateFrom` / `dateTo` | string | — | Filter on `period_end` (`YYYY-MM-DD`) |
| `dedupe` | boolean | `true` | One row per period, latest filing |
| `userAgentEmail` | string | — | Optional contact for the SEC User-Agent |

## Good for

- Pulling multi-year fundamentals for a watchlist into a spreadsheet
- Feeding a screener, model, or dashboard with clean financials
- Students and indie fintech builders who don't want to parse XBRL by hand

## Pricing

**Pay per result — $3.00 per 1,000 rows.** No subscription; you pay only for the
data you pull. A typical single-company, curated-metrics run is a few hundred rows.

## How it works / notes

Data comes from the SEC EDGAR `companyfacts` XBRL API (`data.sec.gov`), accessed
within SEC's fair-access policy (descriptive User-Agent, polite rate). XBRL
duration facts (income-statement items) can report both year-to-date and discrete
quarters ending on the same date — these are kept as separate rows and
distinguished by `period_start`. Balance-sheet (instant) facts have an empty
`period_start`.

Not affiliated with or endorsed by the SEC.
