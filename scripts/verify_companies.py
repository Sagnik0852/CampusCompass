"""Probe Lever / Greenhouse / Ashby public job-board APIs to find which companies
have live boards, then upsert verified ones into the Supabase `companies` table.

The ATS careers-scan workflow (n8n/ats_careers_scan.json) reads that table daily.

Usage:
    python scripts/verify_companies.py                    # probe built-in candidate list
    python scripts/verify_companies.py Meesho Groww       # probe specific names
    python scripts/verify_companies.py --file names.txt   # one company name per line
    python scripts/verify_companies.py --dry-run          # probe only, don't write to DB

Already verified live (seeded in DB): CRED (lever), Postman (greenhouse).
"""
import argparse
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Companies worth probing (Indian startups hiring PM/growth/analyst interns).
# Wrong guesses cost nothing — invalid slugs just 404.
CANDIDATES = [
    "Meesho", "Groww", "Razorpay", "PhonePe", "Swiggy", "Zomato", "Zepto",
    "CoinSwitch", "Slice", "Jupiter", "Fi Money", "Khatabook", "Whatfix",
    "Zetwerk", "Unacademy", "UpGrad", "Urban Company", "NoBroker", "Dream11",
    "Dream Sports", "MPL", "Games24x7", "ShareChat", "Rocketlane", "Chargebee",
    "Hasura", "Dukaan", "Rupifi", "StockGro", "Plum", "KukuFM", "Pocket FM",
    "Leap Finance", "BrightCHAMPS", "Skillmatics", "Park Plus", "Multiplier",
    "Atlan", "Hevo Data", "Airmeet", "DealShare", "Jar", "Stanza Living",
]


def slug_variants(name: str) -> list[str]:
    base = name.lower().strip()
    v = {
        base.replace(" ", ""),
        base.replace(" ", "-"),
        base.replace(" ", "_"),
    }
    return [s for s in v if s]


def probe(provider: str, slug: str) -> int | None:
    """Return live posting count if the board exists, else None."""
    urls = {
        "lever": f"https://api.lever.co/v0/postings/{slug}?mode=json",
        "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
    }
    try:
        r = requests.get(urls[provider], timeout=15, headers={"User-Agent": "CampusCompass/1.0"})
        if r.status_code != 200:
            return None
        d = r.json()
        if provider == "lever":
            return len(d) if isinstance(d, list) else None
        jobs = d.get("jobs")
        return len(jobs) if isinstance(jobs, list) else None
    except Exception:
        return None


def upsert(rows: list[dict]) -> None:
    if not SUPABASE_URL or not SERVICE_KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env to write results.")
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/companies",
        headers={
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        params={"on_conflict": "ats_provider,ats_slug"},
        json=rows,
        timeout=30,
    )
    if r.status_code >= 300:
        sys.exit(f"Upsert failed ({r.status_code}): {r.text[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="company names to probe")
    ap.add_argument("--file", help="file with one company name per line")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    names = args.names or (open(args.file).read().splitlines() if args.file else CANDIDATES)
    names = [n.strip() for n in names if n.strip()]

    hits = []
    for name in names:
        found = False
        for provider in ("lever", "greenhouse", "ashby"):
            for slug in slug_variants(name):
                n = probe(provider, slug)
                time.sleep(0.3)  # be polite
                if n is not None:
                    print(f"  ✓ {name:<20} {provider:<11} slug={slug:<20} ({n} live postings)")
                    hits.append({
                        "name": name, "ats_provider": provider, "ats_slug": slug,
                        "active": True, "notes": f"verified via script, {n} postings",
                    })
                    found = True
                    break
            if found:
                break
        if not found:
            print(f"  ✗ {name:<20} no public board found (may use Keka/Darwinbox/custom)")

    print(f"\n{len(hits)}/{len(names)} companies have live public boards.")
    if hits and not args.dry_run:
        upsert(hits)
        print("Upserted into Supabase `companies`. The ATS workflow will pick them up on its next run.")
    elif hits:
        print("(dry run — nothing written)")


if __name__ == "__main__":
    main()
