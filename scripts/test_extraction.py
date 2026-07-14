"""Test the Claude extraction prompt on a sample posting (or your own text file)
before wiring it into n8n.

Usage:
    pip install anthropic python-dotenv
    python scripts/test_extraction.py                 # runs on built-in sample
    python scripts/test_extraction.py my_posting.txt  # runs on a file
"""
import json
import os
import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic python-dotenv")

SYSTEM = (
    'You extract structured data from internship job postings in India. Output ONLY a valid '
    'JSON object, no markdown fences, no commentary. If a field is not stated use null '
    '(arrays: [], booleans: false). Never guess stipend numbers. Schema: '
    '{"title":string,"company":string,"role_category":"pm"|"growth"|"analyst"|"swe"|"other",'
    '"location":string|null,"city":string|null,"is_remote":boolean,'
    '"stipend_min_inr":integer|null,"stipend_max_inr":integer|null,'
    '"duration_months":number|null,"yoe_required":number,"ppo_offered":boolean,'
    '"posted_at":"YYYY-MM-DD"|null,"skills":[string],"perks":[string]}. '
    'Rules: stipend is monthly INR ("8-12k" -> min 8000 max 12000; "unpaid" -> 0; convert '
    'lakhs/year to monthly). city: one normalized Indian city (Bangalore, Mumbai, Delhi NCR, '
    'Hyderabad, Pune, Chennai, Kolkata, or the proper city name), null if remote-only. '
    'yoe_required: years of prior experience asked, 0 if none mentioned. posted_at: resolve '
    'relative dates against the given today date. skills: lowercase canonical tags (excel, '
    'sql, power bi, google analytics, figma, a/b testing, seo, communication...), exclude '
    'generic filler like "hardworking". role_category: pm=product roles, '
    'growth=marketing/growth/community, analyst=data/business/product analyst, '
    'swe=software/web/app/backend/frontend/qa/devops/ml engineering, else other.'
)

SAMPLE = """
Product Management Intern — Bangalore | Posted 3 days ago
FintechCo (Series B, 120 employees)
Stipend: ₹ 20,000-25,000 /month | Duration: 6 Months | Starts Immediately

About: Work with the payments pod to ship features used by 2M+ users.
Responsibilities: write PRDs, run A/B experiments, analyze funnels in SQL and Mixpanel,
coordinate with design on Figma mocks.
Requirements: strong communication, Excel proficiency, prior product internship of at
least 6 months preferred. Only candidates available for full 6 months apply.
Perks: Certificate, Letter of recommendation, Flexible work hours, PPO for top performers.
"""


def main():
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 else SAMPLE
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        temperature=0,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Today's date: {date.today()}\n\nPosting URL: (test)\nPosting text:\n---\n{text}\n---",
        }],
    )
    raw = msg.content[0].text
    # strip markdown fences if the model adds them (n8n workflows do the same)
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
        print(json.dumps(parsed, indent=2))
        print("\n✓ Valid JSON. Fields:", ", ".join(parsed.keys()))
    except json.JSONDecodeError:
        print("✗ Model did not return valid JSON:\n", raw)


if __name__ == "__main__":
    main()
