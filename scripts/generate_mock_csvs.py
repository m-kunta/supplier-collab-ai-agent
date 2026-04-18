import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

import yaml

DEFAULT_OUTPUT_DIR = Path("data") / "inbound" / "mock"
REFERENCE_DATE = date(2026, 4, 3)
PERFORMANCE_END_DATE = date(2026, 3, 28)

VENDOR_SEEDS = [
    {
        "vendor_name": "Northstar Foods Co",
        "primary_category": "Cereal",
        "buyer_name": "Alex Carter",
        "planner_name": "Riley Brooks",
    },
    {
        "vendor_name": "Blue Harbor Pantry",
        "primary_category": "Snacks",
        "buyer_name": "Jordan Park",
        "planner_name": "Morgan Lee",
    },
    {
        "vendor_name": "Cedar Peak Provisions",
        "primary_category": "Beverage",
        "buyer_name": "Taylor Quinn",
        "planner_name": "Avery Kim",
    },
    {
        "vendor_name": "Suntrail Grocery Works",
        "primary_category": "Frozen",
        "buyer_name": "Casey Monroe",
        "planner_name": "Drew Patel",
    },
    {
        "vendor_name": "Maple Bridge Supply",
        "primary_category": "Household",
        "buyer_name": "Parker Lane",
        "planner_name": "Emerson Shaw",
    },
    {
        "vendor_name": "Orbit Harvest Brands",
        "primary_category": "Wellness",
        "buyer_name": "Reese Logan",
        "planner_name": "Hayden Reese",
    },
    {
        "vendor_name": "Silver Meadow Foods",
        "primary_category": "Bakery",
        "buyer_name": "Blake Turner",
        "planner_name": "Rowan Ellis",
    },
    {
        "vendor_name": "Crimson Valley Trading",
        "primary_category": "Pantry",
        "buyer_name": "Skyler West",
        "planner_name": "Cameron Price",
    },
]


def ensure_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def write_csv(output_dir: Path, filename: str, fieldnames: list[str], rows: list[dict]) -> int:
    filepath = output_dir / filename
    with filepath.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {filepath} with {len(rows)} rows.")
    return len(rows)


def build_vendor_master_rows(vendor_count: int) -> list[dict]:
    if vendor_count < 1:
        raise ValueError("vendor_count must be >= 1")

    rows = []
    for index in range(vendor_count):
        seed = VENDOR_SEEDS[index % len(VENDOR_SEEDS)]
        cycle = index // len(VENDOR_SEEDS)
        suffix = "" if cycle == 0 else f" {cycle + 1}"
        rows.append(
            {
                "vendor_id": f"V{1001 + index}",
                "vendor_name": f"{seed['vendor_name']}{suffix}",
                "vendor_status": "active",
                "primary_category": seed["primary_category"],
                "buyer_name": seed["buyer_name"],
                "planner_name": seed["planner_name"],
            }
        )
    return rows


def generate_vendor_master(output_dir: Path, vendor_rows: list[dict]) -> int:
    fieldnames = [
        "vendor_id",
        "vendor_name",
        "vendor_status",
        "primary_category",
        "buyer_name",
        "planner_name",
    ]
    return write_csv(output_dir, "vendor_master.csv", fieldnames, vendor_rows)


