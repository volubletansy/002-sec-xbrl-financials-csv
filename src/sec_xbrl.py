"""SEC XBRL company financials -> tidy rows.

Zero-dependency (stdlib only) core for the Asset Lab actor
`002-sec-xbrl-financials-csv`. Fetches the official SEC EDGAR companyfacts XBRL
API and flattens it into one row per (company, concept, unit, fiscal period),
ready to drop into Sheets/Excel.

Data source: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
Ticker map:  https://www.sec.gov/files/company_tickers.json

SEC fair-access policy requires a descriptive User-Agent and ~<=10 req/s. Both
are honored here. All data is U.S. government public-domain; ToS-clean.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from typing import Iterable, Optional

# --- constants ---------------------------------------------------------------

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# A descriptive UA is mandatory. Callers should pass their own contact; this is
# a sane, non-personal default. (We never put a user's personal email here.)
DEFAULT_USER_AGENT = "AssetLab-SEC-XBRL/1.0 (contact: admin@asset-lab.example)"

# Curated common fundamentals (us-gaap concept names). Override via `concepts`.
DEFAULT_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "ResearchAndDevelopmentExpense",
]

DEFAULT_TAXONOMIES = ("us-gaap", "dei")

# Output column order — this IS the documented schema. The health-check asserts
# exactly this header, so a change here is treated as an output-shape change.
COLUMNS = [
    "ticker",
    "cik",
    "entity_name",
    "taxonomy",
    "concept",
    "label",
    "unit",
    "period_start",
    "period_end",
    "fiscal_year",
    "fiscal_period",
    "value",
    "form",
    "filed",
    "frame",
    "accession",
]

_MIN_INTERVAL_S = 0.15  # ~6.6 req/s, under SEC's ~10 req/s ceiling
_last_request_ts = 0.0


class SecError(Exception):
    """Clear, user-facing error for any SEC fetch/parse failure."""


# --- http --------------------------------------------------------------------

def _throttle() -> None:
    global _last_request_ts
    wait = _MIN_INTERVAL_S - (time.monotonic() - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.monotonic()


def http_get_json(url: str, user_agent: str, retries: int = 4, timeout: int = 30):
    """GET JSON with a mandatory UA, throttling, and backoff on 429/5xx."""
    attempt = 0
    while True:
        _throttle()
        req = urllib.request.Request(
            url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if "gzip" in enc:
                    import gzip
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise SecError(f"Not found (404): {url}") from e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
                attempt += 1
                continue
            raise SecError(f"HTTP {e.code} from SEC for {url}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
                attempt += 1
                continue
            raise SecError(f"Network error reaching SEC ({url}): {e}") from e


# --- identifiers -------------------------------------------------------------

def load_ticker_map(user_agent: str = DEFAULT_USER_AGENT) -> dict:
    """{UPPER_TICKER: cik_int} from the official SEC ticker file."""
    data = http_get_json(TICKER_MAP_URL, user_agent)
    out = {}
    # file is {"0": {"cik_str":320193,"ticker":"AAPL","title":"..."}, ...}
    for row in data.values():
        try:
            out[str(row["ticker"]).upper()] = int(row["cik_str"])
        except (KeyError, ValueError, TypeError):
            continue
    if not out:
        raise SecError("Ticker map came back empty or malformed.")
    return out


def resolve_cik(identifier: str, ticker_map: Optional[dict] = None,
                user_agent: str = DEFAULT_USER_AGENT) -> int:
    """Accept a numeric CIK ('320193' / '0000320193') or a ticker ('AAPL')."""
    ident = str(identifier).strip()
    if not ident:
        raise SecError("Empty company identifier.")
    digits = ident.lstrip("0") or "0"
    if ident.replace("-", "").isdigit():
        return int(digits)
    if ticker_map is None:
        ticker_map = load_ticker_map(user_agent)
    cik = ticker_map.get(ident.upper())
    if cik is None:
        raise SecError(f"Unknown ticker: {ident!r} (not in SEC ticker map).")
    return cik


# --- facts -------------------------------------------------------------------

def fetch_companyfacts(cik: int, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    try:
        return http_get_json(COMPANYFACTS_URL.format(cik=cik), user_agent)
    except SecError as e:
        if "404" in str(e):
            raise SecError(
                f"No XBRL company facts for CIK {cik:010d} "
                "(entity may not be an XBRL filer)."
            ) from e
        raise


def flatten_facts(
    facts_json: dict,
    ticker: str = "",
    concepts: Optional[Iterable[str]] = None,
    taxonomies: Iterable[str] = DEFAULT_TAXONOMIES,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list:
    """Flatten a companyfacts payload into COLUMNS-shaped row dicts.

    `concepts=None` -> DEFAULT_CONCEPTS; `concepts="all"` -> every concept.
    `date_from`/`date_to` filter on period_end (inclusive, 'YYYY-MM-DD').
    """
    cik = facts_json.get("cik")
    entity = facts_json.get("entityName", "")
    all_facts = facts_json.get("facts", {})

    if concepts == "all":
        wanted = None
    else:
        wanted = set(concepts) if concepts else set(DEFAULT_CONCEPTS)

    rows = []
    for taxonomy in taxonomies:
        concept_map = all_facts.get(taxonomy, {})
        for concept, body in concept_map.items():
            if wanted is not None and concept not in wanted:
                continue
            label = body.get("label", "")
            for unit, points in body.get("units", {}).items():
                for p in points:
                    end = p.get("end")
                    if date_from and (end or "") < date_from:
                        continue
                    if date_to and (end or "") > date_to:
                        continue
                    rows.append({
                        "ticker": ticker.upper(),
                        "cik": cik,
                        "entity_name": entity,
                        "taxonomy": taxonomy,
                        "concept": concept,
                        "label": label,
                        "unit": unit,
                        "period_start": p.get("start", ""),
                        "period_end": end or "",
                        "fiscal_year": p.get("fy", ""),
                        "fiscal_period": p.get("fp", ""),
                        "value": p.get("val", ""),
                        "form": p.get("form", ""),
                        "filed": p.get("filed", ""),
                        "frame": p.get("frame", ""),
                        "accession": p.get("accn", ""),
                    })
    return rows


def dedupe_latest(rows: list) -> list:
    """Collapse restated/duplicate datapoints into one row per *period*.

    Key = (taxonomy, concept, unit, period_start, period_end); keep the most
    recently `filed` instance. `fiscal_year`/`fiscal_period` describe the FILING,
    not the datapoint's period, so they are deliberately NOT in the key — every
    later 10-K re-reports prior periods as comparatives, and keying on fy/fp
    would keep all those identical copies. `period_start` keeps a quarterly and
    an annual figure that share an end date distinct."""
    best = {}
    for r in rows:
        key = (r["taxonomy"], r["concept"], r["unit"],
               r["period_start"], r["period_end"])
        cur = best.get(key)
        if cur is None or (r["filed"] or "") > (cur["filed"] or ""):
            best[key] = r
    out = list(best.values())
    out.sort(key=lambda r: (r["concept"], r["unit"],
                            str(r["period_end"]), str(r["period_start"])))
    return out


def write_csv(rows: list, fileobj) -> None:
    writer = csv.DictWriter(fileobj, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


# --- orchestration -----------------------------------------------------------

def company_rows(
    identifier: str,
    concepts: Optional[Iterable[str]] = None,
    taxonomies: Iterable[str] = DEFAULT_TAXONOMIES,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    dedupe: bool = True,
    ticker_map: Optional[dict] = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list:
    """Full pipeline for one company: resolve -> fetch -> flatten -> dedupe."""
    is_ticker = not str(identifier).replace("-", "").isdigit()
    cik = resolve_cik(identifier, ticker_map, user_agent)
    facts = fetch_companyfacts(cik, user_agent)
    ticker = str(identifier).upper() if is_ticker else ""
    rows = flatten_facts(facts, ticker, concepts, taxonomies, date_from, date_to)
    return dedupe_latest(rows) if dedupe else rows
