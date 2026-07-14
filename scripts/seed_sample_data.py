"""Seed Supabase with realistic fake postings so the dashboard/digest work before
the scraper has collected real data. Safe to re-run (URLs are unique per run).

Usage:
    pip install requests python-dotenv
    python scripts/seed_sample_data.py            # inserts ~400 rows
    python scripts/seed_sample_data.py --wipe     # deletes seeded rows first
"""
import argparse
import os
import random
import sys
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
if not SUPABASE_URL or not SERVICE_KEY:
    sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env first.")

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates,return=minimal",
}

random.seed(42)

CITIES = ["Bangalore", "Mumbai", "Delhi NCR", "Hyderabad", "Pune", "Chennai", None]
CITY_W = [0.30, 0.18, 0.18, 0.10, 0.09, 0.05, 0.10]  # None = remote

COMPANIES = [
    "Zeptonow", "CredAvenue", "Meesho", "Groww", "Razorpay", "Zomato", "Swiggy",
    "PhonePe", "CoinSwitch", "Unacademy", "UpGrad", "Slice", "Jupiter", "Fi Money",
    "Park+", "Skillmatics", "Leap Finance", "BrightCHAMPS", "Plum Benefits",
    "KukuFM", "Pocket FM", "Rocketlane", "Chargebee", "Freshworks", "Zoho",
    "Postman", "Hasura", "Dukaan", "Bijnis", "Rupifi", "EarlySalary", "StockGro",
]

# skill -> (base weight, monthly growth multiplier) per role.
# growth > 1 means the skill trends UP over the seeded window (gives the
# dashboard real "SQL up 40%" style movement to show).
SKILLS = {
    "pm": {
        "sql": (0.35, 1.09), "excel": (0.55, 0.99), "figma": (0.30, 1.03),
        "wireframing": (0.25, 1.0), "a/b testing": (0.20, 1.06),
        "jira": (0.20, 1.0), "google analytics": (0.25, 1.02),
        "communication": (0.60, 1.0), "market research": (0.35, 1.0),
        "python": (0.10, 1.08), "notion": (0.15, 1.02), "ai tools": (0.12, 1.15),
    },
    "growth": {
        "seo": (0.40, 1.0), "google analytics": (0.45, 1.02),
        "meta ads": (0.35, 1.01), "google ads": (0.30, 1.01),
        "content writing": (0.45, 0.98), "excel": (0.35, 1.0),
        "canva": (0.30, 1.0), "email marketing": (0.25, 1.0),
        "influencer marketing": (0.15, 1.05), "sql": (0.12, 1.10),
        "a/b testing": (0.15, 1.06), "ai tools": (0.15, 1.14),
    },
    "analyst": {
        "sql": (0.75, 1.02), "excel": (0.70, 0.99), "power bi": (0.40, 1.04),
        "tableau": (0.30, 0.99), "python": (0.45, 1.05),
        "statistics": (0.25, 1.0), "google sheets": (0.20, 1.0),
        "data visualization": (0.30, 1.0), "r": (0.08, 0.95),
        "machine learning": (0.12, 1.06), "ai tools": (0.10, 1.16),
    },
    "swe": {
        "python": (0.45, 1.03), "javascript": (0.45, 1.0), "react": (0.40, 1.02),
        "node.js": (0.35, 1.0), "sql": (0.40, 1.01), "java": (0.30, 0.98),
        "git": (0.35, 1.0), "data structures": (0.30, 1.0), "docker": (0.15, 1.05),
        "aws": (0.18, 1.04), "machine learning": (0.15, 1.08), "ai tools": (0.18, 1.18),
    },
}

STIPEND = {  # (median, spread) monthly INR by role
    "pm": (22000, 12000), "growth": (15000, 9000), "analyst": (20000, 11000),
    "swe": (28000, 15000),
}
CITY_MULT = {"Bangalore": 1.15, "Mumbai": 1.1, "Delhi NCR": 1.05, "Hyderabad": 1.0,
             "Pune": 0.95, "Chennai": 0.9, None: 0.85}

TITLES = {
    "pm": ["Product Management Intern", "APM Intern", "Product Intern", "Product Strategy Intern"],
    "growth": ["Growth Intern", "Marketing Intern", "Performance Marketing Intern", "Growth & Community Intern"],
    "analyst": ["Data Analyst Intern", "Business Analyst Intern", "Product Analyst Intern", "BI Intern"],
    "swe": ["Software Engineering Intern", "SDE Intern", "Backend Developer Intern", "Full Stack Intern"],
}

PERKS = ["certificate", "lor", "flexible hours", "5 days a week", "informal dress code", "free snacks"]


def make_posting(i: int, d: date) -> dict:
    role = random.choices(["pm", "growth", "analyst", "swe"], [0.22, 0.27, 0.26, 0.25])[0]
    months_ago = (date.today() - d).days / 30.0
    skills = []
    for skill, (base, growth) in SKILLS[role].items():
        p = min(0.95, base * (growth ** (8 - months_ago)))  # window is ~8 months
        if random.random() < p:
            skills.append(skill)
    city = random.choices(CITIES, CITY_W)[0]
    med, spread = STIPEND[role]
    base_stipend = max(0, random.gauss(med * CITY_MULT[city], spread / 2))
    unpaid = random.random() < 0.08
    smin = 0 if unpaid else int(round(base_stipend / 1000) * 1000)
    smax = smin if unpaid or random.random() < 0.6 else int(smin * random.uniform(1.2, 1.8) // 1000 * 1000)
    # YoE creep: later postings ask for slightly more prior experience
    yoe = 0.0
    if random.random() < 0.15 + 0.02 * (8 - months_ago):
        yoe = random.choice([0.5, 1.0, 1.0, 2.0])
    return {
        "source": random.choices(["internshala", "wellfound", "linkedin"], [0.6, 0.15, 0.25])[0],
        "source_url": f"https://seeded.campuscompass.dev/posting/{i}",
        "scraped_at": f"{d.isoformat()}T09:00:00Z",
        "posted_at": d.isoformat(),
        "title": random.choice(TITLES[role]),
        "company": random.choice(COMPANIES),
        "role_category": role,
        "location": city or "Work from home",
        "city": city,
        "is_remote": city is None,
        "stipend_min_inr": smin,
        "stipend_max_inr": smax,
        "duration_months": random.choice([2, 3, 3, 6, 6]),
        "yoe_required": yoe,
        "ppo_offered": random.random() < 0.25,
        "skills": skills,
        "perks": random.sample(PERKS, k=random.randint(1, 3)),
        "raw_text": "[seeded sample posting]",
        "extraction_model": "seed-script",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wipe", action="store_true", help="delete previously seeded rows first")
    ap.add_argument("-n", type=int, default=400)
    args = ap.parse_args()

    if args.wipe:
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/postings",
            headers=HEADERS,
            params={"extraction_model": "eq.seed-script"},
            timeout=30,
        )
        r.raise_for_status()
        print("Wiped previously seeded rows.")

    today = date.today()
    rows = []
    for i in range(args.n):
        d = today - timedelta(days=int(random.triangular(0, 240, 60)))
        rows.append(make_posting(i, d))

    for start in range(0, len(rows), 100):
        batch = rows[start:start + 100]
        r = requests.post(f"{SUPABASE_URL}/rest/v1/postings", headers=HEADERS, json=batch, timeout=60)
        if r.status_code >= 300:
            sys.exit(f"Insert failed ({r.status_code}): {r.text[:500]}")
        print(f"Inserted {start + len(batch)}/{len(rows)}")

    print("Done. Run: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