def generate_purchase_orders(output_dir: Path, vendor_rows: list[dict]) -> int:
    fieldnames = [
        "po_number",
        "po_line",
        "vendor_id",
        "sku",
        "sku_description",
        "qty_ordered",
        "requested_delivery_date",
        "po_status",
        "ship_to_dc",
    ]
    rows = []
    for idx, vendor in enumerate(vendor_rows):
        vendor_id = vendor["vendor_id"]
        sku_base = (idx + 1) * 100
        po_base = 9000 + ((idx + 1) * 10)
        rows.extend(
            [
                {
                    "po_number": f"PO-{po_base + 1}",
                    "po_line": 1,
                    "vendor_id": vendor_id,
                    "sku": f"SKU-{sku_base + 1:03d}",
                    "sku_description": f"{vendor['primary_category']} Core Item A",
                    "qty_ordered": 400 + (idx * 35),
                    "requested_delivery_date": (REFERENCE_DATE - timedelta(days=2 + idx)).isoformat(),
                    "po_status": "shipped",
                    "ship_to_dc": "DC-Atlanta",
                },
                {
                    "po_number": f"PO-{po_base + 2}",
                    "po_line": 1,
                    "vendor_id": vendor_id,
                    "sku": f"SKU-{sku_base + 2:03d}",
                    "sku_description": f"{vendor['primary_category']} Core Item B",
                    "qty_ordered": 260 + (idx * 30),
                    "requested_delivery_date": (REFERENCE_DATE + timedelta(days=4 + idx)).isoformat(),
                    "po_status": "open",
                    "ship_to_dc": "DC-Dallas",
                },
                {
                    "po_number": f"PO-{po_base + 3}",
                    "po_line": 1,
                    "vendor_id": vendor_id,
                    "sku": f"SKU-{sku_base + 3:03d}",
                    "sku_description": f"{vendor['primary_category']} Core Item C",
                    "qty_ordered": 300 + (idx * 28),
                    "requested_delivery_date": (REFERENCE_DATE + timedelta(days=7 + idx)).isoformat(),
                    "po_status": "open",
                    "ship_to_dc": "DC-Chicago",
                },
            ]
        )
    return write_csv(output_dir, "purchase_orders.csv", fieldnames, rows)


def generate_vendor_performance(output_dir: Path, vendor_rows: list[dict]) -> int:
    fieldnames = ["vendor_id", "week_ending", "metric_code", "metric_value", "metric_uom"]
    rows = []

    base_fill = [0.962, 0.958, 0.960, 0.955, 0.950, 0.948, 0.942, 0.940, 0.935, 0.930, 0.925, 0.920, 0.918]
    base_otif = [0.940, 0.930, 0.940, 0.920, 0.900, 0.890, 0.880, 0.880, 0.870, 0.860, 0.850, 0.840, 0.830]

    for vendor_index, vendor in enumerate(vendor_rows):
        vendor_id = vendor["vendor_id"]
        drift = vendor_index * 0.003

        for week_index in range(13):
            week_end = PERFORMANCE_END_DATE - timedelta(days=(12 - week_index) * 7)
            fill_rate = max(0.75, base_fill[week_index] - drift)
            otif = max(0.70, base_otif[week_index] - (drift * 1.2))
            rows.extend(
                [
                    {
                        "vendor_id": vendor_id,
                        "week_ending": week_end.isoformat(),
                        "metric_code": "FILL_RATE",
                        "metric_value": round(fill_rate, 4),
                        "metric_uom": "pct",
                    },
                    {
                        "vendor_id": vendor_id,
                        "week_ending": week_end.isoformat(),
                        "metric_code": "OTIF",
                        "metric_value": round(otif, 4),
                        "metric_uom": "pct",
                    },
                    {
                        "vendor_id": vendor_id,
                        "week_ending": week_end.isoformat(),
                        "metric_code": "LEAD_TIME_COMPLIANCE",
                        "metric_value": round(max(0.70, 0.88 - drift), 4),
                        "metric_uom": "pct",
                    },
                    {
                        "vendor_id": vendor_id,
                        "week_ending": week_end.isoformat(),
                        "metric_code": "FORECAST_ACCURACY",
                        "metric_value": round(max(0.68, 0.85 - (drift * 0.8)), 4),
                        "metric_uom": "pct",
                    },
                    {
                        "vendor_id": vendor_id,
                        "week_ending": week_end.isoformat(),
                        "metric_code": "PROMO_FILL_RATE",
                        "metric_value": round(max(0.70, 0.88 - (drift * 1.1)), 4),
                        "metric_uom": "pct",
                    },
                ]
            )

    return write_csv(output_dir, "vendor_performance.csv", fieldnames, rows)


