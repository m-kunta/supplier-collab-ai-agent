from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

# Load .env before any src imports resolve provider/API key env vars.
load_dotenv()

from src.agent import summarize_request  # noqa: E402

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Supplier collaboration briefing scaffold CLI."
    )
    parser.add_argument("--vendor", required=True, help="Vendor name or canonical vendor ID.")
    parser.add_argument("--date", required=True, help="Meeting date in YYYY-MM-DD format.")
    parser.add_argument(
        "--data-dir",
        default="data/inbound/mock",
        help="Path to the manifest-driven data landing zone.",
    )
    parser.add_argument(
        "--lookback-weeks",
        type=int,
        default=13,
        help="Lookback window for scorecard and trend calculations.",
    )
    parser.add_argument(
        "--persona-emphasis",
        choices=["buyer", "planner", "both"],
        default="both",
        help="Primary audience for the briefing.",
    )
    parser.add_argument(
        "--include-benchmarks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include benchmark calculations in the future generated briefing.",
    )
    parser.add_argument(
        "--output-format",
        choices=["md", "docx", "both"],
        default="docx",
        help="Intended output format.",
    )
    parser.add_argument(
        "--category-filter",
        default=None,
        help="Optional category filter for vendors spanning multiple categories.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    summary = summarize_request(
        vendor=args.vendor,
        meeting_date=args.date,
        data_dir=Path(args.data_dir),
        lookback_weeks=args.lookback_weeks,
        persona_emphasis=args.persona_emphasis,
        include_benchmarks=args.include_benchmarks,
        output_format=args.output_format,
        category_filter=args.category_filter,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
