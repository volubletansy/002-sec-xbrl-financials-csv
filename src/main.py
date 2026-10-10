"""Apify actor entrypoint for sec-xbrl-financials-csv.

Deliberately SDK-free: this actor only makes plain HTTP calls to the SEC, so it
does not need `apify`/`crawlee` (which drag in pydantic + browser-fingerprinting
deps that have repeatedly broken on version bumps). Instead it talks to Apify's
documented REST API using the env vars every actor run gets, with stdlib only.

On the Apify platform:
  - input  <- GET  key-value-stores/{store}/records/{INPUT key}
  - output -> POST datasets/{dataset}/items   (batched)
Off-platform (local test/dev): reads a local INPUT.json if present and writes
`output.csv` instead of pushing.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.error
import urllib.request

from .sec_xbrl import (
    DEFAULT_TAXONOMIES,
    DEFAULT_USER_AGENT,
    SecError,
    company_rows,
    load_ticker_map,
    write_csv,
)

_PUSH_BATCH = 1000  # rows per dataset POST; keeps each payload well under limits


def _env(*names: str, default: str | None = None) -> str | None:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


def _api_base() -> str:
    return _env("APIFY_API_BASE_URL", "APIFY_API_PUBLIC_BASE_URL",
                default="https://api.apify.com").rstrip("/")


def _log(msg: str) -> None:
    print(msg, flush=True)


# --- Apify I/O (REST, no SDK) ------------------------------------------------

def get_input() -> dict:
    token = _env("APIFY_TOKEN")
    store = _env("APIFY_DEFAULT_KEY_VALUE_STORE_ID", "ACTOR_DEFAULT_KEY_VALUE_STORE_ID")
    key = _env("APIFY_INPUT_KEY", "ACTOR_INPUT_KEY", default="INPUT")

    if token and store:
        url = f"{_api_base()}/v2/key-value-stores/{store}/records/{key}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            raise

    # local fallbacks for dev/testing
    for p in ("storage/key_value_stores/default/INPUT.json", "INPUT.json"):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raw = _env("ACTOR_INPUT", "APIFY_INPUT_JSON")
    return json.loads(raw) if raw else {}


def push_items(items: list) -> str:
    token = _env("APIFY_TOKEN")
    dataset = _env("APIFY_DEFAULT_DATASET_ID", "ACTOR_DEFAULT_DATASET_ID")

    if token and dataset:
        url = f"{_api_base()}/v2/datasets/{dataset}/items"
        for i in range(0, len(items), _PUSH_BATCH):
            batch = items[i:i + _PUSH_BATCH]
            data = json.dumps(batch).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=60).close()
        return "Apify dataset"

    # local fallback: write a CSV so the run is still inspectable off-platform
    with open("output.csv", "w", newline="", encoding="utf-8") as f:
        write_csv(items, f)
    return "output.csv"


# --- main --------------------------------------------------------------------

def main() -> None:
    inp = get_input() or {}

    companies = inp.get("companies") or []
    if isinstance(companies, str):
        companies = [c.strip() for c in companies.replace(",", "\n").splitlines() if c.strip()]
    if not companies:
        _log("ERROR: input 'companies' is required (tickers or CIKs).")
        sys.exit(1)

    concepts = inp.get("concepts") or None
    if concepts in (["all"], "all"):
        concepts = "all"
    taxonomies = inp.get("taxonomies") or list(DEFAULT_TAXONOMIES)
    date_from = inp.get("dateFrom") or None
    date_to = inp.get("dateTo") or None
    dedupe = inp.get("dedupe", True)
    email = (inp.get("userAgentEmail") or "").strip()
    ua = f"AssetLab-SEC-XBRL/1.0 (contact: {email})" if email else DEFAULT_USER_AGENT

    ticker_map = load_ticker_map(ua)

    rows: list = []
    for ident in companies:
        try:
            r = company_rows(
                ident, concepts=concepts, taxonomies=taxonomies,
                date_from=date_from, date_to=date_to, dedupe=dedupe,
                ticker_map=ticker_map, user_agent=ua,
            )
        except SecError as e:
            _log(f"WARN: skipping {ident!r}: {e}")
            continue
        _log(f"{ident}: {len(r)} rows")
        rows.extend(r)

    dest = push_items(rows)
    _log(f"Done. {len(rows)} rows across {len(companies)} companies -> {dest}.")
