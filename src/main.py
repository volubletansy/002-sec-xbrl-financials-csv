"""Apify actor entrypoint for sec-xbrl-financials-csv.

Reads actor input, pulls tidy XBRL rows for each company, and pushes them to the
default dataset (Apify exports it to CSV/JSON/Excel). The data logic lives in the
dependency-free `sec_xbrl` module so it stays testable off-platform.
"""
from __future__ import annotations

try:
    from apify import Actor
except ImportError:  # off-platform (tests/health-check) — not needed there
    Actor = None

from .sec_xbrl import (
    DEFAULT_CONCEPTS,
    DEFAULT_TAXONOMIES,
    DEFAULT_USER_AGENT,
    SecError,
    company_rows,
    load_ticker_map,
)


def _user_agent(inp: dict) -> str:
    email = (inp.get("userAgentEmail") or "").strip()
    return f"AssetLab-SEC-XBRL/1.0 (contact: {email})" if email else DEFAULT_USER_AGENT


async def main() -> None:
    if Actor is None:
        raise RuntimeError("apify SDK not available; run on the Apify platform.")
    async with Actor:
        inp = await Actor.get_input() or {}

        companies = inp.get("companies") or []
        if isinstance(companies, str):
            companies = [c.strip() for c in companies.replace(",", "\n").splitlines() if c.strip()]
        if not companies:
            raise ValueError("Input 'companies' is required (tickers or CIKs).")

        concepts = inp.get("concepts") or None
        if concepts in (["all"], "all"):
            concepts = "all"
        taxonomies = inp.get("taxonomies") or list(DEFAULT_TAXONOMIES)
        date_from = inp.get("dateFrom") or None
        date_to = inp.get("dateTo") or None
        dedupe = inp.get("dedupe", True)
        ua = _user_agent(inp)

        ticker_map = load_ticker_map(ua)  # fetched once, reused across companies

        total = 0
        for ident in companies:
            try:
                rows = company_rows(
                    ident, concepts=concepts, taxonomies=taxonomies,
                    date_from=date_from, date_to=date_to, dedupe=dedupe,
                    ticker_map=ticker_map, user_agent=ua,
                )
            except SecError as e:
                Actor.log.warning(f"Skipping {ident!r}: {e}")
                continue
            if rows:
                await Actor.push_data(rows)
                total += len(rows)
            Actor.log.info(f"{ident}: {len(rows)} rows")

        Actor.log.info(f"Done. {total} rows across {len(companies)} companies.")