def generate_oos_events(output_dir: Path, vendor_rows: list[dict]) -> int:
    fieldnames = ["vendor_id", "sku", "oos_start_date", "oos_end_date", "oos_units_lost", "root_cause_code"]
    rows = []
    for idx, vendor in enumerate(vendor_rows):
        vendor_id = vendor["vendor_id"]
        sku_base = (idx + 1) * 100
        rows.extend(
            [
                {
                    "vendor_id": vendor_id,
                    "sku": f"SKU-{sku_base + 1:03d}",
                    "oos_start_date": (REFERENCE_DATE - timedelta(days=5 + idx)).isoformat(),
                    "oos_end_date": "",
                    "oos_units_lost": 100 + (idx * 12),
                    "root_cause_code": "short_fill",
                },
                {
                    "vendor_id": vendor_id,
                    "sku": f"SKU-{sku_base + 3:03d}",
                    "oos_start_date": (REFERENCE_DATE - timedelta(days=10 + idx)).isoformat(),
                    "oos_end_date": (REFERENCE_DATE - timedelta(days=8 + idx)).isoformat(),
                    "oos_units_lost": 70 + (idx * 10),
                    "root_cause_code": "late_shipment",
                },
            ]
        )
    return write_csv(output_dir, "oos_events.csv", fieldnames, rows)


def generate_promo_calendar(output_dir: Path, vendor_rows: list[dict]) -> int:
    fieldnames = [
        "promo_id",
        "event_name",
        "vendor_id",
        "sku",
        "start_date",
        "end_date",
        "promoted_volume",
        "promo_type",
    ]
    rows = []
    for idx, vendor in enumerate(vendor_rows):
        sku_base = (idx + 1) * 100
        rows.append(
            {
                "promo_id": f"PRM-{idx + 1:03d}",
                "event_name": f"Seasonal Lift {idx + 1}",
                "vendor_id": vendor["vendor_id"],
                "sku": f"SKU-{sku_base + 1:03d}",
                "start_date": (REFERENCE_DATE + timedelta(days=1 + idx)).isoformat(),
                "end_date": (REFERENCE_DATE + timedelta(days=8 + idx)).isoformat(),
                "promoted_volume": 1200 + (idx * 90),
                "promo_type": "tpr",
            }
        )
    return write_csv(output_dir, "promo_calendar.csv", fieldnames, rows)


def generate_manifest(output_dir: Path, counts: dict[str, int]) -> None:
    manifest = {
        "version": "1.0",
        "generated_at": "2026-04-03T08:00:00",
        "source_system": "Mock Generator",
        "environment": "mock",
        "data_directory": "./",
        "files": {
            "vendor_master": {
                "filename": "vendor_master.csv",
                "row_count": counts["vendor_master"],
                "required": True,
            },
            "purchase_orders": {
                "filename": "purchase_orders.csv",
                "row_count": counts["purchase_orders"],
                "required": True,
            },
            "vendor_performance": {
                "filename": "vendor_performance.csv",
                "row_count": counts["vendor_performance"],
                "required": True,
            },
            "oos_events": {
                "filename": "oos_events.csv",
                "row_count": counts["oos_events"],
                "required": False,
            },
            "promo_calendar": {
                "filename": "promo_calendar.csv",
                "row_count": counts["promo_calendar"],
                "required": False,
            },
        },
    }

    filepath = output_dir / "manifest.yaml"
    with filepath.open("w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False)
    print(f"Generated {filepath}")


def generate_mock_data(output_dir: Path = DEFAULT_OUTPUT_DIR, vendor_count: int = 6) -> dict[str, int]:
    ensure_dir(output_dir)
    vendor_rows = build_vendor_master_rows(vendor_count)

    counts = {
        "vendor_master": generate_vendor_master(output_dir, vendor_rows),
        "purchase_orders": generate_purchase_orders(output_dir, vendor_rows),
        "vendor_performance": generate_vendor_performance(output_dir, vendor_rows),
        "oos_events": generate_oos_events(output_dir, vendor_rows),
        "promo_calendar": generate_promo_calendar(output_dir, vendor_rows),
    }
    generate_manifest(output_dir, counts)
    print("Mock data generation complete!")
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate mock landing-zone CSV files.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write mock files (default: data/inbound/mock)",
    )
    parser.add_argument(
        "--vendor-count",
        type=int,
        default=6,
        help="Number of fictional vendors to generate (default: 6)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_mock_data(output_dir=Path(args.output_dir), vendor_count=args.vendor_count)


if __name__ == "__main__":
    main()
