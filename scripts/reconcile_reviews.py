"""Recover missing human-review handoffs. Preview by default; --apply persists.

Run from the repository root with apps/api/.venv/bin/python scripts/reconcile_reviews.py.
Only prints record identifiers and counts, never credentials or conversation text.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
load_dotenv(root / "apps/api/.env")
sys.path.insert(0, str(root / "apps/api"))

from app.db.session import SessionLocal
from app.services.reviews import ReviewService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Create missing review tasks and repair their waiting states.")
    args = parser.parse_args()
    with SessionLocal() as db:
        report = ReviewService(db).reconcile_missing_review_tasks(apply=args.apply)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
