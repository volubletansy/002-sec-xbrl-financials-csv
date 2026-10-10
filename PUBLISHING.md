# Publishing checklist — 002-sec-xbrl-financials-csv

Everything below is decided. Publishing is an account/legal action (accepting
Apify's Monetization Terms + payout setup), so it happens in **your** Apify
Console — this file is the fill-in-the-blanks. Fields are copy-paste ready.

## 0. Get the code onto Apify (build)

Either connect the GitHub repo or push from the CLI:

- **GitHub:** Console → Create Actor → "Link GitHub repo" →
  `https://github.com/volubletansy/002-sec-xbrl-financials-csv` → Build.
- **CLI:** `apify login` then `apify push` from `assets/002-sec-xbrl-financials-csv/`.

Confirm the build is **green** and a test run returns rows before publishing
(it should now — the actor is SDK-free stdlib only).

## 1. Publication tab — the storefront

- **Name / SEO title:** `SEC EDGAR Financials Scraper — Company Fundamentals to CSV`
- **Short description (summary):**
  > Extract US public company financials (revenue, net income, EPS, assets…) from
  > official SEC EDGAR XBRL into a tidy, one-row-per-metric CSV. Tickers or CIKs in,
  > clean spreadsheet out — no API keys, no raw JSON.
- **Categories:** `Developer tools` + `Business` (add `Finance` if offered).
- **README / description:** auto-pulled from the repo `README.md` — already written.
- **Screenshots (capture from a real run, don't fake):**
  1. The Apify **dataset tab** showing the output table.
  2. The same data opened in **Google Sheets/Excel** (the "tidy" payoff).

## 2. Monetization tab — the decision (all selected)

- Accept **Apify's Monetization Terms** and set up **payout** (PayPal / Stripe /
  crypto). ← only you can do this.
- **Model: Pay per result (PPR).** Best fit — it's a data extractor, buyers pay
  only for rows pulled, and this actor's compute is tiny (plain HTTP), so the
  margin over platform compute cost is healthy.
- **Price: $3.00 per 1,000 results.** (Benchmarked against per-result data actors
  like Outscraper; matches `listing.md`. Easy to raise later if demand shows.)
- Not chosen, and why: **Rental/subscription** (buyers want occasional pulls, not a
  monthly fee); **Pay per event** (overkill — one "result" = one row is the natural
  unit here); **Free** (leaves money on the table for a working tool).

## 3. Go public

- Set the actor to **Public** and submit for Apify review.
- After it's live: set the asset's `STATUS` to `live`, and update
  `log/experiments.csv` row to `stage=4` with the `published_date`. Then
  `scripts/health-check` covers it and the Day-14 `/review` clock starts
  (threshold: ≥3 organic users).
