# SEC EDGAR Financials Scraper — Company Fundamentals to CSV

> Extract any US public company's financials (revenue, net income, EPS, assets…)
> from official SEC EDGAR XBRL data into a tidy CSV — one row per metric per
> period. No raw JSON, no API keys.

**Title (store search phrase):** `SEC EDGAR Financials Scraper – Company Fundamentals to CSV`
<!-- Buyers search "SEC EDGAR", "SEC financials CSV", "XBRL", "company fundamentals".
     Keep those words in the title/first line; that's what store search ranks on. -->

## What it does

Give it tickers or CIKs. It pulls each company's official XBRL facts from SEC
EDGAR and returns a clean, spreadsheet-ready table — one row per
(company, metric, unit, period), deduplicated to the latest filing so you get a
clean time series instead of raw, restated JSON. Public-domain SEC data, fetched
within SEC's fair-access rules.

## Example input

```json
{
  "companies": ["AAPL", "MSFT"],
  "concepts": ["Revenues", "NetIncomeLoss", "EarningsPerShareDiluted"],
  "dateFrom": "2021-01-01"
}
```

## Example output (CSV)

```csv
ticker,cik,entity_name,taxonomy,concept,label,unit,period_start,period_end,fiscal_year,fiscal_period,value,form,filed,frame,accession
AAPL,320193,Apple Inc.,us-gaap,NetIncomeLoss,Net Income (Loss),USD,2022-09-25,2023-09-30,2023,FY,96995000000,10-K,2023-11-03,CY2023,0000320193-23-000106
MSFT,789019,MICROSOFT CORPORATION,us-gaap,EarningsPerShareDiluted,"Earnings Per Share, Diluted",USD/shares,2022-07-01,2023-06-30,2023,FY,9.68,10-K,2023-07-27,CY2023,0000950170-23-035122
```

Leave `concepts` empty for a curated set of common fundamentals, or pass
`["all"]` for every reported concept. Export the result as CSV, JSON, or Excel.

## Why this one

- **Tidy by default** — one row per period, restated/duplicate filings collapsed
  to the latest value. Drops straight into Sheets/Excel or pandas.
- **Official source** — reads the SEC EDGAR `companyfacts` XBRL API directly, so
  it doesn't break on website redesigns and stays ToS-clean.
- **Reliable** — mandatory User-Agent, request throttling, and automatic retries.
- Ticker **or** CIK input; date filtering; US-GAAP + DEI taxonomies.

## Pricing (simple, pay-per-result)

**$3.00 per 1,000 result rows.** No subscription — pay only for what you pull.
(A typical single-company, curated-metrics run is a few hundred rows.)

## Store assets to capture before publishing

- **Screenshot 1:** the Apify dataset tab showing the output table (real run).
- **Screenshot 2:** the same data opened in Google Sheets/Excel (the "tidy" payoff).
- No GIF needed (this is an actor, not an extension).

---
*Draft — publish from your own Apify account. Do not fabricate screenshots; run it
once and capture the real output.*
